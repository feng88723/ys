# -*- coding: utf-8 -*-
"""
91插骚鲍 四壳通用 Python Spider
站点: https://xn--zj4a.91xsb50.buzz/ (苹果CMS v10 + CF + sharktech 双层盾)
破盾: 内置过盾Cookie (CF clearance + sharktech挑战令牌)
列表: <a class="item" href="/index.php/vod/detail/id/{vid}.html">
      <img class="lazy" src="占位" data-original="封面"> <p>标题</p>
详情: 内嵌HlsJsPlayer { "url": "https://...m3u8" } 直链
播放: 详情页直接返回m3u8直链
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
        self.siteUrl = "https://xn--zj4a.91xsb50.buzz"
        self.rawSite = self.siteUrl
        self.HOST = self.siteUrl
        self.base = "/index.php"
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        self.ext = {}
        # 过盾Cookie (CF clearance + sharktech)
        self.cookies = {
            "CHCK": "1",
            "UID": "2610151838b285b21442f54a4b89ce9f9830",
            "UID_cZEx3B5PBqOC6WlOEuVXCZT3InqGPLsGoqm": "ok",
            "auth": "v=current&id=5dbc5a4df1b6b097ff9e442eb49c1292",
            "CRIBLOCK": "AEw0QAAAAABq0VrwADLkjwAAAABq0Vrw",
            "cf_clearance": "wJT31s61f37VNMEKTZT96qQgmfOJT5cnceTU2JHwOBY-179210",
            "c6s_RobotVerify": "1",
        }
        # 分类 (父+子, 铁律7; 童颜巨乳5184 未成年跳过)
        self.categories = [
            {"type_id": "5177", "type_name": "视频一区"},
            {"type_id": "5178", "type_name": "视频一区-精品推荐"},
            {"type_id": "5179", "type_name": "视频一区-国产精品"},
            {"type_id": "5180", "type_name": "视频一区-主播秀色"},
            {"type_id": "5181", "type_name": "视频一区-日本有码"},
            {"type_id": "5182", "type_name": "视频一区-日本无码"},
            {"type_id": "5183", "type_name": "视频一区-中文字幕"},
            {"type_id": "5185", "type_name": "视频一区-性感人妻"},
            {"type_id": "5186", "type_name": "视频一区-强奸乱伦"},
            {"type_id": "5187", "type_name": "视频一区-欧美情色"},
            {"type_id": "5188", "type_name": "视频一区-三级伦理"},
            {"type_id": "5189", "type_name": "视频一区-卡通动漫"},
            {"type_id": "5190", "type_name": "视频一区-丝袜OL"},
            {"type_id": "5191", "type_name": "视频一区-自拍偷拍"},
            {"type_id": "5192", "type_name": "视频一区-剧情介绍"},
            {"type_id": "5193", "type_name": "视频一区-网曝系列"},
            {"type_id": "5194", "type_name": "视频一区-麻豆传媒"},
            {"type_id": "5202", "type_name": "视频二区"},
            {"type_id": "5204", "type_name": "视频二区-国产传媒"},
            {"type_id": "5205", "type_name": "视频二区-网曝黑料"},
            {"type_id": "5206", "type_name": "视频二区-主播网红"},
            {"type_id": "5207", "type_name": "视频二区-高清无码"},
            {"type_id": "5209", "type_name": "视频二区-极品欧美"},
            {"type_id": "5210", "type_name": "视频二区-3D动漫"},
            {"type_id": "5211", "type_name": "视频二区-东南亚"},
            {"type_id": "5212", "type_name": "视频二区-重口味"},
        ]
        self.filter_dict = {}
        for c in self.categories:
            self.filter_dict[c["type_id"]] = []
        self._minor_re = re.compile(r"(萝莉|幼女|少女|童颜|童|teen|loli|schoolgirl|\d{1,2}岁|小学生|初中|未成年)", re.I)

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
            html = self._fetch(self.siteUrl + self.base + "/vod/type/id/5178.html")
            vod_list = self._parse_list(html)
            if vod_list:
                result["list"] = vod_list
        except Exception:
            pass
        return result

    def categoryContent(self, *args):
        tid = args[0] if args else "5178"
        pg = args[1] if len(args) > 1 else 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        url = f"{self.siteUrl}{self.base}/vod/type/id/{tid}.html"
        if pg > 1:
            url = f"{self.siteUrl}{self.base}/vod/type/id/{tid}/page/{pg}.html"
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
        m = re.search(r"id/(\d+)", ids)
        vid = m.group(1) if m else ids
        url = f"{self.siteUrl}{self.base}/vod/detail/id/{vid}.html"
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
        url = f"{self.siteUrl}{self.base}/vod/search/wd/{kw}.html"
        if pg > 1:
            url = f"{self.siteUrl}{self.base}/vod/search/wd/{kw}/page/{pg}.html"
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
        # pid可能为详情页URL: 抓m3u8
        if pid and "detail" in pid:
            try:
                ph = self._fetch(pid if pid.startswith("http") else self.siteUrl + pid)
                mm = re.search(r'new HlsJsPlayer\(\s*\{\s*"id":\s*"player",\s*"url":\s*"([^"]+)"', ph)
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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        raw = ""
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(url, headers=hdrs, cookies=self.cookies, timeout=timeout, impersonate="chrome131", verify=False)
            if resp.status_code == 200:
                raw = resp.text
        except Exception:
            pass
        if not raw:
            try:
                import requests as req_lib
                resp = req_lib.get(url, headers=hdrs, cookies=self.cookies, timeout=timeout, verify=False)
                if resp.status_code == 200:
                    raw = resp.text
            except Exception:
                pass
        if not raw:
            import urllib.request
            import ssl
            ck_str = "; ".join("%s=%s" % (k, v) for k, v in self.cookies.items())
            hdrs2 = dict(hdrs)
            hdrs2["Cookie"] = ck_str
            req = urllib.request.Request(url, headers=hdrs2)
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
        if not raw:
            return ""
        if "sharktech" in raw or "Security Verification" in raw[:300]:
            return ""
        return raw

    def _parse_list(self, html):
        vod_list = []
        if not html:
            return vod_list
        items = re.findall(
            r'<a class="item"[^>]*href="(/index\.php/vod/detail/id/(\d+)\.html)"[^>]*>\s*'
            r'<div class="thumb">.*?data-original="([^"]+)"[^>]*>.*?'
            r'<div class="title">\s*<p>([^<]+)</p>',
            html, re.S)
        for href, vid, pic, title in items:
            title = title.strip()
            if not title:
                continue
            if self._is_minor(title):
                continue
            if pic.startswith("/"):
                pic = self.siteUrl + pic
            vod_list.append({
                "vod_id": href,
                "vod_name": title[:80],
                "vod_pic": pic,
                "vod_remarks": "",
            })
            if len(vod_list) >= 20:
                break
        if not vod_list:
            dts = re.findall(r'href="(/index\.php/vod/detail/id/(\d+)\.html)"[^>]*>', html)
            for href, vid in dts:
                vod_list.append({"vod_id": href, "vod_name": "视频" + vid, "vod_pic": "", "vod_remarks": ""})
                if len(vod_list) >= 20:
                    break
        return vod_list

    def _parse_detail(self, html, vid):
        title = ""
        m2 = re.search(r'<title>(.*?)</title>', html, re.S)
        if m2:
            title = m2.group(1).replace("91插骚鲍", "").replace("_91插骚鲍", "").strip()
        if not title:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        vod_name = title if title else f"视频{vid}"
        # 播放直链
        mm = re.search(r'new HlsJsPlayer\(\s*\{\s*"id":\s*"player",\s*"url":\s*"([^"]+)"', html)
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
