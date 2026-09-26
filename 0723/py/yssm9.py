# coding: utf-8
# ============================================================
# HsVoice 有声站 (www.yssm9.xyz) 播放源
# 同时适配 OK影视(ok影视) 与 TVBox 全系 Python 源规范:
#   - OK影视(FongMi/TV): 类名 Spider, 继承 from base.spider import Spider,
#     用框架内置 self.fetch 发请求; 播放地址键名为 "url"
#   - TVBoxOSC / CatVodOpen / 影视仓(旧版): 同样识别 "url" 键
#   - 注意: 绝不能同时返回 "playUrl" 键 —— OK影视 的 PlaySpec 用
#     getRealUrl() = playUrl + url 拼接, 双键同值会拼出 "MP3MP3" 错误地址
#     (上一版"无法播放"的根因), 本版只返回 "url" 键
#
# 站点类型: 有声小说 / 音频站, 播放源为 MP3 直链
# 页面结构:
#   首页        /                     -> div.book-card / div.update-item
#   分类        /cate_detail.php?cate=<分类名>&page=<页>
#   搜索        /search.php?wd=<关键词>&page=<页> (站内分页链接写 search.html 但不生效)
#   详情        /play.php?id=<数字id>
#              h1.book-name 标题; a.book-author-link 分类/主播
#              div.audio-item[data-src="mp3"][data-subtitle="集名"]
#   播放源      /upload/audio/*.mp3  (audio/mpeg, 支持 Range)
# 用法:
#   OK影视: 将本文件放入 ok影视 py 目录(如 ok影视数据目录下的 py/), 源名显示为"yssm9有声"
#   TVBox : 拷入 tvbox/py/ 目录或作为自定义源导入
# ============================================================

import re
import json
import gzip
import ssl
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urljoin

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 站点无封面资源, vod_pic 留空由播放器显示默认占位
PIC_PLACEHOLDER = ""

# 站内分类 (与导航栏 cate-item 一致, type_id 直接用中文名)
CLASSES = [
    {"type_id": "经典禁曲", "type_name": "经典禁曲"},
    {"type_id": "单部有声", "type_name": "单部有声"},
    {"type_id": "性爱偷录", "type_name": "性爱偷录"},
    {"type_id": "音乐改编", "type_name": "音乐改编"},
    {"type_id": "有声连载", "type_name": "有声连载"},
    {"type_id": "淫词骚麦", "type_name": "淫词骚麦"},
]

PLAY_PAGE = re.compile(r'/play\.php\?id=(\d+)')

_BaseSpider: type = object  # 占位: 运行时在 try 中替换为框架基类或回退实现
try:
    # OK影视 运行时: base 模块由框架注入
    from base.spider import Spider as _BaseSpider  # type: ignore
except Exception:
    # TVBox 等无 base 模块的环境: 提供同构回退基类 (纯标准库)
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE

    class _Resp:
        def __init__(self, data, headers, status=200):
            self._data = data
            self.headers = headers
            self.status = status

        def json(self):
            return json.loads(self._data.decode("utf-8", errors="replace"))

        @property
        def text(self):
            return self._data.decode("utf-8", errors="replace")

        @property
        def content(self):
            return self._data

    class _BaseSpider:
        def fetch(self, url, headers=None, timeout=15, allow_redirects=True):
            hdrs = {"User-Agent": UA, "Referer": "https://www.yssm9.xyz/"}
            if isinstance(headers, dict):
                hdrs.update({str(k): str(v) for k, v in headers.items()})
            if "Accept-Encoding" not in hdrs:
                hdrs["Accept-Encoding"] = "gzip"
            req = Request(url, headers=hdrs)
            with urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
                raw = r.read()
                enc = ""
                try:
                    enc = r.headers.get("Content-Encoding") or ""
                except Exception:
                    pass
                if enc and "gzip" in enc.lower():
                    raw = gzip.decompress(raw)
                return _Resp(raw, r.headers, getattr(r, "status", 200))


