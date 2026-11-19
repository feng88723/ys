# -*- coding: utf-8 -*-
"""
AiPorn（aipornx 系域名）TVBox / FongMi Python Spider
=====================================================
单文件自包含，零第三方依赖（requests 可选，缺失自动降级 urllib）。
框架范式与 missav.py 完全一致：裸类 Spider、无参实例化、13 方法齐备、
detailContent 四态归一化、playerContent().header 为 dict、localProxy 返回四项。

站点结构（实测）
----------------
  首页          https://<host>/home/
  最新更新      /search/-------------/            （第 1 页）
                /search/----------<pg>---/       （第 N 页）
  频道          /aidj/<slug>/  例 /aidj/anthurium/  翻页 /aidj/<slug>/page/<pg>/
  标签          /search/------------<tag>-/      （第 1 页）
                /search/----------<pg>--<tag>-/  （第 N 页）
  详情          /detail/<id>/
  播放页        /play/<vid>-<ep>/
  搜索          /search/-------------/?wd=<kw>
                /search/<kw>----------<pg>---/

播放地址获取（关键）
--------------------
  播放页内联 player_data=({...}) JSON，其 url 形如 "<id>|<ep>"：
      GET /huangguo.php?ac=play&id=<id>&ep=<ep>&_=<ms>
  返回 JSON {code:1, url:"/hgmedia.php?e=<base64>"}；
  对 e= 后面的 base64 补 `=` 到 4 字节后解码，即得到真实 m3u8 地址。
  解码失败时退用 /hgmedia.php?e=... 站方代理直链。

防盗链
------
  · 详情/播放页要求带 Referer=<host>/，否则部分资源 403。
  · 真实 m3u8 分片不加密，但跨域直连时壳播放器可能缺 UA / Referer，
    因此本 spider 内置自建本地中继（127.0.0.1 随机端口）统一回源并兜底。
"""

import base64
import html as _htmlmod
import json
import os
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

# ── 可选依赖：线程化 HTTP 服务（Python 3.7+ 自带） ───────────────────────────
try:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
except Exception:                       # pragma: no cover - 极老解释器兜底
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import socketserver

    class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True


# ══════════════════════════════════════════════════════════════════════════
# 卷一  站点常量
# ══════════════════════════════════════════════════════════════════════════

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# 域名按「用户给定优先 + 实测可用镜像」排序；发现阶段并发探测，取第一个通过校验的
_HOSTS = (
    "https://www.aipornx.cc",
    "https://aipornx.cc",
)

_DEFAULT_HOST = _HOSTS[0]

_HOME_MIN_BYTES = 20000

_TIMEOUT = 20
_DETAIL_TIMEOUT = 25

# 分类表：(显示名, type_id)  →  categoryContent 按 type_id 分派
_CLASSES = (
    ("首页", "home"),
    ("最新更新", "latest"),
    ("AI成人短剧", "/aidj/anthurium/"),
    ("AI成人漫剧", "/aidj/camelia/"),
    ("AI换脸", "/aidj/daisy/"),
    ("AI魔改", "/aidj/frangipani/"),
    ("标签选剧", "tags_index"),
)

# 首页「标签选剧」明列的标签（实时拉取失败时兜底）
_TAGS_SNAPSHOT = ["现代", "都市", "奇幻", "大男主", "系统", "后宫"]


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
    """GET → (status, content_type, body_bytes)。失败抛异常。"""
    timeout = timeout or _TIMEOUT
    hdr = headers if headers is not None else _headers(site)
    sess = _get_session()
    if sess is not None:
        try:
            r = sess.get(url, headers=hdr, timeout=timeout, allow_redirects=True)
            ct = r.headers.get("Content-Type", "") or ""
            return r.status_code, ct, r.content
        except Exception:
            pass                        # 落到 urllib
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
    """带重试的取文本：站点偶发 5xx / 连接抖动时避免整页失败。"""
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
    """判定首页是否为真站（排除停放页 / JS 挑战页）。"""
    if not body or len(body) < _HOME_MIN_BYTES:
        return False
    if b"vod-card" not in body and b"/aidj/" not in body and b"/detail/" not in body:
        return False
    return True


