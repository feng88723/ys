# -*- coding: utf-8 -*-
"""
MAXJAV 四壳通用 Python Spider
站点: https://maxjav.xyz/ (JAV Max Quality 番号资料站, WordPress)
结构: /{id}/{slug}/ 详情 | /category/{slug}/ 分类 | /page/{n}/ 分页 | /?s={kw} 搜索
播放: 详情页 emload.com 网盘文件页 (番号.mkv 下载)
防护: Cloudflare Turnstile (自动内置默认反代, 支持 ext.direct 直连)
"""
import re
import os
import json
import urllib.parse
import urllib.request
import ssl

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""):
            pass

class Spider(_BaseSpider):
    name = "MAXJAV"
    host = "https://maxjav.xyz"
    rawSite = "https://maxjav.xyz"
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"

    def init(self, extend=""):
        self.ext = {}
        if extend:
            try:
                self.ext = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                self.ext = {}
        # 铁律15: CF站点默认启用反代
        self.siteUrl = self.ext.get("proxy") or self.ext.get("siteUrl") or self.rawSite
        if self.ext.get("direct"):
            self.siteUrl = self.rawSite
        self.HOST = self.siteUrl

        self.categories = [
            {"type_id": "uncensored", "type_name": "无码Uncen"},
            {"type_id": "decensored", "type_name": "去码Decen"},
            {"type_id": "hd", "type_name": "高清HD"},
            {"type_id": "4k", "type_name": "4K"},
            {"type_id": "8k", "type_name": "8K"},
            {"type_id": "bluray", "type_name": "蓝光BD"},
            {"type_id": "vr", "type_name": "VR"},
            {"type_id": "amatuer", "type_name": "素人Amatuer"},
            {"type_id": "leaks", "type_name": "流出Leak"},
            {"type_id": "colls", "type_name": "合集Colls"},
        ]
        self.filter_dict = {}
        for c in self.categories:
            self.filter_dict[c["type_id"]] = []
        self._ssl_ctx = ssl.create_default_context()
        try:
            self._ssl_ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        except Exception:
            pass

    def getDependence(self):
        return ""

    def _is_challenge(self, html):
        """检测CF挑战页"""
        if not html:
            return True
        if "Just a moment" in html or "正在进行安全验证" in html or "请稍候" in html:
            return True
        if "cf-browser-verification" in html or "challenge-platform" in html:
            return True
        return False

    def _http_get(self, url, timeout=10):
        """单通道GET, 返回 (html, error)"""
        req = urllib.request.Request(url, headers={
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.rawSite + "/",
        })
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self._ssl_ctx))
        resp = opener.open(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="ignore")

    def _fetch(self, url, timeout=10):
        """多通道容错: ext.proxy反代 → 默认反代 → 直连, 挑战页自动切换"""
        # 组装各通道URL (域名替换式反代)
        channels = []
        # 通道1: 用户配置的反代 (ext.proxy / ext.siteUrl)
        if self.ext.get("proxy") and self.siteUrl != self.rawSite:
            channels.append(url.replace(self.rawSite, self.siteUrl))
        # 通道2: 默认反代 (从配置文件读取)
        default_proxy = self._default_proxy()
        if default_proxy and default_proxy not in (self.siteUrl,):
            channels.append(url.replace(self.rawSite, default_proxy))
        # 通道3: 当前siteUrl (直连或已配反代)
        if self.siteUrl != self.rawSite:
            channels.append(url.replace(self.rawSite, self.siteUrl))
        # 通道4: 直连
        channels.append(url)

        # 去重保序
        seen = set()
        uniq = []
        for c in channels:
            if c not in seen:
                seen.add(c)
                uniq.append(c)

        last_err = None
        for ch in uniq:
            try:
                html = self._http_get(ch, timeout=timeout)
                if self._is_challenge(html):
                    last_err = "CF challenge from " + ch[:60]
                    continue
                return html
            except Exception as e:
                last_err = str(e)[:80]
                continue
        if last_err:
            raise Exception(last_err)
        return ""

    def _default_proxy(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            for cand in [os.path.join(base, "assets", "proxy_config.json"),
                         os.path.join(os.path.dirname(base), "assets", "proxy_config.json")]:
                if os.path.isfile(cand):
                    import json as _json
                    cfg = _json.load(open(cand, encoding="utf-8"))
                    return cfg.get("default_proxy", "")
        except Exception:
            pass
        return "https://xsz-shared-proxy.97471201.workers.dev"

    def _to_site(self, path):
        """把 rawSite 路径映射到当前 siteUrl(反代)"""
        if self.siteUrl == self.rawSite:
            return path
        return self.siteUrl + path.replace(self.rawSite, "")

    def _parse_list(self, html):
        vod_list = []
        # 卡片: <div class="post post-{id}..." id="post-{id}"> ... <h2 class="title"><a href="{host}/{id}/{slug}/">标题</a></h2> ... <img src="...">
        posts = re.findall(r'<div[^>]*class="[^"]*post[^"]*"[^>]*id="post-(\d+)"[^>]*>(.*?)</div>\s*(?=<div|</div>|$)', html, re.S)
        if not posts:
            posts = re.findall(r'id="post-(\d+)"[^>]*>(.*?)(?=<div[^>]*id="post-|</div>|$)', html, re.S)
        if not posts:
            # 兜底: 直接匹配文章链接
            arts = re.findall(r'href=["\']([^"\']*?/(\d+)/[^"\']*/)["\'][^>]*>([^<]{2,120})</a>', html)
            for href, pid, title in arts:
                href = href.replace("http://web.archive.org", "").replace("https://web.archive.org", "")
                if "maxjav" in href or href.startswith("/"):
                    vod_list.append({
                        "vod_id": pid,
                        "vod_name": title.strip(),
                        "vod_pic": "",
                        "vod_remarks": "",
                    })
            return vod_list

        for pid, body in posts:
            try:
                link_m = re.search(r'href=["\']([^"\']*?/' + re.escape(pid) + r'/[^"\']*/)["\']', body)
                if not link_m:
                    continue
                href = link_m.group(1)
                href = href.replace("http://web.archive.org", "").replace("https://web.archive.org", "")
                # 图片
                img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', body)
                vod_pic = img_m.group(1) if img_m else ""
                if vod_pic.startswith("//"):
                    vod_pic = "https:" + vod_pic
                # 标题
                title_m = re.search(r'<h[123][^>]*>(?:<a[^>]*>)?(.*?)(?:</a>)?</h[123]>', body, re.S)
                vod_name = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else pid
                # 备注: 从分类/标签提取
                remark_m = re.findall(r'category-([\w\-]+)', body)
                vod_remarks = ""
                if remark_m:
                    tags = [r for r in set(remark_m) if r not in ("type-post", "status-publish", "hentry")]
                    if tags:
                        vod_remarks = " ".join(list(tags)[:2])
                vod_list.append({
                    "vod_id": pid,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks,
                })
            except Exception:
                continue
        return vod_list

    def _parse_total(self, html):
        total_m = re.search(r'class=["\']pages["\'][^>]*>.*?(\d+)\s*</a>', html, re.S)
        if total_m:
            return int(total_m.group(1)) * 10
        page_nums = re.findall(r'/page/(\d+)/', html)
        if page_nums:
            return max(int(p) for p in page_nums) * 10
        # WP分页 "Older posts" 等
        return 10

    def homeContent(self, *args):
        result = {"class": self.categories, "filters": self.filter_dict, "list": []}
        try:
            html = self._fetch(self._to_site(self.rawSite + "/"))
            result["list"] = self._parse_list(html)
        except Exception:
            pass
        return result

    def homeVideoContent(self, *args):
        return {"page": 1, "pagecount": 1, "limit": 10, "total": 0, "list": []}

    def categoryContent(self, *args):
        tid = str(args[0]) if args else "uncensored"
        pg = int(args[1]) if len(args) > 1 and args[1] else 1
        if isinstance(tid, dict):
            tid = tid.get("tid", "uncensored")
            pg = int(tid.get("pg", 1))
        page_path = f"/page/{pg}/" if pg > 1 else "/"
        url = self._to_site(f"{self.rawSite}/category/{tid}{page_path}")
        try:
            html = self._fetch(url)
            vod_list = self._parse_list(html)
            total = self._parse_total(html)
            pagecount = (total + 10 - 1) // 10 if total else 1
            return {"page": pg, "pagecount": pagecount, "limit": 10, "total": total, "list": vod_list}
        except Exception:
            return {"page": pg, "pagecount": 1, "limit": 10, "total": 0, "list": []}

    def detailContent(self, *args):
        ids = args[0] if args else []
        if isinstance(ids, str):
            ids = [ids]
        result_list = []
        for vid in ids:
            try:
                # 详情页URL: 可能是 /{id}/{slug}/ 或 /?p={id}
                url = self._to_site(f"{self.rawSite}/?p={str(vid)}")
                html = self._fetch(url)
                # 如果重定向到文章页则URL含slug; 直接解析
                title_m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html)
                vod_name = title_m.group(1).strip() if title_m else ""
                if not vod_name:
                    # h2.title (文章标题, 排除站点名)
                    t2 = re.search(r'<h[12][^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>\s*<a[^>]*>(.*?)</a>', html, re.S)
                    vod_name = re.sub(r'<[^>]+>', '', t2.group(1)).strip() if t2 else ""
                if not vod_name:
                    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
                    vod_name = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else str(vid)
                if vod_name == "JAV Max Quality" or vod_name == "maxJAV":
                    vod_name = str(vid)
                # 封面
                img_m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
                vod_pic = img_m.group(1) if img_m else ""
                if not vod_pic:
                    imgs = re.findall(r'<img[^>]+src=["\']([^"\']*?(?:pics\.dmm|blogspot|postimg)[^"\']+)["\']', html)
                    if imgs:
                        vod_pic = imgs[0]
                # 番号信息
                info = self._parse_info(html)
                # 播放源: emload下载链接
                play_from = "EMLOAD"
                play_url = self._parse_emload(html)
                vod = {
                    "vod_id": str(vid),
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_content": info["content"],
                    "vod_play_from": play_from,
                    "vod_play_url": play_url,
                    "vod_remarks": info["remarks"],
                    "type_name": "番号",
                }
                result_list.append(vod)
            except Exception:
                continue
        return {"list": result_list}

    def _parse_info(self, html):
        content_parts = []
        remarks = ""
        # 番号信息是文本行形式: "ID: SNIS144 / Release Date: ... / Length: ... / Director: ... / Maker: ... / Label: ..."
        # 先提取正文区域(排除script/style)
        body = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.S)
        body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.S)
        body = re.sub(r'<[^>]+>', '\n', body)
        body = body.replace('&nbsp;', ' ').replace('&#8211;', '-').replace('&amp;', '&')
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        field_map = {
            'id': '番号', 'release date': '发行日期', 'length': '时长',
            'director': '导演', 'maker': '制作商', 'label': '发行标签',
            'quality video': '画质', 'bitrate': '码率', 'series': '系列',
        }
        for l in lines:
            m = re.match(r'^([A-Za-z ]+?)\s*:\s*(.+)$', l)
            if m:
                k = m.group(1).strip().lower()
                v = m.group(2).strip()
                if k in field_map:
                    content_parts.append(f"{field_map[k]}: {v}")
                    if k == 'id' and not remarks:
                        remarks = v.replace(' ', '').upper()
        return {
            "content": "\n".join(content_parts) if content_parts else "",
            "remarks": remarks,
        }

    def _parse_emload(self, html):
        # 详情页下载链接: emload.com/file/{fid}/{name} (兼容archive重写前缀)
        links = re.findall(r'href=["\']([^"\']*emload\.com/file/[^"\']+)["\']', html)
        links = [re.sub(r'https?://web\.archive\.org/web/\d+/', '', l) for l in links]
        if links:
            return "#".join(links[:3])
        # 兜底: 任意 .mkv/.mp4 链接
        links2 = re.findall(r'href=["\']([^"\']*?\.(?:mkv|mp4)[^"\']*)["\']', html)
        links2 = [re.sub(r'https?://web\.archive\.org/web/\d+/', '', l) for l in links2]
        if links2:
            return "#".join(links2[:3])
        return ""

    def playerContent(self, *args):
        flag = args[0] if args else ""
        id_str = str(args[1]) if len(args) > 1 else ""
        if not id_str:
            return {"parse": 0, "jx": 0, "url": "", "header": {}}
        # id_str 是 emload 文件页URL 或 详情页URL
        if id_str.startswith("http"):
            return {
                "parse": 0,
                "jx": 0,
                "url": id_str,
                "header": {"User-Agent": self.ua, "Referer": self.rawSite + "/"}
            }
        # 番号形式: 尝试详情页找emload
        try:
            url = self._to_site(f"{self.rawSite}/?p={id_str}")
            html = self._fetch(url)
            em = self._parse_emload(html)
            if em:
                return {
                    "parse": 0,
                    "jx": 0,
                    "url": em.split("#")[0],
                    "header": {"User-Agent": self.ua, "Referer": self.rawSite + "/"}
                }
        except Exception:
            pass
        return {"parse": 0, "jx": 0, "url": "", "header": {}}

    def searchContent(self, *args):
        wd = args[0] if args else ""
        pg = int(args[1]) if len(args) > 1 and args[1] else 1
        if isinstance(wd, dict):
            wd = wd.get("wd", "")
            pg = int(wd.get("pg", 1))
        try:
            search_url = self._to_site(f"{self.rawSite}/page/{pg}/?s={urllib.parse.quote(str(wd))}")
            html = self._fetch(search_url)
            vod_list = self._parse_list(html)
            total = self._parse_total(html)
            pagecount = (total + 10 - 1) // 10 if total else 1
            return {"page": pg, "pagecount": pagecount, "limit": 10, "total": total, "list": vod_list}
        except Exception:
            return {"page": pg, "pagecount": 1, "limit": 10, "total": 0, "list": []}

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    def getProxyUrl(self, *args):
        return ""

    def isVideoFormat(self, url):
        return any(url.lower().endswith(ext) for ext in [".m3u8", ".mp4", ".mkv", ".avi", ".flv"])

    def check(self, *args):
        return True

    def destroy(self, *args):
        pass

    def getName(self):
        return self.name
