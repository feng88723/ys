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

import re, time
from urllib.parse import quote, urljoin, urlparse

class Spider(BaseSpider):
    def getName(self):
        return "蜜桃臀"

    def init(self, extend=""):
        self.host = "https://okav30.cc"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.skip_tids = {"70"}

    def getDependence(self):
        return ""

    def _get(self, url, retry=2):
        import urllib.request
        for i in range(retry + 1):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode("utf-8", errors="ignore")
            except Exception:
                if i == retry:
                    return ""
                time.sleep(0.5)
        return ""

    def homeContent(self, filter=None):
        classes = [
            {"type_id": "43", "type_name": "国产AV"},
            {"type_id": "45", "type_name": "欧美AV"},
            {"type_id": "44", "type_name": "日本AV"},
            {"type_id": "47", "type_name": "成人动漫"},
            {"type_id": "48", "type_name": "中文av"},
            {"type_id": "50", "type_name": "乱伦侵犯"},
            {"type_id": "51", "type_name": "探花约炮"},
            {"type_id": "65", "type_name": "口交自慰"},
            {"type_id": "66", "type_name": "群交多P"},
            {"type_id": "67", "type_name": "AI换脸"},
            {"type_id": "71", "type_name": "丝袜制服"},
            {"type_id": "73", "type_name": "成人短剧"},
            {"type_id": "52", "type_name": "色情主播"},
            {"type_id": "62", "type_name": "网爆吃瓜"},
            {"type_id": "55", "type_name": "伦理三级"},
            {"type_id": "63", "type_name": "反差母狗"},
            {"type_id": "57", "type_name": "av解说"},
            {"type_id": "58", "type_name": "重口味"},
            {"type_id": "56", "type_name": "偷拍偷窥"},
            {"type_id": "54", "type_name": "麻豆传媒"},
            {"type_id": "60", "type_name": "男同女同"},
            {"type_id": "59", "type_name": "人妖TS"},
            {"type_id": "64", "type_name": "异域风情"},
            {"type_id": "69", "type_name": "厂牌经典"},
            {"type_id": "49", "type_name": "日本有码"},
            {"type_id": "68", "type_name": "素人特摄"},
            {"type_id": "72", "type_name": "日韩精选"},
            {"type_id": "61", "type_name": "骑兵破解"},
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self.categoryContent("43", "1")

    def categoryContent(self, tid, pg, filter=None, extend=None):
        if str(tid) in self.skip_tids:
            return {"page": int(pg or 1), "pagecount": 1, "limit": 0, "total": 0, "list": []}
        pg = str(pg or "1")
        if pg == "1":
            url = f"{self.host}/index.php/vod/type/id/{tid}.html"
        else:
            url = f"{self.host}/index.php/vod/type/id/{tid}/page/{pg}.html"
        html = self._get(url)
        if not html:
            return {"page": int(pg), "pagecount": 1, "limit": 0, "total": 0, "list": []}
        videos = self._parse_list(html)
        pagecount = 1
        if f"/page/{int(pg)+1}.html" in html:
            pagecount = int(pg) + 1
        m = re.search(r"/page/(\d+)\.html", html)
        if m:
            pagecount = max(pagecount, int(m.group(1)))
        return {
            "page": int(pg),
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
            "list": videos
        }

    def _parse_list(self, html):
        videos = []
        blocks = re.split(r'<div class="video-item">', html)
        for block in blocks[1:]:
            m_id = re.search(r'href="(/index\.php/vod/(?:detail|play)/id/(\d+)\.html)"', block)
            if not m_id:
                continue
            vid = m_id.group(2)
            pic = ""
            m_pic = re.search(r'data-src="(https?://[^"]+)"', block)
            if m_pic:
                pic = m_pic.group(1)
            else:
                m_pic = re.search(r'src="(https://img\.[^"]+)"', block)
                if m_pic:
                    pic = m_pic.group(1)
            name = ""
            m_alt = re.search(r'alt="([^"]*)"', block)
            if m_alt:
                name = self._unescape(m_alt.group(1)).strip()
            if not name or len(name) < 2 or name in ("avatar", "蜜桃臀高清AV"):
                m_title = re.search(r'title="([^"]{4,80})"', block)
                if m_title:
                    name = self._unescape(m_title.group(1)).strip()
            if not name or len(name) < 2:
                continue
            remarks = ""
            m_du = re.search(r'data-url="([^"]*)"', block)
            if m_du and "#" in m_du.group(1):
                remarks = f"{m_du.group(1).count('#')+1}线路"
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic.startswith("http") else (self.host + pic if pic else ""),
                "vod_remarks": remarks
            })
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

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        if isinstance(ids, (list, tuple)):
            vod_id = str(ids[0])
        else:
            vod_id = str(ids)
        url = f"{self.host}/index.php/vod/play/id/{vod_id}.html"
        html = self._get(url)
        if not html:
            return {"list": []}
        name = ""
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            name = self._unescape(m.group(1)).split("-")[0].strip()
        if not name:
            m = re.search(r'alt="([^"]{4,80})"', html)
            if m:
                name = self._unescape(m.group(1)).strip()
        pic = ""
        m = re.search(r'data-src="(https://img\.[^"]+)"', html)
        if m:
            pic = m.group(1)
        play_from = []
        play_url = []
        m3u8s = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
        seen = set()
        for u in m3u8s:
            if u in seen:
                continue
            seen.add(u)
            play_from.append(f"线路{len(play_from)+1}")
            play_url.append(f"正片${u}")
        if not play_from:
            data_urls = re.findall(r'data-url="([^"]+)"', html)
            for du in data_urls[:1]:
                parts = du.split("#")
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    if "$" in p:
                        _, u = p.split("$", 1)
                    else:
                        u = p
                    if u in seen:
                        continue
                    seen.add(u)
                    play_from.append(f"线路{len(play_from)+1}")
                    play_url.append(f"正片${u}")
        if not play_from:
            play_from = ["默认"]
            play_url = [f"正片${url}"]
        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": name or f"视频{vod_id}",
                "vod_pic": pic,
                "vod_content": name,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url)
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        pg = str(pg or "1")
        url = f"{self.host}/index.php/vod/search.html?wd={quote(key)}"
        if pg != "1":
            url = f"{self.host}/index.php/vod/search/page/{pg}.html?wd={quote(key)}"
        html = self._get(url)
        if not html:
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 0, "total": 0}
        videos = self._parse_list(html)
        return {
            "list": videos,
            "page": int(pg),
            "pagecount": 1,
            "limit": 24,
            "total": len(videos)
        }

    def playerContent(self, flag, id, vipFlags=None):
        url = id
        if not url.startswith("http"):
            play_url = f"{self.host}/index.php/vod/play/id/{id}.html"
            html = self._get(play_url)
            m3u8s = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html or "")
            if m3u8s:
                url = m3u8s[0]
            else:
                url = play_url
        header = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host
        }
        if ".m3u8" in url:
            proxy = self._proxy_m3u8_url(url)
            return {
                "parse": 0,
                "jx": 0,
                "url": proxy,
                "header": header
            }
        return {
            "parse": 0,
            "jx": 0,
            "url": url,
            "header": header
        }

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
            import urllib.request
            hdrs = dict(self.headers)
            hdrs["Referer"] = self.host + "/"
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            cleaned = self._clean_m3u8(content, url)
            return [200, "application/vnd.apple.mpegurl", cleaned]
        except Exception as e:
            return [500, "text/plain", str(e)[:200]]

    def _clean_m3u8(self, content, base_url=""):
        if not content or "#EXTM3U" not in content:
            return content
        parsed = urlparse(base_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        lines = content.splitlines()
        out = []
        i = 0
        seen_discontinuity = False
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXT-X-DISCONTINUITY"):
                seen_discontinuity = True
                out.append(line)
                i += 1
                continue
            if line.startswith("#EXT-X-KEY"):
                m = re.search(r'URI="([^"]+)"', line)
                if m:
                    key_uri = m.group(1)
                    if key_uri.startswith("/"):
                        abs_key = base_origin + key_uri
                        line = line.replace(f'URI="{key_uri}"', f'URI="{abs_key}"')
                    elif not key_uri.startswith("http"):
                        abs_key = urljoin(base_url, key_uri)
                        line = line.replace(f'URI="{key_uri}"', f'URI="{abs_key}"')
                out.append(line)
                i += 1
                continue
            if line.startswith("#EXTINF:"):
                dur = 0.0
                try:
                    dur = float(line.split(":")[1].split(",")[0])
                except Exception:
                    pass
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                is_ad = False
                if not seen_discontinuity and next_line:
                    if "vod.18j" in next_line or "/stream/" in next_line:
                        is_ad = True
                    elif self._is_ad_segment(next_line, dur):
                        is_ad = True
                if is_ad:
                    i += 2
                    continue
                out.append(line)
                if next_line:
                    if next_line.startswith("/") and not next_line.startswith("//"):
                        next_line = base_origin + next_line
                    out.append(next_line)
                    i += 2
                    continue
            elif line.startswith("#EXT-X-STREAM-INF"):
                out.append(line)
                if i + 1 < len(lines):
                    out.append(lines[i + 1])
                    i += 2
                    continue
            else:
                out.append(line)
            i += 1
        result = "\n".join(out)
        if "#EXT-X-MEDIA-SEQUENCE" not in result and "#EXTM3U" in result:
            result = result.replace("#EXTM3U", "#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:0", 1)
        return result

    def _is_ad_segment(self, url, duration):
        if not url:
            return False
        low = url.lower()
        if any(k in low for k in ["ad", "gg", "adv", "preroll", "ads", "banner", "pre-roll"]):
            return True
        if duration > 0 and duration <= 1.5:
            return True
        return False

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False