def _probe_host(host, out, idx, timeout=9):
    try:
        st, ct, body = _http_get(host.rstrip("/") + "/home/", timeout=timeout)
        if st == 200 and _valid_home(body):
            out[idx] = host
    except Exception:
        return


def _discover_host():
    """并发探测镜像域名，返回第一个可用的（结果缓存）。"""
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
# 卷四  列表 / 详情 / 播放解析
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


def _fix_pic(u):
    if not u:
        return ""
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin(_site() + "/", u)


def _parse_list(html, site=None):
    """解析 vod-card 卡片（列表 / 频道 / 搜索 / 首页通用）。已去重。"""
    site = site or _site()
    items = []
    seen = set()
    for m in re.finditer(r'<article class="vod-card">(.*?)</article>', html or "", re.S):
        try:
            blk = m.group(1)
            lm = re.search(r'<a class="vod-pic" href="(/detail/\d+/)\s*"', blk)
            if not lm:
                continue
            path = lm.group(1)
            if path in seen:
                continue
            seen.add(path)

            im = re.search(r'<img[^>]+src="([^"]+)"', blk)
            pic = _fix_pic(im.group(1)) if im else ""
            if "media.hgpicimg.cc//" in pic:
                pic = pic.replace("media.hgpicimg.cc//", "media.hgpicimg.cc/")

            nm = re.search(r'<div class="vod-name"><a[^>]*>([^<]+)</a>', blk)
            if not nm:
                nm = re.search(r'<img[^>]+alt="([^"]+)"', blk)
            name = _clean(nm.group(1)) if nm else path

            rm = re.search(r'class="vod-remarks">([^<]+)<', blk)
            remarks = _clean(rm.group(1)) if rm else ""

            items.append({
                "vod_id": path,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
        except Exception:
            continue
    return items


def _pagecount(html, pg):
    nums = [int(n) for n in re.findall(r"/page/(\d+)/", html or "")]
    nums += [int(n) for n in re.findall(
        r'class="[^"]*current[^"]*"[^>]*>\s*(\d+)', html or "")]
    for n in re.findall(r"-{10}(\d+)-", html or ""):
        nums.append(int(n))
    pc = max(nums) if nums else int(pg)
    return max(pc, int(pg))


def _parse_detail(html, vid, site=None):
    """解析详情页元数据。"""
    site = site or _site()
    vod = {
        "vod_id": vid, "vod_name": "", "vod_pic": "", "vod_content": "",
        "vod_actor": "", "vod_director": "", "vod_area": "",
        "vod_lang": "", "vod_year": "", "vod_remarks": "",
    }
    om = re.search(r'property="og:title" content="([^"]+)"', html)
    vod["vod_name"] = _clean(om.group(1)) if om else ""
    if not vod["vod_name"]:
        hm = re.search(r'<div class="detail-info"><h1>([^<]+)</h1>', html)
        vod["vod_name"] = _clean(hm.group(1)) if hm else vid

    im = re.search(r'property="og:image" content="([^"]+)"', html)
    if im:
        vod["vod_pic"] = _fix_pic(im.group(1)).replace(
            "media.hgpicimg.cc//", "media.hgpicimg.cc/")

    dm = re.search(r'property="og:description" content="([^"]+)"', html)
    if dm:
        vod["vod_content"] = _clean(dm.group(1))

    tags = []
    for m in re.finditer(r'class="detail-tag"[^>]*>#([^<]+)</a>', html):
        t = _clean(m.group(1))
        if t and t not in tags:
            tags.append(t)
    vod["type_name"] = ", ".join(tags)
    return vod


def _collect_eps(html, site=None):
    """从详情页收集选集：{play_path: 集名}，按集号排序。"""
    site = site or _site()
    eps = {}
    for m in re.finditer(
            r'<a class="ep[^"]*"[^>]*href="(/play/[\d\-]+/)"[^>]*>([^<]+)</a>',
            html or ""):
        eps[m.group(1)] = _clean(m.group(2))
    if not eps:
        for m in re.finditer(
                r'href="(/play/[\d\-]+/)"[^>]*>(第[^<]*集)</a>', html or ""):
            eps[m.group(1)] = _clean(m.group(2))

    def _epno(p):
        mm = re.search(r"-(\d+)/$", p)
        return int(mm.group(1)) if mm else 0

    return sorted(eps.items(), key=lambda kv: _epno(kv[0]))


def _resolve_play(play_path, site=None):
    """播放页 → (真实m3u8或站方代理URL, 是否为m3u8直链)。

    流程：play 页 player_data JSON → huangguo.php API → hgmedia base64 解码。
    任何一步失败返回 ("", False)，由调用方降级。
    """
    site = site or _site()
    page_url = play_path if play_path.startswith("http") else site + play_path
    try:
        html = _get_text(page_url, site=site, timeout=_DETAIL_TIMEOUT)
    except Exception:
        return "", False
    try:
        pd = re.search(r"player_data=(\{.*?\})</script>", html or "", re.S)
        if not pd:
            return "", False
        data = json.loads(pd.group(1))
        raw = str(data.get("url") or "")
        parts = raw.split("|")
        if len(parts) < 2:
            return "", False
        api = "%s/huangguo.php?ac=play&id=%s&ep=%s&_=%d" % (
            site, quote(parts[0], safe=""), quote(parts[1], safe=""),
            int(time.time() * 1000))
        js = _get_text(api, site=site, timeout=15)
        try:
            d = json.loads(js) if js else {}
        except Exception:
            d = {}
        u = str(d.get("url") or "")
        if d.get("code") == 1 and u.startswith("/hgmedia.php?e="):
            proxy = site + u
            token = u.split("e=", 1)[1]
            pad = "=" * (-len(token) % 4)
            try:
                dec = base64.b64decode(token + pad).decode("utf-8", "ignore")
                if dec.startswith("http") and ".m3u8" in dec:
                    return dec, True
            except Exception:
                dec = ""
            return proxy, False
    except Exception:
        pass
    return "", False


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
            if p.path.rstrip("/") not in ("/ajv", ""):
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
    return "http://127.0.0.1:%d/ajv?u=" % port


def _relay_wrap(u):
    p = _relay_prefix()
    return (p + quote(u, safe="")) if (p and u) else ""


def _relay_unwrap(u):
    if not u:
        return u
    if "/ajv?u=" in u and u.startswith("http://127.0.0.1:"):
        return unquote(u.split("/ajv?u=", 1)[1])
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
    """detailContent 的 ids 四态归一化：str / list / tuple / 逗号串。

    AiPorn 的 vod_id 形如 /detail/123/（完整路径），不能像番号那样取末段。
    """
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
        if p.isdigit():
            p = "/detail/%s/" % p
        elif not p.startswith("/"):
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
            "filters": {},
        }

    def homeVideoContent(self):
        try:
            site = _site()
            html = _get_text_retry(site + "/home/", site=site, timeout=_TIMEOUT)
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
                html = _get_text_retry(site + "/home/", site=site, timeout=_TIMEOUT)
                lst = _parse_list(html, site)
                return {"page": 1, "pagecount": 1, "limit": len(lst) or 30,
                        "total": len(lst), "list": lst}

            if tid == "tags_index":
                return {"page": 1, "pagecount": 1, "limit": 20, "total": 6,
                        "list": self._tags_index()}

            if tid == "latest":
                if pg > 1:
                    url = "%s/search/----------%d---/" % (site, pg)
                else:
                    url = site + "/search/-------------/"
                html = _get_text_retry(url, site=site, timeout=_TIMEOUT)
                lst = _parse_list(html, site)
                return {"page": pg, "pagecount": _pagecount(html, pg),
                        "limit": len(lst), "total": 0, "list": lst}

            if tid.startswith("tag:"):
                tag = tid[4:]
                q = quote(tag, safe="")
                if pg > 1:
                    url = "%s/search/----------%d--%s-/" % (site, pg, q)
                else:
                    url = "%s/search/------------%s-/" % (site, q)
                html = _get_text_retry(url, site=site, timeout=_TIMEOUT)
                lst = _parse_list(html, site)
                return {"page": pg, "pagecount": _pagecount(html, pg),
                        "limit": len(lst), "total": 0, "list": lst}

            # 频道路径 /aidj/<slug>/
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

    def _tags_index(self):
        tags = []
        try:
            site = _site()
            html = _get_text(site + "/home/", site=site, timeout=_TIMEOUT)
            if html:
                seen = set()
                for m in re.finditer(
                        r'href="/search/-+%E[^"]+"[^>]*>#([^<]+)</a>', html):
                    t = _clean(m.group(1))
                    if t and t not in seen:
                        seen.add(t)
                        tags.append(t)
        except Exception:
            pass
        if not tags:
            tags = list(_TAGS_SNAPSHOT)
        return [{
            "vod_id": "tag:" + t,
            "vod_name": t,
            "vod_pic": "",
            "vod_remarks": "",
            "vod_tag": "folder",
        } for t in tags]

    def detailContent(self, ids):
        out = []
        try:
            site = _site()
            for vid in _norm_ids(ids)[:1]:
                html = _get_text_retry(site + vid, site=site,
                                       timeout=_DETAIL_TIMEOUT)
                info = _parse_detail(html, vid, site)
                eps = _collect_eps(html, site)

                if eps:
                    lines = []
                    for play_path, name in eps:
                        lines.append("%s$%s" % (name, play_path))
                    info["vod_play_from"] = "AiPorn"
                    info["vod_play_url"] = "#".join(lines)
                    info["vod_remarks"] = "更新至%d集" % len(eps)
                else:
                    info["vod_play_from"] = "AiPorn"
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
                url = "%s/search/%s----------%d---/" % (site, q, pg)
            else:
                url = "%s/search/-------------/?wd=%s" % (site, q)
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
            s = s.strip()
            if not s:
                return empty

            site = _site()
            target, is_m3u8 = _resolve_play(s, site=site)
            if not target:
                # 解析失败：退化为壳自带嗅探播放原播放页
                page = s if s.startswith("http") else site + s
                return {"parse": 1, "jx": 0, "playUrl": "", "url": page,
                        "format": "", "header": header}

            relayed = _relay_wrap(target)
            if relayed:
                return {"parse": 0, "jx": 0, "playUrl": "",
                        "url": relayed,
                        "format": "application/x-mpegURL" if is_m3u8 else "",
                        "header": {}}

            shell_port = _find_shell_port()
            if shell_port:
                return {"parse": 0, "jx": 0, "playUrl": "",
                        "url": "http://127.0.0.1:%d/proxy?url=%s" % (
                            shell_port, quote(target, safe="")),
                        "format": "application/x-mpegURL" if is_m3u8 else "",
                        "header": {}}

            return {"parse": 0, "jx": 0, "playUrl": "",
                    "url": target,
                    "format": "application/x-mpegURL" if is_m3u8 else "",
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
    cc = sp.categoryContent("latest", 1, False, None)
    print("列表 :", len(cc["list"]), "pagecount =", cc["pagecount"])
    if cc["list"]:
        v = cc["list"][0]
        print("首条 :", v["vod_id"], "|", v["vod_name"][:40], "|", v["vod_remarks"])
        dc = sp.detailContent([v["vod_id"]])
        if dc["list"]:
            d = dc["list"][0]
            print("详情 :", d["vod_name"][:40])
            print("线路 :", d["vod_play_from"])
            print("选集 :", d["vod_play_url"][:120])
            tok = d["vod_play_url"].split("#")[0].split("$", 1)[1]
            pc = sp.playerContent(d["vod_play_from"], tok, None)
            print("播放 :", (pc["url"] or "(EMPTY)")[:110])
    sc = sp.searchContent("AI", False, "1")
    print("搜索 :", len(sc["list"]))
#（注：内容由AI生成）
