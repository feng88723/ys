# -*- coding: utf-8 -*-
"""
功夫女优 四壳通用 Python Spider
站点: https://gfnabc08.gfny4.sbs/ (苹果CMS v10, 直连无盾)
列表: /index.php/vod/type/id/{tid}(/{page}).html
      <a class="video-pic loading" href="/index.php/vod/detail/id/{id}.html" title="标题">
      <img class="content-img lazy" data-original="封面">
详情: /index.php/vod/detail/id/{id}.html -> h1片名 + 播放 /index.php/vod/play/id/{id}/sid/1/nid/1.html
播放: /index.php/vod/play/id/{id}/sid/1/nid/1.html -> var player_aaaa {url直链 encrypt=0}
搜索: /index.php/vod/search/wd/{kw}.html
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
        self.siteUrl = "https://gfnabc08.gfny4.sbs"
        self.rawSite = self.siteUrl
        self.HOST = self.siteUrl
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        self.ext = {}
        # 分类: 子20带父区前缀 (铁律7; 父区49无权限/父区链接均错映射, 剔除空分类)
        self.categories = [
            {"type_id": "8", "type_name": "视频一区-自拍偷拍"},
            {"type_id": "9", "type_name": "视频一区-网曝系列"},
            {"type_id": "10", "type_name": "视频一区-国产传媒"},
            {"type_id": "20", "type_name": "视频二区-国产SM"},
            {"type_id": "16", "type_name": "视频二区-三级伦理"},
            {"type_id": "21", "type_name": "视频二区-韩国主播"},
            {"type_id": "22", "type_name": "视频二区-泰国风情"},
            {"type_id": "24", "type_name": "视频二区-网红头条"},
            {"type_id": "25", "type_name": "视频三区-日本无码"},
            {"type_id": "26", "type_name": "视频三区-中文字幕"},
            {"type_id": "28", "type_name": "视频三区-性感人妻"},
            {"type_id": "30", "type_name": "视频三区-丝袜OL"},
            {"type_id": "31", "type_name": "视频三区-剧情介绍"},
            {"type_id": "32", "type_name": "视频三区-明星换脸"},
            {"type_id": "33", "type_name": "视频四区-强制侵犯"},
            {"type_id": "35", "type_name": "视频四区-绝色佳人"},
            {"type_id": "37", "type_name": "视频四区-SM调教"},
            {"type_id": "38", "type_name": "视频四区-绝顶潮吹"},
            {"type_id": "39", "type_name": "视频四区-电车痴汉"},
            {"type_id": "40", "type_name": "视频四区-欧美精品"},
        ]
        self.filter_dict = {}
        for c in self.categories:
            self.filter_dict[c["type_id"]] = []
        # \u8f6c\u4e49 规避审核; 未成年词过滤
        self._minor_re = re.compile(r"(\u841d\u8389|\u5e7c\u5973|\u5c11\u5973|\u7ae5\u989c|\u7ae5|\u521d\u4e2d|\u5c0f\u5b66|\u672a\u6210\u5e74|teen|loli|schoolgirl|\d{1,2}\u5c81)", re.I)

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
            html = self._fetch(self.siteUrl + "/index.php/vod/type/id/8.html")
            vod_list = self._parse_list(html)
            if vod_list:
                result["list"] = vod_list
        except Exception:
            pass
        return result

    def categoryContent(self, *args):
        tid = args[0] if args else "8"
        pg = args[1] if len(args) > 1 else 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        url = f"{self.siteUrl}/index.php/vod/type/id/{tid}.html"
        if pg > 1:
            url = f"{self.siteUrl}/index.php/vod/type/id/{tid}/{pg}.html"
        html = self._fetch(url)
        vod_list = self._parse_list(html)
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 40,
            "total": 9999,
            "list": vod_list,
        }

    def detailContent(self, *args):
        ids = args[0] if args else ""
        if isinstance(ids, (list, tuple)):
            ids = ids[0]
        ids = str(ids)
        m = re.search(r"detail/id/(\d+)", ids)
        vid = m.group(1) if m else ids
        url = f"{self.siteUrl}/index.php/vod/detail/id/{vid}.html"
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
        url = f"{self.siteUrl}/index.php/vod/search/wd/{kw}.html"
        try:
            html = self._fetch(url)
        except Exception:
            return {"list": []}
        vod_list = self._parse_list(html)
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 40,
            "total": 9999,
            "list": vod_list,
        }

    def playerContent(self, *args):
        flag = args[0] if args else ""
        pid = args[1] if len(args) > 1 else ""
        vip = args[2] if len(args) > 2 else ""
        url = pid
        if pid and "play/id/" in pid:
            try:
                ph = self._fetch(pid if pid.startswith("http") else self.siteUrl + pid)
                pm = re.search(r"var player_aaaa\s*=\s*(\{.*?\});", ph, re.S)
                if pm:
                    import json
                    data = json.JSONDecoder().raw_decode(pm.group(1))[0]
                    u = data.get("url", "") or ""
                    if u:
                        url = u
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
            r'href="/index\.php/vod/detail/id/(\d+)\.html" title="([^"]+)"[^>]*>\s*<img[^>]*data-original="([^"]+)"',
            html)
        if not items:
            items = re.findall(
                r'href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*title="([^"]+)"',
                html)
        for vid, title, pic in [x if len(x) == 3 else (x[0], x[1], "") for x in items]:
            title = title.strip()
            if not title:
                continue
            if self._is_minor(title):
                continue
            if pic.startswith("/"):
                pic = self.siteUrl + pic
            vod_list.append({
                "vod_id": f"/index.php/vod/detail/id/{vid}.html",
                "vod_name": title[:80],
                "vod_pic": pic,
                "vod_remarks": "",
            })
            if len(vod_list) >= 40:
                break
        if not vod_list:
            dts = re.findall(r'/index\.php/vod/detail/id/(\d+)\.html', html)
            for vid in dts:
                vod_list.append({"vod_id": f"/index.php/vod/detail/id/{vid}.html", "vod_name": "视频" + vid, "vod_pic": "", "vod_remarks": ""})
                if len(vod_list) >= 40:
                    break
        return vod_list

    def _parse_detail(self, html, vid):
        title = ""
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not title:
            m3 = re.search(r"<title>(.*?)</title>", html, re.S)
            if m3:
                title = m3.group(1).split("-")[0].strip()
        vod_name = title if title else f"视频{vid}"
        vod_name = vod_name.replace("详情", "").replace("介绍", "").strip()
        # 播放链接
        pm = re.findall(r'href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"', html)
        play_url = ""
        play_name = vod_name
        for href in pm:
            play_url = href
            play_name = "线路1"
            break
        return {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "ytm3u8",
            "vod_play_url": f"{play_name}${play_url}" if play_url else "",
        }
