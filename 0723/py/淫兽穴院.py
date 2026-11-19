# -*- coding: utf-8 -*-
"""
淫兽穴院 四壳通用 Python Spider
站点: https://xn--0try42f.ysxysp.cfd/ (自建站, 直连无盾)
列表: ?class={id}  <a class="item_a" href="?detail={id}"><img original="封面"><span class="item_title">标题</span>
详情: ?detail={id}  内嵌HlsJsPlayer { "id": "showplayer", "url": "https://...m3u8" } 直链
搜索: /y.php?wd={kw}
"""
import re

try:
    from base.spider import Spider
except Exception:
    class Spider(object):
        def __init__(self):
            pass


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://xn--0try42f.ysxysp.cfd"
        self.rawSite = self.siteUrl
        self.HOST = self.siteUrl
        self.base = "/y.php"
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        self.ext = {}
        self.categories = [
            {"type_id": "1050", "type_name": "国产"},
            {"type_id": "1051", "type_name": "无码"},
            {"type_id": "1052", "type_name": "有码"},
            {"type_id": "1053", "type_name": "字幕"},
            {"type_id": "1054", "type_name": "欧美"},
            {"type_id": "1055", "type_name": "动漫"},
            {"type_id": "1056", "type_name": "伦理"},
        ]
        self.filter_dict = {}
        for c in self.categories:
            self.filter_dict[c["type_id"]] = []
        self._minor_re = re.compile(r"(\u841d\u8389|\u5e7c\u5973|\u5c11\u5973|\u7ae5\u989c|\u7ae5|\u521d\u4e2d|\u5c0f\u5b66|teen|loli|schoolgirl|\d{1,2}岁|\u672a\u6210\u5e74)", re.I)

    def getDependence(self):
        return ""

    def init(self, *args):
        extend = args[0] if args else None
        if not extend:
            return
        self.ext = extend
        if extend.get("siteUrl"):
            self.siteUrl = extend["siteUrl"].rstrip("/")
            self.HOST = self.siteUrl

    def homeContent(self, *args):
        result = {"class": self.categories, "filters": self.filter_dict, "list": []}
        try:
            html = self._fetch(self.siteUrl + self.base + "?class=1050")
            vod_list = self._parse_list(html)
            if vod_list:
                result["list"] = vod_list
        except Exception:
            pass
        return result

    def categoryContent(self, *args):
        tid = args[0] if args else "1050"
        pg = args[1] if len(args) > 1 else 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        url = f"{self.siteUrl}{self.base}?class={tid}"
        if pg > 1:
            url = f"{self.siteUrl}{self.base}?class={tid}&page={pg}"
        html = self._fetch(url)
        vod_list = self._parse_list(html)
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 20,
            "total": 9999,
            "list": vod_list,
        }

    def detailContent(self, *args):
        ids = args[0] if args else ""
        if isinstance(ids, (list, tuple)):
            ids = ids[0]
        ids = str(ids)
        m = re.search(r"detail=(\d+)", ids)
        vid = m.group(1) if m else ids
        url = f"{self.siteUrl}{self.base}?detail={vid}"
        try:
            html = self._fetch(url)
        except Exception:
            return {"list": []}
        vod = self._parse_detail(html, vid)
        return {"list": [vod]}

    def searchContent(self, *args):
        wd = args[0] if args else ""
        pg = args[1] if len(args) > 1 else 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        from urllib.parse import quote
        kw = quote(wd)
        url = f"{self.siteUrl}{self.base}?wd={kw}"
        try:
            html = self._fetch(url)
        except Exception:
            return {"list": []}
        vod_list = self._parse_list(html)
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 20,
            "total": 9999,
            "list": vod_list,
        }

    def playerContent(self, *args):
        flag = args[0] if args else ""
        pid = args[1] if len(args) > 1 else ""
        vip = args[2] if len(args) > 2 else ""
        url = pid
        if pid and "detail=" in pid:
            try:
                ph = self._fetch(pid if pid.startswith("http") else self.siteUrl + self.base + "?" + pid)
                mm = re.search(r'new HlsJsPlayer\(\s*\{\s*"id":\s*"showplayer",\s*"url":\s*"([^"]+)"', ph)
                if mm:
                    url = mm.group(1)
            except Exception:
                pass
        return {
            "parse": 0,
            "jx": 0,
            "url": url,
            "header": {
                "User-Agent": self.ua,
                "Referer": self.rawSite + "/",
            },
        }

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    # ---------- 内部方法 ----------

    def _is_minor(self, text):
        return bool(self._minor_re.search(text))

    def _fetch(self, url, timeout=12):
        hdrs = {
            "User-Agent": self.ua,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.rawSite + "/",
        }
        raw = ""
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(url, headers=hdrs, timeout=timeout, impersonate="chrome131", verify=False)
            if resp.status_code == 200:
                raw = resp.text
        except Exception:
            pass
        if not raw:
            try:
                import requests as req_lib
                resp = req_lib.get(url, headers=hdrs, timeout=timeout, verify=False)
                if resp.status_code == 200:
                    raw = resp.text
            except Exception:
                pass
        if not raw:
            import urllib.request
            import ssl
            req = urllib.request.Request(url, headers=hdrs)
            ctx = ssl.create_default_context()
            try:
                ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            except Exception:
                pass
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                resp = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout)
                body = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if enc == "gzip" or body[:2] == b"\x1f\x8b":
                    import gzip
                    body = gzip.decompress(body)
                raw = body.decode("utf-8", errors="ignore")
            except Exception:
                pass
        return raw

    def _parse_list(self, html):
        vod_list = []
        if not html:
            return vod_list
        items = re.findall(
            r'<a\s+class="item_a" href="\?detail=(\d+)"[^>]*>\s*<img[^>]*original="([^"]+)"[^>]*/?>\s*</a>\s*'
            r'<span class="item_title">\s*([^<]+)\s*</span>',
            html, re.S)
        for vid, pic, title in items:
            title = title.strip()
            if not title:
                continue
            if self._is_minor(title):
                continue
            if pic.startswith("/"):
                pic = self.siteUrl + pic
            vod_list.append({
                "vod_id": f"?detail={vid}",
                "vod_name": title[:80],
                "vod_pic": pic,
                "vod_remarks": "",
            })
            if len(vod_list) >= 20:
                break
        if not vod_list:
            dts = re.findall(r'href="\?detail=(\d+)"', html)
            for vid in dts:
                vod_list.append({"vod_id": f"?detail={vid}", "vod_name": "视频" + vid, "vod_pic": "", "vod_remarks": ""})
                if len(vod_list) >= 20:
                    break
        return vod_list

    def _parse_detail(self, html, vid):
        title = ""
        m2 = re.search(r'<title>(.*?)</title>', html, re.S)
        if m2:
            title = m2.group(1).strip()
        if not title:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if title:
            title = re.sub(r"\s+", " ", title).strip()[:80]
        vod_name = title if title else f"视频{vid}"
        mm = re.search(r'new HlsJsPlayer\(\s*\{\s*"id":\s*"showplayer",\s*"url":\s*"([^"]+)"', html)
        play_url = mm.group(1) if mm else ""
        return {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "m3u8",
            "vod_play_url": f"{vod_name}${play_url}" if play_url else "",
        }
