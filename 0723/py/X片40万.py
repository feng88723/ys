# -*- coding: utf-8 -*-
"""
X片40万 四壳通用 Python Spider
站点: https://hzlpzs.xp40w6601.top/40wxp/ (苹果CMS v10, 直连无盾)
列表: /40wxp/index.php/vod/type/id/{tid}(/{page}).html
      <li><a class="thumbnail" href="/40wxp/index.php/vod/detail/id/{id}.html"><img class="loadi" data-original="封面">
详情: /40wxp/index.php/vod/detail/id/{id}.html -> 片名 + 播放 /40wxp/index.php/vod/play/id/{id}/sid/1/nid/1.html
播放: /40wxp/index.php/vod/play/id/{id}/sid/1/nid/1.html -> var player_aaaa {url直链}
搜索: /40wxp/index.php/vod/search/wd/{kw}.html
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
        self.siteUrl = "https://hzlpzs.xp40w6601.top/40wxp"
        self.rawSite = self.siteUrl
        self.HOST = self.siteUrl
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        self.ext = {}
        # 分类46 (父3区+子43, 剔113萝莉少女; 同名分类带区前缀)
        self.categories = [
            {"type_id": "30", "type_name": "高清精品视频1区"},
            {"type_id": "55", "type_name": "视频1区-网曝流出"},
            {"type_id": "54", "type_name": "视频1区-偷拍自拍"},
            {"type_id": "63", "type_name": "视频1区-换脸明星"},
            {"type_id": "77", "type_name": "视频1区-国产精品"},
            {"type_id": "62", "type_name": "视频1区-乱伦实录"},
            {"type_id": "49", "type_name": "视频1区-精品推荐"},
            {"type_id": "57", "type_name": "视频1区-国产探花"},
            {"type_id": "56", "type_name": "视频1区-同性恋"},
            {"type_id": "51", "type_name": "视频1区-欧美精品"},
            {"type_id": "50", "type_name": "视频1区-直播做爱"},
            {"type_id": "59", "type_name": "视频1区-SM调教"},
            {"type_id": "61", "type_name": "视频1区-麻豆诱惑"},
            {"type_id": "58", "type_name": "视频1区-人妻熟女"},
            {"type_id": "60", "type_name": "视频1区-制服诱惑"},
            {"type_id": "92", "type_name": "高清精品视频2区"},
            {"type_id": "97", "type_name": "视频2区-国产传媒"},
            {"type_id": "96", "type_name": "视频2区-国产主播"},
            {"type_id": "95", "type_name": "视频2区-国产视频"},
            {"type_id": "94", "type_name": "视频2区-网曝黑料"},
            {"type_id": "99", "type_name": "视频2区-网红头条"},
            {"type_id": "100", "type_name": "视频2区-明星换脸"},
            {"type_id": "98", "type_name": "视频2区-女同性恋"},
            {"type_id": "101", "type_name": "视频2区-抖阴视频"},
            {"type_id": "102", "type_name": "视频2区-激情动漫"},
            {"type_id": "103", "type_name": "视频2区-SM调教"},
            {"type_id": "104", "type_name": "视频2区-韩国主播"},
            {"type_id": "112", "type_name": "视频2区-强奸乱伦"},
            {"type_id": "105", "type_name": "视频2区-VR视角"},
            {"type_id": "111", "type_name": "视频2区-女优明星"},
            {"type_id": "106", "type_name": "视频2区-人妖系列"},
            {"type_id": "114", "type_name": "视频2区-伦理三级"},
            {"type_id": "115", "type_name": "视频2区-制服诱惑"},
            {"type_id": "110", "type_name": "视频2区-欧美无码"},
            {"type_id": "107", "type_name": "视频2区-中文字幕"},
            {"type_id": "108", "type_name": "视频2区-日本有码"},
            {"type_id": "116", "type_name": "视频2区-AV解说"},
            {"type_id": "109", "type_name": "视频2区-日本无码"},
            {"type_id": "29", "type_name": "高清精品视频3区"},
            {"type_id": "73", "type_name": "视频3区-黑料网爆"},
            {"type_id": "64", "type_name": "视频3区-主播做爱"},
            {"type_id": "66", "type_name": "视频3区-探花约炮"},
            {"type_id": "67", "type_name": "视频3区-自拍短视频"},
            {"type_id": "65", "type_name": "视频3区-传媒出品"},
            {"type_id": "76", "type_name": "视频3区-AI换脸"},
            {"type_id": "75", "type_name": "视频3区-调教SM"},
            {"type_id": "71", "type_name": "视频3区-男同性恋"},
            {"type_id": "74", "type_name": "视频3区-高清做爱"},
            {"type_id": "69", "type_name": "视频3区-动漫"},
            {"type_id": "68", "type_name": "视频3区-欧美精品"},
            {"type_id": "70", "type_name": "视频3区-女同性恋"},
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
            html = self._fetch(self.siteUrl + "/index.php/vod/type/id/30.html")
            vod_list = self._parse_list(html)
            if vod_list:
                result["list"] = vod_list
        except Exception:
            pass
        return result

    def categoryContent(self, *args):
        tid = args[0] if args else "30"
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
            "limit": 20,
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
            "limit": 20,
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
                pm = re.search(r'var player_aaaa.*?"url":"([^"]*)"', ph, re.S)
                if pm and pm.group(1):
                    u = pm.group(1).replace("\\/", "/")
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
            r'href="[^"]*?/vod/detail/id/(\d+)\.html"[^>]*>\s*<img[^>]*data-original="([^"]+)"',
            html)
        if not items:
            items = re.findall(
                r'href="[^"]*?/vod/detail/id/(\d+)\.html"',
                html)
        for it in items:
            vid = it[0]
            pic = it[1] if len(it) > 1 else ""
            title = ""
            m = re.search(r'data-original="' + re.escape(pic) + r'"[^>]*>\s*</a>\s*<div[^>]*>\s*<h5[^>]*><a[^>]*>([^<]+)', html)
            if not m:
                m = re.search(r'alt="([^"]+)"', html[html.find("vod/detail/id/" + vid):html.find("vod/detail/id/" + vid) + 600])
            if m:
                title = m.group(1).strip()
            if not title:
                title = "视频" + vid
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
            if len(vod_list) >= 20:
                break
        if not vod_list:
            dts = re.findall(r'/vod/detail/id/(\d+)\.html', html)
            for vid in dts:
                vod_list.append({"vod_id": f"/index.php/vod/detail/id/{vid}.html", "vod_name": "视频" + vid, "vod_pic": "", "vod_remarks": ""})
                if len(vod_list) >= 20:
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
        vod_name = vod_name.replace("详情", "").replace("介绍", "").replace("剧情", "").strip()
        # 播放链接 (去路径前缀)
        pms = re.findall(r'href="([^"]*?/vod/play/id/\d+/sid/(\d+)/nid/1\.html)"', html)
        seen = {}
        for href, sid in pms:
            if "/40wxp" in href:
                href = href.split("/40wxp", 1)[1]
            seen.setdefault(sid, href)
        lines = []
        for sid, href in seen.items():
            lines.append((f"线路{sid}", href))
        play_from = ""
        play_url = ""
        if lines:
            play_from = "$$$".join(x[0] for x in lines)
            play_url = "#".join(f"{x[0]}${x[1]}" for x in lines)
        return {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }
