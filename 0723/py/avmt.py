# -*- coding: utf-8 -*-
"""
JAVMIT（javmit 系域名）TVBox / FongMi Python Spider
====================================================
单文件自包含，零第三方依赖（requests 可选，缺失自动降级 urllib）。
框架范式与 missav.py / avdj.py 完全一致：裸类 Spider、无参实例化、
13 方法齐备、detailContent 四态归一化、playerContent().header 为 dict、
localProxy 返回四项、自建本地中继。

站点结构（实测）
----------------
  首页          https://<host>/zh-CN/
  字幕          /zh-CN/category/subtitles/
  最新浏览      /zh-CN/video/?sort=date&date=all&view=grid&rawx_per_page=48
  未经审查     /zh-CN/uncensored/  （子页 chips：fc2 / heyzo / 1pondo ...）
  分类          /zh-CN/categories/
  演员          /zh-CN/actors/
  详情          /zh-CN/video/<slug>/
  搜索          /zh-CN/?s=<kw>
  翻页统一      <path>/page/<pg>/

播放地址（关键）
----------------
  详情页内联画质按钮：
      <button class="rawx-quality-btn" data-src="<m3u8>" data-label="AUTO|1080P|480P">
  兜底取 data-default-src / og:video / JSON-LD contentUrl。
  data-src 可能为相对地址，需 urljoin 绝对化。
  本 spider 将每个画质作为一条播放线路（vod_play_from 用 $$$ 分隔）。

防盗链
------
  · m3u8 / 分片跨域直连时需带 Referer=<host>/ 与浏览器 UA；
    因此内置自建本地中继（127.0.0.1 随机端口）统一回源并按需重写。
"""

import base64                     # noqa: F401  （预留：部分子站用到）
import html as _htmlmod
import json
import os                         # noqa: F401
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import quote, unquote, urljoin, urlparse, parse_qs

# ── 可选依赖：requests ──────────────────────────────────────────────────────
try:
    import requests                    # noqa: F401
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

# ── 可选依赖：线程化 HTTP 服务 ──────────────────────────────────────────────
try:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
except Exception:                       # pragma: no cover
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import socketserver

    class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True


# ══════════════════════════════════════════════════════════════════════════
# 卷一  站点常量
# ══════════════════════════════════════════════════════════════════════════

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

_HOSTS = (
    "https://javmit.com",
)

_DEFAULT_HOST = _HOSTS[0]

_HOME_MIN_BYTES = 20000

_TIMEOUT = 20
_DETAIL_TIMEOUT = 25

_LANG = "/zh-CN"

# 分类表：(显示名, type_id)
_CLASSES = (
    ("主页", "home"),
    ("字幕", _LANG + "/category/subtitles/"),
    ("最新", "video"),
    ("未经审查", "uncensored_index"),
    ("分类", "categories_index"),
    ("演员", "actors_index"),
)

# 「最新」分类的过滤器（与壳 filters 协议对齐）
_FILTERS = {
    "video": [
        {"key": "sort", "name": "排序", "value": [
            {"n": "最新", "v": "date"},
            {"n": "最受关注", "v": "views"},
            {"n": "评分最高", "v": "liked"},
            {"n": "A-Z", "v": "title"},
            {"n": "随机", "v": "random"},
        ]},
        {"key": "res", "name": "画质", "value": [
            {"n": "全部", "v": ""},
            {"n": "4K", "v": "4K"},
            {"n": "1080P", "v": "1080P"},
            {"n": "720P", "v": "720P"},
            {"n": "480P", "v": "480P"},
        ]},
        {"key": "date", "name": "时间", "value": [
            {"n": "所有时间", "v": "all"},
            {"n": "最后一小时", "v": "hour"},
            {"n": "今天", "v": "day"},
            {"n": "这星期", "v": "week"},
            {"n": "本月", "v": "month"},
        ]},
    ]
}

# 无码子来源快照（实时拉取失败时兜底）
_UNC_SNAPSHOT = [
    (_LANG + "/uncensored/uncensored-leak/", "未删减版泄露", "1525"),
    (_LANG + "/uncensored/fc2/", "FC2", "1218"),
    (_LANG + "/uncensored/heyzo/", "HEYZO", "245"),
    (_LANG + "/uncensored/caribbeancom/", "Caribbeancom", "212"),
    (_LANG + "/uncensored/10musume/", "10musume", "160"),
    (_LANG + "/uncensored/1pondo/", "1pondo", "154"),
    (_LANG + "/uncensored/pacopacomama/", "帕科帕科马马", "142"),
    (_LANG + "/uncensored/tokyohot/", "Tokyo Hot", "109"),
    (_LANG + "/uncensored/naughty0930/", "H0930", "105"),
    (_LANG + "/uncensored/marriedslash/", "已婚斜杠", "96"),
    (_LANG + "/uncensored/naughty4610/", "淘气4610", "90"),
    (_LANG + "/uncensored/caribbeancompr/", "加勒比公司", "68"),
    (_LANG + "/uncensored/gachinco/", "加钦科", "0"),
    (_LANG + "/uncensored/xxx-av/", "XXX-AV", "0"),
]


