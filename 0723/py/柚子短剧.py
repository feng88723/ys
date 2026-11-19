# -*- coding: utf-8 -*-
# RE_PATH: Next.js custom SPA (not AppleCMS). /api/catalogue/browse and /api/catalogue/search
#          return HTML card fragments (data-total / data-pages). Detail = season page with
#          <a class="series-episode-link" href=".../season-1-episode-N/"> grid.
# RE_OBSTACLE: free guest account (eden_account from /api/account/bootstrap) + per-episode
#          playback credential cookie (eden_play_* from POST /api/playback/{id}?mode=mse).
#          HLS master.m3u8 requires these cookies -> resolved through localProxy on the client.
# youzidj.com TVBox source (youzi short-drama)
# pipeline: episode page -> data-video + contentUrl -> bootstrap -> playback -> m3u8 -> localProxy(HLS)

import concurrent.futures
import gzip
import json
import re
import threading
import time
import urllib.parse
import urllib.request
import urllib.error

SITE = {
    "name": "柚子短剧",
    "host": "youzidj.com",
    "proto": "https",
    "cats": [("campus", "校园"), ("costume", "古装"), ("cultivation", "修仙"),
             ("family-ethics", "家庭伦理"), ("martial-arts", "武侠"),
             ("urban", "都市"), ("wealthy-family", "豪门")],
    "per_page": 24,
    "list_ttl": 120,
    "detail_ttl": 600,
    "home_ttl": 300,
    "block_title": ["幼女", "未成年", "女童", "小学生", "中学生", "初中生",
                    "高中生", "萝莉", "loli", "jailbait", "underage"],
}

PROXY_BASE = "http://" + "127.0.0.1" + ":%d/proxy" % 9978

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

CARD_ANCHOR = re.compile(r'<a class="home-drama-card-link"')
RE_CARD_BLOCK = re.compile(r'<article[^>]*class="drama-card')
RE_HREF = re.compile(r'href="(/dramas/[^"/]+/season-1/)"')
RE_TITLE = re.compile(r'class="drama-card-title"[^>]*>([^<]+)</p>')
RE_TITLE_ALT = re.compile(r'aria-label="查看详情：([^"]+?)(?: · 第1季)?"')
RE_COVER = re.compile(r'catalogue-art/([a-z0-9-]+)-960\.webp')
RE_REMARKS = re.compile(r'home-card-episodes-long">([^<]+)<')
RE_SEASON_PAGE = re.compile(r'<a\b[^>]*class="series-episode-link"[^>]*href="((?:https?://[^"/]+)?/dramas/[^"]*?season-1-episode-\d+/)"')
RE_EPI_ALABEL = re.compile(r'aria-label="第\s*(\d+)\s*集\s*([^"]*)"')
RE_EPI_TITLE = re.compile(r'title="([^"]*)"')
RE_EPI_PAID = re.compile(r'data-paid="([^"]*)"')
RE_SEASON_COVER = re.compile(r'catalogue-art/([a-z0-9-]+)-960\.webp')
RE_EPI_VIDEO = re.compile(r'data-video="([a-z0-9-]+)"')
RE_CONTENT_URL = re.compile(r'contentUrl"\s*:\s*"(https://youzidj\.com/media/[a-z0-9-]+/[a-z0-9-]+/master\.m3u8)"')
RE_TOTAL = re.compile(r'data-total="(\d+)"')
RE_PAGES = re.compile(r'data-pages="(\d+)"')
RE_NAME_TITLE = re.compile(r'<title>([^<]*)</title>')


