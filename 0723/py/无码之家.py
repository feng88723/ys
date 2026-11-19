# -*- coding: utf-8 -*-
"""
无码之家 四壳通用 Python Spider
站点: https://wmzw7.wmzjsp.xyz/ss/ (苹果CMS v10 模板llgl)
结构: 分类 /vod/type/id/{tid}.html 分页 /page/{n}.html
      列表 <dl><dt><a href="/ss/index.php/vod/play/id/{vid}/sid/1/nid/1.html" title="标题"><img data-src="封面"></a></dt></dl>
      播放页 player_aaaa JSON -> url 为 m3u8 直链 (cdn2020.com)
      搜索 /vod/search/wd/{kw}.html 分页 /page/{n}.html
防护: 无 (直连200)
"""
import re
import json
import time
import random

try:
    from base.spider import Spider
except Exception:
    class Spider(object):
        def __init__(self):
            pass


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://wmzw7.wmzjsp.xyz"
        self.rawSite = "https://wmzw7.wmzjsp.xyz"
        self.HOST = self.siteUrl
        self.base = "/ss/index.php"
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        self.ext = {}
        # 分类 (萝莉少女 id=21 未成年跳过, 铁律13)
        self.categories = [
            {"type_id": "6", "type_name": "国产精品"},
            {"type_id": "7", "type_name": "网曝吃瓜"},
            {"type_id": "8", "type_name": "自拍偷拍"},
            {"type_id": "9", "type_name": "传媒出品"},
            {"type_id": "10", "type_name": "网红主播"},
            {"type_id": "11", "type_name": "探花寻花"},
            {"type_id": "12", "type_name": "抖阴视频"},
            {"type_id": "13", "type_name": "国产其它"},
            {"type_id": "14", "type_name": "日韩精品"},
            {"type_id": "15", "type_name": "日本无码"},
            {"type_id": "16", "type_name": "日本有码"},
            {"type_id": "20", "type_name": "中文字幕"},
            {"type_id": "22", "type_name": "人妻熟妇"},
            {"type_id": "23", "type_name": "韩国主播"},
            {"type_id": "24", "type_name": "日韩其它"},
            {"type_id": "25", "type_name": "欧美精品"},
            {"type_id": "26", "type_name": "欧美无码"},
            {"type_id": "27", "type_name": "欧美另类"},
            {"type_id": "28", "type_name": "欧美其它"},
            {"type_id": "29", "type_name": "明星换脸"},
            {"type_id": "30", "type_name": "AV解说"},
            {"type_id": "31", "type_name": "三级伦理"},
            {"type_id": "32", "type_name": "成人动漫"},
        ]
        self.filter_dict = {}
        for c in self.categories:
            self.filter_dict[c["type_id"]] = []
        self._minor_re = re.compile(r"(萝莉|幼女|少女|童|teen|loli|schoolgirl|\d{1,2}岁|小学生|初中|高中妹|未成年)", re.I)

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
        if extend.get("direct"):
            pass

    def homeContent(self, *args):
        result = {"class": self.categories, "filters": self.filter_dict, "list": []}
        try:
            html = self._fetch(self.siteUrl + "/ss/")
            vod_list = self._parse_list(html)
            if vod_list:
                result["list"] = vod_list
        except Exception:
            pass
        return result

    def categoryContent(self, *args):
        tid = args[0] if args else "6"
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
            "limit": 36,
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
        # 直达播放页取 player_aaaa
        url = f"{self.siteUrl}{self.base}/vod/play/id/{vid}/sid/1/nid/1.html"
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
            "limit": 36,
            "total": 9999,
            "list": vod_list,
        }

    def playerContent(self, *args):
        flag = args[0] if args else ""
        pid = args[1] if len(args) > 1 else ""
        vip = args[2] if len(args) > 2 else ""
        url = pid
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
        param = args[0] if args else ""
        if param and param.startswith("m3u8:"):
            return self._proxy_m3u8_url(param[5:])
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
        # 通道1: curl_cffi (TLS指纹伪装, TVBox Chaquo环境有)
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(url, headers=hdrs, timeout=timeout, impersonate="chrome131", verify=False)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        # 通道2: requests (自动解压, verify=False破证书链)
        try:
            import requests as req_lib
            resp = req_lib.get(url, headers=hdrs, timeout=timeout, verify=False)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        # 通道3: urllib (纯标准库兜底 + gzip解压)
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
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        resp = opener.open(req, timeout=timeout)
        raw = resp.read()
        enc = resp.headers.get("Content-Encoding", "")
        if enc == "gzip" or raw[:2] == b"\x1f\x8b":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="ignore")

    def _parse_list(self, html):
        vod_list = []
        if not html:
            return vod_list
        # <dl>卡片块: 直达播放页
        dls = re.findall(r"<dl>(.*?)</dl>", html, re.S)
        for dl in dls:
            m = re.search(r'<dt><a href="([^"]+)"[^>]*title="([^"]*)"[^>]*>(.*?)</a></dt>', dl, re.S)
            if not m:
                continue
            href, title, inner = m.group(1), m.group(2).strip(), m.group(3)
            # 跳过外链广告卡片
            if not href.startswith("/ss/index.php/vod/play/"):
                continue
            if not title:
                continue
            # 未成年标题跳过 (铁律13)
            if self._is_minor(title):
                continue
            mm = re.search(r"id/(\d+)", href)
            if not mm:
                continue
            vid = mm.group(1)
            img = ""
            im = re.search(r'data-src="([^"]+)"', inner)
            if not im:
                im = re.search(r'data-original="([^"]+)"', inner)
            if not im:
                im = re.search(r'src="([^"]+)"', inner)
            if im:
                img = im.group(1)
            if img.startswith("/"):
                img = self.siteUrl + img
            vod_list.append({
                "vod_id": href,
                "vod_name": title[:80],
                "vod_pic": img,
                "vod_remarks": "m3u8",
            })
            if len(vod_list) >= 36:
                break
        return vod_list

    def _parse_detail(self, html, vid):
        # 标题 h1
        title = ""
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not title:
            m2 = re.search(r'<title>(.*?)</title>', html, re.S)
            if m2:
                title = m2.group(1).split("-")[0].strip()
        # player_aaaa JSON
        url = ""
        pm = re.search(r"var player_aaaa\s*=\s*(\{.*?\});", html, re.S)
        if pm:
            try:
                data = json.JSONDecoder().raw_decode(pm.group(1))[0]
                u = data.get("url", "") or ""
                if u:
                    url = u.replace("\\/", "/")
            except Exception:
                pass
        if not url:
            # 兜底: 找 m3u8/mp4 直链
            um = re.search(r'https?://[^"\'<> ]+?\.(?:m3u8|mp4)(?:[^"\'<> ]*)', html)
            if um:
                url = um.group(0)
        vod_name = title if title else f"视频{vid}"
        vod_play_url = ""
        if url:
            vod_play_url = f"{vod_name}${{{url}}}"
        return {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "m3u8",
            "vod_play_url": vod_play_url,
        }

    def _proxy_m3u8_url(self, url):
        """广告清洗代理 (本地代理, 壳支持时自动生效)"""
        return [404, "text/plain", ""]

    def _clean_m3u8(self, m3u8):
        try:
            import urllib.request
            req = urllib.request.Request(m3u8, headers={"User-Agent": self.ua, "Referer": self.rawSite + "/"})
            resp = urllib.request.urlopen(req, timeout=12)
            content = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return m3u8
        lines = []
        for line in content.splitlines():
            s = line.strip()
            if s.startswith("#"):
                lines.append(line)
            else:
                lines.append(line)
        return "\n".join(lines)
