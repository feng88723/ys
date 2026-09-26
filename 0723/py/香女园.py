#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import json
import time
import urllib.parse
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    requests = None

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""):
            pass

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

JUVENILE_PATTERNS = [
    r"萝莉", r"幼女", r"少女", r"童", r"teen", r"loli", r"schoolgirl",
    r"未成年", r"小女", r"女童", r"幼童", r"孩童", r"小学生",
]

def _is_juvenile(text):
    if not text:
        return False
    t = text.lower()
    for p in JUVENILE_PATTERNS:
        if re.search(p, t, re.I):
            return True
    return False


class Spider(_BaseSpider):
    header = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }

    def __init__(self):
        self.siteUrl = "https://ikt.xny6.makeup/cn/home/web"
        self.rawSite = "https://ikt.xny6.makeup"
        self.session = None
        self._cache = {}
        self._cache_time = {}

    def getDependence(self):
        return ""

    def init(self, extend=""):
        if isinstance(extend, dict):
            ext = extend
        elif isinstance(extend, str) and extend.strip():
            try:
                ext = json.loads(extend)
            except Exception:
                try:
                    import ast
                    ext = ast.literal_eval(extend)
                except Exception:
                    ext = {}
        else:
            ext = {}
        if ext.get("siteUrl"):
            self.siteUrl = ext["siteUrl"].rstrip("/")
        if ext.get("proxy"):
            self.siteUrl = ext["proxy"].rstrip("/")
        if ext.get("direct"):
            self.siteUrl = "https://ikt.xny6.makeup/cn/home/web"
        if requests:
            self.session = requests.Session()
            self.session.trust_env = False
            self.session.headers.update(self.header)
        self._fetch(self.siteUrl + "/", timeout=10)

    def _fetch(self, url, timeout=15, data=None):
        now = time.time()
        if url in self._cache and now - self._cache_time.get(url, 0) < 60:
            return self._cache[url]
        try:
            if self.session:
                if data:
                    r = self.session.post(url, data=data, timeout=timeout, verify=False)
                else:
                    r = self.session.get(url, timeout=timeout, verify=False)
            else:
                import urllib.request
                req = urllib.request.Request(url, headers=self.header)
                if data:
                    req.data = urllib.parse.urlencode(data).encode()
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    r = type("R", (), {
                        "text": resp.read().decode("utf-8", errors="ignore"),
                        "status_code": resp.getcode(),
                    })()
            if r.status_code == 200:
                self._cache[url] = r.text
                self._cache_time[url] = now
                if len(self._cache) > 24:
                    oldest = min(self._cache_time, key=self._cache_time.get)
                    self._cache.pop(oldest, None)
                    self._cache_time.pop(oldest, None)
                return r.text
        except Exception:
            pass
        return ""

    def _abs(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        return urljoin(self.siteUrl + "/", url)

    def _parse_list(self, html):
        vlist = []
        pattern = re.compile(
            r'<a[^>]*class="cover"[^>]*href="([^"]*vod/play/id/(\d+)[^"]*)"[^>]*>\s*'
            r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"',
            re.S,
        )
        for m in pattern.finditer(html):
            play_url, vod_id, pic, name = m.group(1), m.group(2), m.group(3), m.group(4)
            name = name.strip()
            if _is_juvenile(name):
                continue
            vlist.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": self._abs(pic),
                "vod_remarks": "",
            })
        if not vlist:
            pattern2 = re.compile(
                r'<a[^>]*href="([^"]*vod/play/id/(\d+)[^"]*)"[^>]*>.*?'
                r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"',
                re.S,
            )
            for m in pattern2.finditer(html):
                play_url, vod_id, pic, name = m.group(1), m.group(2), m.group(3), m.group(4)
                name = name.strip()
                if _is_juvenile(name):
                    continue
                if not any(v["vod_id"] == vod_id for v in vlist):
                    vlist.append({
                        "vod_id": vod_id,
                        "vod_name": name,
                        "vod_pic": self._abs(pic),
                        "vod_remarks": "",
                    })
        return vlist

    def _parse_pages(self, html, tid):
        pages = re.findall(r'vod/type/id/' + str(tid) + r'/page/(\d+)\.html', html)
        nums = [int(p) for p in pages]
        return max(nums) if nums else 1

    def homeContent(self, *args):
        cls = [
            {"type_id": "20", "type_name": "亚洲情色"},
            {"type_id": "21", "type_name": "强奸乱伦"},
            {"type_id": "22", "type_name": "偷拍自拍"},
            {"type_id": "23", "type_name": "风骚寡妇"},
            {"type_id": "24", "type_name": "制服师生"},
            {"type_id": "25", "type_name": "欧美性爱"},
            {"type_id": "26", "type_name": "JAV高清"},
            {"type_id": "27", "type_name": "VR虚拟"},
            {"type_id": "28", "type_name": "无码视频"},
            {"type_id": "29", "type_name": "有码视频"},
            {"type_id": "30", "type_name": "国产视频"},
            {"type_id": "31", "type_name": "女同"},
            {"type_id": "32", "type_name": "动漫"},
            {"type_id": "33", "type_name": "三级伦理"},
        ]
        filters = {}
        for c in cls:
            filters[c["type_id"]] = [
                {"key": "sort", "name": "排序", "init": "", "value": [
                    {"n": "最新", "v": "new"},
                    {"n": "最热", "v": "hot"},
                ]}
            ]
        html = self._fetch(self.siteUrl + "/")
        vlist = self._parse_list(html)
        return {"class": cls, "filters": filters, "list": vlist}

    def homeVideoContent(self, *args):
        html = self._fetch(self.siteUrl + "/")
        vlist = self._parse_list(html)
        return {"page": 1, "pagecount": 1, "limit": len(vlist), "total": len(vlist), "list": vlist}

    def categoryContent(self, *args):
        tid = None
        page = 1
        if args:
            tid = str(args[0]) if args[0] else "20"
            if len(args) > 1 and args[1]:
                try:
                    page = int(args[1])
                except Exception:
                    page = 1
        if tid is None:
            tid = "20"
        url = self.siteUrl + "/index.php/vod/type/id/" + tid + "/page/" + str(page) + ".html"
        html = self._fetch(url)
        vlist = self._parse_list(html)
        total_pages = self._parse_pages(html, tid)
        total = total_pages * 20
        return {"page": page, "pagecount": total_pages, "limit": 20, "total": total, "list": vlist}

    def detailContent(self, *args):
        ids = args[0] if args else []
        if isinstance(ids, str):
            ids = [ids]
        results = []
        for vod_id in ids:
            vod_id = str(vod_id)
            play_url = self.siteUrl + "/index.php/vod/play/id/" + vod_id + "/sid/1/nid/1.html"
            html = self._fetch(play_url)
            vod_name = ""
            vod_pic = ""
            vod_content = ""
            m3u8_url = ""
            name_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if name_m:
                vod_name = name_m.group(1).strip()
            title_m = re.search(r'<title>([^<]+)</title>', html)
            if not vod_name and title_m:
                vod_name = title_m.group(1).strip()
            pic_m = re.search(r'<img[^>]*class="[^"]*cover[^"]*"[^>]*src="([^"]*)"', html)
            if pic_m:
                vod_pic = self._abs(pic_m.group(1))
            if not vod_pic:
                pic_m2 = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html)
                if pic_m2:
                    vod_pic = self._abs(pic_m2.group(1))
            pd_m = re.search(r'player_data\s*=\s*(\{[^;]+\})', html)
            if pd_m:
                try:
                    pd = json.loads(pd_m.group(1))
                    m3u8_url = pd.get("url", "")
                    if m3u8_url and m3u8_url.startswith("\\/"):
                        m3u8_url = "https:" + m3u8_url.replace("\\/", "/")
                except Exception:
                    url_m = re.search(r'"url"\s*:\s*"([^"]+)"', pd_m.group(1))
                    if url_m:
                        m3u8_url = url_m.group(1).replace("\\/", "/")
            if not m3u8_url:
                m3u8_m = re.search(r'(https?:\\?/\\?/[^"\s]+\.m3u8[^"\s]*)', html)
                if m3u8_m:
                    m3u8_url = m3u8_m.group(1).replace("\\/", "/")
            if _is_juvenile(vod_name):
                continue
            play_from = "ckplayer"
            play_url_str = "正片$" + m3u8_url if m3u8_url else "正片$"
            results.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_content": vod_content,
                "vod_play_from": play_from,
                "vod_play_url": play_url_str,
            })
        return {"list": results}

    def searchContent(self, *args):
        wd = ""
        page = 1
        if args:
            wd = str(args[0]) if args[0] else ""
            if len(args) > 1 and args[1]:
                try:
                    page = int(args[1])
                except Exception:
                    page = 1
        if not wd:
            return {"page": 1, "pagecount": 0, "limit": 20, "total": 0, "list": []}
        url = self.siteUrl + "/index.php/vod/search.html"
        html = self._fetch(url, data={"wd": wd})
        vlist = self._parse_list(html)
        pages = re.findall(r'vod/search/page/(\d+)\.html', html)
        if not pages:
            pages = re.findall(r'page/(\d+)\.html', html)
        total_pages = max([int(p) for p in pages]) if pages else 1
        total = total_pages * 20
        return {"page": page, "pagecount": total_pages, "limit": 20, "total": total, "list": vlist}

    def playerContent(self, *args):
        flag = args[0] if args else "ckplayer"
        vid = args[1] if len(args) > 1 else ""
        url = str(vid) if vid else ""
        header = {
            "User-Agent": UA,
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }
        return {"parse": 0, "jx": 0, "url": url, "header": header}

    def localProxy(self, *args):
        param = args[0] if args else ""
        if not param:
            return [404, "text/plain", ""]
        try:
            if isinstance(param, dict):
                url = param.get("url", "")
            else:
                url = str(param)
            if url.startswith("local://"):
                url = url.replace("local://", "https://", 1)
            if not url.startswith("http"):
                return [404, "text/plain", ""]
            if self.session:
                r = self.session.get(url, timeout=15, verify=False, headers={
                    "User-Agent": UA,
                    "Referer": self.rawSite + "/",
                })
                if r.status_code == 200:
                    ctype = r.headers.get("Content-Type", "application/octet-stream")
                    return [200, ctype, r.content]
        except Exception:
            pass
        return [404, "text/plain", ""]

    def isVideoFormat(self, *args):
        return True

    def manualVideoCheck(self, *args):
        return False

    def action(self, *args):
        return ""

    def destroy(self, *args):
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
        self._cache.clear()
        self._cache_time.clear()