def _to_int(v, default=1):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _clean(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", str(s))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _blocked(name, kws=None):
    txt = str(name or "").lower()
    for k in (kws or SITE["block_title"]):
        if k and k.lower() in txt:
            return True
    return False


try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        def init(self, extend=""):
            pass


class Spider(_BaseSpider):
    def __init__(self):
        self.ext = {}
        self.proto = SITE["proto"]
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._youzi_cache = {}
        self._youzi_lock = threading.RLock()
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def getDependence(self):
        return ""

    def getName(self):
        return SITE["name"]

    def init(self, extend=""):
        return ""

    def getCategory(self):
        return ""

    def getFilter(self):
        return {}

    def action(self, action):
        return ""

    def destroy(self):
        with self._cache_lock:
            self._cache.clear()
        with self._youzi_lock:
            self._youzi_cache.clear()
        return ""

    def localProxy(self, param):
        try:
            q = urllib.parse.urlparse(str(param))
            qs = urllib.parse.parse_qs(q.query)
            target = (qs.get("url") or [""])[0]
            if not target:
                return [404, "text/plain", "missing url"]
            m = re.search(r"/media/([a-z0-9-]+)/", target)
            video = m.group(1) if m else None
            cookies, referer = self._youzi_tokens(video, target, force=False)
            if not cookies:
                return [403, "text/plain", "auth failed"]
            status, ctype, content = self._youzi_fetch(target, cookies, referer)
            if status == 403:
                cookies, referer = self._youzi_tokens(video, target, force=True)
                if cookies:
                    status, ctype, content = self._youzi_fetch(target, cookies, referer)
            if status != 200 or not content:
                msg = content[:160] if isinstance(content, bytes) else str(content)[:160]
                return [status or 502, "text/plain", msg]
            low = target.lower()
            head = content[:7].lower() if isinstance(content, bytes) else content[:7].lower()
            is_playlist = low.endswith(".m3u8") or head == "#extm3u"
            if is_playlist:
                text = content.decode("utf-8", "ignore") if isinstance(content, bytes) else content
                base_dir = target.rsplit("/", 1)[0] + "/"
                out = []
                for line in text.splitlines():
                    ls = line.strip()
                    if ls and not ls.startswith("#"):
                        abs_u = urllib.parse.urljoin(base_dir, ls)
                        out.append(PROXY_BASE + "?do=youzi&url=" + urllib.parse.quote(abs_u, safe=""))
                    else:
                        out.append(line)
                return [200, "application/vnd.apple.mpegurl", ("\n".join(out)).encode("utf-8")]
            return [200, ctype or "application/octet-stream", content]
        except Exception as e:
            return [500, "text/plain", str(e)[:160]]

    def isVideoFormat(self, url):
        text = str(url or "").lower()
        return bool(re.search(r"\.(?:m3u8|mp4|mkv|flv|avi|ts|m4s)(?:[?#]|$)", text))

    def manualVideoCheck(self):
        return False

    @property
    def base(self):
        return "%s://%s" % (self.proto, SITE["host"])

    def _raw(self, url, timeout=15):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.base + "/",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                enc = "utf-8"
                ct = (r.headers.get("Content-Type") or "").lower()
                m = re.search(r"charset=([\w-]+)", ct)
                if m:
                    enc = m.group(1)
                return raw.decode(enc, "ignore"), ""
        except Exception as e:
            return "", str(e)

    def _fetch(self, path, ttl=0, timeout=15):
        key = str(path)
        if ttl > 0:
            with self._cache_lock:
                hit = self._cache.get(key)
                if hit and (time.time() - hit[1]) < ttl and hit[0]:
                    return hit[0], ""
        url = path if path.startswith("http") else self.base + path
        body, err = self._raw(url, timeout)
        if (not body) and url.startswith("https://"):
            alt = "http://" + url[len("https://"):]
            body, err = self._raw(alt, timeout)
            if body:
                self.proto = "http"
        if ttl > 0 and body:
            with self._cache_lock:
                self._cache[key] = (body, time.time())
        return body, err

    def _merge_cookie(self, cookies, header):
        if not header:
            return
        first = header.split(";", 1)[0].strip()
        if "=" in first:
            k, v = first.split("=", 1)
            cookies[k.strip()] = v.strip()

    def _yreq(self, url, cookies, referer, method="GET", data=None, timeout=20):
        headers = {
            "User-Agent": UA,
            "Referer": referer,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if cookies:
            headers["Cookie"] = "; ".join("%s=%s" % (k, v) for k, v in cookies.items())
        if method == "POST":
            headers["X-Requested-With"] = "XMLHttpRequest"
            headers["Origin"] = "https://youzidj.com"
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                for sc in (r.headers.get_all("Set-Cookie") or []):
                    self._merge_cookie(cookies, sc)
                return r.status, (r.headers.get("Content-Type") or "").lower(), raw
        except urllib.error.HTTPError as e:
            try:
                for sc in (e.headers.get_all("Set-Cookie") or []):
                    self._merge_cookie(cookies, sc)
            except Exception:
                pass
            return e.code, "", b""
        except Exception:
            return 0, "", b""

    def _youzi_auth(self, ep_url, data_video, referer, max_retry=3):
        cookies = {}
        delay = 1.0
        for _ in range(max_retry):
            self._yreq("https://youzidj.com/api/account/bootstrap", cookies, referer, "POST", b"{}")
            _st, _ct, pb = self._yreq(
                "https://youzidj.com/api/playback/%s?mode=mse" % data_video, cookies, referer, "POST", b"{}")
            if cookies:
                expires = 0
                try:
                    expires = int(json.loads(pb.decode("utf-8", "ignore")).get("expires_at", 0))
                except Exception:
                    pass
                return cookies, expires
            if _st == 503:
                time.sleep(min(delay, 15))
                delay *= 2
            else:
                break
        return {}, 0

    def _youzi_tokens(self, video, target, force=False):
        with self._youzi_lock:
            c = self._youzi_cache.get(video) if video else None
            if c and not force and (c["expires"] - time.time() > 90):
                return dict(c["cookies"]), c["referer"]
        c = self._youzi_cache.get(video) if video else None
        if not c:
            return {}, target
        ep_url, data_video, referer = c["ep_url"], c["data_video"], c["referer"]
        cookies, expires = self._youzi_auth(ep_url, data_video, referer)
        with self._youzi_lock:
            self._youzi_cache[video] = {
                "cookies": cookies, "referer": referer, "ep_url": ep_url,
                "data_video": data_video, "expires": expires}
        return dict(cookies), referer

    def _youzi_fetch(self, target, cookies, referer, timeout=20):
        return self._yreq(target, dict(cookies), referer, "GET", None, timeout)

    def _cards(self, html):
        items = []
        starts = [m.start() for m in RE_CARD_BLOCK.finditer(html)]
        if not starts:
            starts = [m.start() for m in CARD_ANCHOR.finditer(html)]
        if not starts:
            return items
        bounds = starts + [len(html)]
        seen = set()
        for i in range(len(starts)):
            block = html[bounds[i]:bounds[i + 1]]
            if len(block) > 20000:
                block = block[:20000]
            hm = RE_HREF.search(block)
            if not hm:
                continue
            slug = hm.group(1)
            if slug in seen:
                continue
            seen.add(slug)
            tm = RE_TITLE.search(block)
            title = _clean(tm.group(1)) if tm else ""
            if not title:
                am = RE_TITLE_ALT.search(block)
                title = _clean(am.group(1)) if am else ""
            title = re.sub(r"\s*·\s*第\d+季\s*$", "", title).strip()
            if not title:
                continue
            if _blocked(title):
                continue
            cm = RE_COVER.search(block)
            pic = self.base + "/catalogue-art/" + cm.group(1) + "-960.webp" if cm else ""
            rm = RE_REMARKS.search(block)
            remarks = _clean(rm.group(1)) if rm else ""
            items.append({
                "vod_id": slug,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
        return items

    def _pageinfo(self, html, page):
        tp = RE_TOTAL.search(html)
        pp = RE_PAGES.search(html)
        total = _to_int(tp.group(1), 0) if tp else 0
        pc = _to_int(pp.group(1), 0) if pp else 0
        if not pc:
            pc = page + (1 if total > 0 else 0)
        if not total:
            total = max(len(self._cards(html)) * pc, len(self._cards(html)))
        return pc, total

    def _filters(self):
        return {}

    def homeContent(self, *args):
        body, _ = self._fetch("/api/catalogue/browse?page=1", ttl=SITE["home_ttl"])
        items = self._cards(body)
        cats = [{"type_id": t, "type_name": n} for t, n in SITE["cats"]]
        return {"class": cats, "filters": self._filters(), "list": items}

    def homeVideoContent(self, *args):
        return self.homeContent(*args)

    def categoryContent(self, tid, pg, filter, extend, *args):
        tid = str(tid or "").strip()
        page = max(_to_int(pg, 1), 1)
        known = {t for t, _ in SITE["cats"]}
        if tid in known:
            path = "/api/catalogue/browse?category=%s&page=%d" % (tid, page)
        else:
            path = "/api/catalogue/browse?page=%d" % page
        body, _ = self._fetch(path, ttl=SITE["list_ttl"])
        items = self._cards(body)
        pc, total = self._pageinfo(body, page)
        return {
            "list": items, "page": page, "pagecount": pc,
            "limit": SITE["per_page"], "total": total,
        }

    def _detail_one(self, path):
        body, _ = self._fetch(path, ttl=SITE["detail_ttl"])
        if not body:
            return None
        name = ""
        sm = re.search(r'class="drama-card-title"[^>]*>([^<]+)</p>', body)
        if not sm:
            sm = re.search(r'<h1[^>]*>([^<]+)</h1>', body)
        if sm:
            name = _clean(sm.group(1))
        if not name:
            t = RE_NAME_TITLE.search(body)
            name = _clean(t.group(1)) if t else ""
        name = re.sub(r"\|.*$", "", name).strip()
        name = re.sub(r"\s*·\s*第\d+季\s*$", "", name).strip()
        if not name:
            return None
        if _blocked(name):
            return None
        pic = ""
        cm = RE_SEASON_COVER.search(body)
        if cm:
            pic = self.base + "/catalogue-art/" + cm.group(1) + "-960.webp"
        eps = []
        seen_ep = set()
        for em in RE_SEASON_PAGE.finditer(body):
            href = em.group(1)
            if href in seen_ep:
                continue
            seen_ep.add(href)
            if href.startswith("http"):
                ep_url = href
            else:
                ep_url = self.base + href
            blk = body[em.start():em.start() + 800]
            am = RE_EPI_ALABEL.search(blk)
            if am:
                num = am.group(1)
                etitle = _clean(am.group(2))
            else:
                tm = RE_EPI_TITLE.search(blk)
                etitle = _clean(tm.group(1)) if tm else ""
                nm = re.search(r'episode-(\d+)', href)
                num = nm.group(1) if nm else "0"
            paid = RE_EPI_PAID.search(blk)
            if paid and paid.group(1) == "true":
                continue
            label = "第%s集" % num
            if etitle:
                label += " " + etitle
            eps.append((int(num) if num.isdigit() else 0, label, ep_url))
        if not eps:
            return None
        eps.sort(key=lambda x: x[0])
        parts = ["%s$%s" % (e[1], e[2]) for e in eps]
        return {
            "vod_id": path,
            "vod_name": name,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "柚子短剧",
            "vod_play_url": "#".join(parts),
        }

    def detailContent(self, ids, *args):
        out = []
        raw = ids if isinstance(ids, (list, tuple)) else [ids]
        for i in raw:
            if not i:
                continue
            pid = str(i).split("$")[-1].strip()
            if not pid.startswith("http") and not pid.startswith("/"):
                pid = "/dramas/%s/season-1/" % pid
            try:
                one = self._detail_one(pid)
            except Exception:
                one = None
            if one:
                out.append(one)
        return {"list": out, "page": 1, "pagecount": 1, "limit": len(out), "total": len(out)}

    def playerContent(self, flag, id, vipFlags, *args):
        ep_url = str(id or "").strip()
        if ep_url.startswith("//"):
            ep_url = "https:" + ep_url
        if not ep_url.startswith("http"):
            ep_url = self.base + (ep_url if ep_url.startswith("/") else "/" + ep_url)
        body, err = self._fetch(ep_url, ttl=SITE["detail_ttl"])
        if not body:
            return {"parse": 0, "jx": 0, "url": "", "playUrl": "",
                    "header": {"User-Agent": UA}, "format": "", "contentType": "",
                    "msg": "episode page fail:%s" % (err or "")[:60]}
        vm = RE_EPI_VIDEO.search(body)
        if not vm:
            return {"parse": 0, "jx": 0, "url": "", "playUrl": "",
                    "header": {"User-Agent": UA}, "format": "", "contentType": "",
                    "msg": "no data-video on episode page"}
        data_video = vm.group(1)
        cm = RE_CONTENT_URL.search(body)
        if not cm:
            return {"parse": 0, "jx": 0, "url": "", "playUrl": "",
                    "header": {"User-Agent": UA}, "format": "", "contentType": "",
                    "msg": "no contentUrl on episode page"}
        content_url = cm.group(1)
        cookies, expires = self._youzi_auth(ep_url, data_video, ep_url)
        if not cookies:
            return {"parse": 0, "jx": 0, "url": "", "playUrl": "",
                    "header": {"User-Agent": UA}, "format": "", "contentType": "",
                    "msg": "guest auth failed"}
        with self._youzi_lock:
            self._youzi_cache[data_video] = {
                "cookies": cookies, "referer": ep_url, "ep_url": ep_url,
                "data_video": data_video, "expires": expires}
        proxy_url = (PROXY_BASE + "?do=youzi&url="
                     + urllib.parse.quote(content_url, safe="") + "&_=1")
        return {
            "parse": 0, "jx": 0, "url": proxy_url, "playUrl": "",
            "header": {"User-Agent": UA},
            "format": "application/vnd.apple.mpegurl",
            "contentType": "application/vnd.apple.mpegurl", "msg": "",
        }

    def searchContent(self, key, quick=False, pg=1, *args):
        kw = str(key or "").strip()
        page = max(_to_int(pg, 1), 1)
        empty = {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}
        if not kw:
            return empty
        path = "/api/catalogue/search?q=%s&page=%d" % (urllib.parse.quote(kw), page)
        body, _ = self._fetch(path, ttl=SITE["list_ttl"])
        items = self._cards(body)
        pc, total = self._pageinfo(body, page)
        return {"list": items, "page": page, "pagecount": pc,
                "limit": SITE["per_page"], "total": total}

    def searchContentA(self, key, quick, pg=1, *args):
        return self.searchContent(key, quick, pg, *args)
