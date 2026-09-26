# coding: utf-8
#无眠修
# ============================================================
# MMRGB 爬虫源 (TVBox / FongMi / PeekPro / 鱼壳 / 默影视)
# 站点: https://mmrgb.com
# 类型: 美女套图站（Discuz! X3.5，门户 + 23 个版块），站点本身不含视频，
#       本源的"播放"= 图片直链浏览（图片线路）+ 帖内网页浏览（网页线路）
# 数据来源: 首页/分类/搜索 共用一套 card 卡片; 正文大图在 <img zoomfile/file="...">
# 图片: https://attachment.mmrgb.com/forum/...  【实测无防盗链，直连可取】
# 搜索: search.php 两步走（起搜 302 -> Location 带 searchid -> 结果页同 card 结构）
# 兼容: FongMi / 蜂蜜影视、PeekPro、OK影视、鱼壳(WebTV)、默影视 等基于 CatVod 的 Python 壳
# 最后验证: 2026-09-16
# ============================================================
import html as _html
import json
import re
from urllib.parse import quote, urljoin

try:
    from base.spider import Spider as BaseSpider
except Exception:  # 独立调试时可脱离壳运行
    class BaseSpider(object):
        def fetch(self, url, headers=None, timeout=None, **kw):
            import urllib.request
            import http.cookiejar
            op = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            req = urllib.request.Request(url, headers=dict(headers or {}))
            try:
                r = op.open(req, timeout=timeout or 15)
                body = r.read()
                if hasattr(body, "decode"):
                    try:
                        body = body.decode("utf-8", "ignore")
                    except Exception:
                        pass
                return type("R", (), {"status_code": getattr(r, "status", 200),
                                      "text": body, "headers": dict(r.headers or {})})
            except Exception as e:
                return type("R", (), {"status_code": 0, "text": "", "headers": {},
                                      "err": str(e)})

        def post(self, url, data=None, headers=None, timeout=None, **kw):
            import urllib.request
            req = urllib.request.Request(url, data=(data.encode("utf-8") if isinstance(data, str) else data),
                                         headers=dict(headers or {}))
            try:
                r = urllib.request.urlopen(req, timeout=timeout or 15)
                return type("R", (), {"status_code": 200, "text": r.read().decode("utf-8", "ignore"),
                                      "headers": {}})
            except Exception:
                return type("R", (), {"status_code": 0, "text": "", "headers": {}})

        def log(self, msg):
            try:
                print("[mmrgb]", msg)
            except Exception:
                pass


