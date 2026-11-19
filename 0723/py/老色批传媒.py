# -*- coding: utf-8 -*-
"""
老色批传媒 四壳通用Python Spider
站点: https://xn--qxu.lspcm.pro  (入口 /?source=m5vo49d30h 为空壳, 真入口根路径 /)
类型: 苹果CMS(MacCMS) V10路由 + 雷池WAF(Chaitin SafeLine)人机验证
结构:
  首页:  /                       (首页推荐列表)
  全量:  /index.php/vod/home/page/{pg}.html
  分类:  /index.php/vod/type/id/{tid}.html
  分类翻页: /index.php/vod/type/id/{tid}/page/{pg}.html
  详情:  /index.php/vod/detail/id/{id}.html
  搜索:  /index.php/vod/search/wd/{urlencode词}.html
播放: 西瓜播放器(xgplayer)+HLS, 详情JS {id:"video-js",url:"m3u8"}
WAF:  首次访问返回验证页, POST /ajax.php?action=robot_verify (data=source=当前URL)
      拿到 c6s_RobotVerify=1 cookie 后带cookie全程访问(session)
卡片: <a href=".../vod/detail/id/{id}.html" data-video-id=...>
      <img class="jsblur lanjiazai" src="/style/lazy.svg" data-original="{封面}">
封面: 本地 /upload/* 或绝对域 sbzytpimg7.com
"""
import re
import urllib.parse
import requests

try:
    from base.spider import Spider
except Exception:
    class Spider:
        def init(self, extend=""):
            pass


