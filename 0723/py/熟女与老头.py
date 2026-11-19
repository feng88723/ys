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
        return "熟女与老头"

    def init(self, extend=""):
        self.host = "https://www.mzdmm1.top"
        self.prefix = "/go"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + self.prefix + "/",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.skip_tids = {"83"}

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
                time.sleep(0.4)
        return ""

    def homeContent(self, filter=None):
        classes = [
            {"type_id": "33", "type_name": "精品推荐"},
            {"type_id": "67", "type_name": "国产视频"},
            {"type_id": "68", "type_name": "中文字幕"},
            {"type_id": "69", "type_name": "国产传媒"},
            {"type_id": "70", "type_name": "日本有码"},
            {"type_id": "71", "type_name": "日本无码"},
            {"type_id": "72", "type_name": "强奸乱伦"},
            {"type_id": "73", "type_name": "制服诱惑"},
            {"type_id": "74", "type_name": "国产主播"},
            {"type_id": "75", "type_name": "激情动漫"},
            {"type_id": "76", "type_name": "明星换脸"},
            {"type_id": "77", "type_name": "抖阴视频"},
            {"type_id": "78", "type_name": "女优明星"},
            {"type_id": "79", "type_name": "网曝黑料"},
            {"type_id": "80", "type_name": "伦理三级"},
            {"type_id": "81", "type_name": "AV解说"},
            {"type_id": "82", "type_name": "SM调教"},
            {"type_id": "84", "type_name": "极品媚黑"},
            {"type_id": "85", "type_name": "女同性恋"},
            {"type_id": "86", "type_name": "网红头条"},
            {"type_id": "34", "type_name": "国产主播"},
            {"type_id": "35", "type_name": "国产乱伦"},
            {"type_id": "36", "type_name": "自拍偷拍"},
            {"type_id": "38", "type_name": "网曝事件"},
            {"type_id": "39", "type_name": "传媒探花"},
            {"type_id": "42", "type_name": "中文字幕"},
            {"type_id": "43", "type_name": "制服诱惑"},
            {"type_id": "44", "type_name": "淫妻作乐"},
            {"type_id": "45", "type_name": "港台辣妹"},
            {"type_id": "46", "type_name": "足浴撩妹"},
            {"type_id": "47", "type_name": "反差母狗"},
            {"type_id": "48", "type_name": "AI换脸"},
            {"type_id": "49", "type_name": "VR视角"},
            {"type_id": "50", "type_name": "重口性癖"},
            {"type_id": "52", "type_name": "无码流出"},
            {"type_id": "53", "type_name": "丝袜美腿"},
            {"type_id": "54", "type_name": "多人群交"},
            {"type_id": "55", "type_name": "凌辱快感"},
            {"type_id": "56", "type_name": "角色剧情"},
            {"type_id": "58", "type_name": "韩国三级"},
            {"type_id": "59", "type_name": "欧美激情"},
            {"type_id": "60", "type_name": "人妻熟女"},
            {"type_id": "61", "type_name": "主奴调教"},
            {"type_id": "62", "type_name": "动漫卡通"},
            {"type_id": "63", "type_name": "变性伪娘"},
            {"type_id": "65", "type_name": "野外露出"},
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self.categoryContent("67", "1")

    def categoryContent(self, tid, pg, filter=None, extend=None):
        if str(tid) in self.skip_tids:
            return {"page": int(pg or 1), "pagecount": 1, "limit": 0, "total": 0, "list": []}
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
        if f"/page/{int(pg)+1}.html" in html:
            pagecount = int(pg) + 1
        m = re.search(r"/page/(\d+)\.html", html)
        if m:
            pagecount = max(pagecount, int(m.group(1)))
        return {"page": int(pg), "pagecount": pagecount, "limit": 24, "total": pagecount * 24, "list": videos}

    def _parse_list(self, html):
        videos = []
        pattern = r'<div class="video-play[^"]*">\s*<a href="(/go/index\.php/vod/play/id/(\d+)/[^"]*)"[^>]*title="([^"]*)"[^>]*>\s*<img[^>]+src="([^"]+)"'
        for m in re.finditer(pattern, html, re.S):
            href, vid, name, pic = m.groups()
            name = self._unescape(name).strip()
            if not name or len(name) < 2:
                continue
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic.startswith("http") else urljoin(self.host, pic),
                "vod_remarks": ""
            })
        if not videos:
            for m in re.finditer(r'href="(/go/index\.php/vod/play/id/(\d+)/[^"]*)"[^>]*title="([^"]*)"', html):
                href, vid, name = m.groups()
                name = self._unescape(name).strip()
                if name and len(name) > 2:
                    videos.append({"vod_id": vid, "vod_name": name, "vod_pic": "", "vod_remarks": ""})
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
        """主列表含相对路径时，解析出真正的媒体 m3u8 绝对地址"""
        if not url or ".m3u8" not in url:
            return url
        body = self._get(url)
        if not body:
            return url
        # 已是媒体列表
        if "#EXTINF" in body and "#EXT-X-STREAM-INF" not in body:
            return url
        # 主列表：取第一条子列表并转绝对
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ".m3u8" in line:
                if line.startswith("http"):
                    return line
                return urljoin(url, line)
        return url

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        url = f"{self.host}{self.prefix}/index.php/vod/play/id/{vod_id}/sid/1/nid/1.html"
        html = self._get(url)
        if not html:
            return {"list": []}
        name = ""
        play_url = ""
        m_url = re.search(r'"url"\s*:\s*"(https?:\\/\\/[^"]+\.m3u8[^"]*)"', html)
        if m_url:
            play_url = m_url.group(1).replace("\\/", "/")
        if not play_url:
            m3 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
            if m3:
                play_url = m3.group(1)
        m_name = re.search(r'"vod_name"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        if m_name:
            try:
                name = m_name.group(1).encode("utf-8").decode("unicode_escape")
            except Exception:
                name = self._unescape(m_name.group(1))
        if not name:
            m2 = re.search(r"<title>([^<]+)</title>", html)
            if m2:
                name = self._unescape(m2.group(1)).split("_")[0].replace("正在线播放", "").strip()
        pic = ""
        m4 = re.search(r'<img[^>]+src="(https?://[^"]+)"', html)
        if m4:
            pic = m4.group(1)
        if play_url:
            play_url = self._resolve_m3u8(play_url)
        if not play_url:
            play_url = url
        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": name or f"视频{vod_id}",
                "vod_pic": pic,
                "vod_content": name,
                "vod_play_from": "线路1",
                "vod_play_url": f"正片${play_url}"
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        pg = str(pg or "1")
        url = f"{self.host}{self.prefix}/index.php/vod/search.html?wd={quote(key)}"
        if pg != "1":
            url = f"{self.host}{self.prefix}/index.php/vod/search/page/{pg}.html?wd={quote(key)}"
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
            m_url = re.search(r'"url"\s*:\s*"(https?:\\/\\/[^"]+\.m3u8[^"]*)"', html or "")
            if m_url:
                url = m_url.group(1).replace("\\/", "/")
            if not url.startswith("http"):
                m3 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html or "")
                if m3:
                    url = m3.group(1)
                else:
                    url = play_page
        if ".m3u8" in url:
            url = self._resolve_m3u8(url)
        header = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + self.prefix + "/",
            "Origin": self.host
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
            import urllib.request
            hdrs = dict(self.headers)
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            # 若仍是主列表，再解析一次
            if "#EXT-X-STREAM-INF" in content and "#EXTINF" not in content:
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and ".m3u8" in line:
                        sub = line if line.startswith("http") else urljoin(url, line)
                        req2 = urllib.request.Request(sub, headers=hdrs)
                        with urllib.request.urlopen(req2, timeout=15) as resp2:
                            content = resp2.read().decode("utf-8", errors="ignore")
                        url = sub
                        break
            cleaned = self._clean_m3u8(content, url)
            return [200, "application/vnd.apple.mpegurl", cleaned]
        except Exception as e:
            return [500, "text/plain", str(e)[:200]]

    def _clean_m3u8(self, content, base_url=""):
        if not content or "#EXTM3U" not in content:
            return content
        parsed = urlparse(base_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        lines = [l.strip() for l in content.splitlines()]
        # 找到第一个真正的 AES-128 KEY（非 METHOD=NONE）位置，前面全是贴片
        real_start = 0
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-KEY") and "AES-128" in line and "METHOD=NONE" not in line:
                real_start = i
                break
        # 保留头部标签 + 从 real_start 开始的内容
        header = []
        for line in lines:
            if line.startswith("#EXTM3U") or line.startswith("#EXT-X-VERSION") or \
               line.startswith("#EXT-X-TARGETDURATION") or line.startswith("#EXT-X-PLAYLIST-TYPE") or \
               line.startswith("#EXT-X-MEDIA-SEQUENCE"):
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
                m = re.search(r'URI="([^"]+)"', line)
                if m:
                    key_uri = m.group(1)
                    if key_uri.startswith("/"):
                        line = line.replace(f'URI="{key_uri}"', f'URI="{base_origin + key_uri}"')
                    elif not key_uri.startswith("http"):
                        line = line.replace(f'URI="{key_uri}"', f'URI="{urljoin(base_url, key_uri)}"')
                out.append(line)
                i += 1
                continue
            if line.startswith("#EXTINF:"):
                next_line = body_lines[i + 1] if i + 1 < len(body_lines) else ""
                # 跳过仍是贴片目录的段
                if next_line and ("/20261008/" in next_line or "/7Lzh4PuW/" in next_line):
                    i += 2
                    continue
                out.append(line)
                if next_line:
                    if next_line.startswith("/") and not next_line.startswith("//"):
                        next_line = base_origin + next_line
                    out.append(next_line)
                    i += 2
                    continue
            elif line.startswith("#EXT-X-DISCONTINUITY"):
                # 跳过贴片后的 discontinuity（已切到正片）
                i += 1
                continue
            elif line.startswith("#EXT-X-ENDLIST"):
                out.append(line)
                i += 1
            else:
                if line and not line.startswith("#"):
                    if line.startswith("/") and not line.startswith("//"):
                        line = base_origin + line
                    if "/20261008/" not in line and "/7Lzh4PuW/" not in line:
                        out.append(line)
                elif line.startswith("#"):
                    out.append(line)
                i += 1
        return "\n".join(out)

    def _is_ad_segment(self, url, duration):
        if not url:
            return False
        low = url.lower()
        if any(k in low for k in ["ad", "gg", "adv", "preroll", "ads", "banner"]):
            return True
        if duration > 0 and duration <= 1.5:
            return True
        return False

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False
