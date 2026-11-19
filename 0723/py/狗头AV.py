# coding=utf-8
try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        def getName(self): return ""
        def init(self, extend=""): pass
        def homeContent(self, filter=None): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter=None, extend=None): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick=False, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags=None): return {}
        def localProxy(self, param): return [404, "text/plain", ""]
        def getDependence(self): return ""
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False

import re, time, urllib.request
from urllib.parse import quote, urljoin, urlparse

class Spider(BaseSpider):
    def getName(self):
        return "狗头AV"

    def init(self, extend=""):
        self.host = "https://4g.goutouav39.cc"
        self.prefix = "/goutou"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + self.prefix + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def getDependence(self):
        return ""

    def _get(self, url, retry=2):
        for i in range(retry + 1):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode("utf-8", errors="ignore")
            except Exception:
                if i == retry:
                    return ""
                time.sleep(0.4)
        return ""

    def homeContent(self, filter=None):
        classes = [
            {"type_id": "292", "type_name": "狗头资源"},
            {"type_id": "119", "type_name": "斯卡资源"},
            {"type_id": "244", "type_name": "玉兔资源"},
            {"type_id": "355", "type_name": "黄瓜短剧"},
            {"type_id": "332", "type_name": "155资源"},
            {"type_id": "206", "type_name": "仓鼠资源"},
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self.categoryContent("292", "1")

    def categoryContent(self, tid, pg, filter=None, extend=None):
        pg = str(pg or "1")
        if pg == "1":
            url = f"{self.host}{self.prefix}/index.php/vod/type/id/{tid}.html"
        else:
            url = f"{self.host}{self.prefix}/index.php/vod/type/id/{tid}/page/{pg}.html"
        html = self._get(url)
        if not html:
            return {"page": int(pg), "pagecount": 1, "limit": 0, "total": 0, "list": []}
        videos = self._parse_list(html)
        pagecount = 1
        pages = re.findall(r"type/id/%s/page/(\d+)" % re.escape(str(tid)), html)
        if pages:
            pagecount = max(int(x) for x in pages)
        if f"/page/{int(pg)+1}.html" in html:
            pagecount = max(pagecount, int(pg) + 1)
        return {"page": int(pg), "pagecount": pagecount, "limit": 24, "total": pagecount * 24, "list": videos}

    def _parse_list(self, html):
        videos = []
        pattern = r'href="(/goutou/index\.php/vod/detail/id/(\d+)\.html)"[^>]*>.*?(?:data-original|src)="([^"]+)"'
        for m in re.finditer(pattern, html, re.S):
            href, vid, pic = m.groups()
            name = ""
            # title nearby
            block = html[max(0, m.start() - 50): m.end() + 200]
            tm = re.search(r'(?:title|alt)="([^"]{4,80})"', block)
            if not tm:
                tm = re.search(r'>([^<]{6,50})</a>', block)
            if tm:
                name = self._unescape(tm.group(1)).strip()
            if not name or len(name) < 2:
                continue
            if not pic.startswith("http"):
                pic = urljoin(self.host, pic)
            videos.append({"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": ""})
        if not videos:
            for m in re.finditer(r'href="(/goutou/index\.php/vod/detail/id/(\d+)\.html)"', html):
                vid = m.group(2)
                videos.append({"vod_id": vid, "vod_name": f"视频{vid}", "vod_pic": "", "vod_remarks": ""})
        seen = set()
        uniq = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                uniq.append(v)
        return uniq

    def _unescape(self, s):
        try:
            import html as H
            return H.unescape(s)
        except:
            return s

    def _resolve_m3u8(self, url):
        if not url or ".m3u8" not in url:
            return url
        body = self._fetch_raw(url)
        if not body:
            return url
        if "#EXTINF" in body and "#EXT-X-STREAM-INF" not in body:
            return url
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and ".m3u8" in line:
                return line if line.startswith("http") else urljoin(url, line)
        return url

    def _fetch_raw(self, url):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + self.prefix + "/",
            })
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _extract_play_url(self, html):
        if not html:
            return ""
        # player_aaaa
        m = re.search(r'player_[a-zA-Z0-9_]+\s*=\s*(\{.+?\})\s*;', html, re.S)
        if m:
            block = m.group(1)
            um = re.search(r'"url"\s*:\s*"((?:\\.|[^"\\])*)"', block)
            if um:
                u = um.group(1).replace("\\/", "/")
                if u.startswith("http"):
                    return u
        m3s = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
        if m3s:
            return m3s[0]
        return ""

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        # prefer play page for player_aaaa
        play_page = f"{self.host}{self.prefix}/index.php/vod/play/id/{vod_id}/sid/1/nid/1.html"
        html = self._get(play_page)
        if not html:
            html = self._get(f"{self.host}{self.prefix}/index.php/vod/detail/id/{vod_id}.html")
        name = ""
        m = re.search(r'"vod_name"\s*:\s*"((?:\\.|[^"\\])*)"', html or "")
        if m:
            try:
                name = m.group(1).encode("utf-8").decode("unicode_escape")
            except Exception:
                name = self._unescape(m.group(1))
        if not name:
            m = re.search(r"<title>([^<]+)</title>", html or "")
            if m:
                name = self._unescape(m.group(1)).split("-")[0].strip()
        pic = ""
        m = re.search(r'data-original="(https?://[^"]+)"', html or "")
        if m:
            pic = m.group(1)
        play_url = self._extract_play_url(html or "")
        if play_url and ".m3u8" in play_url:
            play_url = self._resolve_m3u8(play_url)
        if not play_url:
            play_url = play_page
        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": name or f"视频{vod_id}",
                "vod_pic": pic,
                "vod_content": name,
                "vod_play_from": "线路1",
                "vod_play_url": f"正片${play_url}",
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        pg = str(pg or "1")
        q = quote(key)
        if pg == "1":
            url = f"{self.host}{self.prefix}/index.php/vod/search/wd/{q}.html"
        else:
            url = f"{self.host}{self.prefix}/index.php/vod/search/wd/{q}/page/{pg}.html"
        html = self._get(url)
        if not html:
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 0, "total": 0}
        videos = self._parse_list(html)
        return {"list": videos, "page": int(pg), "pagecount": 1, "limit": 24, "total": len(videos)}

    def playerContent(self, flag, id, vipFlags=None):
        url = id
        if not url.startswith("http"):
            play_page = f"{self.host}{self.prefix}/index.php/vod/play/id/{id}/sid/1/nid/1.html"
            html = self._get(play_page)
            url = self._extract_play_url(html or "") or play_page
        if ".m3u8" in url:
            url = self._resolve_m3u8(url)
        header = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + self.prefix + "/",
            "Origin": self.host,
        }
        if ".m3u8" in url:
            proxy = self._proxy_m3u8_url(url)
            return {"parse": 0, "jx": 0, "url": proxy, "header": header}
        return {"parse": 0, "jx": 0, "url": url, "header": header}

    def _proxy_m3u8_url(self, url):
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if not base:
                    return url
                if "?" in base:
                    return base + "&url=" + quote(url) + "&type=m3u8"
                return base + "?url=" + quote(url) + "&type=m3u8"
        except Exception:
            pass
        return url

    def localProxy(self, param):
        try:
            if isinstance(param, dict):
                url = param.get("url") or param.get("u") or ""
            else:
                url = str(param) if param else ""
            if not url:
                return [404, "text/plain", ""]
            body = self._fetch_raw(url)
            if not body:
                return [502, "text/plain", "fetch failed"]
            if "#EXT-X-STREAM-INF" in body and "#EXTINF" not in body:
                for line in body.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and ".m3u8" in line:
                        sub = line if line.startswith("http") else urljoin(url, line)
                        body = self._fetch_raw(sub)
                        url = sub
                        break
            cleaned = self._clean_m3u8(body or "", url)
            return [200, "application/vnd.apple.mpegurl", cleaned]
        except Exception as e:
            return [500, "text/plain", str(e)[:200]]

    def _clean_m3u8(self, content, base_url=""):
        if not content or "#EXTM3U" not in content:
            return content
        parsed = urlparse(base_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        base_date = None
        m = re.search(r"/(20\d{6})/", base_url)
        if m:
            base_date = m.group(1)
        lines = [l.strip() for l in content.splitlines()]
        real_start = 0
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-KEY") and "AES-128" in line and "METHOD=NONE" not in line:
                real_start = i
                break
        header = []
        for line in lines:
            if line.startswith("#EXTM3U") or line.startswith("#EXT-X-VERSION") or \
               line.startswith("#EXT-X-TARGETDURATION") or line.startswith("#EXT-X-PLAYLIST-TYPE") or \
               line.startswith("#EXT-X-MEDIA-SEQUENCE") or line.startswith("#DISC"):
                header.append(line)
            elif line.startswith("#EXTINF") or line.startswith("#EXT-X-KEY") or \
                 line.startswith("#EXT-X-DISCONTINUITY") or (line and not line.startswith("#")):
                break
        body_lines = lines[real_start:] if real_start > 0 else lines
        out = list(header)
        if "#EXT-X-MEDIA-SEQUENCE" not in "\n".join(out):
            out.append("#EXT-X-MEDIA-SEQUENCE:0")
        i = 0
        while i < len(body_lines):
            line = body_lines[i]
            if line.startswith("#EXT-X-KEY"):
                if "METHOD=NONE" in line:
                    i += 1
                    continue
                mk = re.search(r'URI="([^"]+)"', line)
                if mk:
                    key_uri = mk.group(1)
                    if key_uri.startswith("/"):
                        line = line.replace(f'URI="{key_uri}"', f'URI="{base_origin + key_uri}"')
                    elif not key_uri.startswith("http"):
                        line = line.replace(f'URI="{key_uri}"', f'URI="{urljoin(base_url, key_uri)}"')
                out.append(line)
                i += 1
                continue
            if line.startswith("#EXTINF:"):
                next_line = body_lines[i + 1] if i + 1 < len(body_lines) else ""
                abs_next = next_line
                if next_line.startswith("/") and not next_line.startswith("//"):
                    abs_next = base_origin + next_line
                is_ad = False
                if base_date and abs_next:
                    md = re.search(r"/(20\d{6})/", abs_next)
                    if md and md.group(1) != base_date:
                        is_ad = True
                if is_ad:
                    i += 2
                    continue
                out.append(line)
                if abs_next:
                    out.append(abs_next)
                    i += 2
                    continue
            elif line.startswith("#EXT-X-DISCONTINUITY"):
                i += 1
                continue
            elif line.startswith("#EXT-X-ENDLIST"):
                out.append(line)
                i += 1
            else:
                if line and not line.startswith("#"):
                    if line.startswith("/") and not line.startswith("//"):
                        line = base_origin + line
                    if base_date:
                        md = re.search(r"/(20\d{6})/", line)
                        if md and md.group(1) != base_date:
                            i += 1
                            continue
                    out.append(line)
                elif line.startswith("#"):
                    out.append(line)
                i += 1
        return "\n".join(out)

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False