class Spider(Spider):
    def getName(self):
        return "老色批传媒"

    def init(self, extend=""):
        self.rawSite = "https://xn--qxu.lspcm.pro"
        self.siteUrl = "https://xn--qxu.lspcm.pro"
        self.HOST = self.siteUrl
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.sess = requests.Session()
        self.sess.headers.update(self.headers)
        self._ensure_waf()

    # ---- 雷池WAF人机验证穿透 ----
    def _is_waf_page(self, text):
        # 验证页特征: 含 slg-bg / robot_verify / 雷池 且无详情卡片
        return ("slg-bg" in text or "robot_verify" in text or "雷池" in text) and "vod/detail/id/" not in text

    def _ensure_waf(self):
        # 站点慢, 首次访问加大超时+重试, 确保过验cookie生效
        for attempt in range(3):
            try:
                r = self.sess.get(self.HOST + "/", timeout=40)
                if self._is_waf_page(r.text):
                    source = self.HOST + "/"
                    self.sess.post(
                        self.HOST + "/ajax.php?action=robot_verify",
                        data={"source": source},
                        headers={"Referer": source, "X-Requested-With": "XMLHttpRequest"},
                        timeout=20,
                    )
                # 过验后验证cookie
                if self.sess.cookies.get("c6s_RobotVerify"):
                    return
            except Exception:
                pass
            # 若已拿到verify cookie则视为成功
            if self.sess.cookies.get("c6s_RobotVerify"):
                return
        # 兜底: 显式过验一次
        try:
            self.sess.post(
                self.HOST + "/ajax.php?action=robot_verify",
                data={"source": self.HOST + "/"},
                headers={"Referer": self.HOST + "/", "X-Requested-With": "XMLHttpRequest"},
                timeout=20,
            )
        except Exception:
            pass

    def _fetch(self, url, retry=3):
        for attempt in range(retry):
            try:
                r = self.sess.get(url, timeout=40)
                if self._is_waf_page(r.text):
                    source = url
                    try:
                        self.sess.post(
                            self.HOST + "/ajax.php?action=robot_verify",
                            data={"source": source},
                            headers={"Referer": source, "X-Requested-With": "XMLHttpRequest"},
                            timeout=20,
                        )
                        r = self.sess.get(url, timeout=40)
                    except Exception:
                        pass
                return r.text
            except Exception:
                if attempt == retry - 1:
                    return ""
                continue
        return ""

    def homeContent(self, *args):
        cats = [
            {"type_id": "1544", "type_name": "制服丝袜"},
            {"type_id": "1545", "type_name": "群交淫乱"},
            {"type_id": "1546", "type_name": "无码专区"},
            {"type_id": "1547", "type_name": "国产精品"},
            {"type_id": "1548", "type_name": "卡通动漫"},
            {"type_id": "1549", "type_name": "中文字幕"},
            {"type_id": "1550", "type_name": "欧美性爱"},
            {"type_id": "1551", "type_name": "巨乳美乳"},
            {"type_id": "1552", "type_name": "伦理三级"},
            {"type_id": "1554", "type_name": "人妖伪娘"},
            {"type_id": "1555", "type_name": "亚洲有码"},
            {"type_id": "1556", "type_name": "角色扮演"},
            {"type_id": "1557", "type_name": "黑料吃瓜"},
            {"type_id": "1558", "type_name": "国产传媒"},
        ]
        # 首页推荐: 根路径
        vod = []
        try:
            html = self._fetch(self.HOST + "/")
            vod = self._parse_list(html)
        except Exception:
            pass
        return {"class": cats, "filters": {}, "list": vod}

    def categoryContent(self, tid, pg, *args):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg <= 1:
            url = f"{self.HOST}/index.php/vod/type/id/{tid}.html"
        else:
            url = f"{self.HOST}/index.php/vod/type/id/{tid}/page/{pg}.html"
        try:
            html = self._fetch(url)
        except Exception:
            html = ""
        vod = self._parse_list(html)
        total = self._parse_total(html, tid)
        return {"page": pg, "pagecount": 9999, "limit": 24, "total": total, "list": vod}

    def detailContent(self, ids, *args):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0])
        else:
            vid = str(ids)
        m = re.search(r"(\d+)", vid)
        vid = m.group(1) if m else vid
        url = f"{self.HOST}/index.php/vod/detail/id/{vid}.html"
        try:
            html = self._fetch(url)
        except Exception:
            html = ""
        vod = self._parse_detail(html, vid)
        return {"list": [vod]}

    def searchContent(self, key, pg, *args):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        wd = urllib.parse.quote(key)
        url = f"{self.HOST}/index.php/vod/search/wd/{wd}.html"
        try:
            html = self._fetch(url)
        except Exception:
            html = ""
        vod = self._parse_list(html)
        return {"page": pg, "pagecount": 1, "limit": 24, "total": len(vod), "list": vod}

    def playerContent(self, flag, id, vipFlags, *args):
        return {"parse": 0, "jx": 0, "url": id, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.rawSite + "/"}}

    def localProxy(self, param):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        return url.lower().endswith((".m3u8", ".mp4"))

    def manualVideoCheck(self):
        return True

    # ---- 解析 ----
    def _parse_list(self, html):
        vod = []
        # 按卡片块切分: <a href=".../vod/detail/id/{id}.html" ...> ... </a>
        # 标题在块内 <h3 class="grid__item__title...">标题</h3>
        blocks = re.split(r'vod/detail/id/', html)
        for i in range(1, len(blocks)):
            bk = blocks[i]
            m = re.match(r"(\d+)\.html", bk)
            if not m:
                continue
            vid = m.group(1)
            card = bk[:1200]  # 卡片内内容上限
            title = ""
            tm = re.search(r'<h3[^>]*>(.*?)</h3>', card, re.S)
            if tm:
                title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
            if not title:
                tm = re.search(r'alt="([^"]+)"', card)
                if tm:
                    title = tm.group(1).strip()
            pic = ""
            pm = re.search(r'data-original="([^"]+)"', card)
            if pm:
                pic = pm.group(1)
            else:
                pm2 = re.search(r'src="([^"]+)"', card)
                if pm2 and "lazy.svg" not in pm2.group(1):
                    pic = pm2.group(1)
            if title:
                vod.append({"vod_id": vid, "vod_name": title, "vod_remarks": "", "vod_pic": pic})
        return vod

    def _parse_total(self, html, tid):
        # 末页页码, 形如 type/id/{tid}/page/{n}.html
        pages = re.findall(rf'type/id/{tid}/page/(\d+)\.html', html)
        nums = [int(x) for x in pages if x.isdigit()]
        return max(nums) if nums else 0

    def _parse_detail(self, html, vid):
        title = ""
        tm = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        if tm:
            title = tm.group(1).strip()
        else:
            tm2 = re.search(r"<title>([^<]+)", html)
            if tm2:
                title = tm2.group(1).strip().replace("_老色批传媒", "")
        pic = ""
        pm = re.search(r'data-original="([^"]+)"', html)
        if not pm:
            pm = re.search(r'poster"\s*:\s*"([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        # 播放地址(西瓜播放器 JS url)
        urls = []
        for m in re.finditer(r'"url"\s*:\s*"((?:https?:)?//[^"]+\.(?:m3u8|mp4)[^"]*)"', html):
            u = m.group(1)
            if u.startswith("//"):
                u = "https:" + u
            if u not in urls:
                urls.append(u)
        if not urls:
            for m in re.finditer(r'(https?:)?//[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html):
                u = m.group(0)
                if u.startswith("//"):
                    u = "https:" + u
                if u not in urls:
                    urls.append(u)
        play_url = "#".join(urls)
        vod_play_from = "$$$".join(["高清"] * (len(urls) if urls else 1))
        return {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": title,
            "vod_play_from": vod_play_from,
            "vod_play_url": play_url,
        }

    def getDependence(self):
        return ""

    def getCategory(self):
        return ""

    def getFilter(self):
        return {}

    def destroy(self):
        pass

    def searchContentA(self, key, quick, pg=1):
        return self.searchContent(key, pg)