# ══════════════════════════════════════════════════════════════════════════
# 卷二  HTTP 层
# ══════════════════════════════════════════════════════════════════════════

_SESSION = None
_SESSION_LOCK = threading.Lock()


def _headers(site=None, extra=None):
    h = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if site:
        h["Referer"] = site.rstrip("/") + "/"
    if extra:
        h.update(extra)
    return h


def _get_session():
    global _SESSION
    if not _HAS_REQUESTS:
        return None
    with _SESSION_LOCK:
        if _SESSION is None:
            try:
                s = requests.Session()
                s.headers.update(_headers())
                s.max_redirects = 5
                _SESSION = s
            except Exception:
                _SESSION = False
        return _SESSION or None


def _http_get(url, site=None, timeout=None, headers=None):
    timeout = timeout or _TIMEOUT
    hdr = headers if headers is not None else _headers(site)
    sess = _get_session()
    if sess is not None:
        try:
            r = sess.get(url, headers=hdr, timeout=timeout, allow_redirects=True)
            ct = r.headers.get("Content-Type", "") or ""
            return r.status_code, ct, r.content
        except Exception:
            pass
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, (r.headers.get("Content-Type") or ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Content-Type") or "") if e.headers else "", b""


def _get_text(url, site=None, timeout=None, headers=None):
    st, ct, body = _http_get(url, site=site, timeout=timeout, headers=headers)
    if st >= 400:
        raise RuntimeError("HTTP %s for %s" % (st, url))
    enc = "utf-8"
    m = re.search(r"charset=([\w\-]+)", ct or "", re.I)
    if m:
        enc = m.group(1)
    try:
        return body.decode(enc, "ignore")
    except Exception:
        return body.decode("utf-8", "ignore")


def _get_text_retry(url, site=None, timeout=None, attempts=3, min_len=500):
    last = None
    for i in range(attempts):
        try:
            txt = _get_text(url, site=site, timeout=timeout)
            if txt and len(txt) > min_len:
                return txt
            last = RuntimeError("short body %d" % len(txt or ""))
        except Exception as e:
            last = e
        time.sleep(0.5 * (i + 1))
    raise last if last else RuntimeError("fetch failed")


# ══════════════════════════════════════════════════════════════════════════
# 卷三  域名发现
# ══════════════════════════════════════════════════════════════════════════

_HOST_CACHE = ""
_HOST_LOCK = threading.Lock()


def _valid_home(body):
    if not body or len(body) < _HOME_MIN_BYTES:
        return False
    if b"v-card" not in body and b"list-video" not in body and b"/zh-CN/" not in body:
        return False
    low = body[:20000].lower()
    return b"javmit" in low


def _probe_host(host, out, idx, timeout=9):
    try:
        st, ct, body = _http_get(host.rstrip("/") + _LANG + "/", timeout=timeout)
        if st == 200 and _valid_home(body):
            out[idx] = host
    except Exception:
        return


def _discover_host():
    global _HOST_CACHE
    if _HOST_CACHE:
        return _HOST_CACHE
    with _HOST_LOCK:
        if _HOST_CACHE:
            return _HOST_CACHE
        hosts = list(_HOSTS)
        out = [None] * len(hosts)
        ths = []
        for i, h in enumerate(hosts):
            t = threading.Thread(target=_probe_host, args=(h, out, i))
            t.daemon = True
            t.start()
            ths.append(t)
        deadline = time.time() + 12
        for t in ths:
            left = deadline - time.time()
            if left <= 0:
                break
            t.join(left)
        for i in range(len(hosts)):
            if out[i]:
                _HOST_CACHE = out[i]
                return _HOST_CACHE
        _HOST_CACHE = _DEFAULT_HOST
        return _HOST_CACHE


def _site():
    return _discover_host().rstrip("/")


# ══════════════════════════════════════════════════════════════════════════
# 卷四  列表 / 详情解析
# ══════════════════════════════════════════════════════════════════════════

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(s):
    if not s:
        return ""
    s = _htmlmod.unescape(s)
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = _TAG_RE.sub("", s)
    s = s.replace("\u00a0", " ").replace("\u3000", " ")
    return _WS_RE.sub(" ", s).strip()


def _path_of(url):
    p = urlparse(url or "")
    return p.path or "/"


def _dur_norm(t):
    nums = re.findall(r"\d+", t or "")
    if len(nums) >= 3:
        return "%d:%02d:%02d" % (int(nums[0]), int(nums[1]), int(nums[2]))
    if len(nums) == 2:
        return "%d:%02d" % (int(nums[0]), int(nums[1]))
    if len(nums) == 1:
        return nums[0]
    return ""


def _pagecount(html, pg):
    nums = []
    for m in re.finditer(
            r'class="[^"]*page-numbers[^"]*"[^>]*href="([^"]+)"', html or ""):
        for n in re.findall(r"/page/(\d+)/", m.group(1)):
            nums.append(int(n))
    for m in re.finditer(
            r'href="([^"]+)"[^>]*class="[^"]*page-numbers', html or ""):
        for n in re.findall(r"/page/(\d+)/", m.group(1)):
            nums.append(int(n))
    pc = max(nums) if nums else int(pg)
    return max(pc, int(pg))


def _abs(u, site=None):
    if not u:
        return ""
    u = u.strip().replace("\\/", "/")
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin((site or _site()).rstrip("/") + "/", u)


def _parse_list(html, site=None):
    """统一解析 v-card / list-video 两种卡片，按出现顺序去重。"""
    site = site or _site()
    items = []
    seen = set()
    for m in re.finditer(
            r'<article class="(?:v-card|list-video)"[^>]*>(.*?)</article>',
            html or "", re.S):
        try:
            blk = m.group(1)
            lm = re.search(
                r'<a href="(https://javmit\.com' + _LANG + r'/[^"]+/)" '
                r'class="(?:vc-thumb-wrap|lv-thumb)"', blk)
            if not lm:
                lm = re.search(
                    r'<a href="(https://javmit\.com' + _LANG + r'/[^"]+/)"', blk)
            if not lm:
                continue
            path = _path_of(lm.group(1))
            if any(k in path for k in ("/category/", "/actor/", "/tag/", "/channel/")):
                continue
            if path in seen:
                continue
            seen.add(path)

            pic = ""
            im = re.search(
                r'<img[^>]+class="(?:vc-thumb-img|lv-thumb-img)"[^>]*>', blk)
            if im:
                tag = im.group(0)
                ss = re.search(r'srcset="([^"]+)"', tag)
                if ss:
                    best, bw = "", -1
                    for part in ss.group(1).split(","):
                        part = part.strip()
                        mm = re.match(r"(\S+)\s+(\d+)w", part)
                        if mm and int(mm.group(2)) > bw:
                            bw, best = int(mm.group(2)), mm.group(1)
                    pic = best
                if not pic:
                    sm = re.search(r'src="([^"]+)"', tag)
                    pic = sm.group(1) if sm else ""
            pic = _abs(pic, site)

            tm = re.search(r'<h3 class="(?:vc-title|lv-title)">(.*?)</h3>',
                           blk, re.S)
            title = _clean(tm.group(1)) if tm else ""
            if not title:
                am = re.search(r'<img[^>]+alt="([^"]+)"', blk)
                title = _clean(am.group(1)) if am else path
            title = re.sub(r"\[(?:下载和[^\]]*|Download[^\]]*)\]\s*$",
                           "", title).strip()

            dm = re.search(r'class="(?:vc-dur|lv-dur)">([^<]+)<', blk)
            remarks = _dur_norm(dm.group(1)) if dm else ""
            if "rawx-unc-badge" in blk:
                remarks = ("无码 " + remarks).strip()

            items.append({
                "vod_id": path,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
        except Exception:
            continue
    return items


def _parse_detail(html, vid, site=None):
    """解析详情页元数据 + 播放线路。返回 (vod_dict, [(label, abs_url), ...])。"""
    site = site or _site()
    vod = {
        "vod_id": vid, "vod_name": "", "vod_pic": "", "vod_content": "",
        "vod_actor": "", "vod_director": "", "vod_area": "日本",
        "vod_lang": "", "vod_year": "", "vod_remarks": "",
    }

    # JSON-LD VideoObject
    ld = {}
    for m in re.finditer(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.S):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        for o in (d.get("@graph") or [d]):
            if isinstance(o, dict) and o.get("@type") == "VideoObject":
                ld = o
                break
        if ld:
            break

    if ld.get("name"):
        vod["vod_name"] = _clean(ld["name"])
    if ld.get("description"):
        vod["vod_content"] = _clean(ld["description"])
    if ld.get("thumbnailUrl"):
        vod["vod_pic"] = _abs(ld["thumbnailUrl"], site)
    if ld.get("uploadDate"):
        vod["vod_year"] = str(ld["uploadDate"])[:4]
    if ld.get("duration"):
        dm = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(ld["duration"]))
        if dm:
            h, mi, s = (int(x) if x else 0 for x in dm.groups())
            vod["vod_remarks"] = "%d:%02d:%02d" % (h, mi, s) if h else "%d:%02d" % (mi, s)

    actors_ld = []
    if isinstance(ld.get("actor"), list):
        actors_ld = [a.get("name", "") for a in ld["actor"] if isinstance(a, dict)]

    chip_names = []
    for m in re.finditer(r'class="si-actor-card">(.*?)</a>', html, re.S):
        am = re.search(r'<img[^>]+alt="([^"]+)"', m.group(1))
        if am and _clean(am.group(1)):
            chip_names.append(_clean(am.group(1)))
    if not chip_names:
        for m in re.finditer(
                r'<a[^>]+href="https://javmit\.com' + _LANG +
                r'/actor/[^"]+"[^>]*class="actor-chip"[^>]*>(.*?)</a>', html, re.S):
            nm = re.search(r'actor-chip-name">([^<]+)<', m.group(1))
            if nm:
                chip_names.append(_clean(nm.group(1)))
    vod["vod_actor"] = ", ".join(chip_names or [a for a in actors_ld if a])

    if not vod["vod_name"]:
        om = re.search(r'property="og:title" content="([^"]+)"', html)
        vod["vod_name"] = _clean(om.group(1)).replace(" - JAVMIT", "") if om else vid
    pm = re.search(r'<video[^>]+poster="([^"]+)"', html)
    if pm:
        vod["vod_pic"] = _abs(pm.group(1), site)

    kinds = []
    for m in re.finditer(
            r'<a[^>]+href="https://javmit\.com' + _LANG +
            r'/(?:category|tag)/[^"]+"[^>]*>([^<]+)</a>', html):
        t = _clean(m.group(1))
        if t and t not in kinds:
            kinds.append(t)
    vod["type_name"] = ", ".join(kinds[:8])

    # 播放线路：画质按钮 AUTO/1080P/480P
    lines = []
    seen = set()
    for m in re.finditer(
            r'class="rawx-quality-btn[^"]*"[^>]*data-src="([^"]+)"[^>]*'
            r'data-label="([^"]+)"|data-src="([^"]+)"[^>]*data-label="([^"]+)"',
            html):
        src = m.group(1) or m.group(3)
        lab = m.group(2) or m.group(4)
        src = _abs(src, site)
        if src and src not in seen:
            seen.add(src)
            lines.append((lab or "默认", src))
    if not lines:
        mm = re.search(r'data-default-src="([^"]+\.m3u8[^"]*)"', html) or \
            re.search(r'property="og:video" content="([^"]+)"', html) or \
            re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
        if mm:
            lines.append(("默认", _abs(mm.group(1), site)))

    return vod, lines


# ══════════════════════════════════════════════════════════════════════════
# 卷五  自建本地中继
# ══════════════════════════════════════════════════════════════════════════

_RELAY_LOCK = threading.Lock()
_RELAY = None
_RELAY_TRIED = False
_RELAY_WORKERS = [0, 0]


def _is_playlist(url, ctype, body):
    if body[:7] == b"#EXTM3U":
        return True
    if "mpegurl" in (ctype or "").lower():
        return True
    return url.lower().split("?")[0].endswith(".m3u8")


def _rewrite_tag_line(line, base_url, prefix):
    def _sub(m):
        raw = m.group(1)
        return 'URI="%s%s"' % (prefix, quote(urljoin(base_url, raw), safe=""))
    return re.sub(r'URI="([^"]+)"', _sub, line)


def _rewrite_m3u8(text, base_url, prefix):
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            out.append(raw)
            continue
        if s.startswith("#"):
            out.append(_rewrite_tag_line(s, base_url, prefix) if 'URI="' in s else raw)
            continue
        out.append(prefix + quote(urljoin(base_url, s), safe=""))
    return "\n".join(out) + "\n"


def _origin_of(u):
    try:
        p = urlparse(u)
        if p.scheme and p.netloc:
            return "%s://%s" % (p.scheme, p.netloc)
    except Exception:
        pass
    return ""


def _relay_fetch(target):
    site = _origin_of(target)
    st, ct, body = 0, "", b""
    for attempt in (0, 1):
        try:
            st, ct, body = _http_get(target, site=site, timeout=25)
        except Exception:
            st, ct, body = 0, "", b""
        if st == 200 and body:
            break
        if st not in (0, 403, 408, 429, 500, 502, 503, 504):
            break
        if attempt == 0:
            time.sleep(0.35)

    if st == 0 or (st >= 400 and not body):
        try:
            st, ct, body = _http_get(target, site=None, timeout=25,
                                     headers={"User-Agent": _UA})
        except Exception:
            return 502, "text/plain", b"relay upstream error"
    if st >= 400 and not body:
        return 502, "text/plain", b"relay upstream error"

    if _is_playlist(target, ct, body):
        prefix = _relay_prefix()
        if prefix:
            try:
                txt = _rewrite_m3u8(body.decode("utf-8", "ignore"), target, prefix)
                return st, "application/vnd.apple.mpegurl", txt.encode("utf-8")
            except Exception:
                return st, "application/vnd.apple.mpegurl", body
        return st, "application/vnd.apple.mpegurl", body

    if body[:1] == b"\x47":
        return st, "video/mp2t", body
    return st, (ct or "application/octet-stream"), body


class _RelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, status, ctype, body):
        try:
            self.send_response(int(status))
            self.send_header("Content-Type", ctype or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Accept-Ranges", "none")
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            try:
                self.close_connection = True
            except Exception:
                pass

    def do_HEAD(self):
        self._send(200, "text/plain", b"")

    def do_GET(self):
        _RELAY_WORKERS[0] += 1
        _RELAY_WORKERS[1] += 1
        try:
            p = urlparse(self.path)
            if p.path.rstrip("/") not in ("/jmv", ""):
                self._send(404, "text/plain", b"not found")
                return
            q = parse_qs(p.query or "")
            target = (q.get("u") or [""])[0]
            if not target:
                self._send(400, "text/plain", b"missing u")
                return
            target = unquote(target)
            st, ct, body = _relay_fetch(target)
            self._send(st, ct, body)
        except Exception:
            try:
                self._send(502, "text/plain", b"relay error")
            except Exception:
                pass
        finally:
            _RELAY_WORKERS[0] -= 1


def _ensure_relay():
    global _RELAY, _RELAY_TRIED
    with _RELAY_LOCK:
        if _RELAY is not None:
            return _RELAY
        if _RELAY_TRIED:
            return (None, 0)
        _RELAY_TRIED = True
        for _ in range(3):
            try:
                srv = ThreadingHTTPServer(("127.0.0.1", 0), _RelayHandler)
                srv.daemon_threads = True
                t = threading.Thread(target=srv.serve_forever,
                                     kwargs={"poll_interval": 0.3})
                t.daemon = True
                t.start()
                _RELAY = (srv, int(srv.server_address[1]))
                return _RELAY
            except Exception:
                continue
        _RELAY = (None, 0)
        return _RELAY


def _relay_prefix():
    srv, port = _ensure_relay()
    if not port:
        return ""
    return "http://127.0.0.1:%d/jmv?u=" % port


def _relay_wrap(u):
    p = _relay_prefix()
    return (p + quote(u, safe="")) if (p and u) else ""


def _relay_unwrap(u):
    if not u:
        return u
    if "/jmv?u=" in u and u.startswith("http://127.0.0.1:"):
        return unquote(u.split("/jmv?u=", 1)[1])
    if "/proxy?url=" in u and u.startswith("http://127.0.0.1:"):
        return unquote(u.split("/proxy?url=", 1)[1])
    return u


# ── 壳代理探测（备选通道） ────────────────────────────────────────────────

_SHELL_PORTS = (9978, 9988, 9999, 8888, 8080, 8000)
_SHELL_PORT_OK = None
_SHELL_LOCK = threading.Lock()
_SHELL_PROBE_MARK = b"<html"
_SHELL_PROBE_URL = "https://example.com/"


def _open_ports():
    out = []
    for p in _SHELL_PORTS:
        try:
            s = socket.socket()
            s.settimeout(0.35)
            s.connect(("127.0.0.1", p))
            s.close()
            out.append(p)
        except Exception:
            continue
    return out


def _probe_shell_port(port, out, idx):
    try:
        u = "http://127.0.0.1:%d/proxy?url=%s" % (
            port, quote(_SHELL_PROBE_URL, safe=""))
        st, ct, body = _http_get(u, site=None, timeout=8,
                                 headers={"User-Agent": _UA})
        if st == 200 and body and (_SHELL_PROBE_MARK in body[:4096] or len(body) > 100):
            out[idx] = port
    except Exception:
        return


def _find_shell_port():
    global _SHELL_PORT_OK
    if _SHELL_PORT_OK is not None:
        return _SHELL_PORT_OK
    with _SHELL_LOCK:
        if _SHELL_PORT_OK is not None:
            return _SHELL_PORT_OK
        ports = _open_ports()
        out = [0] * len(ports)
        ths = []
        for i, p in enumerate(ports):
            t = threading.Thread(target=_probe_shell_port, args=(p, out, i))
            t.daemon = True
            t.start()
            ths.append(t)
        for t in ths:
            t.join(9)
        found = 0
        for v in out:
            if v:
                found = v
                break
        _SHELL_PORT_OK = found
        return found


# ══════════════════════════════════════════════════════════════════════════
# 卷六  Spider
# ══════════════════════════════════════════════════════════════════════════

def _norm_ids(ids):
    """detailContent 的 ids 四态归一化；JAVMIT 的 vod_id 是完整 /zh-CN/ 路径。"""
    if isinstance(ids, (list, tuple)):
        parts = [str(x) for x in ids]
    else:
        parts = str(ids or "").split(",")
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        p = _relay_unwrap(p)
        p = p.split("#")[0].split("?")[0]
        if not p:
            continue
        if p.startswith("http"):
            p = urlparse(p).path
        if not p.startswith("/"):
            p = "/" + p.strip("/") + "/"
        out.append(p)
    return out


def _norm_extend(extend):
    if not extend:
        return {}
    if isinstance(extend, dict):
        return extend
    try:
        return json.loads(str(extend))
    except Exception:
        return {}


class Spider:

    def __init__(self):
        self.site = _DEFAULT_HOST
        try:
            t = threading.Thread(target=self._warmup)
            t.daemon = True
            t.start()
        except Exception:
            pass

    def _warmup(self):
        try:
            self.site = _discover_host()
        except Exception:
            pass
        try:
            _ensure_relay()
        except Exception:
            pass

    # ── 契约必需 ────────────────────────────────────────────────────────

    def getDependence(self):
        return []

    def init(self, extend=""):
        cfg = extend
        if isinstance(cfg, str) and cfg.strip().startswith("{"):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = extend
        if isinstance(cfg, dict):
            h = cfg.get("host") or cfg.get("url") or cfg.get("site")
            if h and str(h).startswith("http"):
                global _HOST_CACHE
                _HOST_CACHE = str(h).rstrip("/")
        elif isinstance(cfg, str):
            s = cfg.strip()
            if s.startswith("http"):
                _HOST_CACHE = s.rstrip("/")
        self.site = _discover_host()
        return self.site

    def homeContent(self, filter=None):
        return {
            "class": [{"type_id": tid, "type_name": name} for name, tid in _CLASSES],
            "filters": _FILTERS,
        }

    def homeVideoContent(self):
        try:
            site = _site()
            html = _get_text_retry(site + _LANG + "/", site=site, timeout=_TIMEOUT)
            return {"list": _parse_list(html, site)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        extend = _norm_extend(extend)
        try:
            site = _site()
            tid = str(tid or "home").strip()

            if tid == "home":
                html = _get_text_retry(site + _LANG + "/", site=site, timeout=_TIMEOUT)
                lst = _parse_list(html, site)
                return {"page": 1, "pagecount": 1, "limit": len(lst) or 12,
                        "total": len(lst), "list": lst}

            if tid == "uncensored_index":
                return {"page": 1, "pagecount": 1, "limit": 20, "total": 15,
                        "list": self._uncensored_index()}

            if tid == "categories_index":
                return {"page": 1, "pagecount": 1, "limit": 120, "total": 115,
                        "list": self._categories_index()}

            if tid == "actors_index":
                return self._actors_index(pg)

            if tid == "video":
                return self._video_browse(pg, extend)

            # 其余一律是站内列表路径（分类 / 演员 / 标签 / 无码子页 / 字幕）
            path = tid if tid.startswith("/") else "/" + tid
            url = site + path
            if pg > 1:
                url = url.rstrip("/") + "/page/%d/" % pg
            html = _get_text_retry(url, site=site, timeout=_TIMEOUT)
            lst = _parse_list(html, site)
            return {"page": pg, "pagecount": _pagecount(html, pg),
                    "limit": len(lst), "total": 0, "list": lst}
        except Exception:
            return {"list": [], "page": pg, "pagecount": pg, "limit": 0, "total": 0}

    def _video_browse(self, pg, extend):
        site = _site()
        sort = extend.get("sort") or "date"
        res = extend.get("res") or ""
        date = extend.get("date") or "all"
        q = "sort=%s&date=%s&view=grid&rawx_per_page=48" % (sort, date)
        if res:
            q += "&res=" + quote(str(res), safe="")
        if sort == "random":
            q += "&rawx_seed=2095419780"
        if pg > 1:
            url = "%s%s/video/page/%d/?%s" % (site, _LANG, pg, q)
        else:
            url = "%s%s/video/?%s" % (site, _LANG, q)
        html = _get_text_retry(url, site=site, timeout=_TIMEOUT)
        lst = _parse_list(html, site)
        return {"page": pg, "pagecount": _pagecount(html, pg),
                "limit": len(lst), "total": 0, "list": lst}

    def _uncensored_index(self):
        site = _site()
        entries = [{
            "vod_id": _LANG + "/uncensored/",
            "vod_name": "全部未经审查",
            "vod_pic": "",
            "vod_remarks": "4180",
            "vod_tag": "folder",
        }]
        subs = []
        try:
            html = _get_text(site + _LANG + "/uncensored/", site=site, timeout=_TIMEOUT)
            if html:
                seen = set()
                for m in re.finditer(
                        r'<a href="https://javmit\.com(' + _LANG +
                        r'/uncensored/[a-z0-9\-]+/)"[^>]*>(.*?)</a>',
                        html, re.S):
                    path, inner = m.group(1), m.group(2)
                    if path in seen:
                        continue
                    seen.add(path)
                    name = _clean(re.sub(r"<span[^>]*>.*?</span>", "",
                                         inner, flags=re.S))
                    cm = re.search(r"<span[^>]*>([\d,]+)</span>", inner)
                    if name:
                        subs.append((path, name, cm.group(1) if cm else ""))
        except Exception:
            pass
        if not subs:
            subs = _UNC_SNAPSHOT
        for path, name, cnt in subs:
            entries.append({
                "vod_id": path,
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": cnt,
                "vod_tag": "folder",
            })
        return entries

    def _categories_index(self):
        site = _site()
        entries = []
        try:
            html = _get_text(site + _LANG + "/categories/", site=site, timeout=_TIMEOUT)
            if html:
                for blk in html.split('<div class="cat-card">')[1:]:
                    self._cat_card(blk, entries)
                if not entries:
                    for m in re.finditer(
                            r'<a href="(https://javmit\.com' + _LANG +
                            r'/(?:category|uncensored)/[^"]+)" '
                            r'class="cc-header">(.*?)</a>', html, re.S):
                        name = _clean(
                            re.search(r'cc-name">(.*?)</div>', m.group(2), re.S).group(1)) \
                            if "cc-name" in m.group(2) else _clean(m.group(2))
                        entries.append({
                            "vod_id": _path_of(m.group(1)),
                            "vod_name": name,
                            "vod_pic": "",
                            "vod_remarks": "",
                            "vod_tag": "folder",
                        })
        except Exception:
            pass
        return entries

    def _cat_card(self, blk, entries):
        site = _site()
        hm = re.search(
            r'<a href="(https://javmit\.com' + _LANG +
            r'/(?:category|uncensored)/[^"]*)" class="cc-header">', blk)
        if not hm:
            return
        nm = re.search(r'cc-name">(.*?)</div>', blk, re.S)
        cm = re.search(r'cc-count">([^<]+)<', blk)
        pm = re.search(r'class="cc-preview-img"[^>]*src="([^"]+)"', blk) or \
            re.search(r'<img[^>]+src="([^"]+)"[^>]*class="cc-preview-img"', blk)
        entries.append({
            "vod_id": _path_of(hm.group(1)),
            "vod_name": _clean(nm.group(1)) if nm else _path_of(hm.group(1)),
            "vod_pic": _abs(pm.group(1), site) if pm else "",
            "vod_remarks": _clean(cm.group(1)) if cm else "",
            "vod_tag": "folder",
        })

    def _actors_index(self, pg):
        site = _site()
        url = site + _LANG + "/actors/"
        if pg > 1:
            url += "page/%d/" % pg
        entries = []
        try:
            html = _get_text_retry(url, site=site, timeout=_TIMEOUT)
            for m in re.finditer(
                    r'<a href="(https://javmit\.com' + _LANG +
                    r'/actor/[^"]+)" class="costar-card actors-hub-card">(.*?)</a>',
                    html or "", re.S):
                blk = m.group(2)
                nm = re.search(r'actors-hub-name">([^<]+)<', blk)
                cm = re.search(r'actors-hub-count">([^<]+)<', blk)
                pm = re.search(r'<img[^>]+src="([^"]+)"', blk)
                entries.append({
                    "vod_id": _path_of(m.group(1)),
                    "vod_name": _clean(nm.group(1)) if nm else _path_of(m.group(1)),
                    "vod_pic": _abs(pm.group(1), site) if pm else "",
                    "vod_remarks": _clean(cm.group(1)) if cm else "",
                    "vod_tag": "folder",
                })
            pc = _pagecount(html, pg)
        except Exception:
            html, pc = "", pg
        if pc < pg:
            pc = pg
        return {"page": pg, "pagecount": pc, "limit": 100,
                "total": pc * 100, "list": entries}

    def detailContent(self, ids):
        out = []
        try:
            site = _site()
            for vid in _norm_ids(ids)[:1]:
                html = _get_text_retry(site + vid, site=site,
                                       timeout=_DETAIL_TIMEOUT)
                info, lines = _parse_detail(html, vid, site)
                if lines:
                    info["vod_play_from"] = "$$$".join(l[0] for l in lines)
                    info["vod_play_url"] = "$$$".join("播放$" + l[1] for l in lines)
                else:
                    info["vod_play_from"] = "JAVMIT"
                    info["vod_play_url"] = "播放$" + vid
                out.append(info)
        except Exception:
            return {"list": []}
        return {"list": out}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        try:
            site = _site()
            kw = str(key or "").strip()
            if not kw:
                return {"list": [], "page": pg, "pagecount": pg}
            q = quote(kw, safe="")
            if pg > 1:
                url = "%s%s/page/%d/?s=%s" % (site, _LANG, pg, q)
            else:
                url = "%s%s/?s=%s" % (site, _LANG, q)
            html = _get_text_retry(url, site=site, timeout=_TIMEOUT)
            lst = _parse_list(html, site)
            return {"list": lst, "page": pg,
                    "pagecount": _pagecount(html, pg),
                    "limit": len(lst), "total": 0}
        except Exception:
            return {"list": [], "page": pg, "pagecount": pg, "limit": 0, "total": 0}

    def playerContent(self, flag, ids, vipFlags=None):
        header = _headers(_site())
        empty = {"parse": 0, "jx": 0, "playUrl": "", "url": "",
                 "format": "application/x-mpegURL", "header": header}
        try:
            s = str(ids or "")
            if "$" in s:
                s = s.split("$", 1)[1]
            s = _relay_unwrap(s.strip())
            try:
                s = unquote(s)
            except Exception:
                pass
            s = s.strip().replace("\\/", "/")
            if not s:
                return empty

            target = _abs(s)
            relayed = _relay_wrap(target)
            if relayed:
                return {"parse": 0, "jx": 0, "playUrl": "",
                        "url": relayed,
                        "format": "application/x-mpegURL",
                        "header": {}}

            shell_port = _find_shell_port()
            if shell_port:
                return {"parse": 0, "jx": 0, "playUrl": "",
                        "url": "http://127.0.0.1:%d/proxy?url=%s" % (
                            shell_port, quote(target, safe="")),
                        "format": "application/x-mpegURL",
                        "header": {}}

            return {"parse": 0, "jx": 0, "playUrl": "",
                    "url": target,
                    "format": "application/x-mpegURL",
                    "header": header}
        except Exception:
            return empty

    def localProxy(self, param):
        try:
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except Exception:
                    param = {"url": param}
            if not isinstance(param, dict):
                param = {}
            target = param.get("url") or param.get("u") or ""
            if isinstance(target, list):
                target = target[0] if target else ""
            target = unquote(str(target or "").strip())
            if not target.startswith("http"):
                return [404, "text/plain", b"bad url", {}]
            st, ct, body = _relay_fetch(target)
            if not isinstance(body, bytes):
                body = str(body).encode("utf-8", "ignore")
            return [int(st), ct or "application/octet-stream", body, {}]
        except Exception:
            return [502, "text/plain", b"proxy error", {}]

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        try:
            u = str(url or "").lower()
            return (".m3u8" in u) or (".mp4" in u) or ("mpegurl" in u)
        except Exception:
            return False

    def action(self, action):
        return {}

    def destroy(self):
        try:
            srv, port = _RELAY if _RELAY else (None, 0)
            if srv is not None:
                srv.shutdown()
                srv.server_close()
        except Exception:
            pass
        return None


# ── 本地调试入口 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    sp = Spider()
    print("host :", _discover_host())
    print("relay:", _relay_prefix() or "(不可用)")
    hc = sp.homeContent()
    print("分类 :", len(hc["class"]), [c["type_name"] for c in hc["class"]])
    cc = sp.categoryContent("video", 1, False, {"sort": "date"})
    print("列表 :", len(cc["list"]), "pagecount =", cc["pagecount"])
    if cc["list"]:
        v = cc["list"][0]
        print("首条 :", v["vod_id"], "|", v["vod_name"][:40], "|", v["vod_remarks"])
        dc = sp.detailContent([v["vod_id"]])
        if dc["list"]:
            d = dc["list"][0]
            print("详情 :", d["vod_name"][:40], "|", d["vod_year"],
                  "|", d["vod_actor"][:30])
            print("线路 :", d["vod_play_from"])
            print("选集 :", d["vod_play_url"][:120])
            fl = d["vod_play_from"].split("$$$")[0]
            tok = d["vod_play_url"].split("$$$")[0].split("$", 1)[1]
            pc = sp.playerContent(fl, tok, None)
            print("播放 :", (pc["url"] or "(EMPTY)")[:110])
    sc = sp.searchContent("ABF-335", False, "1")
    print("搜索 :", len(sc["list"]), [x["vod_id"] for x in sc["list"][:5]])
#（注：内容由AI生成）
