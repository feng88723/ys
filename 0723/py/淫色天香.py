# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════
# 判型记录(卡01 第四节;跨会话可读 —— 接手先读这段,别重新判一遍)
#   RE_TARGET   : https://9.ystx5074.cc:8888/  (淫色天香)
#   RE_PATH     : 纯HTML服务端渲染 + 一层 document.write(decodeURIComponent()) 编码
#                 + 卡片路由 to="/play/<15hex>" + 播放页内嵌 var url="...m3u8?sign=..."
#   RE_OBSTACLE : ① 页面双层编码(URI 编码层 + 标题数字字符引用) ② 播放地址 MinIO 预签名
#                 sign 防盗链(有效期短,每次抓播放页即得新签,天然规避过期)
#                 ③ CDN 资源域 res-ys2026.jnpih.com 对机房出口 IP 封锁(网络层,非站级盾)
#                 ④ 封面图是懒加载 data-original 且内容是 base64 文本存的 WebP
#                    (.dat 后缀 + application/octet-stream),壳的图片加载器直连必裂
#                    → 必须走 localProxy 本地代理:抓字节 → base64 解码 → 返 image/webp
#   RE_EVIDENCE : probe 判 paywall=client(前端遮罩,标记 preview);工具判 JS混淆为误判
#                 (实为 URI 编码层被当成 _0x 特征,人工判型修正)
#   RE_TOOLS    : zaka_crack_kit probe / shellsim L1 PASS(2026-10-17)
#   RE_NOTE     : L3 真播需在可达 res-ys2026.jnpih.com 的网络下验证(本环境被封锁)
#   RE_CREATED  : 2026-10-17
#   RE_FIX      : 2026-10-17 v2 对齐四壳协议;v3 按 tvbox-dev 技能 13 接口规范补全
#                 (补 action 接口 / detailContent 遍历 ids / playerContent 补 format
#                  / init 预热防分类空白 / 页面 TTL 缓存 / 字段补全)
#                 v4 修复用户反馈「没图、没子分类」:
#                 (a) 分类动态解析 nav_cat 导航区(17 个细分分类,v3 只写死 4 个)
#                 (b) 封面本地代理 localProxy 抓 .dat → base64 解码 → image/webp,
#                     vod_pic 指向本机代理(127.0.0.1:9978/proxy?do=local&key=pic/<b64>)
#                 (c) 条目级过滤(铁律13:标题含未成年关键词不返回)
#                 (d) 列表返回后后台并发预取封面(壳随后调 localProxy 秒回)
#                 v4.1:空分类并发探活剔除(实测 28 其他综艺/29 成人游戏/31 AI脱衣
#                 是占位空分类,不剔用户点进去白屏;探活页顺带进缓存点击秒开)
#                 代理地址拆 host/port 两个常量(换壳改端口只改一处)
# ══════════════════════════════════════════════════════════════
# TVBox 源 · 淫色天香
# 站点档案(SITE)是唯一需要按站改的地方,其余逻辑通用。
# 自检:python3 shellsim.py 本文件 --run --strict   (AUDIT_OK 才算成)
#
# ── 壳接口约定(四壳:TVBox/FongMi/CatVod 等,type=3 的 py 源)────────
# 13 个标准接口一个不能少:
#   getDependence / init / homeContent / homeVideoContent / categoryContent
#   / detailContent / searchContent / playerContent / localProxy
#   / isVideoFormat / manualVideoCheck / action / destroy
# 1. 双协议兼容继承:try from base.spider import Spider,失败则本地最小基类兜底
#    (独立 class 不继承 → TVBox/PyramidStore 运行时分类空白)
# 2. 方法签名一律 *args 收尾 —— 不同壳传参个数不一样,写死会被 TypeError 打挂
# 3. playerContent 的 header 是 dict,另带 format/contentType
# 4. homeContent 返回 class + filters(dict,禁止空数组)+ list 三键
# 5. detailContent 的 ids 是 list/tuple 必须遍历(只取第一个 = 详情空白第一大原因)
# 6. vod 条目字段带全(vod_id/vod_name/vod_pic/vod_remarks;详情加年份地区演员导演)
# 7. vod_play_from 多线路 $$$ 连接;vod_play_url 每集「集名$地址」、多集 # 连接
# 8. init 里预热:TLS 握手 + 首屏缓存,避免壳首次 homeContent 握手未就绪 → 分类空白
# 9. 只用标准库(urllib),别 import requests —— 壳内置 python 不一定带
# 10. isVideoFormat 先剥 ?sign= 查询串再判断(带预签名的 m3u8 会被误判)
# 11. 封面走 localProxy 代理(vod_pic 指向 127.0.0.1:9978),localProxy 抓字节解码后
#     返回 [200, content_type, bytes];返回 None 或空壳会导致图片空白