UA_MOBILE = ("Mozilla/5.0 (Linux; Android 14; 22127RK46C) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# ---- 可调参数 ----
REQUEST_TIMEOUT = 20
MAX_DETAIL_PAGES = 8        # 单帖最多翻几页正文（超长帖保护）
MAX_THREADS_PER_PAGE = 20   # 站点每页就是 20 个卡片

# 播放线路偏好：
#   "image" = 默认走图片直链（支持图片/漫画查看器的壳最舒服）
#   "web"   = 默认走帖内网页浏览（webview 打开原帖，翻页看大图）
DEFAULT_PLAY_LINE = "image"


class Spider(BaseSpider):
    def __init__(self):
        # 零网络：只做本地初始化
        self.extend = ""
        self.host = "https://mmrgb.com"
        self.attach = "https://attachment.mmrgb.com"
        self.classes = [
            {"type_id": "portal:new", "type_name": "最新"},
            {"type_id": "portal:hot", "type_name": "热门"},
            {"type_id": "portal:month", "type_name": "月榜"},
            {"type_id": "portal:year", "type_name": "年榜"},
            {"type_id": "portal:total", "type_name": "总榜"},
            {"type_id": "portal:favnew", "type_name": "收藏榜"},
            {"type_id": "f2", "type_name": "XiuRen 秀人网"},
            {"type_id": "f3", "type_name": "MFStar 模范学院"},
            {"type_id": "f4", "type_name": "MiStar 魅妍社"},
            {"type_id": "f5", "type_name": "MyGirl 美媛馆"},
            {"type_id": "f6", "type_name": "Imiss 爱蜜社"},
            {"type_id": "f7", "type_name": "BoLoLi 波萝社 & Tukmo 兔几盟"},
            {"type_id": "f8", "type_name": "YouWu 尤物馆"},
            {"type_id": "f9", "type_name": "UXing 优星馆"},
            {"type_id": "f10", "type_name": "MiiTao 蜜桃社"},
            {"type_id": "f11", "type_name": "FeiLin 嗲囡囡"},
            {"type_id": "f12", "type_name": "WingS 影私荟"},
            {"type_id": "f13", "type_name": "Taste 顽味生活"},
            {"type_id": "f14", "type_name": "LeYuan 星乐园"},
            {"type_id": "f15", "type_name": "HuaYan 花の颜"},
            {"type_id": "f16", "type_name": "DKGirl 御女郎"},
            {"type_id": "f17", "type_name": "MintYe 薄荷叶"},
            {"type_id": "f18", "type_name": "YouMi 尤蜜荟"},
            {"type_id": "f19", "type_name": "Candy 糖果画报 & 网红馆"},
            {"type_id": "f20", "type_name": "MTMeng 模特联盟"},
            {"type_id": "f21", "type_name": "MiCat 猫萌榜 & RuiSg 瑞丝馆"},
            {"type_id": "f22", "type_name": "HuaYang 花漾show"},
            {"type_id": "f23", "type_name": "XingYan 星颜社"},
            {"type_id": "f24", "type_name": "XiaoYu 语画界"},
        ]
        # 版块排序（实测 orderby=dateline / views / replies 均生效）
        self.filters = {
            "f%d" % i: [{
                "key": "order", "name": "排序",
                "value": [
                    {"n": "最新发布", "v": "dateline"},
                    {"n": "最多查看", "v": "views"},
                    {"n": "最多回复", "v": "replies"},
                ],
            }] for i in range(2, 25)
        }
        self.headers = {
            "User-Agent": UA_MOBILE,
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self._search_cache = None  # (keyword, searchid)

    def getName(self):
        return "MMRGB魅色MM"

    def getDependence(self):
        return []

    def init(self, extend=""):
        # 零网络；部分壳会把 Site.ext 传进来
        self.extend = extend or ""
        if isinstance(self.extend, (bytes, bytearray)):
            try:
                self.extend = self.extend.decode("utf-8", "ignore")
            except Exception:
                self.extend = ""

    # ---------------- 基础工具 ----------------
    @staticmethod
    def _norm_ids(ids):
        """兼容 list / tuple / str / bytes / 空。"""
        if ids is None:
            return ""
        if isinstance(ids, (list, tuple)):
            if not ids:
                return ""
            ids = ids[0]
        if isinstance(ids, bytes):
            try:
                ids = ids.decode("utf-8", errors="ignore")
            except Exception:
                ids = str(ids)
        return str(ids).strip()

    @staticmethod
    def _as_bool(v, default=False):
        if isinstance(v, bool):
            return v
        if v is None:
            return default
        s = str(v).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off", ""):
            return False
        return default

    def _clean(self, text):
        text = re.sub(r"<!--[\s\S]*?-->", "", text or "")
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        return _html.unescape(text)

    def _fetch(self, url, headers=None, timeout=None, _depth=0):
        """优先走壳子原生 fetch；302 手动跟随；兜底 urllib（带 cookie）。"""
        h = dict(self.headers)
        h.update(headers or {})
        timeout = timeout or REQUEST_TIMEOUT
        try:
            r = self.fetch(url, headers=h, timeout=timeout)
            if r is not None:
                code = getattr(r, "status_code", 200) or 200
                txt = getattr(r, "text", "") or ""
                if isinstance(txt, bytes):
                    try:
                        txt = txt.decode("utf-8", "ignore")
                    except Exception:
                        txt = ""
                if code == 200 and txt:
                    return txt
                # 壳子没跟随重定向：从 Location 手动跳
                if code in (301, 302, 303, 307, 308) and _depth < 3:
                    loc = ""
                    hdrs = getattr(r, "headers", None) or {}
                    try:
                        if hasattr(hdrs, "get"):
                            loc = hdrs.get("Location") or hdrs.get("location") or ""
                        elif isinstance(hdrs, dict):
                            loc = hdrs.get("Location") or hdrs.get("location") or ""
                    except Exception:
                        loc = ""
                    if loc:
                        return self._fetch(urljoin(url, loc), headers=headers,
                                           timeout=timeout, _depth=_depth + 1)
        except Exception:
            pass
        # 兜底：urllib（自动带 cookie、自动跟 302）
        try:
            import urllib.request
            import http.cookiejar
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            opener.addheaders = []
            req = urllib.request.Request(url, headers=h)
            body = opener.open(req, timeout=timeout).read()
            return body.decode("utf-8", "ignore")
        except Exception:
            return ""

    # ---------------- 列表解析（首页/分类/搜索 同一套 card） ----------------
    _CARD_SPLIT = re.compile(r'<div class="card[\s"]')

    def _parse_cards(self, page):
        items = []
        seen = set()
        if not page:
            return items
        for block in self._CARD_SPLIT.split(page)[1:]:
            m = re.search(r'href="thread-(\d+)-\d+-\d+\.html"', block)
            if not m:
                continue
            tid = m.group(1)
            if tid in seen:
                continue
            seen.add(tid)

            pic = ""
            mp = re.search(r'ui8-image="([^"]+)"', block)
            if mp:
                pic = mp.group(1).strip()

            name = ""
            mt = re.search(r"<p>([\s\S]*?)</p>", block)
            if mt:
                txt = self._clean(mt.group(1))
                lines = [x.strip() for x in txt.split("\n") if x.strip()]
                for ln in reversed(lines):
                    if re.search(r"[\u4e00-\u9fa5A-Za-z]", ln) and not re.fullmatch(r"[\d\s\.]+", ln):
                        name = ln
                        break
                if not name and lines:
                    name = lines[-1]

            remark = ""
            mv = re.search(r'fa-eye[^>]*>\s*</i>\s*([\d\.]+)', block)
            if mv:
                remark = mv.group(1).strip() + "阅"

            items.append({
                "vod_id": str(tid),
                "vod_name": name or ("帖 " + tid),
                "vod_pic": pic,
                "vod_remarks": remark,
                "style": {"type": "rect", "ratio": 0.75},
            })
        return items

    @staticmethod
    def _max_page(page, patterns, current):
        best = int(current or 1)
        for pat in patterns:
            for x in re.findall(pat, page or ""):
                try:
                    n = int(x)
                except Exception:
                    continue
                if current < n <= 20000 and n > best:
                    best = n
        return best

    @staticmethod
    def _order_of(extend):
        """extend 可能是 dict、JSON 字符串、'order=xxx' 或纯 'xxx'。"""
        if not extend:
            return ""
        v = ""
        if isinstance(extend, dict):
            v = extend.get("order") or extend.get("sort") or ""
        else:
            s = str(extend).strip()
            # JSON 字符串（部分壳把 filterSelect 序列化后传入）
            if s.startswith("{") and s.endswith("}"):
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        v = obj.get("order") or obj.get("sort") or ""
                except Exception:
                    v = ""
            if not v:
                m = re.search(r"order=([A-Za-z_]+)", s)
                v = m.group(1) if m else s
        v = str(v).strip()
        return v if v in ("dateline", "views", "replies") else ""

    def _cat_url(self, tid, page, order=""):
        tid = str(tid or "portal:hot")
        if tid.startswith("portal:"):
            return "%s/portal.php?order=%s&page=%d" % (
                self.host, tid.split(":", 1)[1] or "hot", page)
        fid = tid[1:] if tid.startswith("f") else re.sub(r"\D", "", tid)
        if not fid:
            fid = "2"
        if order:
            return "%s/forum.php?mod=forumdisplay&fid=%s&orderby=%s&page=%d" % (
                self.host, fid, order, page)
        return "%s/forum-%s-%d.html" % (self.host, fid, page)

    # ---------------- 首页 ----------------
    def homeContent(self, filter=False):
        # 部分壳把 filter 以字符串传入
        need_filter = self._as_bool(filter, False)
        result = {"class": self.classes}
        if need_filter:
            result["filters"] = self.filters
        else:
            result["filters"] = {}
        return result

    def getHomeContent(self, filter=False):
        return self.homeContent(filter)

    def homeVideoContent(self):
        try:
            html = self._fetch(self.host + "/portal.php?order=new")
            return {"list": self._parse_cards(html)}
        except Exception as e:
            self.log({"homeVideo": "exception", "error": str(e)[:160]})
            return {"list": []}

    # ---------------- 分类 ----------------
    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        order = self._order_of(extend)
        url = self._cat_url(tid, page, order)
        try:
            html = self._fetch(url)
            lst = self._parse_cards(html)
        except Exception as e:
            self.log({"category": "exception", "tid": tid, "error": str(e)[:160]})
            lst = []
            html = ""

        tid = str(tid or "")
        if tid.startswith("portal:"):
            pats = [r"page=(\d+)"]
        else:
            fid = tid[1:] if tid.startswith("f") else re.sub(r"\D", "", tid)
            pats = [
                r"forum-%s-(\d+)\.html" % re.escape(fid or "0"),
                r"fid=%s&amp;page=(\d+)" % re.escape(fid or "0"),
                r"fid=%s&page=(\d+)" % re.escape(fid or "0"),
            ]
        pagecount = self._max_page(html, pats, page)
        if pagecount < page:
            pagecount = page
        # 当前页有数据但估不出总页时，至少给 page+1 方便继续翻（部分壳依赖）
        if lst and pagecount <= page:
            pagecount = page + 1

        return {
            "list": lst,
            "page": page,
            "pagecount": pagecount,
            "limit": MAX_THREADS_PER_PAGE,
            "total": pagecount * MAX_THREADS_PER_PAGE,
        }

    # ---------------- 详情 ----------------
    def _skeleton(self, vid, title="", pic="", remarks="解析中"):
        return {"list": [{
            "vod_id": str(vid),
            "vod_name": title or "未知标题",
            "vod_pic": pic or "",
            "vod_remarks": remarks,
            "vod_content": "",
            "vod_play_from": "网页",
            "vod_play_url": "整帖浏览$web|" + str(vid),
            "vod_player": "pics",
        }]}

    @staticmethod
    def _images_of(page):
        """按文档顺序提取正文大图（zoomfile 优先，其次 file / data-original / src）。"""
        urls = []
        for tag in re.findall(r"<(?:img|a)\b[^>]*>", page or "", flags=re.I):
            got = ""
            for attr in ("zoomfile", "file", "data-original", "data-src", "src"):
                m = re.search(r'%s\s*=\s*"([^"]+)"' % attr, tag, flags=re.I)
                if not m:
                    continue
                u = _html.unescape(m.group(1).strip())
                if not u or u.startswith("data:") or "static/image" in u or "smiley" in u:
                    continue
                if not u.startswith("http"):
                    u = urljoin("https://mmrgb.com/", u)
                if "attachment.mmrgb.com" not in u and "mmrgb.com/forum/" not in u:
                    continue
                got = u
                break
            if got and got not in urls:
                urls.append(got)
        return urls

    def _thread_page(self, tid, page=1):
        if page <= 1:
            return "%s/thread-%s-1-1.html" % (self.host, tid)
        return "%s/thread-%s-%d-1.html" % (self.host, tid, page)

    def detailContent(self, ids):
        raw = self._norm_ids(ids)
        if not raw:
            return {"list": []}
        # 兼容: 纯 tid / thread-123-1-1.html / 完整URL / 带 |$| 后缀
        raw = raw.split("|$|")[0]
        m = re.search(r"thread-(\d+)", raw) or re.search(r"(\d{2,})", raw)
        if not m:
            return {"list": []}
        tid = m.group(1)

        try:
            page_html = self._fetch(self._thread_page(tid))
            if not page_html or len(page_html) < 500:
                return self._skeleton(tid, "帖 " + tid, "", "解析失败")

            # 标题：<title>{标题} - {版块} - MMRGB</title>
            name = ""
            mt = re.search(r"<title>(.*?)</title>", page_html, re.S)
            if mt:
                title = self._clean(mt.group(1)).strip()
                parts = re.split(r"\s+-\s+", title)
                if len(parts) >= 2:
                    title = " - ".join(parts[:-2]) if len(parts) > 2 else parts[0]
                name = title.strip()
            if not name:
                md0 = re.search(r'name="description"\s+content="([^"]*)"', page_html)
                if md0:
                    name = _html.unescape(md0.group(1)).split(",")[0].strip()
            if not name:
                name = "帖 " + tid

            # 简介
            content = ""
            md = re.search(r'name="description"\s+content="([^"]*)"', page_html)
            if md:
                content = _html.unescape(md.group(1)).strip()
                content = re.sub(r",?魅色MM｜MMRGB.*$", "", content).strip()

            # 正文图片（多页合并）
            images = self._images_of(page_html)
            pages = [1]
            for x in re.findall(r"thread-%s-(\d+)-1\.html" % re.escape(tid), page_html):
                try:
                    n = int(x)
                except Exception:
                    continue
                if 1 < n <= MAX_DETAIL_PAGES and n not in pages:
                    pages.append(n)
            pages.sort()
            for p in pages[1:]:
                sub = self._fetch(self._thread_page(tid, p))
                if not sub:
                    continue
                for u in self._images_of(sub):
                    if u not in images:
                        images.append(u)

            remark = "%dP" % len(images) if images else "无图"
            if not images:
                if "回复可见" in page_html or "如果您要查看本帖隐藏内容请回复" in page_html:
                    remark = "回复可见"
                return self._skeleton(tid, name, "", remark)

            pic = images[0]
            # 详情已解析的图片写入缓存，播放时少一次网络
            if not hasattr(self, "_img_cache") or not isinstance(self._img_cache, dict):
                self._img_cache = {}
            self._img_cache[str(tid)] = images

            # 图片播放：走壳自带 pics 查看器（pics:// + && 拼接整套图）
            # 参考 MOMO 图库写法，兼容 蜂蜜/鱼壳/默影视/OK/PeekPro
            # 线路：直连（pics 直链） / 带头（@Referer） / 网页（原帖 webview）
            vod = {
                "vod_id": str(tid),
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
                "vod_content": ("共 %d 张图。%s" % (len(images), content)).strip(),
                "vod_play_from": "直连$$$带头$$$网页",
                "vod_play_url": "图集$direct|%s$$$图集$ref|%s$$$整帖浏览$web|%s" % (tid, tid, tid),
                "vod_player": "pics",
            }
            return {"list": [vod]}
        except Exception as e:
            self.log({"detail": "exception", "ids": raw, "error": str(e)[:160]})
            return self._skeleton(raw)

    # ---------------- 搜索 ----------------
    def _search_urls(self, key, page):
        kw = quote(str(key or "").strip())
        u1 = "%s/search.php?mod=forum&srchtxt=%s&searchsubmit=yes" % (self.host, kw)
        u2 = ("%s/search.php?mod=forum&kw=%s&searchsubmit=yes"
              "&orderby=lastpost&ascdesc=desc" % (self.host, kw))
        return u1, u2

    def _search_follow(self, sid, key, page):
        kw = quote(str(key or "").strip())
        url = ("%s/search.php?mod=forum&searchid=%s&orderby=lastpost"
               "&ascdesc=desc&searchsubmit=yes&kw=%s" % (self.host, sid, kw))
        if page > 1:
            url += "&page=%d" % page
        return url

    def searchContent(self, key, quick=False, pg="1"):
        """兼容两参(searchContent(key,quick))与三参(含 pg)调用。"""
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        kw = str(key or "").strip()
        if not kw:
            return {"list": [], "page": page, "pagecount": 1, "limit": MAX_THREADS_PER_PAGE, "total": 0}

        u1, _u2 = self._search_urls(kw, page)
        cache = getattr(self, "_search_cache", None)

        try:
            # 翻页：复用上一次起搜得到的 searchid
            if page > 1 and cache and cache[0] == kw and cache[1]:
                page_html = self._fetch(self._search_follow(cache[1], kw, page))
                lst = self._parse_cards(page_html)
                if lst:
                    return {
                        "list": lst,
                        "page": page,
                        "pagecount": page + (1 if len(lst) >= MAX_THREADS_PER_PAGE else 0) or page,
                        "limit": MAX_THREADS_PER_PAGE,
                        "total": 0,
                    }

            # 起搜（壳会跟随 302 到结果页；未跟随则再跟一次 Location）
            page_html = self._fetch(u1)
            lst = self._parse_cards(page_html)
            m = re.search(r"searchid=(\d+)", page_html or "")
            sid = m.group(1) if m else ""
            if sid:
                self._search_cache = (kw, sid)
            if not lst and sid:
                page_html = self._fetch(self._search_follow(sid, kw, page))
                lst = self._parse_cards(page_html)

            pagecount = page
            if lst and len(lst) >= MAX_THREADS_PER_PAGE:
                pagecount = page + 1
            # 从结果页再估一次总页
            for x in re.findall(r"[?&]page=(\d+)", page_html or ""):
                try:
                    n = int(x)
                    if n > pagecount:
                        pagecount = n
                except Exception:
                    pass

            return {
                "list": lst,
                "page": page,
                "pagecount": max(pagecount, page),
                "limit": MAX_THREADS_PER_PAGE,
                "total": 0,
            }
        except Exception as e:
            self.log({"search": "exception", "key": kw, "error": str(e)[:160]})
            return {"list": [], "page": page, "pagecount": 1, "limit": MAX_THREADS_PER_PAGE, "total": 0}

    # ---------------- 播放 ----------------
    def _collect_images(self, tid):
        """按详情逻辑重新拉齐图片列表（带简易缓存）。"""
        tid = str(tid or "").strip()
        if not tid:
            return []
        cache = getattr(self, "_img_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._img_cache = cache
        if tid in cache and cache[tid]:
            return cache[tid]

        page_html = self._fetch(self._thread_page(tid))
        if not page_html:
            return []
        images = self._images_of(page_html)
        pages = [1]
        for x in re.findall(r"thread-%s-(\d+)-1\.html" % re.escape(tid), page_html):
            try:
                n = int(x)
            except Exception:
                continue
            if 1 < n <= MAX_DETAIL_PAGES and n not in pages:
                pages.append(n)
        pages.sort()
        for p in pages[1:]:
            sub = self._fetch(self._thread_page(tid, p))
            if not sub:
                continue
            for u in self._images_of(sub):
                if u not in images:
                    images.append(u)
        if images:
            cache[tid] = images
        return images

    def playerContent(self, flag, id, vipFlags=None):
        """
        图片：pics://url1&&url2&&... 交给壳内置图片查看器
        网页：parse=1 打开原帖
        """
        raw = str(id or "").strip()
        fl = str(flag or "").strip().lower()

        # 集名$url → 取后半
        if "$" in raw:
            raw = raw.split("$", 1)[1].strip()

        mode = "direct"
        tid = raw
        if raw.startswith("direct|"):
            mode, tid = "direct", raw[7:]
        elif raw.startswith("ref|"):
            mode, tid = "ref", raw[4:]
        elif raw.startswith("web|"):
            mode, tid = "web", raw[4:]
        elif raw.startswith("img|"):
            # 兼容旧格式：单张图
            url = raw[4:].strip()
            return {
                "parse": 0,
                "playUrl": "",
                "url": "pics://" + url,
                "header": json.dumps({
                    "User-Agent": UA_MOBILE,
                    "Referer": self.host + "/",
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                }, ensure_ascii=False),
            }

        if fl in ("带头", "ref", "referer"):
            mode = "ref"
        elif fl in ("网页", "web"):
            mode = "web"
        elif fl in ("直连", "direct", "图片"):
            mode = "direct"

        m = re.search(r"(\d+)", str(tid))
        tid = m.group(1) if m else str(tid).strip()

        # 网页线路：webview 打开原帖
        if mode == "web":
            return {
                "parse": 1,
                "jx": 0,
                "url": self._thread_page(tid, 1) if tid else (self.host + "/portal.php"),
                "header": dict(self.headers),
            }

        if not tid:
            return {"parse": 0, "playUrl": "", "url": ""}

        images = self._collect_images(tid)
        if not images:
            # 无图时退回原帖
            return {
                "parse": 1,
                "jx": 0,
                "url": self._thread_page(tid, 1),
                "header": dict(self.headers),
            }

        clean = [u.split("@")[0].strip() for u in images if u and str(u).startswith("http")]
        if not clean:
            return {"parse": 0, "playUrl": "", "url": ""}

        ua = UA_MOBILE
        ref = self.host + "/"
        if mode == "ref":
            # 部分壳认 url@Referer=xx&User-Agent=yy
            tagged = ["%s@Referer=%s&User-Agent=%s" % (u, ref, ua) for u in clean]
            pics_url = "pics://" + "&&".join(tagged)
        else:
            pics_url = "pics://" + "&&".join(clean)

        # header 用 JSON 字符串，兼容蜂蜜/鱼壳/默影视对 header 类型的差异
        hdr = {
            "User-Agent": ua,
            "Referer": ref,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        return {
            "parse": 0,
            "playUrl": "",
            "url": pics_url,
            "header": json.dumps(hdr, ensure_ascii=False),
        }

    # ---------------- 推荐 ----------------
    def recommendContent(self, ids, pg="1"):
        raw = self._norm_ids(ids)
        vid = ""
        m = re.search(r"thread-(\d+)", raw) or re.search(r"(\d{2,})", raw)
        if m:
            vid = m.group(1)
        try:
            html = self._fetch(self.host + "/portal.php?order=hot")
            lst = self._parse_cards(html)
            out = [x for x in lst if str(x.get("vod_id")) != str(vid)][:12]
            return {"list": out}
        except Exception:
            return {"list": []}

    # ---------------- 壳兼容桩（避免部分壳反射调用时报错） ----------------
    def isVideoFormat(self, url):
        # 本源是图片/网页，不是视频流；返回 False 避免壳把 jpg 当视频缓冲
        u = str(url or "").lower()
        if re.search(r"\.(jpg|jpeg|png|webp|gif|bmp|avif)(\?|$)", u):
            return False
        if "attachment.mmrgb.com" in u:
            return False
        return False

    def manualVideoCheck(self):
        # 不启用手动视频嗅探（图片源）
        return False

    def localProxy(self, param):
        return None

    def action(self, action):
        return ""

    def liveContent(self, url):
        return []

    def destroy(self):
        self._search_cache = None
