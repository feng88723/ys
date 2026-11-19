# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════
#                 "encrypt":0,"points":0,"trysee":0,
#                 "url":"\/upload\/vod_file\/...\/x.mp4?md5=...&expires=..."}</script>
#   RE_CREATED  : 2026-10-18
# ══════════════════════════════════════════════════════════════
#
#   getDependence / init / homeContent / homeVideoContent / categoryContent
#   / detailContent / searchContent / playerContent / localProxy
#   / isVideoFormat / manualVideoCheck / action / destroy

import concurrent.futures
import gzip
import html as _html
import json
import re
import threading
import time
import urllib.parse
import urllib.request

# ──────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
SITE = {
    "name": "X红颜",
    "protos": ("https", "http"),
    "host": "xhongyan.com",
    "cats": [("1", "onlyfans泄露影片"), ("2", "知名网黄自制"),
             ("3", "高清糖心vlog作品"), ("4", "国产业余自拍")],
    "sorts": [("time", "最新"), ("hits", "热门")],
    "per_page": 20,
    "list_ttl": 60,
    "detail_ttl": 300,
    "home_ttl": 120,
    "block_title": ["幼女", "未成年", "女童", "小学生", "中学生", "初中生",
                    "高中生", "萝莉", " Junior Idol"],
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

RE_CARD_START = re.compile(r'<div class="videoBox_wrap">')
RE_ITEM = re.compile(r'/index\.php/vod/(?:play|detail)/id/(\d+)/sid/(\d+)/nid/(\d+)\.html')
RE_PIC = re.compile(r'data-src="([^"]+)"')
RE_PIC_SRC = re.compile(r'<img[^>]+src="([^"]+)"')
RE_TITLE_ALT = re.compile(r'alt="([^"]{2,120})"')
RE_TITLE_SPAN = re.compile(r'<span class="title[^"]*">([^<]+)</span>')
RE_TITLE_ATTR = re.compile(r'\s+title="([^"]{2,120})"')
RE_PIC_DETAIL = re.compile(r'/upload/vod/[^\s"\'()>]+\.(?:png|jpg|jpeg|webp)', re.I)
RE_PLAY_LINK = re.compile(
    r'href="(/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"[^>]*>\s*([^<]{0,30}?)\s*<')
RE_PLAYER = re.compile(r'var\s+player_data\s*=\s*(\{.*?\})\s*</script>', re.S)
RE_THUMB = re.compile(r'class="[^"]*(?:thumb|poster|pic|img)[^"]*"[^>]*>\s*<img[^>]+src=["\']([^"\']+)', re.I | re.S)
RE_META_DESC = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', re.I)
RE_PAGE = re.compile(r'(?:type/id/\d+(?:/by/\w+)?)/page/(\d+)\.html')
RE_ANY_PAGE = re.compile(r'/page/(\d+)\.html')


def _to_int(v, default=1):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _clean(s):
    """去标签/空白/HTML 实体"""
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", str(s))
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _abs_url(u, base):
    """相对路径补全为绝对 URL"""
    if not u:
        return ""
    u = str(u).strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    return urllib.parse.urljoin(base, u)


def _blocked(name, kws=None):
    """标题黑名单命中判定(合规底线)"""
    txt = str(name or "")
    for k in (kws or SITE["block_title"]):
        if k and k in txt:
            return True
    return False


# ──────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        def init(self, extend=""):
            pass


class Spider(_BaseSpider):
    def __init__(self):
        self.ext = {}
        self.proto = SITE["protos"][0]
        self._cache = {}                    # url -> (body, at)
        self._cache_lock = threading.RLock()
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def getDependence(self):
        return ""

    def getName(self):
        return SITE["name"]

    def init(self, extend=""):
        cfg = {}
        try:
            if isinstance(extend, dict):
                cfg = extend
            elif extend:
                cfg = json.loads(extend)
                if not isinstance(cfg, dict):
                    cfg = {}
        except Exception:
            cfg = {}
        self.ext = cfg
        pr = str(cfg.get("proto") or "").strip().lower()
        if pr in ("http", "https"):
            self.proto = pr
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
        return ""

    def localProxy(self, param):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        text = str(url or "").lower()
        return bool(re.search(r"\.(?:m3u8|mp4|mkv|flv|avi|ts)(?:[?#]|$)", text))

    def manualVideoCheck(self):
        return False

    @property
    def base(self):
        return "%s://%s" % (self.proto, SITE["host"])

    def _raw(self, url, timeout=15):
        """单次请求:auto-accept gzip;返回 (text, err)"""
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
        """带缓存 + https/http 自愈降级"""
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

    def _cards(self, html):
        """切分 videoBox_wrap 卡片块,抽出 id/标题/封面/标签"""
        items = []
        starts = [m.start() for m in RE_CARD_START.finditer(html)]
        if not starts:
            return items
        bounds = starts + [len(html)]
        seen = set()
        for i in range(len(starts)):
            block = html[bounds[i]:bounds[i + 1]]
            if len(block) > 20000:
                block = block[:20000]
            href = RE_ITEM.search(block)
            if not href:
                continue
            vid, sid, nid = href.group(1), href.group(2), href.group(3)
            if vid in seen:
                continue
            pic = ""
            pm = RE_PIC.search(block)
            if pm and "lazyload" not in pm.group(1):
                pic = _abs_url(pm.group(1), self.base)
            if not pic:
                km = RE_PIC_DETAIL.search(block)
                if km:
                    pic = _abs_url(km.group(0), self.base)
            title = ""
            tm = RE_TITLE_ALT.search(block)
            if tm:
                title = _clean(tm.group(1))
            if not title:
                tm = RE_TITLE_SPAN.search(block)
                if tm:
                    title = _clean(tm.group(1))
            if not title:
                tm = RE_TITLE_ATTR.search(block)
                if tm:
                    title = _clean(tm.group(1))
            if not title:
                continue
            if _blocked(title):
                continue
            tag = ""
            kg = re.search(r'data-text="([^"]{1,20})"', block)
            if kg:
                tag = _clean(kg.group(1))
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": tag or "",
                "sid": sid,
                "nid": nid,
            })
        return items

    def _pagecount(self, html, cur, has_item):
        """从分页链接里取最大页码做 pagecount"""
        mx = 0
        for n in RE_PAGE.findall(html):
            mx = max(mx, _to_int(n, 0))
        if not mx:
            for n in RE_ANY_PAGE.findall(html):
                v = _to_int(n, 0)
                if v <= 500:
                    mx = max(mx, v)
        if not mx:
            mx = cur + 1 if has_item else cur
        return max(mx, cur)

    def _filters(self):
        """筛选维度(dict 形态,四壳要求必须是 dict)"""
        return {"排序": [{"n": n, "v": v} for v, n in SITE["sorts"]]}

    def _extend_of(self, extend):
        """壳回传的筛选值兼容多种形态:dict / JSON 字符串 / 裸值"""
        if isinstance(extend, str) and extend.strip():
            try:
                extend = json.loads(extend)
            except Exception:
                return {}
        return extend if isinstance(extend, dict) else {}

    def _sort_of(self, extend):
        ext = self._extend_of(extend)
        v = str(ext.get("排序") or ext.get("sort") or "").strip()
        if not v and isinstance(ext.get("filters"), dict):
            v = str(ext["filters"].get("排序") or ext["filters"].get("sort") or "").strip()
        for k, _n in SITE["sorts"]:
            if v == k or v == _n:
                return k
        return SITE["sorts"][0][0]

    def homeContent(self, *args):
        body, _ = self._fetch("/?t=%d" % int(time.time() // SITE["home_ttl"]), ttl=SITE["home_ttl"])
        items = self._cards(body)
        if not items:
            body, _ = self._fetch("/index.php/vod/type/id/%s/by/%s.html"
                                  % (SITE["cats"][0][0], SITE["sorts"][0][0]), ttl=SITE["home_ttl"])
            items = self._cards(body)
        cats = [{"type_id": t, "type_name": n} for t, n in SITE["cats"]]
        return {"class": cats, "filters": self._filters(), "list": items}

    def homeVideoContent(self, *args):
        return self.homeContent(*args)

    def categoryContent(self, tid, pg, filter, extend, *args):
        tid = str(tid or "").strip() or SITE["cats"][0][0]
        page = max(_to_int(pg, 1), 1)
        sort = self._sort_of(extend)
        path = "/index.php/vod/type/id/%s/by/%s" % (tid, sort)
        if page > 1:
            path += "/page/%d" % page
        body, _ = self._fetch(path + ".html", ttl=SITE["list_ttl"])
        items = self._cards(body)
        pc = self._pagecount(body, page, bool(items))
        return {
            "list": items,
            "page": page,
            "pagecount": pc,
            "limit": SITE["per_page"],
            "total": max(len(items) * pc, len(items)),
        }

    def _detail_one(self, vid):
        """单部影片:详情页含标题+封面+多线路播放链接,一次请求全拿到"""
        body, _ = self._fetch("/index.php/vod/detail/id/%s.html" % vid,
                              ttl=SITE["detail_ttl"])
        if not body:
            return None
        t = re.search(r"<title>([^<]*)</title>", body)
        name = _clean(t.group(1)) if t else ""
        if not name:
            return None
        name = (name.split("详情介绍")[0].split("在线观看")[0]
                    .split("迅雷下载")[0].strip())
        if " - " in name:
            name = name.split(" - ")[0].strip()
        if not name:
            return None
        if _blocked(name):
            return None
        pic = ""
        dm = RE_PIC.search(body)
        if dm:
            pic = _abs_url(dm.group(1), self.base)
        if not pic:
            km = RE_PIC_DETAIL.search(body)
            if km:
                pic = _abs_url(km.group(0), self.base)
        content = ""
        md = RE_META_DESC.search(body)
        if md:
            content = _clean(md.group(1))
        groups = {}
        for _u, vid2, sid, nid, label in RE_PLAY_LINK.findall(body):
            if vid2 != vid:
                continue
            groups.setdefault(sid, {})[int(nid)] = _clean(label)
        if not groups:
            groups = {"1": {1: "正片"}}
        froms, urls = [], []
        for sid in sorted(groups.keys(), key=lambda x: _to_int(x, 0)):
            eps = groups[sid]
            if not eps:
                continue
            parts = []
            for nid in sorted(eps.keys()):
                label = eps[nid] or ("第%d集" % nid)
                play_url = "%s/index.php/vod/play/id/%s/sid/%s/nid/%s.html" % (
                    self.base, vid, sid, nid)
                parts.append("%s$%s" % (label, play_url))
            if not parts:
                continue
            froms.append("线路%s" % sid)
            urls.append("#".join(parts))
        if not urls:
            return None
        return {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": content,
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }

    def detailContent(self, ids, *args):
        out = []
        raw = ids if isinstance(ids, (list, tuple)) else [ids]
        for i in raw:
            if i is None:
                continue
            vid = str(i).split("$")[-1].split("-")[0].strip()
            if not vid.isdigit():
                continue
            try:
                one = self._detail_one(vid)
            except Exception:
                one = None
            if one:
                out.append(one)
        return {"list": out, "page": 1, "pagecount": 1, "limit": len(out), "total": len(out)}

    def playerContent(self, flag, id, vipFlags, *args):
        neg = {"parse": 0, "jx": 0, "playUrl": "", "url": "",
               "header": {"User-Agent": UA}, "format": "video/mp4",
               "contentType": "video/mp4", "msg": ""}
        tok = str(id or "").split("$")[-1].strip()
        if tok.startswith("http"):
            play_url = tok
        else:
            m = re.match(r"^(\d+)-(\d+)-(\d+)$", tok)
            if m:
                vid, sid, nid = m.group(1), m.group(2), m.group(3)
            elif tok.isdigit():
                vid, sid, nid = tok, "1", "1"
            else:
                neg["msg"] = "地址无效"
                return neg
            play_url = "%s/index.php/vod/play/id/%s/sid/%s/nid/%s.html" % (
                self.base, vid, sid, nid)
        body, err = self._fetch(play_url, ttl=SITE["detail_ttl"])
        if not body:
            neg["msg"] = "取播放页失败:%s" % (err or "网络错误")[:60]
            return neg
        pm = RE_PLAYER.search(body)
        if not pm:
            neg["msg"] = "未找到播放器配置(页面结构变了?)"
            return neg
        try:
            conf = json.loads(pm.group(1))
        except Exception:
            neg["msg"] = "播放器配置解析失败"
            return neg
        url = str(conf.get("url") or "").strip()
        if not url:
            neg["msg"] = "播放器未返回地址(需会员?)"
            return neg
        if url.startswith("/"):
            url = self.base + url
        if "%" in url:
            try:
                url = urllib.parse.unquote(url)
            except Exception:
                pass
        if not url.startswith("http"):
            neg["msg"] = "播放地址形态异常"
            return neg
        low = url.split("?")[0].lower()
        if low.endswith(".mp4"):
            fmt = "video/mp4"
        elif low.endswith(".m3u8"):
            fmt = "application/vnd.apple.mpegurl"
        else:
            fmt = "video/mp4"
        return {
            "parse": 0, "jx": 0, "playUrl": "", "url": url,
            "header": {"User-Agent": UA, "Referer": self.base + "/"},
            "format": fmt, "contentType": fmt,
        }

    def searchContent(self, key, quick=False, pg=1, *args):
        kw = str(key or "").strip()
        page = max(_to_int(pg, 1), 1)
        empty = {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}
        if not kw:
            return empty
        path = "/index.php/vod/search/keyword/%s" % urllib.parse.quote(kw)
        if page > 1:
            path += "/page/%d" % page
        path += ".html"
        body, _ = self._fetch(path, ttl=SITE["list_ttl"])
        items = self._cards(body)
        pc = self._pagecount(body, page, bool(items))
        return {
            "list": items,
            "page": page,
            "pagecount": pc,
            "limit": SITE["per_page"],
            "total": max(len(items) * pc, len(items)),
        }

    def searchContentA(self, key, quick, pg=1, *args):
        return self.searchContent(key, quick, pg, *args)
