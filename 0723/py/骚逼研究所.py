# -*- coding: utf-8 -*-
"""
骚逼研究所 四壳通用Python Spider
站点: https://108298.sbyjs.help  (index.php?go=tydh9)
类型: 海洋CMS老版PHP + 雷池WAF(Chaitin SafeLine)人机验证
结构:
  首页/全量:  /index.php?m=vod-index-pg-{page}.htm
  分类:      /index.php?m=vod-type-id-{tid}-pg-{page}.htm
  详情:      /index.php?m=vod-detail-id-{id}.htm
  搜索:      /index.php?m=vod-search-wd-{wd}.htm
播放: 西瓜播放器(xgplayer)+HLS, 详情JS对象 {id:"okplayer",url:"m3u8"}
WAF:  首次访问返回验证页, POST /ajax.php?action=robot_verify (data=source=当前URL)
      拿到 c6s_RobotVerify=1 cookie 后带cookie重访即可(全程session)
图片: lazy加载, 取 original 属性; 图片域 s.lasha250923.top / sha.lashayu.com
"""
import re
import requests

try:
    from base.spider import Spider
except Exception:
    class Spider:
        def init(self, extend=""):
            pass


class Spider(Spider):
    def getName(self):
        return "骚逼研究所"

    def init(self, extend=""):
        self.rawSite = "https://108298.sbyjs.help"
        self.siteUrl = "https://108298.sbyjs.help"
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
        return ("slg-bg" in text or "robot_verify" in text or "雷池" in text) and "vod-detail-id-" not in text

    def _ensure_waf(self):
        try:
            r = self.sess.get(self.HOST + "/index.php?go=tydh9", timeout=15)
            if self._is_waf_page(r.text):
                source = self.HOST + "/index.php?go=tydh9"
                self.sess.post(
                    self.HOST + "/ajax.php?action=robot_verify",
                    data={"source": source},
                    headers={"Referer": source, "X-Requested-With": "XMLHttpRequest"},
                    timeout=15,
                )
        except Exception:
            pass

    def _fetch(self, url, retry=3):
        for attempt in range(retry):
            try:
                r = self.sess.get(url, timeout=30)
                if self._is_waf_page(r.text):
                    # 过期/失效则重新过验一次
                    source = url
                    try:
                        self.sess.post(
                            self.HOST + "/ajax.php?action=robot_verify",
                            data={"source": source},
                            headers={"Referer": source, "X-Requested-With": "XMLHttpRequest"},
                            timeout=15,
                        )
                        r = self.sess.get(url, timeout=30)
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
            {"type_id": "2001", "type_name": "日韩有码"},
            {"type_id": "2002", "type_name": "日韩无码"},
            {"type_id": "2003", "type_name": "中文字幕"},
            {"type_id": "2005", "type_name": "欧美情色"},
            {"type_id": "2006", "type_name": "国产情色"},
            {"type_id": "2007", "type_name": "网红主播"},
            {"type_id": "2008", "type_name": "成人动漫"},
        ]
        # 首页推荐: 全量第一页
        vod = []
        try:
            html = self._fetch(self.HOST + "/index.php?m=vod-index-pg-1.htm")
            vod = self._parse_list(html)
        except Exception:
            pass
        return {"class": cats, "filters": {}, "list": vod}

    def categoryContent(self, tid, pg, *args):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        url = f"{self.HOST}/index.php?m=vod-type-id-{tid}-pg-{pg}.htm"
        try:
            html = self._fetch(url)
        except Exception:
            html = ""
        vod = self._parse_list(html)
        total = self._parse_total(html)
        return {"page": pg, "pagecount": 9999, "limit": 24, "total": total, "list": vod}

    def detailContent(self, ids, *args):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0])
        else:
            vid = str(ids)
        m = re.search(r"(\d+)", vid)
        vid = m.group(1) if m else vid
        url = f"{self.HOST}/index.php?m=vod-detail-id-{vid}.htm"
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
        import urllib.parse
        wd = urllib.parse.quote(key)
        url = f"{self.HOST}/index.php?m=vod-search-wd-{wd}.htm"
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
        # 卡片: <a class="depraved" href=".../vod-detail-id-{id}.htm" title="{标题}"><img original="{封面}">
        for m in re.finditer(r'vod-detail-id-(\d+)\.htm(?:"|&quot;)\s+title="([^"]+)"', html):
            vid, title = m.group(1), m.group(2).strip()
            if not title:
                continue
            vod.append({"vod_id": vid, "vod_name": title, "vod_remarks": "", "vod_pic": ""})
        # 封面填充: 同一块内找 original
        blocks = re.split(r'vod-detail-id-', html)
        for i in range(1, len(blocks)):
            bk = blocks[i]
            m = re.match(r"(\d+)\.htm", bk)
            if not m:
                continue
            vid = m.group(1)
            pic = ""
            pm = re.search(r'original="([^"]+)"', bk[:400])
            if pm:
                pic = pm.group(1)
            else:
                pm2 = re.search(r'src="([^"]+)"', bk[:400])
                if pm2 and "lazy.svg" not in pm2.group(1):
                    pic = pm2.group(1)
            for v in vod:
                if v["vod_id"] == vid and not v["vod_pic"]:
                    v["vod_pic"] = pic
                    break
        return vod

    def _parse_total(self, html):
        # 末页页码, 形如 vod-type-id-2003-pg-17155.htm
        pages = re.findall(r'pg-(\d+)\.htm', html)
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
                title = tm2.group(1).strip().replace("_骚逼研究所", "").replace("_骚逼研究所", "")
        pic = ""
        pm = re.search(r'poster"\s*:\s*"([^"]+)"', html)
        if not pm:
            pm = re.search(r'original="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        # 播放地址
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