import base64
import gzip
import json
import re
import threading
import time
import html as _html
import urllib.parse
import urllib.request

try:
    from concurrent.futures import ThreadPoolExecutor
except Exception:  # 壳内 python 残缺时降级:预取退化为同步
    ThreadPoolExecutor = None

# ──────────────────────────────────────────────────────────────
# 站点档案:换站只改这一段
# ──────────────────────────────────────────────────────────────
SITE = {
    "name": "淫色天香",
    # 域候选表(卡01「域名天天换」):主域 + sitedata.js 里 newDomain 发布的备用域;
    # 按顺序探活,哪个通用哪个;http_get 自带换域重试
    "domains": ["https://9.ystx5074.cc:8888", "https://9.ystx4773.cc:8888"],
    # 分类:
    #  - 动态:首页 nav_cat 导航区解析(站点 17 个细分分类,名称是 HTML 数字实体)
    #  - 兜底:首页 4 大区块(v3 及以前只认这 4 个,子分类全丢 —— 用户反馈根因)
    "nav_re": r'<div id="nav_cat".*?(?=<div id="|\Z)',
    "nav_item_re": (r'<span class="v-s-li-nav-link-vs a-link\s*" '
                    r'to="/type/(\d+)">\s*([^<]+?)\s*</span>'),
    "cats_static": [("1", "大陆"), ("2", "日韩"), ("3", "欧美"), ("4", "动漫")],
    # 分类级黑名单(铁律13:命中即剔除,不采集不写入)。实测命中:36=JK萝莉 23=少女动漫
    "cat_block_kw": ["萝莉", "幼女", "少女", "幼齿", "teen", "loli", "schoolgirl"],
    # 列表页:?page= 分页(实测 /type/1?page=2 = 200;JS pagejump 表单同此形态)
    "list_path": "/type/{fid}?page={pg}",
    # 搜索:/search/<关键词> (实测 /search/test = 结果页 8 条;search?q= 是搜索首页,别用)
    "search_path": "/search/{kw}",
    # 列表条目:卡片 to="/play/<hex>",标题在 rank-title(HTML 实体编码)。
    # 注意:不能用一个正则把卡片整块抓下来再块内取标题 —— 卡片内嵌套 div,
    # 非贪婪 .{0,3000}? 会在第一个三连 </div> 处截断,rank-title 落在块外。
    # 实测 to 与 rank-title 数量一致,按序配对最稳。
    "item_id_re": r'to="(/play/[0-9a-f]+)"',
    "title_re": r'rank-title">([^<]+)</div>',
    # 封面图:懒加载真实地址在 data-original(src 是占位广告图)。
    # 内容是 base64 文本存的 WebP(.dat + octet-stream),壳的 Glide 直连必裂,
    # 必须走 localProxy 解码。列表/搜索/播放页同此形态,按序与卡片配对。
    "pic_re": r'data-original="(https://res-ys2026\.jnpih\.com/image/[^"]+)"',
    # 播放页取流:解码后 var url = "https://res-.../index.m3u8?sign=..."
    "play_re": r'var url = "(https://res-ys2026\.jnpih\.com/m3u8/[^"]+?index\.m3u8\?sign=[^"]+)"',
    # 播放页标题(注意 <title> 只是站名,视频标题在 video-title)
    "detail_title_re": r'video-title">([^<]+)</div>',
    # 播放补头:交给 playerContent(别把片流代过服务器,机房 IP 会被 403)
    "headers": {"Referer": "https://9.ystx5074.cc:8888/"},
    # cookie 门:实测不需要
    "cookie_gate": {},
    # 标题是 base64 的站才打开;本站是 HTML 实体编码,不走这条
    "b64_text": False,
    # 条目级黑名单(铁律13:标题命中即丢弃不返回;单字"童"误伤太宽不收)
    "title_block_kw": ["萝莉", "幼女", "少女", "幼齿", "teen", "loli", "schoolgirl"],
    # 封面本地代理端口(TVBox/FongMi 生态标准 9978;技能约定兼容性最广形态)。
    # 地址与端口拆开写:换壳(如 OK 影视)只改这两个常量。
    "proxy_host": "127.0.0.1",
    "proxy_port": 9978,
    "proxy_base": "http://" + "127.0.0.1" + ":%d/proxy?do=local&key=pic/" % 9978,
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 15
RETRY = 3
CACHE_TTL = 60        # 页面短 TTL 缓存(秒):抵消壳对同一页的重复调用
PIC_CACHE_TTL = 600   # 封面字节缓存(秒)
PIC_TIMEOUT = 10      # 封面抓取超时(秒)


# ──────────────────────────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────────────────────────
def _dec(raw):
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


def _decode_blocks(s):
    """解 document.write(decodeURIComponent("...")) 编码层(卡03 第1级)。
    只解 block,块间内容保持原样 —— 全页 unquote 会把普通 URL 参数一起解坏。"""
    out, pos = [], 0
    for m in re.finditer(r'document\.write\(decodeURIComponent\("([^"]+)"\)\)', s):
        out.append(s[pos:m.start()])
        out.append(urllib.parse.unquote(m.group(1)))
        pos = m.end()
    out.append(s[pos:])
    return "".join(out)


def _blocked(text, keywords):
    """铁律13 命中判断:大小写不敏感包含匹配。"""
    low = str(text or "").lower()
    return any(kw in low for kw in keywords)


def http_get(path, base=None):
    """带回退重试的 GET。抖动退避重试;一个域不通自动换候选域(别一挡就收手,也别硬莽)。"""
    urls = []
    if path.startswith("http"):
        urls = [path]
    else:
        for d in ([base] if base else []) + SITE["domains"]:
            urls.append((d or "").rstrip("/") + path)
    last = None
    for u in urls:
        for attempt in range(RETRY):
            try:
                req = urllib.request.Request(u)
                req.add_header("User-Agent", UA)
                for k, v in SITE["headers"].items():
                    req.add_header(k, v)
                for k, v in SITE["cookie_gate"].items():
                    req.add_header("Cookie", "%s=%s" % (k, v))
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    raw = r.read()
                    if raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                    # 双层解码:字节解码 → URI 编码层
                    return _decode_blocks(_dec(raw)), r.geturl()
            except Exception as e:
                last = e
                time.sleep(0.5 * (attempt + 1))
    return "", None


def http_get_bytes(url, referer=None):
    """抓二进制(封面 .dat 用)。返回 bytes;失败返回 b""。"""
    if not url or not str(url).startswith("http"):
        return b""
    for attempt in range(2):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", UA)
            req.add_header("Referer", referer or SITE["headers"].get("Referer", ""))
            with urllib.request.urlopen(req, timeout=PIC_TIMEOUT) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return raw
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    return b""


def txt_of(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", _html.unescape(s)).strip()


def maybe_b64(s):
    if not SITE["b64_text"] or not s:
        return s
    try:
        return base64.b64decode(s + "=" * ((4 - len(s) % 4) % 4)).decode("utf-8", "ignore")
    except Exception:
        return s


def _to_int(v, default=1):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _b64url_encode(s):
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii").rstrip("=")


def _b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * ((4 - len(s) % 4) % 4)).decode("utf-8", "ignore")


def _pic_proxy_url(pic):
    """封面原图 URL → 本地代理 URL(壳的图片加载器 GET 它 → 壳调 localProxy)。
    原图 URL base64url 后塞 key 里,localProxy 解出来再抓。"""
    if not pic:
        return ""
    return SITE["proxy_base"] + _b64url_encode(pic)


def _pic_url_of_proxy(proxy_url):
    """本地代理 URL → 封面原图 URL(逆运算;容错多种调用形态)。
    支持:dict / 完整代理 URL / 裸 query string / local://key / 裸 key。"""
    if isinstance(proxy_url, dict):
        proxy_url = (proxy_url.get("url") or proxy_url.get("key")
                     or proxy_url.get("u") or "")
    raw = str(proxy_url or "").strip()
    if not raw:
        return ""
    key = ""
    if "?" in raw and "key=" in raw:
        # 形态1:完整代理 URL(带 query)
        try:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
            key = (q.get("key") or [""])[0]
        except Exception:
            key = ""
    elif "key=" in raw:
        # 形态2:裸 query string(do=local&key=pic/xxx)
        try:
            q = urllib.parse.parse_qs(raw)
            key = (q.get("key") or [""])[0]
        except Exception:
            key = ""
    elif raw.startswith("local://"):
        # 形态3:local:// 前缀
        key = raw[len("local://"):]
    else:
        # 形态4:裸 key
        key = raw
    key = key.strip()
    if key.startswith("pic/"):
        key = key[4:]
    if not key:
        return ""
    try:
        return _b64url_decode(key)
    except Exception:
        return ""


def grab_list(html, base):
    out, seen = [], set()
    ids = re.findall(SITE["item_id_re"], html or "")
    titles = re.findall(SITE["title_re"], html or "")
    pics = re.findall(SITE["pic_re"], html or "")
    # 按序配对;数量不一致时以短的为准,防错位
    for i, (href, raw_title) in enumerate(zip(ids, titles)):
        title = txt_of(raw_title)
        if not href or not title:
            continue
        # 铁律13:条目级过滤,命中关键词直接丢弃不返回
        if _blocked(title, SITE["title_block_kw"]):
            continue
        vid = urllib.parse.urljoin(base or SITE["domains"][0], href)
        if vid in seen:
            continue
        seen.add(vid)
        pic = pics[i] if i < len(pics) else ""
        out.append({"vod_id": vid, "vod_name": maybe_b64(title)[:80],
                    "vod_pic": _pic_proxy_url(pic), "vod_remarks": "",
                    "vod_year": "", "vod_area": "", "vod_type": ""})
    return out


def grab_play(html, base):
    urls = re.findall(SITE["play_re"], html or "", re.S)
    lines = []
    for i, u in enumerate(urls[:5]):
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = urllib.parse.urljoin(base or SITE["domains"][0], u)
        if u:
            # 每集格式「集名$地址」,多集 # 连接(壳接口约定第 7 条)
            ep_name = "正片" if i == 0 else "片源%d" % (i + 1)
            lines.append("%s$%s" % (ep_name, u))
    return "#".join(lines)


def grab_pics(html):
    """按序取封面原图 URL 列表(懒加载 data-original;src 是占位广告图别用)。"""
    return re.findall(SITE["pic_re"], html or "")


# ──────────────────────────────────────────────────────────────
# TVBox 四壳接口(13 个标准接口,全部可调用)
# ──────────────────────────────────────────────────────────────
try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        def init(self, extend=""):
            pass


class Spider(_BaseSpider):
    def __init__(self):
        self.ext = {}
        self._page_cache = {}      # url -> (html, final_url)
        self._cache_at = {}        # url -> 时间戳
        self._cache_lock = threading.RLock()
        self._warmed = False
        self._cats = [{"type_id": t, "type_name": n} for t, n in SITE["cats_static"]]
        self._pic_cache = {}       # 原图 url -> [code, ctype, bytes]
        self._pic_cache_at = {}    # 原图 url -> 时间戳
        self._pic_inflight = set() # 抓取中去重(防壳并发重复拉同一张)
        self._pic_lock = threading.RLock()
        self._pool = None
        if ThreadPoolExecutor is not None:
            try:
                self._pool = ThreadPoolExecutor(max_workers=6)
            except Exception:
                self._pool = None

    # ---- 壳启动即调 ----
    def getDependence(self):
        return ""

    def getName(self):
        return SITE["name"]

    def init(self, extend=""):
        # 配置解析兼容 dict / list / JSON 字符串多种形态(壳各版本传法不同)
        cfg = {}
        try:
            if isinstance(extend, dict):
                cfg = extend
            elif isinstance(extend, (list, tuple)):
                cfg = {}
            elif extend:
                cfg = json.loads(extend)
                if not isinstance(cfg, dict):
                    cfg = {}
        except Exception:
            cfg = {}
        self.ext = cfg
        # 预热:TLS 握手 + 首屏进缓存,避免壳首次 homeContent 时握手未就绪 → 分类空白
        try:
            self._fetch("/")
        except Exception:
            pass
        self._warmed = True
        return ""

    def getCategory(self):
        return ""

    def getFilter(self):
        return {}

    def action(self, action):
        return ""

    def destroy(self):
        with self._cache_lock:
            self._page_cache.clear()
            self._cache_at.clear()
        with self._pic_lock:
            self._pic_cache.clear()
            self._pic_cache_at.clear()
            self._pic_inflight.clear()
        if self._pool is not None:
            try:
                self._pool.shutdown(wait=False)
            except Exception:
                pass
        return ""

    def localProxy(self, param):
        # 封面本地代理:壳的图片加载器 GET vod_pic(127.0.0.1:9978/...)→ 壳回调本方法。
        # param 三种形态都兼容:dict / 完整 URL / 裸 query / 裸 key。
        # 原图是 base64 文本存的 WebP(.dat),这里抓字节 → base64 解码 → 返 image/webp。
        try:
            if isinstance(param, dict):
                raw = param.get("url") or param.get("key") or param.get("u") or ""
            else:
                raw = str(param or "")
            pic_url = _pic_url_of_proxy(raw)
            if not pic_url.startswith("http"):
                return [404, "text/plain", ""]
            now = time.time()
            with self._pic_lock:
                hit = self._pic_cache.get(pic_url)
                if hit and now - self._pic_cache_at.get(pic_url, 0) < PIC_CACHE_TTL:
                    return hit
                if pic_url in self._pic_inflight:
                    # 已有协程在抓:稍等它完成(最多 3 秒),到点返回 404 让壳重试
                    deadline = now + 3
                    while pic_url in self._pic_inflight and time.time() < deadline:
                        self._pic_lock.release()
                        time.sleep(0.1)
                        self._pic_lock.acquire()
                    hit = self._pic_cache.get(pic_url)
                    if hit:
                        return hit
                    return [404, "text/plain", ""]
                self._pic_inflight.add(pic_url)
            try:
                body = http_get_bytes(pic_url)
                if not body:
                    return [404, "text/plain", ""]
                # .dat 内容 = 纯 base64 文本(实测前 8 字节 UklGR = RIFF/WEBP 的 base64)
                text = body.strip()
                if re.fullmatch(rb"[A-Za-z0-9+/=\r\n\t ]+", text):
                    img = base64.b64decode(text)
                else:
                    img = body  # 兜底:已是二进制
                if not img:
                    return [404, "text/plain", ""]
                if img[:4] == b"RIFF" and img[8:12] == b"WEBP":
                    ctype = "image/webp"
                elif img[:3] == b"\xff\xd8\xff":
                    ctype = "image/jpeg"
                elif img[:8] == b"\x89PNG\r\n\x1a\n":
                    ctype = "image/png"
                else:
                    ctype = "application/octet-stream"
                ret = [200, ctype, img]
                with self._pic_lock:
                    self._pic_cache[pic_url] = ret
                    self._pic_cache_at[pic_url] = time.time()
                return ret
            finally:
                with self._pic_lock:
                    self._pic_inflight.discard(pic_url)
        except Exception:
            return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        # 注意先剥查询串:m3u8 带 MinIO 预签名 ?sign=,直接 endswith 会误判
        text = str(url or "").lower()
        return bool(re.search(r"\.(?:m3u8|mp4|mkv|flv|avi|ts)(?:[?#]|$)", text))

    def manualVideoCheck(self):
        return False

    # ---- 带 TTL 缓存的取页 ----
    def _fetch(self, path, base=None):
        key = str(path)
        now = time.time()
        with self._cache_lock:
            hit = self._page_cache.get(key)
            if hit and now - self._cache_at.get(key, 0) < CACHE_TTL:
                return hit
        html, final = http_get(path, base)
        with self._cache_lock:
            self._page_cache[key] = (html, final)
            self._cache_at[key] = now
        return html, final

    # ---- 封面预取:列表返回前并发抓本页封面,壳随后逐张调 localProxy 命中秒回 ----
    def _prefetch_pics(self, items):
        pics = []
        for it in items or []:
            url = _pic_url_of_proxy(it.get("vod_pic") or "")
            if url.startswith("http"):
                pics.append(url)
        if not pics:
            return
        if self._pool is not None:
            for u in pics:
                try:
                    self._pool.submit(self._prefetch_one, u)
                except Exception:
                    pass
        else:
            for u in pics:
                self._prefetch_one(u)

    def _prefetch_one(self, pic_url):
        now = time.time()
        with self._pic_lock:
            hit = self._pic_cache.get(pic_url)
            if hit and now - self._pic_cache_at.get(pic_url, 0) < PIC_CACHE_TTL:
                return
            if pic_url in self._pic_inflight:
                return
            self._pic_inflight.add(pic_url)
        try:
            body = http_get_bytes(pic_url)
            if not body:
                return
            text = body.strip()
            img = base64.b64decode(text) if re.fullmatch(rb"[A-Za-z0-9+/=\r\n\t ]+", text) else body
            if not img:
                return
            if img[:4] == b"RIFF" and img[8:12] == b"WEBP":
                ctype = "image/webp"
            elif img[:3] == b"\xff\xd8\xff":
                ctype = "image/jpeg"
            else:
                ctype = "application/octet-stream"
            with self._pic_lock:
                self._pic_cache[pic_url] = [200, ctype, img]
                self._pic_cache_at[pic_url] = time.time()
        except Exception:
            pass
        finally:
            with self._pic_lock:
                self._pic_inflight.discard(pic_url)

    # ---- 分类:动态解析 nav_cat 导航区 + 静态兜底 ----
    def _parse_cats(self, html):
        cats, seen = [], set()
        try:
            m = re.search(SITE["nav_re"], html or "", re.S)
            if m:
                for tid, raw_name in re.findall(SITE["nav_item_re"], m.group(0)):
                    name = _html.unescape(raw_name).strip()
                    if not name or tid in seen:
                        continue
                    # 铁律13:分类名命中未成年关键词,剔除不写入
                    if _blocked(name, SITE["cat_block_kw"]):
                        continue
                    seen.add(tid)
                    cats.append({"type_id": str(tid), "type_name": name})
        except Exception:
            cats = []
        if not cats:
            return [{"type_id": t, "type_name": n} for t, n in SITE["cats_static"]]
        # 并入首页 4 大区块(静态名),与细分导航互补,用户多点入口
        for t, n in SITE["cats_static"]:
            if t not in seen:
                cats.append({"type_id": t, "type_name": n})
                seen.add(t)
        return cats

    def _probe_cats(self, cats):
        """空分类剔除(铁律):并发探活各动态分类,0 卡片的摘掉。
        实测本站 28 其他综艺 / 29 成人游戏 / 31 AI脱衣 是占位空分类,
        不剔的话用户点进去白屏。探活失败(网络抖)保守保留;静态 4 区块不探。
        附带收益:探到的列表页进 TTL 缓存,用户点分类时秒开。"""
        static_ids = {t for t, _ in SITE["cats_static"]}
        dyn = [c for c in cats if c.get("type_id") not in static_ids]
        keep = [c for c in cats if c.get("type_id") in static_ids]
        if not dyn:
            return cats

        def probe(c):
            try:
                h, _ = self._fetch(SITE["list_path"].format(
                    fid=c.get("type_id"), pg=1, kw=""))
                return (c, len(re.findall(SITE["item_id_re"], h or "")) > 0)
            except Exception:
                return (c, True)  # 探活失败保守保留

        try:
            if self._pool is not None:
                results = list(self._pool.map(probe, dyn))
            else:
                results = [probe(c) for c in dyn]
        except Exception:
            results = [(c, True) for c in dyn]
        for c, alive in results:
            if alive:
                keep.append(c)
        return keep or cats

    # ---- 首页 ----
    def homeContent(self, *args):
        # 返回必须带 class/filters/list 三个键;首页数据直接带上,
        # 别只放 homeVideoContent(有些壳不调它,电视上就是白屏)
        try:
            html, base = self._fetch("/")
            home = grab_list(html, base)
            cats = self._parse_cats(html)
            cats = self._probe_cats(cats)
        except Exception:
            home, cats = [], list(self._cats)
        self._cats = cats
        self._prefetch_pics(home)
        return {"class": cats, "filters": {}, "list": home}

    def homeVideoContent(self):
        try:
            html, base = self._fetch("/")
        except Exception:
            html, base = "", None
        items = grab_list(html, base)
        self._prefetch_pics(items)
        return {"list": items}

    # ---- 分类 ----
    def categoryContent(self, tid, pg, filter, extend, *args):
        # P7 坑位:key 类型不稳定,统一 str()/int() 转换
        slug = str(tid or "").strip()
        page = _to_int(pg, 1)
        if not slug:
            return {"page": page, "pagecount": page, "limit": 0, "total": 0, "list": []}
        html, base = self._fetch(SITE["list_path"].format(fid=slug, pg=page, kw=""))
        items = grab_list(html, base)
        self._prefetch_pics(items)
        return {"list": items, "page": page, "pagecount": 9999 if items else page,
                "limit": len(items), "total": 999999}

    # ---- 详情 ----
    def detailContent(self, ids, *args):
        # 致命坑:ids 是 list/tuple(壳可能批量传多个),必须遍历,不能只取第一个
        id_list = list(ids) if isinstance(ids, (list, tuple)) else [ids]
        result_list = []
        for source_id in id_list:
            vid = str(source_id or "").strip()
            if not vid:
                continue
            html, base = self._fetch(vid)
            # 抓取失败(空页/被 403):不返回该条,让壳显示加载失败可重试,
            # 别塞 "正片$" 死链 —— 壳解析出空地址,playerContent url 为空直接报错
            if not html:
                continue
            play = grab_play(html, base)
            title = ""
            m = re.search(SITE["detail_title_re"], html or "", re.S)
            if m:
                title = maybe_b64(txt_of(m.group(1)))
            # 铁律13:详情标题命中未成年关键词,整条不返回
            if _blocked(title, SITE["title_block_kw"]):
                continue
            if not play:
                # 页面在但没解析出播放流(改版/广告页):同样跳过,别给死链
                continue
            # 详情封面:播放页无独立主图,取该页第一张封面(懒加载同形态)
            pic = ""
            pics = grab_pics(html)
            if pics:
                pic = _pic_proxy_url(pics[0])
            result_list.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_type": "",
                "vod_content": title,
                "vod_play_from": "线路1",
                "vod_play_url": play,
            })
        return {"list": result_list}

    # ---- 搜索 ----
    def searchContent(self, key, quick=False, pg=1, *args):
        page = _to_int(pg, 1)
        kw = urllib.parse.quote(str(key or ""))
        html, base = self._fetch(SITE["search_path"].format(pg=page, kw=kw))
        items = grab_list(html, base)
        self._prefetch_pics(items)
        return {"list": items, "page": page, "pagecount": 1,
                "limit": len(items), "total": len(items)}

    def searchContentA(self, key, quick, pg=1, *args):
        return self.searchContent(key, quick, pg)

    # ---- 播放 ----
    def playerContent(self, flag, id, vipFlags, *args):
        # 有 Referer 校验的站:交给 TVBox 的本地代理补头(别把整片代理过服务器);
        # header 是 dict,另带 format/contentType 声明 m3u8
        head = {"User-Agent": UA}
        head.update(SITE["headers"])
        return {"parse": 0, "jx": 0, "playUrl": "", "url": str(id or ""),
                "header": head, "format": "application/x-mpegURL",
                "contentType": "application/x-mpegURL"}
