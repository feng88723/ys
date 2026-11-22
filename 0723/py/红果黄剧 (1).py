# -*- coding: utf-8 -*-
# 黄剧短剧 TVBox 四壳通用 Python 源（适配 5.8.5+ 规范）
# 站点：https://huangju.net/theater
# 数据后端：https://api.huangju.net
# 仅标准库；网络优先走宿主 self.fetch（需读 Set-Cookie 做 CloudFront 签名），无宿主时 urllib 兜底
import re
import json
import time
import gzip
import base64
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""):
            pass

# 未成年相关关键词（命中即跳过，不采集不展示）
_MINOR_KEYS = ["萝莉", "幼女", "未成年", "loli", "teen", "schoolgirl",
               "儿童", "幼童", "童贞", "少女", "正太", "初中生", "小学生"]

_CF_COOKIES = ("CloudFront-Policy", "CloudFront-Signature", "CloudFront-Key-Pair-Id")


class Spider(_BaseSpider):
    # ---------------- 基础配置 ----------------
    def getDependence(self):
        return ""

    def getName(self):
        return "黄剧短剧"

    def init(self, extend=""):
        self.HOST = "https://huangju.net"
        self.API = "https://api.huangju.net"
        self.UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Origin": self.HOST,
            "Referer": self.HOST + "/",
        }
        self._categories = None
        self._mem = {}
        try:
            self._load_categories()
        except Exception:
            self._categories = []

    # ---------------- 工具函数 ----------------
    def _is_minor(self, text):
        if not text:
            return False
        t = str(text).lower()
        for k in _MINOR_KEYS:
            if k.lower() in t:
                return True
        return False

    def _clean(self, v):
        if v is None:
            return ""
        return str(v).strip()

    def _cover(self, item):
        return item.get("coverUrl") or item.get("cover") or ""

    def _remarks(self, item):
        status = item.get("status")
        total = item.get("totalEpisodes")
        if total:
            return ("全%s集" % total) if status == "completed" else ("更新至%s集" % total)
        return ""

    def _vod(self, item):
        return {
            "vod_id": "%s-%s" % (item.get("slug", ""), item.get("id")),
            "vod_name": self._clean(item.get("title")),
            "vod_pic": self._cover(item),
            "vod_remarks": self._remarks(item),
        }

    def _cache_get(self, key):
        fn = getattr(self, "getCache", None)
        try:
            if callable(fn):
                v = fn(key)
                if v is not None:
                    return v
        except Exception:
            pass
        # 内置兜底缓存（宿主无 getCache 时也能生效）
        try:
            item = self._mem.get(key)
            if item and item[1] > time.time():
                return item[0]
            if item:
                self._mem.pop(key, None)
        except Exception:
            pass
        return None

    def _cache_set(self, key, value, ttl):
        fn = getattr(self, "setCache", None)
        try:
            if callable(fn):
                fn(key, value, ttl)
        except Exception:
            pass
        try:
            if value is None:
                self._mem.pop(key, None)
            else:
                self._mem[key] = (value, time.time() + float(ttl or 300))
        except Exception:
            pass

    # ---------------- HTTP（可读响应头） ----------------
    def _http(self, url, headers=None, cookie=None, timeout=10):
        """返回 (status, headers_lower_dict, body_bytes)；失败返回 (0, {}, b"")

        优先走宿主 HTTP（self.fetch），没有宿主时用 urllib 兜底。
        set-cookie 必须逐条保留，CloudFront 签名是三条分开下发的。
        """
        h = dict(self.headers)
        h.update(headers or {})
        if cookie:
            h["Cookie"] = cookie

        # 1) 宿主 requests 会话（能完整读响应头）
        fetch = getattr(self, "fetch", None)
        if callable(fetch):
            try:
                resp = fetch(url, headers=h, timeout=timeout, allow_redirects=True)
                hdrs = {}
                try:
                    raw_headers = resp.raw.headers
                    pairs = raw_headers.getlist("Set-Cookie") if hasattr(raw_headers, "getlist") else []
                except Exception:
                    pairs = []
                for k, v in resp.headers.items():
                    k = k.lower()
                    if k == "set-cookie":
                        continue
                    hdrs.setdefault(k, v)
                if pairs:
                    hdrs["set-cookie"] = "\n".join(pairs)
                elif resp.headers.get("set-cookie"):
                    hdrs["set-cookie"] = resp.headers.get("set-cookie")
                body = resp.content or b""
                enc = (hdrs.get("content-encoding") or "").lower()
                if enc == "gzip" and body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)
                return int(resp.status_code or 0), hdrs, body
            except Exception:
                pass

        # 2) urllib 兜底（无第三方依赖）
        try:
            req = urllib.request.Request(url, headers=h)
            resp = urllib.request.urlopen(req, timeout=timeout)
            status = resp.getcode()
            raw = resp.read()
            hdrs = {}
            for k, v in resp.headers.items():
                k = k.lower()
                if k == "set-cookie":
                    hdrs[k] = (hdrs[k] + "\n" + v) if k in hdrs else v
                else:
                    hdrs.setdefault(k, v)
            enc = (hdrs.get("content-encoding") or "").lower()
            if enc == "gzip" and raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return status, hdrs, raw
        except urllib.error.HTTPError as e:
            try:
                raw = e.read() or b""
            except Exception:
                raw = b""
            hdrs = {}
            for k, v in (e.headers or {}).items():
                k = k.lower()
                if k == "set-cookie":
                    hdrs[k] = (hdrs[k] + "\n" + v) if k in hdrs else v
                else:
                    hdrs.setdefault(k, v)
            return e.code, hdrs, raw
        except Exception:
            return 0, {}, b""

    def _json(self, path, params=None):
        url = self.API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        status, _, raw = self._http(url)
        if status != 200 or not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _json_list(self, path):
        url = self.API + path
        status, _, raw = self._http(url)
        if status != 200 or not raw:
            return []
        try:
            data = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            return []
        return data if isinstance(data, list) else []

    # ---------------- 分类 ----------------
    def _load_categories(self):
        data = self._json_list("/categories")
        result = []
        for c in data:
            if not isinstance(c, dict):
                continue
            slug = self._clean(c.get("slug"))
            name = self._clean(c.get("name"))
            if not slug or not name:
                continue
            try:
                count = int(c.get("dramaCount") or 0)
            except Exception:
                count = 0
            if len(slug) > 24 or "," in name or len(name) > 8 or count <= 0:
                continue
            if not re.search(r"[\u4e00-\u9fff]", name):
                continue
            if self._is_minor(name) or self._is_minor(slug):
                continue
            result.append({"type_id": slug, "type_name": name})
        seen = set()
        uniq = []
        for c in result:
            if c["type_id"] in seen:
                continue
            seen.add(c["type_id"])
            uniq.append(c)
        self._categories = uniq

    def homeContent(self, *args):
        try:
            if not self._categories:
                self._load_categories()
            filters = {}
            for c in self._categories:
                filters[c["type_id"]] = [
                    {
                        "key": "sort",
                        "name": "排序",
                        "init": "hot",
                        "value": [
                            {"n": "最热", "v": "hot"},
                            {"n": "最新", "v": "new"},
                        ],
                    }
                ]
            return {"class": self._categories, "filters": filters}
        except Exception:
            return {"class": [], "filters": {}}

    def homeVideoContent(self, *args):
        try:
            data = self._json("/dramas", {"sort": "hot", "page": 1})
            return self._parse_page(data, 1)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    # ---------------- 分类分页 ----------------
    def _extend(self, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v.strip():
            try:
                d = json.loads(v)
                return d if isinstance(d, dict) else {}
            except Exception:
                return {}
        return {}

    def categoryContent(self, *args):
        try:
            tid = str(args[0]) if len(args) > 0 else ""
            pg = 1
            if len(args) > 1:
                try:
                    pg = max(1, int(args[1]))
                except Exception:
                    pg = 1
            extend = self._extend(args[3]) if len(args) > 3 else {}
            sort = self._clean(extend.get("sort")) or "hot"
            params = {"category": tid, "page": pg, "sort": sort}
            data = self._json("/dramas", params)
            return self._parse_page(data, pg)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    def _parse_page(self, data, pg):
        items = data.get("items") or []
        try:
            total = int(data.get("total") or 0)
        except Exception:
            total = 0
        try:
            size = int(data.get("pageSize") or len(items) or 20)
        except Exception:
            size = len(items) or 20
        pagecount = int(total // size) + (1 if total % size else 0) if size else 1
        pagecount = max(pagecount, 1)
        # 服务端会把越界页夹到末页，以它返回的 page 为准，避免壳子翻页错位
        try:
            cur = int(data.get("page") or 0)
        except Exception:
            cur = 0
        if cur <= 0:
            cur = pg
        cur = min(max(cur, 1), pagecount)
        lst = [self._vod(x) for x in items if isinstance(x, dict) and not self._is_minor(x.get("title"))]
        return {"page": cur, "pagecount": pagecount, "limit": size, "total": total, "list": lst}

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        try:
            if isinstance(ids, str):
                ids = [x for x in re.split(r"[,&]", ids) if x]
            vod_list = []
            for vid in (ids or []):
                vid = str(vid).strip()
                if not vid:
                    continue
                data = self._json("/dramas/" + urllib.parse.quote(vid, safe="-"))
                if not data or data.get("id") is None:
                    # 兜底：纯数字 id 时接口不认，用 "-{id}" 形式可直达
                    if vid.isdigit():
                        data = self._json("/dramas/-" + vid)
                if not data or data.get("id") is None:
                    continue
                episodes = data.get("episodes") or []
                play_parts = []
                for ep in episodes:
                    if not isinstance(ep, dict) or not ep.get("playable", True):
                        continue
                    ep_id = ep.get("id")
                    if ep_id is None:
                        continue
                    ep_name = self._clean(ep.get("title")) or ("第%s集" % ep.get("epNo"))
                    play_parts.append("%s$%s" % (ep_name, ep_id))
                if not play_parts:
                    continue
                vod = {
                    "vod_id": "%s-%s" % (data.get("slug", ""), data.get("id")),
                    "vod_name": self._clean(data.get("title")),
                    "vod_pic": self._cover(data),
                    "vod_remarks": self._remarks(data),
                    "vod_year": self._clean(data.get("year")),
                    "vod_area": self._clean(data.get("region")),
                    "vod_content": self._clean(data.get("description") or data.get("seoDescription")),
                    "vod_play_from": "黄剧",
                    "vod_play_url": "#".join(play_parts),
                }
                if not self._is_minor(vod["vod_name"]):
                    vod_list.append(vod)
            return {"list": vod_list}
        except Exception:
            return {"list": []}

    # ---------------- 搜索 ----------------
    def searchContent(self, *args):
        try:
            key = str(args[0]) if len(args) > 0 else ""
            pg = 1
            for a in args[1:]:
                if isinstance(a, bool):
                    continue
                if isinstance(a, int):
                    pg = max(1, a)
                    break
                if isinstance(a, str) and a.isdigit():
                    pg = max(1, int(a))
                    break
            data = self._json("/dramas", {"q": key, "page": pg})
            return self._parse_page(data, pg)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    # ---------------- 播放 ----------------
    def _proxy_base(self):
        fn = getattr(self, "getProxyUrl", None)
        try:
            base = fn() if callable(fn) else ""
        except Exception:
            base = ""
        if not base:
            base = "http://127.0.0.1:9978/proxy?do=py"
        return base

    def _play_signed(self, ep_id):
        """取播放地址并抓取 CloudFront 签名 Cookie。返回 (m3u8_url, cookie_str)

        注意：签名 Cookie 是 /play 接口本身下发的（不是视频域），所以必须直读响应头。
        """
        cached = self._cache_get("cf:%s" % ep_id)
        if isinstance(cached, dict) and cached.get("u") and cached.get("c") \
                and cached.get("e", 0) > time.time():
            return cached["u"], cached["c"]

        api_url = self.API + "/play/" + urllib.parse.quote(str(ep_id), safe="")
        status, hdrs, raw = self._http(api_url, timeout=10)
        if status != 200 or not raw:
            return "", ""
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except Exception:
            return "", ""
        if not isinstance(data, dict):
            return "", ""
        url = self._clean(data.get("url"))
        if not url:
            return "", ""

        sc = hdrs.get("set-cookie") or ""
        pairs = re.findall(r"(CloudFront-[A-Za-z-]+)=([^;,\s]+)", sc)
        ck = {}
        for k, v in pairs:
            if k in _CF_COOKIES:
                ck[k] = v
        if not ck:
            # 没拿到签名，直连必然 403，但仍返回地址让上层能报错
            return url, ""
        cookie = "; ".join("%s=%s" % (k, ck[k]) for k in _CF_COOKIES if k in ck)

        # 缓存到签名过期（expiresAt 是秒级时间戳，兜底 6 小时）
        ttl = 21600
        try:
            exp = int(data.get("expiresAt") or 0)
            if exp > time.time():
                ttl = max(60, min(21600, exp - time.time() - 60))
        except Exception:
            pass
        self._cache_set("cf:%s" % ep_id, {"u": url, "c": cookie, "e": time.time() + ttl}, ttl)
        return url, cookie

    def _get_cookie(self, ep_id):
        cached = self._cache_get("cf:%s" % ep_id)
        if isinstance(cached, dict) and cached.get("c") and cached.get("e", 0) > time.time():
            return cached["c"]
        _, cookie = self._play_signed(ep_id)
        return cookie


    def _proxy_url(self, **params):
        q = urllib.parse.urlencode(params)
        base = self._proxy_base()
        return base + ("&" if "?" in base else "?") + q

    def _rewrite_m3u8(self, body, base_url, ep_id):
        out = []
        base_dir = base_url.rsplit("/", 1)[0] + "/"
        for line in body.splitlines():
            s = line.strip()
            if not s:
                out.append(line)
                continue
            if s.startswith("#"):
                # 处理 #EXT-X-KEY / #EXT-X-MAP 里的 URI="..."
                def _sub(m):
                    u = m.group(2)
                    au = urllib.parse.urljoin(base_dir, u)
                    enc = base64.urlsafe_b64encode(au.encode()).decode().rstrip("=")
                    return m.group(1) + self._proxy_url(type="seg", eid=ep_id, u=enc) + m.group(3)
                out.append(re.sub(r'(URI=")([^"]+)(")', _sub, s))
                continue
            au = urllib.parse.urljoin(base_dir, s)
            enc = base64.urlsafe_b64encode(au.encode()).decode().rstrip("=")
            if au.split("?")[0].endswith(".m3u8"):
                out.append(self._proxy_url(type="play", eid=ep_id, u=enc))
            else:
                out.append(self._proxy_url(type="seg", eid=ep_id, u=enc))
        return "\n".join(out) + "\n"

    def playerContent(self, *args):
        try:
            ep_id = str(args[1]) if len(args) > 1 else ""
            if not ep_id:
                return {"parse": 0, "jx": 0, "url": "", "header": {"User-Agent": self.UA},
                        "format": "application/x-mpegURL"}
            url = self._proxy_url(type="play", eid=ep_id)
            header = {"User-Agent": self.UA, "Referer": self.HOST + "/"}
            return {"parse": 0, "jx": 0, "url": url, "header": header,
                    "format": "application/x-mpegURL"}
        except Exception:
            return {"parse": 0, "jx": 0, "url": "", "header": {"User-Agent": self.UA},
                    "format": "application/x-mpegURL"}

    # ---------------- 本地代理 ----------------
    def localProxy(self, params=None):
        p = params or {}
        typ = str(p.get("type") or "")
        eid = str(p.get("eid") or "")
        raw_u = str(p.get("u") or "")
        if not typ or not eid:
            return [404, "text/plain", "bad request"]
        try:
            if raw_u:
                raw_u += "=" * (-len(raw_u) % 4)
                target = base64.urlsafe_b64decode(raw_u.encode()).decode("utf-8")
            else:
                target = ""
        except Exception:
            return [400, "text/plain", "bad url"]

        url, cookie = self._play_signed(eid)
        if not url:
            return [502, "text/plain", "no play url"]
        if not target:
            target = url
        elif not target.startswith("http"):
            target = urllib.parse.urljoin(url.rsplit("/", 1)[0] + "/", target)

        status, hdrs, body = self._http(target, {"Accept": "*/*", "Referer": self.HOST + "/"}, cookie)
        if status != 200 or not body:
            # Cookie 可能过期，强制刷新一次
            self._cache_set("cf:%s" % eid, None, 0)
            _, cookie2 = self._play_signed(eid)
            if cookie2 and cookie2 != cookie:
                status, hdrs, body = self._http(target, {"Accept": "*/*", "Referer": self.HOST + "/"}, cookie2)
        if status != 200 or not body:
            return [status or 502, "text/plain", "upstream error"]

        ctype = hdrs.get("content-type") or ""
        is_m3u8 = ("mpegurl" in ctype.lower()) or body[:7] == b"#EXTM3U"
        if is_m3u8:
            text = body.decode("utf-8", "ignore")
            text = self._rewrite_m3u8(text, target, eid)
            return [200, "application/vnd.apple.mpegurl", text]
        if not ctype:
            ctype = "video/mp2t" if target.split("?")[0].endswith(".ts") else "application/octet-stream"
        return [200, ctype, body]

    # ---------------- 其余标准接口 ----------------
    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower().split("?")[0]
        return u.endswith(".m3u8") or u.endswith(".mp4") or u.endswith(".ts")

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return {}

    def destroy(self):
        pass
