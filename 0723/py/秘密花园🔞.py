# -*- coding: utf-8 -*-
"""
秘密花园 · TVBox 解析器（spider）—— 新平台版 v2
====================================================================
"""

import base64
import hashlib
import json
import random
import re
import ssl
import threading
import time

# Python 2/3 双兼容（部分 TVBox App 的 py 环境仍是 Python 2.7）
try:
    from urllib import request as _ureq
    from urllib import parse as _uparse
    from urllib import error as _uerr
    _Request = _ureq.Request
except ImportError:  # Python 2
    import urllib2 as _ureq
    import urlparse as _uparse
    _uerr = _ureq
    _Request = _ureq.Request

try:
    import uuid as _uuid
except Exception:
    _uuid = None

# =====================================================================
# 框架探测（必须继承探测到的基类，否则加载即失败）
# =====================================================================
_PYRAMID = False
try:
    from base.spider import Spider as _BaseSpider
    _PYRAMID = True
except Exception:
    try:
        from base.spider import BaseSpider as _BaseSpider
        _PYRAMID = True
    except Exception:
        class _BaseSpider(object):
            def init(self, extend=""):
                pass

try:
    _SSL = ssl.create_default_context()
    _SSL.check_hostname = False
    _SSL.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL = None

# =====================================================================
# AES（pycryptodome → 纯 Python 兜底；ECB + CBC 双模式）
# =====================================================================
try:
    from Crypto.Cipher import AES as _PC_AES
except Exception:
    _PC_AES = None


def _to_bytes(s):
    if isinstance(s, bytes):
        return s
    return s.encode("utf-8")


def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p


def _build_tables():
    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x = _gmul(x, 3)
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    sbox = [0] * 256
    for a in range(256):
        inv = 0 if a == 0 else exp[255 - log[a]]
        s = inv
        for _ in range(4):
            inv = ((inv << 1) | (inv >> 7)) & 0xFF
            s ^= inv
        sbox[a] = s ^ 0x63
    inv_sbox = [0] * 256
    for i, v in enumerate(sbox):
        inv_sbox[v] = i
    return sbox, inv_sbox


_SBOX, _INV_SBOX = _build_tables()
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36,
         0x6C, 0xD8, 0xAB, 0x4D]