class Spider(_BaseSpider):  # type: ignore
    """yssm9.xyz 有声小说站播放源 (名称: yssm9有声)"""

    def __init__(self):
        self.host = "https://www.yssm9.xyz/"
        self.headers = {"User-Agent": UA, "Referer": self.host}
        try:
            super().__init__()
        except Exception:
            pass

    # ---------- OK影视 框架要求的方法 ----------
    def getName(self):
        return "yssm9有声"

    def init(self, extend=""):
        self.host = "https://www.yssm9.xyz/"
        self.headers = {"User-Agent": UA, "Referer": self.host}
        return ""

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(mp3|m3u8|mp4|flv|aac)", url or ""))

    def manualVideoCheck(self):
        pass

    def action(self, action):
        return ""

    def destroy(self):
        pass

    def localProxy(self, param):
        # mp3 直链不经过本代理, 保留最简实现供框架调用
        return [200, "audio/mpeg", (param or {}).get("url", "")]

    # ---------- 工具函数 ----------
    def _get(self, url):
        if not url.startswith("http"):
            url = urljoin(self.host, url)
        return self.fetch(url, headers=self.headers).text

    @staticmethod
    def _clean(html):
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html))
        return t.replace("&nbsp;", " ").strip()

    @staticmethod
    def _grid_slice(html):
        """只保留列表区块(第一个 book-grid), 剔除页面底部的"全站热门推荐"等非列表内容"""
        m = re.search(r'<div class="book-grid">', html)
        if not m:
            return html
        start = m.start()
        end_m = re.search(r'<h2 class="hot-title"', html[start:])
        end = start + end_m.start() if end_m else len(html)
        return html[start:end]

    def _list_items(self, html):
        """提取列表条目, 兼容两种卡片结构, 按 id 去重保序"""
        items = []
        seen = set()

        def push(iid, name, remark):
            if not iid or iid in seen:
                return
            seen.add(iid)
            items.append({"vod_id": iid, "vod_name": name,
                          "vod_pic": PIC_PLACEHOLDER, "vod_remarks": remark})

        # 1) a.book-card 结构 (分类页 / 搜索页):
        #    <a href="/play.php?id=N" class="book-card"> 或 class 在前均可
        for m in re.finditer(
            r'<a(?=[^>]*class="[^"]*book-card[^"]*")' +
            r'(?=[^>]*href="/play\.php\?id=(\d+)")[^>]*>(.*?)</a>',
            html, re.S
        ):
            iid, block = m.group(1), m.group(2)
            tm = re.search(r'class="book-title"[^>]*>(.*?)</h3>', block, re.S)
            name = self._clean(tm.group(1)) if tm else ""
            rm = re.search(r'class="book-update"[^>]*>(.*?)</div>', block, re.S)
            remark = self._clean(rm.group(1)) if rm else ""
            push(iid, name, remark)

        # 2) h3.book-title / h3.update-title 结构 (首页推荐/更新区)
        for m in re.finditer(
            r'<h3 class="(?:book-title|update-title)">(.*?)</h3>', html, re.S
        ):
            block = m.group(1)
            pm = PLAY_PAGE.search(block)
            if not pm:
                push("", "", self._clean(block))
                continue
            # 备注: 卡片内的 book-update / update-meta (日期、播放量)
            tail = html[m.end():m.end() + 800]
            rm = (re.search(r'class="book-update"[^>]*>(.*?)</div>', tail, re.S) or
                  re.search(r'class="update-meta"[^>]*>(.*?)</div>', tail, re.S))
            remark = self._clean(rm.group(1)) if rm else ""
            push(pm.group(1), self._clean(block), remark)

        return items

    # ---------- 首页 ----------
    def homeContent(self, filter=""):
        # OK影视 用 class 渲染分类, 首页内容走 homeVideoContent
        return {"class": CLASSES, "filters": {}}

    def homeVideoContent(self):
        try:
            html = self._get("/")
        except Exception:
            return {"list": []}
        return {"list": self._list_items(html)[:20]}

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg="1", filter="", extend=""):
        try:
            html = self._get("/cate_detail.php?" + urlencode({"cate": tid, "page": pg}))
        except Exception:
            return {"list": [], "page": int(pg or 1), "pagecount": 1,
                    "limit": 20, "total": 0}
        # 页脚统计: "共 207 部作品, 每页20本, 当前第1/11页" (列表区之前, 须用完整页解析)
        total, pagecount = 0, 1
        m = re.search(r"共\s*(\d+)\s*部", html)
        if m:
            total = int(m.group(1))
        m = re.search(r"当前第\s*\d+\s*/\s*(\d+)\s*页", html)
        if m:
            pagecount = int(m.group(1))
        else:  # 兜底: 取最大分页号
            pages = [int(x) for x in re.findall(r"page=(\d+)", html)]
            if pages:
                pagecount = max(pages)
        return {"list": self._list_items(self._grid_slice(html)),
                "page": int(pg or 1),
                "pagecount": pagecount, "limit": 20, "total": total}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick="", pg="1"):
        # 注: 站内分页链接写的是 /search.html, 但该路由会忽略参数返回兜底页;
        #     /search.php 是真正生效的搜索结果路由
        try:
            html = self._get("/search.php?" + urlencode({"wd": key, "page": pg}))
        except Exception:
            return {"list": [], "page": int(pg or 1), "pagecount": 1,
                    "limit": 20, "total": 0}
        total = 0
        m = re.search(r"共\s*(\d+)\s*首", html)
        if m:
            total = int(m.group(1))
        pagecount = 1
        pages = [int(x) for x in re.findall(r"page=(\d+)", html)]
        if pages:
            pagecount = max(pages)
        return {"list": self._list_items(self._grid_slice(html)),
                "page": int(pg or 1),
                "pagecount": pagecount, "limit": 20, "total": total}

    # ---------- 详情 ----------
    def detailContent(self, ids):
        # 兼容传参: OK影视 传 list / TVBox 传 "123"、"123/1"、"123,456"
        if isinstance(ids, (list, tuple)):
            ids = ids[0] if ids else ""
        ids_str = str(ids)
        m = re.search(r"\d+", ids_str)
        vid = m.group(0) if m else ids_str.strip()
        try:
            html = self._get("/play.php?id=" + vid)
        except Exception:
            return {"list": []}
        name_m = re.search(r'<h1 class="book-name">(.*?)</h1>', html, re.S)
        vod_name = self._clean(name_m.group(1)) if name_m else ""
        # 分类 / 主播
        tags = re.findall(
            r'<a[^>]*class="book-author-link"[^>]*>([^<]+)</a>', html)
        actor, cate = "", ""
        for t in tags:
            t = t.strip()
            if t.startswith("主播"):
                actor = t.split("：", 1)[-1]
            elif t.startswith("分类"):
                cate = t.split("：", 1)[-1]
        # 章节: audio-item[data-src][data-subtitle]
        play_urls = []
        used = set()
        for m in re.finditer(
            r'<div class="audio-item"[^>]*data-src="([^"]+)"' +
            r'[^>]*data-subtitle="([^"]*)"', html
        ):
            src, sub = m.group(1), m.group(2)
            if src in used:
                continue
            used.add(src)
            play_urls.append((sub or "第%d集" % (len(play_urls) + 1),
                              urljoin(self.host, src)))
        # 兜底: 只有 data-src 没有 data-subtitle 的条目
        for m in re.finditer(r'<div class="audio-item"[^>]*data-src="([^"]+)"', html):
            src = m.group(1)
            if src in used:
                continue
            used.add(src)
            play_urls.append(("第%d集" % (len(play_urls) + 1),
                              urljoin(self.host, src)))
        vod_play_url = "#".join("%s$%s" % (n, u) for n, u in play_urls)
        return {"list": [{
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": PIC_PLACEHOLDER,
            "vod_actor": actor,
            "vod_class": cate,
            "vod_content": "分类：%s ｜ 主播：%s ｜ 共%d集" % (cate, actor, len(play_urls)),
            "vod_play_from": "yssm9",
            "vod_play_url": vod_play_url,
        }]}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags=""):
        # id 形如 "第1集$https://www.yssm9.xyz/upload/audio/xxx.mp3"
        url = str(id).split("$")[-1].strip()
        if url and not url.startswith("http"):
            url = urljoin(self.host, url)
        # 只返回 "url" 键: OK影视/影视仓 PlaySpec.getRealUrl() = playUrl + url
        # 是拼接语义, 返回 playUrl 会与 url 拼成重复地址导致无法播放;
        # TVBoxOSC / CatVodOpen 同样只读 "url" 键, 单键全系兼容
        return {
            "flag": flag if flag else "yssm9",
            "parse": 0,
            "url": url,
            "header": {"user-agent": UA, "referer": self.host},
        }


if __name__ == "__main__":
    s = Spider()
    print("home:", s.homeContent(""))
    print("homeVideos:", len(s.homeVideoContent().get("list", [])))
    print("cate:", s.categoryContent("淫词骚麦", "1", "", ""))
    print("search:", s.searchContent("妈妈", ""))
    print("detail:", s.detailContent("2615"))