def _expand_key(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[i * 4:i * 4 + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = list(w[i - 1])
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= _RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [_SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return [bytes(bytearray(b for word in w[r * 4:r * 4 + 4] for b in word))
            for r in range(nr + 1)]


def _dec_block(b, rks):
    nr = len(rks) - 1
    s = [b[i] ^ rks[nr][i] for i in range(16)]
    for rnd in range(nr - 1, 0, -1):
        t = s[:]
        for r in range(1, 4):
            row = [s[r + 4 * c] for c in range(4)]
            row = row[-r:] + row[:-r]
            for c in range(4):
                t[r + 4 * c] = row[c]
        s = [_INV_SBOX[x] for x in t]
        s = [s[i] ^ rks[rnd][i] for i in range(16)]
        t = s[:]
        for c in range(4):
            col = [s[4 * c + r] for r in range(4)]
            t[4 * c + 0] = _gmul(col[0], 14) ^ _gmul(col[1], 11) ^ _gmul(col[2], 13) ^ _gmul(col[3], 9)
            t[4 * c + 1] = _gmul(col[0], 9) ^ _gmul(col[1], 14) ^ _gmul(col[2], 11) ^ _gmul(col[3], 13)
            t[4 * c + 2] = _gmul(col[0], 13) ^ _gmul(col[1], 9) ^ _gmul(col[2], 14) ^ _gmul(col[3], 11)
            t[4 * c + 3] = _gmul(col[0], 11) ^ _gmul(col[1], 13) ^ _gmul(col[2], 9) ^ _gmul(col[3], 14)
        s = t
    t = s[:]
    for r in range(1, 4):
        row = [s[r + 4 * c] for c in range(4)]
        row = row[-r:] + row[:-r]
        for c in range(4):
            t[r + 4 * c] = row[c]
    s = [_INV_SBOX[x] for x in t]
    return bytes(bytearray(s[i] ^ rks[0][i] for i in range(16)))


def _pkcs7_unpad(data):
    if not data or len(data) % 16:
        raise ValueError("bad data length")
    n = data[-1]
    if n < 1 or n > 16 or data[-n:] != bytes(bytearray([n])) * n:
        raise ValueError("bad padding")
    return data[:-n]


def aes_ecb_decrypt(key, cipher):
    if not cipher or len(cipher) % 16:
        raise ValueError("bad cipher length")
    if _PC_AES is not None:
        try:
            return _pkcs7_unpad(_PC_AES.new(bytes(key), _PC_AES.MODE_ECB).decrypt(bytes(cipher)))
        except Exception:
            pass
    rks = _expand_key(bytes(key))
    out = bytearray()
    for i in range(0, len(cipher), 16):
        out += _dec_block(cipher[i:i + 16], rks)
    return _pkcs7_unpad(bytes(out))


def aes_cbc_decrypt(key, iv, cipher):
    """AES-256-CBC 解密 + PKCS7（gh() 响应解密用）"""
    if not cipher or len(cipher) % 16:
        raise ValueError("bad cipher length")
    if _PC_AES is not None:
        try:
            return _pkcs7_unpad(_PC_AES.new(bytes(key), _PC_AES.MODE_CBC,
                                            bytes(iv)).decrypt(bytes(cipher)))
        except Exception:
            pass
    rks = _expand_key(bytes(key))
    out = bytearray()
    prev = bytes(iv)
    for i in range(0, len(cipher), 16):
        blk = bytes(cipher[i:i + 16])
        dec = _dec_block(blk, rks)
        out += bytearray(dec[j] ^ prev[j] for j in range(16))
        prev = blk
    return _pkcs7_unpad(bytes(out))


# =====================================================================
# 新平台配置（逆向自 libapp.so / PWA main JS + 实机验证，勿随意改动）
# =====================================================================
INTERFACE_KEY = b"5rs1hzylbfcvt2ufj490ng5cqxlyy46j"   # 响应解密密钥（32B）
IMG_KEY = b"2019ysapp7527"                            # 图片 XOR 密钥（13B）
API_PREFIX = "/api/app"

# 活线路（2026-10-24 实测全部可达；77ydq 为主线路）
API_HOSTS = [
    "https://77ydq.nhxmapi.xyz",
    "https://api1.nhxmapi.xyz",
    "https://api2.nhxmapi.xyz",
    "https://api3.nhxmapi.xyz",
]
# 资源域兜底（/ping/domain/h5 失败时使用；正常以接口返回为准）
IMG_HOST_FALLBACK = "https://nhxm-image.arpuum.cn"
VID_HOST_FALLBACK = "https://nhxmts.arpuum.cn"

APP_UA = ("Mozilla/5.0 (Linux; Android 10; Pixel 3 Build/OPM1.171.014; wv) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
          "Chrome/86.0.4240.185 Mobile Safari/537.36")

# 静态兜底分类（/modules/list 全挂时的最后防线；id 取自 2026-10-24 实测）
_STATIC_MODULES = [
    ("66164ddd85e0ac65d98d4434", "最新"),
    ("66164d7e85e0ac65d98d4432", "推荐"),
    ("6aa660d2fd8c8cf872848acf", "VIP"),
    ("667015e210fbf6bff7a510f4", "黑料"),
    ("666422f8eaf966d24661ff23", "短剧"),
]

IMG_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}

_RE_TAG = re.compile(r"<[^>]+>")
_RE_SPACES = re.compile(r"\s+")


def _strip_tags(s):
    return _RE_SPACES.sub(" ", _RE_TAG.sub("", s or "")).strip()


def _sec2mmss(sec):
    try:
        sec = int(sec)
    except Exception:
        return ""
    if sec <= 0:
        return ""
    return "%d:%02d" % (sec // 60, sec % 60)


def gh_decrypt(data):
    """新平台响应解密（PWA window.cry = gh 完整复刻，Py3 实测通过）。
    data: base64 字符串；前 12B 盐 + interfaceKey 派生 key/iv + AES-256-CBC"""
    t = data.replace("\n", "")
    raw = bytearray(base64.b64decode(t))
    n = bytearray(INTERFACE_KEY) + bytearray(raw[:12])
    del raw[:12]
    o = len(n) // 2                     # 44/2 = 22（JS parseInt 语义=整除）
    s = hashlib.sha256(bytes(n)).digest()[8:24]
    u = hashlib.sha256(bytes(s) + bytes(n[:o])).digest()
    p = hashlib.sha256(bytes(n[o:]) + bytes(s)).digest()
    key = u[0:8] + p[8:24] + u[24:32]   # 32B
    iv = p[0:4] + u[12:20] + p[28:32]   # 16B
    plain = aes_cbc_decrypt(key, iv, bytes(raw))
    return json.loads(plain.decode("utf-8"))


def img_xor_decrypt(data):
    """图片解密：仅前 100 字节与 imgKey 循环 XOR，其余明文"""
    head = bytearray(data[:100])
    for i in range(len(head)):
        head[i] ^= IMG_KEY[i % len(IMG_KEY)]
    return bytes(head) + data[100:]


def _err_label(e):
    """异常 → 短标签"""
    try:
        if isinstance(e, _uerr.HTTPError):
            return "服务端拒绝%s" % e.code
        if isinstance(e, _uerr.URLError):
            reason = getattr(e, "reason", None)
            return ("连接失败" if "timed out" not in str(reason)
                    else "连接超时")
    except Exception:
        pass
    return (str(e) or "未知错误")[:10]


class Spider(_BaseSpider):

    _EXT = {}
    _LOCK = threading.Lock()
    _CACHE = {
        "token": "",             # JWT（匿名登录）
        "token_ts": 0.0,
        "devid": "",             # 16 位设备号（会话内固定）
        "sid": "",               # X-User-Agent 的 Sid
        "api_host": "",          # 当前选用的 API 线路
        "img_host": "",          # 图片资源域
        "img_ts": 0.0,
        "modules": None,         # /modules/list 缓存
        "modules_ts": 0.0,
        "probe": {},             # TCP 预检 {host: (ok, ts)}
        "dead_until": 0.0,       # 熔断截止
        "section_idx": {},       # 模块 → 合集(section)列表缓存 {mid:(secs,ts)}
    }
    _VODS = {}                   # 视频 id → 列表项（详情/播放消费）
    _VOD_ORDER = []              # LRU 淘汰序
    _DRAMA_CACHE = {}            # 短剧 mediaId → 列表项（allMediaInfo，兜底详情用）
    _LAST_ERR = ""
    _LAST_ERR_RAW = ""
    _ERR_SEQ = 0

    _VOD_CAP = 600               # 视频缓存上限
    _SECTION_WINDOW = 3          # 合集型模块：每个分类页展示的合集(section)数

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self._proxy_base = ""
        self._page_size = 24

    # ---------------- 基础 ----------------
    def _ret(self, obj):
        return obj if _PYRAMID else json.dumps(obj, ensure_ascii=False)

    def getName(self):
        return "秘密花园"

    def init(self, extend=""):
        try:
            s = str(extend or "").strip()
            if s:
                if s.startswith("{"):
                    try:
                        d = json.loads(s)
                        if isinstance(d, dict):
                            Spider._EXT.update(d)
                    except Exception:
                        pass
                elif s.startswith("http"):
                    Spider._EXT["host"] = s.rstrip("/")
        except Exception:
            pass
        try:
            ps = int(Spider._EXT.get("pageSize") or 24)
            self._page_size = max(6, min(60, ps))
        except Exception:
            self._page_size = 24
        self._proxy_base = self._get_proxy_base()
        return ""

    def _get_proxy_base(self):
        try:
            if hasattr(self, "getProxyUrl"):
                p = self.getProxyUrl()
                if p and str(p).startswith("http"):
                    return str(p)
        except Exception:
            pass
        p = Spider._EXT.get("proxy")
        if p and str(p).startswith("http"):
            return str(p)
        return ""

    # ---------------- 看门狗 / 诊断（沿袭 v1） ----------------
    def _run_with_deadline(self, fn, args=(), kwargs=None, deadline=5.0):
        box = {}

        def _worker():
            try:
                box["v"] = fn(*args, **(kwargs or {}))
            except Exception:
                box["v"] = None

        try:
            t = threading.Thread(target=_worker)
            t.daemon = True
            t.start()
        except Exception:
            try:
                return fn(*args, **(kwargs or {}))
            except Exception:
                return None
        t.join(deadline)
        if t.is_alive():
            return None
        return box.get("v")

    def _urlopen(self, req, timeout):
        if _SSL is not None:
            try:
                return _ureq.urlopen(req, timeout=timeout, context=_SSL)
            except TypeError:
                pass
        return _ureq.urlopen(req, timeout=timeout)

    def _set_err(self, msg, raw=None):
        Spider._LAST_ERR = str(msg)[:40]
        _r = raw if raw is not None else msg
        Spider._LAST_ERR_RAW = "%s @ %s" % (str(_r)[:200],
                                            time.strftime("%H:%M:%S"))
        Spider._ERR_SEQ += 1

    def _diag_item(self, title="加载失败"):
        err = Spider._LAST_ERR or "接口返回空"
        raw = Spider._LAST_ERR_RAW or err
        return {
            "vod_id": "diag",
            "vod_name": "⚠ %s" % err,
            "vod_pic": "",
            "vod_remarks": "下拉刷新重试；点此查看完整原因",
            "vod_content": ("【%s】\n完整错误：%s\n\n"
                            "排障建议：\n"
                            "1. 下拉刷新重试；\n"
                            "2. 用浏览器打开 http://nhxm888.com （官方发布页）"
                            "测试本机网络（能打开=网络通达，打不开=需代理/换网）；\n"
                            "3. 若浏览器可达而此处失败，请截图本条反馈。")
                           % (title, raw),
        }

    def _tcp_ok(self, host, timeout=1.5):
        try:
            import socket
        except Exception:
            return True
        try:
            h = _uparse.urlparse(host).hostname
            if not h:
                return False
        except Exception:
            return False
        c = Spider._CACHE["probe"]
        hit = c.get(h)
        now = time.time()
        if hit and now - hit[1] < 30:
            return hit[0]
        ok = [False]

        def _probe():
            try:
                s = socket.create_connection((h, 443), timeout)
                s.close()
                ok[0] = True
            except Exception:
                ok[0] = False

        self._run_with_deadline(_probe, deadline=timeout + 0.3)
        c[h] = (ok[0], now)
        if not ok[0]:
            self._set_err("TCP连接失败",
                          raw="TCP连接失败:%s(域名不可达或被网络拦截)" % h)
        return ok[0]

    # ---------------- 设备身份 / 登录 ----------------
    def _devid(self):
        if not Spider._CACHE["devid"]:
            pool = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            Spider._CACHE["devid"] = "".join(
                random.choice(pool) for _ in range(16))
        return Spider._CACHE["devid"]

    def _sid(self):
        if not Spider._CACHE["sid"]:
            if _uuid is not None:
                Spider._CACHE["sid"] = str(_uuid.uuid4())
            else:
                pool = "0123456789abcdef"
                Spider._CACHE["sid"] = "-".join(
                    "".join(random.choice(pool) for _ in range(n))
                    for n in (8, 4, 4, 4, 12))
        return Spider._CACHE["sid"]

    def _xua(self):
        return ("BuildID=com.abc.Butterfly;SysType=pc;DevID=%s;Ver=1.0.0;"
                "DevType=iPhone;Terminal=1;IsH5=1;DeviceBrand=;DeviceModel=;"
                "Sid=%s" % (self._devid(), self._sid()))

    def _token(self, refresh=False):
        """匿名登录拿 JWT（缓存；refresh=True 强制重登）"""
        c = Spider._CACHE
        if not refresh and c["token"] and time.time() - c["token_ts"] < 7200:
            return c["token"]
        body = {"devID": self._devid(), "sysType": "pc", "cutInfos": None}
        env = self._request("/mine/login/h5", method="POST", body=body,
                            timeout=8, no_token=True)
        d = self._unwrap(env)
        tok = ""
        if isinstance(d, dict):
            tok = d.get("token") or ""
        if tok:
            c["token"] = tok
            c["token_ts"] = time.time()
        else:
            self._set_err("登录失败", raw="匿名登录失败:%s"
                          % json.dumps(env, ensure_ascii=False)[:150])
        return tok

    # ---------------- 请求层 ----------------
    def _api_base(self):
        host = Spider._EXT.get("host")
        if host:
            return str(host).rstrip("/")
        if Spider._CACHE["api_host"]:
            return Spider._CACHE["api_host"]
        return API_HOSTS[0]

    def _headers(self, auth=True):
        h = {
            "temp": "test",
            "X-User-Agent": self._xua(),
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": APP_UA,
            "Connection": "close",
        }
        if auth:
            tok = Spider._CACHE["token"]
            if tok:
                h["Authorization"] = tok
        return h

    @staticmethod
    def _resp_info(r):
        bits = []
        try:
            try:
                code = r.getcode()
            except Exception:
                code = getattr(r, "code", None)
            if code is not None:
                bits.append("状态码=%s" % code)
            hdrs = None
            for attr in ("info", "headers"):
                try:
                    h = getattr(r, attr)
                    hdrs = h() if callable(h) else h
                    if hdrs is not None:
                        break
                except Exception:
                    continue
            if hdrs is not None:
                for k in ("Content-Type", "Content-Length", "Server",
                          "Connection", "Location"):
                    try:
                        v = hdrs.get(k)
                        if v is None:
                            v = hdrs.get(k.lower())
                    except Exception:
                        v = None
                    if v:
                        bits.append("%s=%s" % (k, str(v)[:40]))
        except Exception:
            pass
        return ("[" + " ".join(bits) + "]") if bits else "(无响应信息)"

    def _request(self, path, params=None, method="GET", body=None,
                 timeout=6, no_token=False):
        """单次请求 → 响应包络 dict（不解包 data）。
        看门狗包裹；失败返回 None 并记录诊断。"""
        host = self._api_base()
        url = host + API_PREFIX + path
        q = {}
        for k, v in (params or {}).items():
            if v is None or v == "":
                continue
            q[k if isinstance(k, str) else str(k)] = v if isinstance(v, str) else str(v)
        if q:
            url += "?" + _uparse.urlencode(q)
        headers = self._headers(auth=not no_token)
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        def _do():
            try:
                try:
                    req = _Request(url, data=data, headers=headers,
                                   method=method)
                except TypeError:  # Py2 无 method 参数
                    req = _Request(url, data=data, headers=headers)
                r = self._urlopen(req, timeout)
                raw = r.read()
                return (raw, self._resp_info(r))
            except _uerr.HTTPError as e:
                try:
                    return (e.read(), "HTTP %d" % e.code)
                except Exception:
                    return (b"", "HTTP %d" % e.code)
            except Exception as e:
                self._set_err(_err_label(e),
                              raw="%s:%s" % (type(e).__name__, str(e)[:200]))
                return None

        got = self._run_with_deadline(_do, deadline=timeout + 0.5)
        if got is None:
            return None
        raw, info = got
        txt = ""
        try:
            txt = raw.decode("utf-8", "ignore").strip()
        except Exception:
            pass
        if not txt:
            self._set_err("响应为空",
                          raw="响应为空(连接被重置?) %s" % info)
            return None
        try:
            return json.JSONDecoder().raw_decode(txt)[0]
        except Exception:
            self._set_err("响应非JSON",
                          raw="响应非JSON:%s %s" % (txt[:40], info))
            return None

    def _unwrap(self, env):
        """包络 → data（hash=true 走 gh 解密；code 5005/401 标记 token 失效）"""
        if not isinstance(env, dict):
            return None
        code = env.get("code")
        if code not in (0, 200, None):   # 实测成功包络 code=200（部分 0）
            # token 失效族：5005 no token / 5009 invalid token / 401
            if code in (5005, 5009, 401):
                return {"_relogin": True}
            return None
        d = env.get("data")
        if isinstance(d, str) and env.get("hash"):
            try:
                return gh_decrypt(d)
            except Exception as e:
                self._set_err("解密失败",
                              raw="响应解密失败:%s" % str(e)[:120])
                return None
        return d if d is not None else env

    def _get(self, path, params=None, timeout=6):
        """GET 请求（含 token 失效自动重登一次）"""
        return self._call(path, params=params, timeout=timeout)

    def _post(self, path, body=None, timeout=6):
        return self._call(path, method="POST", body=body, timeout=timeout)

    def _call(self, path, params=None, method="GET", body=None, timeout=6):
        c = Spider._CACHE
        if time.time() < c["dead_until"]:
            return None
        seq0 = Spider._ERR_SEQ
        env = self._request(path, params=params, method=method, body=body,
                            timeout=timeout)
        d = self._unwrap(env)
        if isinstance(d, dict) and d.get("_relogin"):
            # token 失效：重登一次再试
            if self._token(refresh=True):
                env = self._request(path, params=params, method=method,
                                    body=body, timeout=timeout)
                d = self._unwrap(env)
            else:
                d = None
        if d is not None:
            c["dead_until"] = 0.0
            if Spider._ERR_SEQ == seq0:
                Spider._LAST_ERR = ""
        elif Spider._ERR_SEQ == seq0:
            self._set_err("接口无数据", raw="接口返回空(code!=0或data缺失)")
        return d

    def _domains(self, force=False):
        """拉取资源域（IMAGE 优先）；1h 缓存，失败用兜底常量"""
        c = Spider._CACHE
        if not force and c["img_host"] and time.time() - c["img_ts"] < 3600:
            return
        img = ""
        try:
            d = self._call("/ping/domain/h5", timeout=6) or {}
            sl = d.get("sourceList") or []
            for it in sl:
                if not isinstance(it, dict) or it.get("type") != "IMAGE":
                    continue
                arr = it.get("url") or it.get("domain") or []
                if isinstance(arr, list) and arr:
                    best = None
                    for u in arr:
                        if not isinstance(u, dict):
                            continue
                        w = u.get("weight") or 0
                        if u.get("url") and (best is None or w > (best.get("weight") or 0)):
                            best = u
                    if best:
                        img = str(best["url"]).rstrip("/")
                        break
        except Exception:
            pass
        c["img_host"] = img or IMG_HOST_FALLBACK
        c["img_ts"] = time.time()

    # ---------------- 媒体 URL ----------------
    def _proxy_wrap(self, url):
        """图片 → 本地代理（XOR 解密）；未开本地代理返回原址（图裂但不阻塞）"""
        if not url:
            return ""
        base = self._proxy_base or self._get_proxy_base()
        if not base:
            return url
        sep = "&" if "?" in base else "?"
        return base + sep + "url=" + _uparse.quote(url, safe="")

    def _pic(self, rel):
        """封面相对路径 → 代理绝对地址"""
        if not rel:
            return ""
        u = str(rel)
        if u.startswith("http://") or u.startswith("https://"):
            pass
        elif u.startswith("//"):
            u = "https:" + u
        else:
            self._domains()
            u = (Spider._CACHE["img_host"] or IMG_HOST_FALLBACK) + "/" + u.lstrip("/")
        return self._proxy_wrap(u)

    def _play_url(self, source_url):
        """sourceURL 相对路径 → 带 token 的 API 代理播放地址（实测可出 HLS）"""
        if not source_url:
            return ""
        u = str(source_url).strip()
        if u.startswith("http://") or u.startswith("https://"):
            # 极少见：已带协议的直链按原样用
            play = u
        else:
            play = (self._api_base() + API_PREFIX + "/vid/h5/m3u8/" +
                    u.lstrip("/"))
        # token 超过 1 小时先匿名重登（JWT 有效期未知，防过期 404/5005）
        if time.time() - Spider._CACHE["token_ts"] > 3600:
            self._token(refresh=True)
        tok = Spider._CACHE["token"]
        if tok:
            play += ("&" if "?" in play else "?") + "token=" + tok
        return play

    def _verify_play(self, url):
        """播放地址预检：拉 m3u8 前 200 字节确认可用；
        若返回 JSON（token 失效）→ 重登后重建地址再验一次。
        预检失败不阻塞返回原地址（交由播放器兜底尝试）。"""
        if not url:
            return url

        def _head(u):
            try:
                req = _Request(u, headers={"User-Agent": APP_UA})
                r = self._urlopen(req, 6)
                return (r.read(200) or b"").decode("utf-8", "ignore")
            except Exception:
                return None

        body = self._run_with_deadline(_head, args=(url,), deadline=6.5)
        if body is None:
            return url                      # 网络层失败：交给播放器
        if body.lstrip().startswith("#EXTM3U"):
            return url                      # ✓ 可用
        if "{" in body[:8]:                 # JSON 错误包络（如 5005 no token）
            if self._token(refresh=True):
                sep = "&" if "?" in url else "?"
                base = url.split(sep)[0]
                new = base + sep + "token=" + Spider._CACHE["token"]
                body2 = self._run_with_deadline(_head, args=(new,),
                                                deadline=6.5)
                if body2 and body2.lstrip().startswith("#EXTM3U"):
                    return new
        return url

    def _cache_vod(self, vid, item):
        if vid in Spider._VODS:
            return
        if len(Spider._VOD_ORDER) >= Spider._VOD_CAP:
            old = Spider._VOD_ORDER.pop(0)
            Spider._VODS.pop(old, None)
        Spider._VODS[vid] = item
        Spider._VOD_ORDER.append(vid)

    # ---------------- 列表项映射 ----------------
    def _vod_video(self, it):
        vid = str(it.get("id") or "")
        name = _strip_tags(it.get("title") or it.get("name") or "")
        remark = []
        t = _sec2mmss(it.get("playTime"))
        if t:
            remark.append(t)
        pc = it.get("playCount")
        if pc:
            remark.append("▶%s" % pc)
        if it.get("permission"):
            remark.append("VIP")
        self._cache_vod(vid, it)
        return {
            "vod_id": vid,
            "vod_name": name[:60],
            "vod_pic": self._pic(it.get("cover") or it.get("verticalCover") or ""),
            "vod_remarks": " · ".join([x for x in remark if x]),
            "vod_content": _strip_tags(it.get("content") or "")[:300],
        }

    def _vod_drama(self, it):
        """短剧（media/series）列表项：vod_id 用 d_ 前缀区分普通视频
        （避免冒号 d: 在部分 TVBox 客户端回传 vod_id 时被截断/混淆）；
        同时缓存媒体项，供详情接口异常时兜底出第 1 集。"""
        mid = str(it.get("id") or "")
        vid = "d_%s" % mid
        Spider._DRAMA_CACHE[mid] = it
        name = _strip_tags(it.get("title") or "")
        remark = []
        te = it.get("totalEpisode")
        if te:
            remark.append("共%s集" % te)
        if it.get("permission"):
            remark.append("VIP")
        cb = it.get("countBrowse")
        if cb:
            remark.append("▶%s" % cb)
        return {
            "vod_id": vid,
            "vod_name": name[:60],
            "vod_pic": self._pic(it.get("horizontalCover")
                                 or it.get("verticalCover") or ""),
            "vod_remarks": " · ".join([x for x in remark if x]),
            "vod_content": _strip_tags(it.get("summary") or "")[:300],
        }

    # =================================================================
    # 首页 / 分类
    # =================================================================
    def _modules(self, timeout=6):
        """首页模块列表（10 分钟缓存）；失败回落静态表"""
        c = Spider._CACHE
        if c["modules"] and time.time() - c["modules_ts"] < 600:
            return c["modules"]
        mods = []
        d = self._call("/modules/list", timeout=timeout) or {}
        plate = (d.get("moviePlate") or {}) if isinstance(d, dict) else {}
        for grp in ("homePage", "shortPlay"):
            for m in (plate.get(grp) or []):
                if isinstance(m, dict) and m.get("id") and m.get("moduleName"):
                    mods.append((str(m["id"]), str(m["moduleName"])))
        if mods:
            c["modules"] = mods
            c["modules_ts"] = time.time()
            return mods
        return [list(x) for x in _STATIC_MODULES]

    def homeContent(self, filter=False):
        """静态兜底分类秒回 + /modules/list 动态分类（失败不阻塞）"""
        classes = []
        for mid, name in self._modules(timeout=5):
            if len(classes) < 30:
                classes.append({"type_id": "m:%s" % mid, "type_name": name})
        if not classes:
            classes = [{"type_id": "m:%s" % mid, "type_name": name}
                       for mid, name in _STATIC_MODULES]
        return self._ret({"class": classes})

    def homeVideoContent(self, filter=False):
        """首页推荐流 = 第一个模块（最新）第 1 页"""
        mods = self._modules(timeout=5)
        lst = []
        if mods:
            lst = self._module_page(mods[0][0], 1, self._page_size)
        if not lst:
            lst.append(self._diag_item("首页内容加载失败"))
        return self._ret({"list": lst, "page": 1, "pagecount": 999,
                          "limit": self._page_size, "total": len(lst)})

    def _module_sections(self, mid, timeout=8):
        """取模块的合集(section)列表（120s 缓存）。
        返回 [] 表示本模块为「视频型」(allVideoInfo) 或空模块。
        注意：合集数受 pageSize 影响，用 100 才能拿全（推荐模块实测 30 个；
        200 反被服务端返回 0，故封顶 100）。"""
        c = Spider._CACHE
        idx = c.get("section_idx") or {}
        ent = idx.get(mid)
        now = time.time()
        if ent is not None and now - ent[1] < 120:
            return ent[0]
        d = self._call("/vid/module/%s" % mid,
                       {"pageNumber": 1, "pageSize": 100}, timeout=timeout) or {}
        secs = []
        if isinstance(d, dict) and d.get("allSection") is not None:
            secs = d.get("allSection") or []
        idx[mid] = (secs, now)
        c["section_idx"] = idx
        return secs

    def _module_page(self, mid, page, size):
        """模块分页：合集型 → 按合集窗口展开；视频型 → allVideoInfo。"""
        secs = self._module_sections(mid)        # 带缓存；[] 即视频型
        if secs:
            return self._module_section_page(mid, page, size, secs)
        d = self._call("/vid/module/%s" % mid,
                       {"pageNumber": page, "pageSize": size},
                       timeout=7) or {}
        vids = d.get("allVideoInfo") if isinstance(d, dict) else None
        if vids is None and isinstance(d, dict):
            vids = d.get("list") or []
        return [self._vod_video(it) for it in (vids or [])
                if isinstance(it, dict) and it.get("id")]

    def _module_section_page(self, mid, page, size, secs=None):
        """合集型模块分页：每页展示连续 _SECTION_WINDOW 个合集，
        合集名附到备注便于辨认；空合集自动跳过。
        合集两类取数路径：
        · type=5（短剧等）→ 内容内嵌在 section.allMediaInfo[]（剧系列表），
          /vid/section/<sid> 对这类恒返回空（实测）；
        · 普通合集 → GET /vid/section/<sid> 取 videos[]。"""
        if secs is None:
            secs = self._module_sections(mid)
        if not secs:
            return []
        page = max(1, page)
        K = self._SECTION_WINDOW
        window = secs[(page - 1) * K:(page - 1) * K + K]
        out = []
        for s in window:
            sname = _strip_tags(s.get("sectionName") or "")
            meds = s.get("allMediaInfo") or []
            if meds:                                   # 短剧型合集
                for it in meds:
                    if not isinstance(it, dict) or not it.get("id"):
                        continue
                    v = self._vod_drama(it)
                    if sname:
                        rem = v.get("vod_remarks", "")
                        v["vod_remarks"] = (sname + " · " + rem) if rem else sname
                    out.append(v)
                continue
            sid = s.get("sectionID")
            if not sid:
                continue
            sd = self._call("/vid/section/%s" % sid,
                            {"pageNumber": 1, "pageSize": size}, timeout=8) or {}
            vs = sd.get("videos") or [] if isinstance(sd, dict) else []
            for it in vs:
                if not isinstance(it, dict) or not it.get("id"):
                    continue
                v = self._vod_video(it)
                if sname:
                    rem = v.get("vod_remarks", "")
                    v["vod_remarks"] = (sname + " · " + rem) if rem else sname
                out.append(v)
        return out

    def _module_pagecount(self, mid, size):
        """合集型模块页数 = ceil(合集数 / 窗口)；视频型返回 1（旧逻辑兜底）。"""
        secs = self._module_sections(mid)
        if not secs:
            return 1
        K = self._SECTION_WINDOW
        return max(1, (len(secs) + K - 1) // K)

    def categoryContent(self, tid="", pg="1", filter=False, extend=None):
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        lst = []
        pc = 9999
        if tid.startswith("m:"):
            mid = tid[2:]
            lst = self._module_page(mid, page, self._page_size)
            pc = self._module_pagecount(mid, self._page_size)
        if not lst:
            lst.append(self._diag_item("分类内容加载失败"))
        return self._ret({
            "list": lst,
            "page": page,
            "pagecount": pc,
            "limit": self._page_size,
            "total": pc * self._page_size,
        })

    # =================================================================
    # 详情 / 搜索 / 播放
    # =================================================================
    def _detail_vod(self, vid):
        it = Spider._VODS.get(str(vid))
        if not isinstance(it, dict):
            return None
        name = _strip_tags(it.get("title") or "")[:80]
        desc = _strip_tags(it.get("content") or "")
        extra = []
        t = _sec2mmss(it.get("playTime"))
        if t:
            extra.append("时长 " + t)
        if it.get("playCount"):
            extra.append("播放 %s" % it.get("playCount"))
        if it.get("likeCount"):
            extra.append("点赞 %s" % it.get("likeCount"))
        pub = (it.get("publisher") or {})
        if isinstance(pub, dict) and pub.get("name"):
            extra.append("UP主 " + str(pub.get("name")))
        tags = it.get("tags") or []
        tnames = [(x.get("name") if isinstance(x, dict) else str(x))
                  for x in tags if x][:10]
        if tnames:
            extra.append("标签 " + " · ".join(tnames))
        act = it.get("actresses") or []
        anames = [(x.get("name") if isinstance(x, dict) else str(x))
                  for x in act if x][:8]
        if anames:
            extra.append("演员 " + " · ".join(anames))
        if it.get("createdAt"):
            extra.append("发布 " + str(it.get("createdAt"))[:10])
        content = desc
        if extra:
            content = (content + "\n\n" if content else "") + "\n".join(extra)
        remark = " · ".join([x for x in [t,
                                         ("▶%s" % it.get("playCount"))
                                         if it.get("playCount") else ""] if x])
        return {
            "vod_id": str(vid),
            "vod_name": name,
            "vod_pic": self._pic(it.get("cover") or it.get("verticalCover") or ""),
            "vod_remarks": remark,
            "vod_content": content[:1600],
            "vod_play_from": "秘密花园",
            "vod_play_url": "正片$%s" % str(vid),
        }

    def detailContent(self, ids):
        if not ids:
            return self._ret({"list": []})
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid)
        if vid.startswith("d_"):          # 短剧（media/series）
            vod = self._detail_drama(vid[2:])
            if vod is not None:
                return self._ret({"list": [vod]})
            return self._ret({"list": [{
                "vod_id": vid,
                "vod_name": "⚠ 短剧加载失败",
                "vod_pic": "",
                "vod_content": self._diag_item("短剧加载失败")["vod_content"],
                "vod_remarks": "",
            }]})
        vod = self._detail_vod(vid)
        if vod is None:
            # 缓存未命中（客户端重启后直接进详情）：尝试搜索接口兜底找回
            vod = self._detail_refetch(vid)
        if vod is None:
            if Spider._LAST_ERR:
                return self._ret({"list": [{
                    "vod_id": vid,
                    "vod_name": "⚠ 详情加载失败",
                    "vod_pic": "",
                    "vod_content": self._diag_item("详情加载失败")["vod_content"],
                    "vod_remarks": "",
                }]})
            return self._ret({"list": []})
        return self._ret({"list": [vod]})

    def _detail_drama(self, mid):
        """短剧详情：GET /media/info?id=<mediaId> → 全部集数。
        选集 url 直接放 videoUrl（相对路径），播放时由 playerContent 构造代理地址。
        兜底：若 /media/info 异常，用列表阶段缓存的 allMediaInfo.contents[0]
        （含第 1 集 videoUrl）至少放出第 1 集，避免整部「加载失败」。"""
        d = self._call("/media/info", {"id": mid}, timeout=8) or {}
        eps = []
        name = ""
        pic = ""
        te = None
        summary = ""
        if isinstance(d, dict) and d.get("id"):
            name = _strip_tags(d.get("title") or "")[:80]
            pic = self._pic(d.get("horizontalCover") or d.get("verticalCover") or "")
            te = d.get("totalEpisode")
            summary = _strip_tags(d.get("summary") or "")
            extra = []
            if te:
                extra.append("共 %s 集" % te)
            if d.get("updateStatus"):
                extra.append("连载中" if int(d.get("updateStatus") or 0) == 1 else "已完结")
            if d.get("countBrowse"):
                extra.append("浏览 %s" % d.get("countBrowse"))
            if d.get("countLike"):
                extra.append("点赞 %s" % d.get("countLike"))
            td = d.get("tagDetails") or []
            tnames = [str(x.get("name")) for x in td
                      if isinstance(x, dict) and x.get("name")]
            if tnames:
                extra.append("标签 " + " · ".join(tnames[:8]))
            if d.get("createdAt"):
                extra.append("上线 " + str(d.get("createdAt"))[:10])
            content = summary
            if extra:
                content = (content + "\n\n" if content else "") + "\n".join(extra)
            for c in (d.get("contents") or []):
                if not isinstance(c, dict):
                    continue
                vu = str(c.get("videoUrl") or "").strip()
                if not vu:
                    continue
                nm = _strip_tags(str(c.get("name") or c.get("episodeNumber") or ""))
                eps.append("%s$%s" % (nm or "播放", vu))
        else:
            # 兜底：用缓存的 allMediaInfo 放出第 1 集
            it = Spider._DRAMA_CACHE.get(mid) or {}
            name = _strip_tags(it.get("title") or "")[:80]
            pic = self._pic(it.get("horizontalCover") or it.get("verticalCover") or "")
            te = it.get("totalEpisode")
            summary = _strip_tags(it.get("summary") or "")
            c0 = (it.get("contents") or [{}])[0] if it.get("contents") else {}
            vu = str(c0.get("videoUrl") or "").strip()
            if vu:
                nm = _strip_tags(str(c0.get("name") or "1"))
                eps.append("%s$%s" % (nm or "1", vu))
                content = (summary + "\n\n⚠ 仅放出第1集（详情接口异常，已兜底）")[:1600] \
                    if summary else "⚠ 仅放出第1集（详情接口异常，已兜底）"
            else:
                return None
        return {
            "vod_id": "d_%s" % mid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": ("共%s集" % te) if te else "",
            "vod_content": content[:1600],
            "vod_play_from": "秘密花园·短剧",
            "vod_play_url": "#".join(eps),
        }

    def _detail_refetch(self, vid):
        """缓存丢失时兜底：拉「最新」模块前几页找该视频"""
        mods = self._modules(timeout=4)
        if not mods:
            return None
        for mid, _n in mods[:2]:
            for page in (1, 2, 3):
                for it in (self._module_raw(mid, page) or []):
                    if str(it.get("id")) == vid:
                        return self._detail_vod(vid)
        return None

    def _module_raw(self, mid, page):
        d = self._call("/vid/module/%s" % mid,
                       {"pageNumber": page, "pageSize": 20}, timeout=6) or {}
        if isinstance(d, dict):
            return d.get("allVideoInfo") or d.get("list") or []
        return []

    def searchContent(self, key, quick=False, *args):
        try:
            page = 1
        except Exception:
            page = 1
        kw = str(key or "").strip()
        lst = []
        if kw:
            d = self._post("/vid/library/search",
                           {"kw": kw, "pageNumber": page,
                            "pageSize": self._page_size},
                           timeout=7) or {}
            vids = d.get("list") if isinstance(d, dict) else None
            if vids is None and isinstance(d, list):
                vids = d
            lst = [self._vod_video(it) for it in (vids or [])
                   if isinstance(it, dict) and it.get("id")]
        if not lst:
            lst.append(self._diag_item("搜索失败"))
        return self._ret({
            "list": lst,
            "page": page,
            "pagecount": 999,
            "limit": self._page_size,
            "total": len(lst),
        })

    def playerContent(self, flag="", id="", vipFlags=""):
        header = {"User-Agent": APP_UA}
        try:
            vid = str(id or "")
            if ("/" in vid or vid.startswith("http")) and ".m3u8" in vid:
                src = vid                # 短剧选集：直接是 sourceURL（videoUrl）
            else:
                it = Spider._VODS.get(vid)
                src = (it or {}).get("sourceURL") or ""
                if not src:
                    # 兜底：重拉「最新」前几页找回 sourceURL
                    self._detail_refetch(vid)
                    it = Spider._VODS.get(vid)
                    src = (it or {}).get("sourceURL") or ""
            if not src:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": ("获取失败：%s" % Spider._LAST_ERR)
                                  if Spider._LAST_ERR
                                  else "该视频暂无播放地址"})
            play = self._verify_play(self._play_url(src))
            if not play:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": "播放地址构造失败"})
            return self._ret({"parse": 0, "url": play, "header": header})
        except Exception:
            return self._ret({"parse": 0, "url": "", "header": header,
                              "msg": "播放地址解析失败，请重试"})

    # =================================================================
    # 本地代理：图片 XOR 解密
    # =================================================================
    def localProxy(self, param):
        if not isinstance(param, dict):
            return [404, "text/plain", b""]
        url = str(param.get("url") or param.get("u") or "")
        if not url.startswith("http"):
            return [404, "text/plain", b""]
        referer = (Spider._CACHE["img_host"] or IMG_HOST_FALLBACK) + "/"

        def _fetch():
            req = _Request(url, headers={"User-Agent": APP_UA,
                                         "Referer": referer})
            r = self._urlopen(req, 10)
            return r.read()

        data = self._run_with_deadline(_fetch, deadline=10.5)
        if not data:
            return [502, "text/plain", b"img fetch failed"]
        # 新平台图片：前 100B 与 imgKey XOR。明文魔数命中→直接转发；
        # 未命中→尝试 XOR 还原（还原后仍不认识则按原数据返回）
        def _magic_ok(b):
            if b[:3] in IMG_MAGIC or b[:4] == b"RIFF":
                return True
            return False

        if not _magic_ok(data[:8]):
            dec = img_xor_decrypt(data)
            if _magic_ok(dec[:8]):
                data = dec
        mime = "image/jpeg"
        for magic, m in IMG_MAGIC.items():
            if data[:len(magic)] == magic:
                mime = m
                break
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            mime = "image/webp"
        return [200, mime, data]

    # ---------------- 兼容桩 ----------------
    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return ""

    def destroy(self):
        return ""

    def stop(self):
        return ""
