# -*- coding: utf-8 -*-
"""
一个ONE · TVBox 解析器（spider）
====================================================================
【ext 高级选项】init 的 extend 支持 JSON：
  {"host":"https://api.xxx.com"}   覆盖入口域
  {"proxy":"http://127.0.0.1:9978/proxy?do=py"}  覆盖代理地址
  {"sort":"like_number"}           写真/漫画/合集排序（published_at/like_number）
"""

import base64
import hashlib
import html
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

# =====================================================================
# 框架探测（§1.1：必须继承探测到的基类，否则加载即失败）
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

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
APP_UA = "okhttp/3.12.1"

try:
    _SSL = ssl.create_default_context()
    _SSL.check_hostname = False
    _SSL.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL = None

# =====================================================================
# AES-CBC 三级回退（pycryptodome → ctypes libcrypto → 纯 Python）
# =====================================================================
try:
    from Crypto.Cipher import AES as _PC_AES
except Exception:
    _PC_AES = None

_CT_LIB = None
_CT_TRIED = False


def _ct_lib():
    """ctypes 加载 libcrypto（Android/Termux/Linux 名称不同，逐个尝试）"""
    global _CT_LIB, _CT_TRIED
    if _CT_TRIED:
        return _CT_LIB
    _CT_TRIED = True
    try:
        import ctypes
        import ctypes.util
        names = []
        try:
            n = ctypes.util.find_library("crypto")
            if n:
                names.append(n)
        except Exception:
            pass
        names += ["libcrypto.so", "libcrypto.so.3", "libcrypto.so.1.1",
                  "libcrypto.so.1.0.0", "libcrypto.dylib", "libcrypto.1.1.dylib"]
        for n in names:
            try:
                lib = ctypes.CDLL(n)
                lib.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
                lib.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
                lib.EVP_aes_128_cbc.restype = ctypes.c_void_p
                _CT_LIB = lib
                return lib
            except Exception:
                continue
    except Exception:
        pass
    return None


# ---------- 纯 Python AES（密钥展开 + 分组加解密，AES-128） ----------
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
    # GF(2^8) 对数表（生成元 3）
    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x = _gmul(x, 3)
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    # S-box = 仿射变换(乘法逆元)
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
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _expand_key(key):
    w = [list(key[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= _RCON[i // 4 - 1]
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return [sum((w[r * 4 + c] for c in range(4)), []) for r in range(11)]


def _enc_block(b, rk):
    s = [b[i] ^ rk[0][i] for i in range(16)]
    for rnd in range(1, 10):
        s = [_SBOX[x] for x in s]
        s = [s[(i + (i % 4) * 4 - (i % 4)) % 16] if False else s[0:16][i] for i in range(16)]
        # ShiftRows
        t = s[:]
        for r in range(1, 4):
            row = [s[r + 4 * c] for c in range(4)]
            row = row[r:] + row[:r]
            for c in range(4):
                t[r + 4 * c] = row[c]
        s = t
        # MixColumns
        t = s[:]
        for c in range(4):
            col = [s[4 * c + r] for r in range(4)]
            t[4 * c + 0] = _gmul(col[0], 2) ^ _gmul(col[1], 3) ^ col[2] ^ col[3]
            t[4 * c + 1] = col[0] ^ _gmul(col[1], 2) ^ _gmul(col[2], 3) ^ col[3]
            t[4 * c + 2] = col[0] ^ col[1] ^ _gmul(col[2], 2) ^ _gmul(col[3], 3)
            t[4 * c + 3] = _gmul(col[0], 3) ^ col[1] ^ col[2] ^ _gmul(col[3], 2)
        s = t
        s = [s[i] ^ rk[rnd][i] for i in range(16)]
    s = [_SBOX[x] for x in s]
    t = s[:]
    for r in range(1, 4):
        row = [s[r + 4 * c] for c in range(4)]
        row = row[r:] + row[:r]
        for c in range(4):
            t[r + 4 * c] = row[c]
    return bytes(t[i] ^ rk[10][i] for i in range(16))


def _dec_block(b, rk):
    s = [b[i] ^ rk[10][i] for i in range(16)]
    for rnd in range(9, 0, -1):
        # InvShiftRows
        t = s[:]
        for r in range(1, 4):
            row = [s[r + 4 * c] for c in range(4)]
            row = row[-r:] + row[:-r]
            for c in range(4):
                t[r + 4 * c] = row[c]
        s = [_INV_SBOX[x] for x in t]
        s = [s[i] ^ rk[rnd][i] for i in range(16)]
        # InvMixColumns
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
    return bytes(s[i] ^ rk[0][i] for i in range(16))


def _py_cbc(key, iv, data, encrypt):
    rk = _expand_key(key)
    out = bytearray()
    prev = bytes(iv)
    fn = _enc_block if encrypt else _dec_block
    for i in range(0, len(data), 16):
        blk = bytes(data[i:i + 16])
        if encrypt:
            blk = bytes(a ^ b for a, b in zip(blk, prev))
            prev = fn(blk, rk)
            out += prev
        else:
            dec = fn(blk, rk)
            out += bytes(a ^ b for a, b in zip(dec, prev))
            prev = blk
    return bytes(out)


def _ct_cbc(key, iv, data, encrypt):
    import ctypes
    lib = _ct_lib()
    if lib is None:
        raise RuntimeError("no libcrypto")
    ctx = lib.EVP_CIPHER_CTX_new()
    if not ctx:
        raise RuntimeError("ctx alloc fail")
    try:
        lib.EVP_CIPHER_CTX_set_padding.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.EVP_DecryptInit_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.EVP_EncryptInit_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.EVP_DecryptUpdate.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_int), ctypes.c_char_p, ctypes.c_int]
        lib.EVP_EncryptUpdate.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_int), ctypes.c_char_p, ctypes.c_int]
        lib.EVP_DecryptFinal_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_int)]
        lib.EVP_EncryptFinal_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_int)]
        lib.EVP_CIPHER_CTX_set_padding(ctx, 0)
        cipher = lib.EVP_aes_128_cbc()
        if encrypt:
            init_fn, upd_fn, fin_fn = (lib.EVP_EncryptInit_ex, lib.EVP_EncryptUpdate,
                                       lib.EVP_EncryptFinal_ex)
        else:
            init_fn, upd_fn, fin_fn = (lib.EVP_DecryptInit_ex, lib.EVP_DecryptUpdate,
                                       lib.EVP_DecryptFinal_ex)
        if not init_fn(ctx, cipher, None, bytes(key), bytes(iv)):
            raise RuntimeError("init fail")
        outlen = ctypes.c_int(0)
        buf = ctypes.create_string_buffer(len(data) + 32)
        if not upd_fn(ctx, buf, ctypes.byref(outlen), bytes(data), len(data)):
            raise RuntimeError("update fail")
        out = buf.raw[:outlen.value]
        fin = ctypes.c_int(0)
        if not fin_fn(ctx, buf, ctypes.byref(fin)):
            raise RuntimeError("final fail")
        return out + buf.raw[:fin.value]
    finally:
        lib.EVP_CIPHER_CTX_free(ctx)


def _pkcs7_pad(data):
    n = 16 - (len(data) % 16)
    return data + bytes([n]) * n


def _pkcs7_unpad(data):
    if not data or len(data) % 16:
        raise ValueError("bad length")
    n = data[-1]
    if n < 1 or n > 16 or data[-n:] != bytes([n]) * n:
        raise ValueError("bad padding")
    return data[:-n]


def aes_cbc_encrypt(key, iv, plain):
    """三级回退加密（PKCS7）"""
    data = _pkcs7_pad(plain)
    if _PC_AES is not None:
        try:
            return _PC_AES.new(bytes(key), _PC_AES.MODE_CBC, bytes(iv)).encrypt(data)
        except Exception:
            pass
    try:
        return _ct_cbc(key, iv, data, True)
    except Exception:
        pass
    return _py_cbc(key, iv, data, True)


def aes_cbc_decrypt(key, iv, cipher):
    """三级回退解密（自动去 PKCS7；非对齐数据原样返回）"""
    if not cipher or len(cipher) % 16:
        return cipher
    if _PC_AES is not None:
        try:
            return _pkcs7_unpad(_PC_AES.new(bytes(key), _PC_AES.MODE_CBC,
                                            bytes(iv)).decrypt(cipher))
        except Exception:
            pass
    try:
        return _pkcs7_unpad(_ct_cbc(key, iv, cipher, False))
    except Exception:
        pass
    return _pkcs7_unpad(_py_cbc(key, iv, cipher, False))


# =====================================================================
# 站点配置（全部逆向自 BuildConfig / ApiModule，勿改动）
# =====================================================================
ENTRY_HOSTS = [
    "https://api.mgzsua.com/",
    "https://api.h52ft6.com/",
    "https://api.xeajfv.com/",
    "https://api.phplhr.com/",
    "https://api.5urjzs.com/",
]
APP_SALT = "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT"
API_AES_KEY = b"l*bv%Ziq000Biaog"      # umeng_kv
API_AES_IV = b"8597506002939249"       # umeng_iv
IMG_AES_KEY = b"saIZXc4yMvq0Iz56"      # image_aes_encrypt_key
IMG_AES_IV = b"kbJYtBJUECT0oyjo"       # image_aes_encrypt_iv
APP_VERSION = "2.5.9.2"
PROXY_FALLBACK = "http://127.0.0.1:9978/proxy?do=py"

IMG_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",
}


def _md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _strip_tags(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t　]+", " ", s).strip()


def _prev_day(d):
    """YYYY-MM-DD 减一天（纯算术，不依赖 datetime 时区）"""
    y, m, dd = int(d[0:4]), int(d[5:7]), int(d[8:10])
    dd -= 1
    if dd < 1:
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        dd = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
              31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return "%04d-%02d-%02d" % (y, m, dd)


def _prev_month(d):
    """YYYY-MM-DD 退回上月 1 号。
    实测服务端 published_at 按「月」过滤（同月任意日返回完全相同的数据），
    故发现流翻尽后直接跳月，无需逐日试探。"""
    y, m = int(d[0:4]), int(d[5:7])
    m -= 1
    if m < 1:
        m = 12
        y -= 1
    return "%04d-%02d-01" % (y, m)


class Spider(_BaseSpider):
    """一个ONE 解析器"""

    # 类级缓存：TVBox 某些壳每次调用都会新建实例，类属性才能跨调用留存
    _LOCK = threading.Lock()
    _CACHE = {
        "token": "", "domains": {}, "server_time": "", "first_day": "2019-11-08",
        "boot_ts": 0.0, "api_host": "", "detail": {},
    }
    _CAT_STATE = {}       # tid -> {"date","page","served"}
    _EXT = {}             # init 传入的高级选项

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self._proxy_base = ""

    # ---------------- 基础 ----------------
    def _ret(self, obj):
        return obj if _PYRAMID else json.dumps(obj, ensure_ascii=False)

    def getName(self):
        return "一个ONE"

    def init(self, extend=""):
        """extend 支持 JSON：host / proxy / sort"""
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
        return PROXY_FALLBACK

    # ---------------- 会话：bootstrap 访客注册 + 域缓存 ----------------
    def _bootstrap(self, force=False):
        with Spider._LOCK:
            c = Spider._CACHE
            if c["token"] and not force and (time.time() - c["boot_ts"] < 600):
                return True
            hosts = list(ENTRY_HOSTS)
            h = Spider._EXT.get("host")
            if h:
                hosts.insert(0, h if h.endswith("/") else h + "/")
            if c["api_host"]:
                hosts.insert(0, c["api_host"])
            for host in hosts:
                try:
                    j = self._raw_post(host, "/v2.5/bootstrap", {}, token="")
                    if j and j.get("code") == 200:
                        d = j.get("data") or {}
                        u = d.get("user") or {}
                        c["token"] = u.get("token") or ""
                        c["domains"] = d.get("domain") or {}
                        c["server_time"] = d.get("server_time") or ""
                        c["first_day"] = d.get("first_day") or "2019-11-08"
                        c["boot_ts"] = time.time()
                        c["api_host"] = host
                        if c["token"]:
                            return True
                except Exception:
                    continue
            return bool(c["token"])

    def _today(self):
        c = Spider._CACHE
        st = c.get("server_time") or ""
        if len(st) >= 10:
            return st[:10]
        return time.strftime("%Y-%m-%d", time.localtime())

    def _api_hosts(self):
        c = Spider._CACHE
        doms = [d if d.endswith("/") else d + "/" for d in (c["domains"].get("api") or [])]
        if c["api_host"] and c["api_host"] not in doms:
            doms.insert(0, c["api_host"])
        for h in ENTRY_HOSTS:
            if h not in doms:
                doms.append(h)
        return doms or ENTRY_HOSTS

    def _sign_headers(self, token=""):
        ts = int(time.time())
        u = str(uuid.uuid4())   # 服务端校验 UUID 格式 8-4-4-4-12（小写+横线），不能用 .hex
        # TreeMap 键序：brand < ip < model < platform < timestamp < user-key < uuid
        joined = ".".join(["NA", "0.0.0.0", "NA", "1", str(ts), "", u])
        sign = _md5(_md5(joined) + APP_SALT)
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "uuid": u,
            "timestamp": str(ts),
            "ip": "0.0.0.0",
            "user-key": "",
            "platform": "1",
            "sign": sign,
            "brand": "NA",
            "model": "NA",
            "app-version": APP_VERSION,
            "token": token or "",
        }

    def _raw_post(self, host, path, form, token="", timeout=25):
        """单域请求：AES 加密 body + 签名头；返回解密后的 dict 或 None"""
        url = host.rstrip("/") + path
        body = b""
        if form is not None:
            plain = urllib.parse.urlencode(form).encode("utf-8")
            body = base64.b64encode(aes_cbc_encrypt(API_AES_KEY, API_AES_IV, plain))
        req = urllib.request.Request(url, data=body,
                                     headers=self._sign_headers(token), method="POST")
        try:
            r = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
            raw = r.read()
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
            except Exception:
                raw = b""
            if e.code in (401, 403):
                return {"__auth__": True}
        except Exception:
            return None
        txt = raw.decode("utf-8", "ignore").strip()
        if not txt:
            return None
        try:
            if txt.startswith("{"):
                return json.JSONDecoder().raw_decode(txt)[0]
            plain = aes_cbc_decrypt(API_AES_KEY, API_AES_IV, base64.b64decode(txt))
            # 服务端偶发把两段独立加密的 base64 拼接返回（bootstrap JSON + 配置段），
            # 连续 CBC 解密后第一段 JSON 之后附带第二段内容 —— raw_decode 只取第一段
            return json.JSONDecoder().raw_decode(plain.decode("utf-8", "ignore"))[0]
        except Exception:
            return None

    def _api_post(self, path, form, _retry=True):
        """多域轮换 + 401 自动重新 bootstrap 重试一次"""
        if not self._bootstrap():
            return None
        last = None
        for host in self._api_hosts():
            j = self._raw_post(host, path, form, token=Spider._CACHE.get("token") or "")
            if j is None:
                continue
            if j.get("__auth__"):
                if _retry:
                    self._bootstrap(force=True)
                    return self._api_post(path, form, _retry=False)
                continue
            code = j.get("code")
            if code == 200:
                return j.get("data")
            last = j
        return last if isinstance(last, dict) else None

    # ---------------- 媒体 URL 辅助 ----------------
    def _dom(self, kind, idx=0):
        lst = Spider._CACHE["domains"].get(kind) or []
        if not lst:
            return ""
        return lst[min(idx, len(lst) - 1)].rstrip("/")

    def _abs(self, kind, path, idx=0):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        d = self._dom(kind, idx)
        return (d + path) if d else path

    def _img_url(self, path):
        return self._abs("image", path)

    def _proxy_wrap(self, url):
        """图片地址 → 本地代理地址（localProxy 负责 AES 解密）"""
        if not url:
            return ""
        base = self._proxy_base or self._get_proxy_base()
        if not base:
            return url
        sep = "&" if "?" in base else "?"
        return base + sep + "type=img&url=" + urllib.parse.quote(url, safe="")

    def _pic(self, path):
        """封面：绝对化 → 包代理（加密存储，必须走 localProxy 解密）"""
        u = self._img_url(path)
        return self._proxy_wrap(u) if u else ""

    # ---------------- 列表项映射 ----------------
    def _vod(self, vid, name, pic, remark="", content=""):
        return {
            "vod_id": str(vid),
            "vod_name": name or "",
            "vod_pic": pic or "",
            "vod_remarks": remark or "",
            "vod_content": content or "",
        }

    def _from_discovery(self, it):
        pic = it.get("thumbnail") or it.get("thumb") or ""
        remark = []
        if it.get("subtitle"):
            remark.append(str(it.get("subtitle")))
        if it.get("number"):
            remark.append(str(it.get("number")))
        if it.get("vol"):
            remark.append("VOL.%s" % it.get("vol"))
        if it.get("published_at"):
            remark.append(str(it.get("published_at"))[:10])
        if it.get("like_number"):
            remark.append("♥%s" % it.get("like_number"))
        return self._vod(it.get("id"), it.get("title"), self._pic(pic),
                         " · ".join([x for x in remark if x]),
                         _strip_tags(it.get("description") or "")[:300])

    def _from_series(self, it):
        remark = []
        if it.get("author"):
            remark.append(str(it.get("author")))
        if it.get("latest_at"):
            remark.append(str(it.get("latest_at"))[:10])
        if it.get("like_total"):
            remark.append("♥%s" % it.get("like_total"))
        # s: 前缀 = series 专辑 id（detailContent 走 series/chapters 流程，
        # 不能把 series id 当 article id 传给 article/detail）
        return self._vod("s:%s" % it.get("id"), it.get("title"),
                         self._pic(it.get("thumb") or ""),
                         " · ".join([x for x in remark if x]))

    def _from_actor(self, it):
        # 演员卡片 = 文件夹卡片（vod_tag=folder）：点击不进详情页，
        # 而是导航进入 categoryContent("actress/<id>") 的作品文件夹
        # （TVBox folder 协议，逆向自 FongMi/TV TypeFragment.onItemClick：
        #   item.isFolder() → openFolder(item.getId()) → 子级列表 + 返回栈）
        return {
            "vod_id": "actress/%s" % it.get("id"),
            "vod_name": it.get("main_name") or it.get("name") or "",
            "vod_pic": self._pic(it.get("thumb") or ""),
            "vod_remarks": "♥%s" % it.get("score") if it.get("score") else "",
            "vod_tag": "folder",
        }

    # ---------------- 首页 ----------------
    def homeContent(self, filter=False):
        # 分类结构对齐 App「发现」页：图文/阅读/影视/电台/写真/漫画
        # （DiscoveryFragment model tab 序列），其后挂 series 专辑流与其他入口。
        classes = [
            {"type_id": "video", "type_name": "影视"},
            {"type_id": "graphic", "type_name": "图文"},
            {"type_id": "article", "type_name": "阅读"},
            {"type_id": "audio", "type_name": "电台"},
            {"type_id": "photo_art", "type_name": "写真"},
            {"type_id": "comic_art", "type_name": "漫画"},
            {"type_id": "photo", "type_name": "写真图集"},
            {"type_id": "comic", "type_name": "漫画合集"},
            {"type_id": "serial", "type_name": "合集大全"},
            {"type_id": "day", "type_name": "每日ONE"},
            {"type_id": "actor", "type_name": "女优名录"},
        ]
        filters = {
            "actor": [{
                "key": "nav", "name": "地区",
                "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "1"},
                          {"n": "中国", "v": "2"}, {"n": "美国", "v": "3"},
                          {"n": "俄罗斯", "v": "4"}, {"n": "日本(男)", "v": "5"}],
            }],
            # 影视日期筛选（对齐 App 日期选择器：年份+月份）。
            # 服务端 published_at 按月过滤，可选范围 = first_day(2019-11) ~ 今天
            "video": [
                {"key": "year", "name": "年份",
                 "value": [{"n": "全部", "v": ""}] + [
                     {"n": str(y), "v": str(y)}
                     for y in range(int(self._today()[:4]),
                                    int((Spider._CACHE.get("first_day")
                                         or "2019-11-08")[:4]) - 1, -1)]},
                {"key": "month", "name": "月份",
                 "value": [{"n": "全部", "v": ""}] + [
                     {"n": "%d月" % i, "v": str(i)} for i in range(12, 0, -1)]},
            ],
        }
        feed = []
        try:
            data = self._api_post("/v2.5/article/discovery",
                                  {"model_id": 3, "series_category": 0,
                                   "published_at": self._today(), "page": 1, "size": 20})
            if isinstance(data, list):
                feed = [self._from_discovery(x) for x in data[:20]]
        except Exception:
            pass
        return self._ret({"class": classes, "list": feed, "filters": filters})

    def homeVideoContent(self):
        try:
            data = self._api_post("/v2.5/article/discovery",
                                  {"model_id": 3, "series_category": 0,
                                   "published_at": self._today(), "page": 1, "size": 20})
            if isinstance(data, list):
                return self._ret({"list": [self._from_discovery(x) for x in data[:20]]})
        except Exception:
            pass
        return self._ret({"list": []})

    # ---------------- 分类列表 ----------------
    # 「发现」页子分类（App 同款：DiscoveryFragment 的 model tab 序列，
    # 界面顺序见图/文/影视/电台/写真/漫画）。
    # 逆向自 DiscoveryModelFragmentPresenter.getDiscoveryApi()：
    #   model 41 → discovery(4, series_category=1) 写真文章流
    #   model 42 → discovery(4, series_category=2) 漫画文章流
    # 直播/广告/AI换脸 tab 由服务端开关控制且无内容源，不接入。
    _DISCOVERY = {
        "graphic": (1, 0),    # 图文
        "article": (2, 0),    # 阅读
        "video": (3, 0),      # 影视
        "audio": (5, 0),      # 电台
        "photo_art": (4, 1),  # 写真（图片文章流）
        "comic_art": (4, 2),  # 漫画（图片文章流）
    }
    # series 流：tid -> (path, 类型名)
    _SERIES = {
        "photo": ("/v2.5/series/album/list", "写真图集"),
        "comic": ("/v2.5/series/manga/list", "漫画合集"),
        "serial": ("/v2.5/series/list", "合集大全"),
    }

    def categoryContent(self, tid="", pg="1", filter=False, extend=None):
        tid = str(tid or "")
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        ext = {}
        try:
            if isinstance(extend, dict):
                ext = extend
            elif extend and str(extend).strip().startswith("{"):
                ext = json.loads(extend)
        except Exception:
            ext = {}
        if Spider._EXT.get("sort") and "sort" not in ext:
            ext["sort"] = Spider._EXT["sort"]

        if tid in self._DISCOVERY:
            return self._cat_discovery(tid, pg, ext)
        if tid in self._SERIES:
            return self._cat_series(tid, pg, ext)
        if tid == "day":
            return self._cat_day(ext)
        if tid == "actor":
            return self._cat_actor(pg, ext)
        # 女优名录文件夹导航（folder 协议）：演员卡片 → 作品文件夹 → 作品内容
        if tid.startswith("actress/"):
            return self._cat_actor_works(tid[len("actress/"):], pg, ext)
        if tid.startswith("work/"):
            return self._cat_work(tid[len("work/"):], pg, ext)
        return self._ret({"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0})

    def _month_span(self, ext):
        """年份/月份筛选 → (起始月, 截止月)（均取当月 1 号；服务端按忽略日期的月份过滤）。
        无筛选 → (今天, first_day 月初)。year+month → 仅该月。"""
        y = str(ext.get("year") or "").strip()
        mo = str(ext.get("month") or "").strip()
        y = y if y.isdigit() and 2019 <= int(y) <= 2100 else ""
        mo = mo if mo.isdigit() and 1 <= int(mo) <= 12 else ""
        if y and mo:
            return "%s-%02d-01" % (y, int(mo)), "%s-%02d-01" % (y, int(mo))
        if y:
            return "%s-12-01" % y, "%s-01-01" % y
        if mo:
            return "%s-%02d-01" % (self._today()[:4], int(mo)), "%s-%02d-01" % (self._today()[:4], int(mo))
        fd = Spider._CACHE.get("first_day") or "2019-11-08"
        return ext.get("date") or self._today(), fd[:8] + "01"

    def _cat_discovery(self, tid, pg, ext):
        """按日期分页的发现流（服务端 published_at 按月过滤，同月数据相同）：
        页内翻页 → 翻尽直接跳到上月 1 号（App 日期选择器同年月逻辑）；
        支持 year/month 筛选定位（影视分类可自选历史年月加载）。"""
        model, scat = self._DISCOVERY[tid]
        st = Spider._CAT_STATE.get(tid)
        if pg <= 1 or not st:
            start, end = self._month_span(ext)
            st = {"date": start, "end": end, "page": 0, "served": 0}
            Spider._CAT_STATE[tid] = st
        items = []
        first_month = (Spider._CACHE.get("first_day") or "2019-11-08")[:8] + "01"
        for _ in range(90):
            if st["served"] >= pg:
                break
            st["page"] += 1
            data = self._api_post("/v2.5/article/discovery",
                                  {"model_id": model, "series_category": scat,
                                   "published_at": st["date"], "page": st["page"], "size": 20})
            lst = data if isinstance(data, list) else []
            if not lst:
                d = _prev_month(st["date"])       # 同月翻尽 → 跳上月（按月过滤）
                if d < first_month or d < st["end"]:
                    break
                st["date"] = d
                st["page"] = 0
                continue
            items = [self._from_discovery(x) for x in lst]
            st["served"] += 1
        total = len(items)
        return self._ret({"list": items, "page": pg,
                          "pagecount": 9999 if total else pg,
                          "limit": 20, "total": total})

    def _cat_series(self, tid, pg, ext):
        path, _ = self._SERIES[tid]
        sort = ext.get("sort") or "published_at"
        data = self._api_post(path, {"type": 0, "page": pg, "size": 20, "sort": sort})
        lst = data if isinstance(data, list) else []
        items = [self._from_series(x) for x in lst]
        return self._ret({"list": items, "page": pg,
                          "pagecount": 9999 if items else pg,
                          "limit": 20, "total": len(items)})

    def _cat_day(self, ext):
        date = ext.get("date") or self._today()
        data = self._api_post("/v2.5/article/day", {"published_at": date})
        info = (data or {}).get("info") or [] if isinstance(data, dict) else []
        items = [self._from_discovery(x) for x in info]
        return self._ret({"list": items, "page": 1,
                          "pagecount": 1, "limit": 20, "total": len(items)})

    def _cat_actor(self, pg, ext):
        nav = str(ext.get("nav") or "").strip()
        if nav:
            data = self._api_post("/v2.5/actor/getMainNavigationActors",
                                  {"page": pg, "size": 20, "main_navigation_id": int(nav),
                                   "tag_ids": ext.get("tags") or ""})
            lst = []
            if isinstance(data, dict):
                lst = data.get("list") or []
            elif isinstance(data, list):
                lst = data
        else:
            data = self._api_post("/v2.5/actor/getHotActors", {"page": pg, "size": 20})
            lst = []
            if isinstance(data, dict):
                lst = data.get("list") or []
            elif isinstance(data, list):
                lst = data
        items = [self._from_actor(x) for x in lst]
        return self._ret({"list": items, "page": pg,
                          "pagecount": 9999 if items else pg,
                          "limit": 20, "total": len(items)})

    def _cat_actor_works(self, aid, pg, ext):
        """演员作品文件夹（folder 卡片列表）：点击演员卡片后进入。
        作品以文件夹卡片呈现（vod_tag=folder + list 样式行卡：缩略图 +
        完整标题 + 日期/番号备注，取代详情页里被截断的选集 pill）。
        第 1 页首项保留「演员简介」入口（原详情页：资料 + 作品集线路）。"""
        try:
            aid = int(aid)
            pg = int(pg)
        except Exception:
            return self._ret({"list": [], "page": 1, "pagecount": 1,
                              "limit": 20, "total": 0})
        items = []
        if pg <= 1:
            d = self._api_post("/v2.5/actor/detail", {"id": aid})
            if isinstance(d, dict) and (d.get("main_name") or d.get("nickname")):
                num = d.get("article_num")
                items.append({
                    "vod_id": "a:%d" % aid,
                    "vod_name": d.get("main_name") or d.get("nickname") or "",
                    "vod_pic": self._pic(d.get("thumb") or ""),
                    "vod_remarks": "演员简介" + (" · 作品 %s 部" % num if num else ""),
                    "style": {"type": "list"},
                })
        data = self._api_post("/v2.5/actor/getActorArticles",
                              {"id": aid, "page": pg, "size": 20,
                               "keyword": "", "sort": ""})
        lst = (data or {}).get("list") if isinstance(data, dict) else data
        lst = lst or []
        for it in lst:
            remark = []
            pub = str(it.get("published_at") or "")[:10]
            if pub:
                remark.append(pub)
            num = str(it.get("number") or "").strip()
            if num and num != "无番号":
                remark.append(num)
            items.append({
                "vod_id": "work/%s" % it.get("id"),
                "vod_name": str(it.get("title") or ""),
                "vod_pic": self._pic(it.get("thumbnail") or it.get("thumb") or ""),
                "vod_remarks": " · ".join(remark) or "点击播放",
                "vod_tag": "folder",
                "style": {"type": "list"},
            })
        return self._ret({"list": items, "page": pg,
                          "pagecount": 9999 if len(lst) >= 20 else pg,
                          "limit": 20, "total": len(items)})

    def _cat_work(self, wid, pg, ext):
        """作品内容文件夹：点击作品文件夹卡片后进入，返回可播放条目
        （视频 → MP4 直链详情；图片 → pics 图集详情，由 detailContent 判定）。"""
        try:
            wid = int(wid)
        except Exception:
            return self._ret({"list": [], "page": 1, "pagecount": 1,
                              "limit": 20, "total": 0})
        d = self._detail_cached(wid) or {}
        m = d.get("model_id") or 0
        if d.get("video_file") and m != 4:
            remark = "视频 · 点击播放"
        elif (d.get("content") and re.search(r"<img", d.get("content") or "")) or m in (4, 1):
            remark = "图片 · 点击浏览"
        else:
            remark = "点击播放"
        items = [{
            "vod_id": str(wid),
            "vod_name": str(d.get("title") or "正片"),
            "vod_pic": self._pic(d.get("thumbnail") or d.get("thumb") or ""),
            "vod_remarks": remark,
            "style": {"type": "list"},
        }]
        return self._ret({"list": items, "page": 1, "pagecount": 1,
                          "limit": 20, "total": 1})

    # ---------------- 详情 ----------------
    def _detail_cached(self, aid):
        """详情短缓存（playerContent 复用，避免重复请求）"""
        key = str(aid)
        c = Spider._CACHE["detail"]
        hit = c.get(key)
        if hit and time.time() - hit[1] < 300:
            return hit[0]
        data = self._api_post("/v2.5/article/detail", {"id": int(aid)})
        # 仅接受真实详情（带 id 字段），错误响应（{"code":4xx}）不进缓存
        if isinstance(data, dict) and data.get("id"):
            if len(c) > 200:
                c.clear()
            c[key] = (data, time.time())
            return data
        return None

    def _content_images(self, detail):
        """从 content HTML 提取图片路径（剥 _thumbnail 取原图，App 同款）"""
        c = detail.get("content") or ""
        srcs = re.findall(r"<img[^>]+?(?:src|data-src)=[\"']([^\"']+)[\"']", c, re.I)
        out = []
        for s in srcs:
            s = s.strip()
            if not s or s.startswith("data:"):
                continue
            s = s.replace("_thumbnail", "")
            if s.startswith("http"):
                out.append(s)
            else:
                out.append(self._img_url(s))
        return out

    # 图文混排占位符（_strip_tags 之前替换，避免被当普通标签剥掉）
    _IMG_MARK = "@@ONEIMG%d@@"

    def _rich_content(self, detail, max_imgs=200):
        """novel:// 纯文本正文：阅读器不渲染 HTML，图片直接略过、不留
        「【第N图】」占位文字，正文干净连贯；仅在末尾附配图数量提示
        （图文混排请走 wv: 线路 → webview:// + 本地代理 HTML 页面）。"""
        d = detail or {}
        html = str(d.get("content") or "")
        marks = []
        if html:
            html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)

            def _img_sub(m):
                sm = re.search(r"(?:src|data-src)\s*=\s*[\"']([^\"']+)[\"']",
                               m.group(0), re.I)
                if not sm:
                    return "\n"
                u = sm.group(1).strip()
                if not u or u.startswith("data:"):
                    return "\n"
                u = u.replace("_thumbnail", "")
                if not u.startswith("http"):
                    u = self._img_url(u)
                if len(marks) < max_imgs:
                    marks.append(u)
                return "\n"

            html = re.sub(r"(?is)<img[^>]+>", _img_sub, html)
            body = _strip_tags(html)
            body = re.sub(r"\n{3,}", "\n\n", body).strip()
            if marks:
                body += "\n\n（本文含 %d 张配图，可切换到「图文」线路图文混排阅读）" % len(marks)
        else:
            body = _strip_tags(d.get("description") or "")
            # 单图图文：content 为空时提示封面图（混排见「图文」线路）
            t = str(d.get("thumbnail") or d.get("thumb") or "").strip()
            if t:
                tip = "\n\n（本条为图条，含封面配图，可切换到「图文」线路图文混排阅读）"
                body = (body + tip) if body else tip.lstrip("\n")
        return body

    def _novel_ret(self, aid, header):
        """novel:// 纯文本返回（wv 混排的降级兜底 / rd 直连）"""
        d = self._detail_cached(aid) or {}
        title = str(d.get("title") or "正文")
        body = self._rich_content(d)
        head = ""
        au = str(d.get("author") or "").strip()
        if au:
            head += "作者：%s\n\n" % au
        tg = [str(t).strip() for t in (d.get("tags") or []) if str(t).strip()]
        if tg:
            head += "标签：%s\n\n" % " · ".join(tg[:10])
        if not body:
            body = "（暂无正文）"
        return self._ret({
            "parse": 0,
            "url": "novel://" + json.dumps(
                {"title": title, "content": head + body}, ensure_ascii=False),
            "header": header,
        })

    # 图文混排 HTML 页面模板（webview:// 播放，FongMi/TVBox 客户端
    # 用内置 WebView 加载 → 文字与图片一起显示；深色主题适配播放器）
    _HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{background:#141414;color:#e8e8e8;font-family:-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;font-size:19px;line-height:1.9;padding:26px 20px 64px;max-width:880px;margin:0 auto}
h1{font-size:25px;line-height:1.45;margin-bottom:8px;color:#fff;font-weight:600}
.meta{font-size:14px;color:#9a9a9a;margin-bottom:24px;line-height:1.8}
p{margin:0 0 18px;text-align:justify;word-break:break-word}
img{max-width:100%;height:auto;display:block;margin:8px auto 20px;border-radius:6px;background:#222}
</style>
</head>
<body>
<h1>__TITLE__</h1>
__META__
__BODY__
</body>
</html>"""

    def _rich_html(self, detail, max_imgs=200):
        """图文混排 HTML 页面：content 内嵌图片按原位还原为 <img>（懒加载、
        本地代理解密地址），文字转 <p> 段落；图文（model 1，content 空）
        回退 description + 封面图。由 localProxy 以 text/html 返回，
        playerContent 用 webview:// 前缀交给客户端 WebView 渲染。"""
        d = detail or {}
        esc = html.escape
        title = esc(str(d.get("title") or "正文"))
        meta = []
        au = str(d.get("author") or "").strip()
        if au:
            meta.append("作者：" + esc(au))
        tg = [str(t).strip() for t in (d.get("tags") or []) if str(t).strip()]
        if tg:
            meta.append("标签：" + esc(" · ".join(tg[:10])))
        pub = str(d.get("published_at") or "")[:10]
        if pub:
            meta.append("日期：" + esc(pub))
        parts = []
        src = str(d.get("content") or "")
        if src:
            src = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", src)
            marks = []

            def _img_sub(m):
                sm = re.search(r"(?:src|data-src)\s*=\s*[\"']([^\"']+)[\"']",
                               m.group(0), re.I)
                if not sm:
                    return "\n"
                u = sm.group(1).strip()
                if not u or u.startswith("data:"):
                    return "\n"
                u = u.replace("_thumbnail", "")
                if not u.startswith("http"):
                    u = self._img_url(u)
                if len(marks) < max_imgs:
                    marks.append(u)
                    return "\n" + self._IMG_MARK % (len(marks) - 1) + "\n"
                return "\n【第%d图·更多图片请用「全图」线路浏览】\n" % (len(marks) + 1)

            src = re.sub(r"(?is)<img[^>]+>", _img_sub, src)
            text = _strip_tags(src)

            def _flush(buf):
                buf = buf.strip()
                if buf:
                    parts.append("<p>%s</p>" % esc(buf).replace("\n", "<br>"))

            for block in re.split(r"\n\s*\n", text):
                buf = ""
                for piece in re.split(r"(@@ONEIMG\d+@@)", block):
                    mm = re.match(r"@@ONEIMG(\d+)@@$", piece.strip())
                    if mm:
                        _flush(buf)
                        buf = ""
                        parts.append('<img loading="lazy" src="%s">' %
                                     self._proxy_wrap(marks[int(mm.group(1))]))
                    else:
                        buf += piece
                _flush(buf)
        else:
            desc = _strip_tags(d.get("description") or "")
            if desc:
                parts.append("<p>%s</p>" % esc(desc).replace("\n", "<br>"))
            t = str(d.get("thumbnail") or d.get("thumb") or "").strip()
            if t:
                parts.append('<img loading="lazy" src="%s">' % self._proxy_wrap(
                    self._img_url(t.replace("_thumbnail", ""))))
        if not parts:
            parts.append("<p>（暂无正文）</p>")
        meta_html = ('<div class="meta">%s</div>' % " · ".join(meta)) if meta else ""
        return (self._HTML_TPL
                .replace("__TITLE__", title)
                .replace("__META__", meta_html)
                .replace("__BODY__", "\n".join(parts)))

    def detailContent(self, ids):
        if not ids:
            return self._ret({"list": []})
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid)

        # 演员详情
        if vid.startswith("a:"):
            return self._actor_detail(vid[2:])

        # 专辑/合集详情（写真集 / 漫画合集 / 剧集）：走 series/chapters
        if vid.startswith("s:"):
            return self._series_detail(vid[2:])

        try:
            aid = int(vid)
        except Exception:
            return self._ret({"list": []})
        d = self._detail_cached(aid)
        if not d:
            return self._ret({"list": []})

        model = d.get("model_id") or 0
        scat = d.get("series_category") or 0
        series_id = d.get("series_id") or 0
        title = d.get("title") or ""
        desc = _strip_tags(d.get("description") or "")
        if d.get("content"):
            body = _strip_tags(d.get("content"))
            desc = (desc + "\n" + body)[:1200] if body else desc
        tags = d.get("tags") or []
        if tags:
            desc += "\n标签：" + " · ".join([str(t) for t in tags[:12]])
        remark = " · ".join([x for x in [
            str(d.get("published_at") or "")[:10],
            ("VOL." + str(d.get("vol"))) if d.get("vol") else "",
            ("♥" + str(d.get("like_number"))) if d.get("like_number") else "",
            ("👁" + str(d.get("views"))) if d.get("views") else "",
        ] if x])

        play_from, play_url = "", ""

        # ---- 音频（model 5）----
        if model == 5:
            if d.get("audio_file") or d.get("video_file"):
                play_from = "音频"
                play_url = "正片$au:%d" % aid
            else:
                remark = (remark + " · 暂无音频").strip(" ·")

        # ---- 视频（model 3 / 6）----
        elif model in (3, 6) or (d.get("video_file") and model not in (4, 5)):
            eps = []
            if d.get("video_file"):
                eps.append(("正片", "mv:%d" % aid))
            if series_id:
                eps += self._serial_video_eps(series_id, exclude=aid)
            if eps:
                play_from = "MP4直链"
                play_url = "#".join("%s$%s" % (n, u) for n, u in eps)
            else:
                remark = (remark + " · 暂无直链(仅加密HLS)").strip(" ·")

        # ---- 图片流：写真/漫画章（model 4）或图文（model 1）----
        elif model == 4 or scat in (1, 2) or model == 1:
            eps = []
            if series_id:
                chs = self._series_chapters(series_id)
                for i, ch in enumerate(chs[:99]):
                    eps.append(("第%d话" % (ch.get("chapter") or (i + 1)),
                                "pics:%s" % ch.get("id")))
            if not eps:
                eps.append(("全图", "pics:%d" % aid))
            # 图文（model 1）三条线路：
            #   「图文」wv: → webview:// 本地代理 HTML 页面，图片文字一起显示
            #   （FongMi/TVBox 客户端用内置 WebView 渲染，实测 novel 阅读器
            #    为纯文本、不渲染 <img>，故混排必须走 webview:// 通道）
            #   「全图」pics: → 纯图浏览（通用兜底）
            #   「文字」rd:  → novel:// 纯文本 + 【第N图】标记（通用兜底）
            if model == 1:
                eps.append(("图文", "wv:%d" % aid))
                eps.append(("文字", "rd:%d" % aid))
            if self._content_images(d) or series_id or model == 1:
                name = "漫画" if (scat == 2 or model == 42) else ("写真" if scat == 1 else "图文")
                play_from = name
                play_url = "#".join("%s$%s" % (n, u) for n, u in eps)

        # ---- 文章（model 2）：三条线路，首选 webview:// 图文混排 ----
        elif model == 2:
            eps = [("图文", "wv:%d" % aid),
                   ("全图", "pics:%d" % aid),
                   ("文字", "rd:%d" % aid)]
            play_from = "阅读"
            play_url = "#".join("%s$%s" % (n, u) for n, u in eps)

        # ---- 其他：无可播放内容，简介即正文 ----

        vod = {
            "vod_id": str(aid),
            "vod_name": title,
            "vod_pic": self._pic(d.get("thumbnail") or d.get("thumb") or ""),
            "vod_remarks": remark,
            "vod_content": desc,
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }
        # 纯图片流（写真/漫画）固定 pics 播放器；图文/阅读走 webview:// 混排，
        # 不设 vod_player，由客户端按 url scheme（pics:// / webview://）自动路由
        if play_from in ("写真", "漫画"):
            vod["vod_player"] = "pics"
        return self._ret({"list": [vod]})

    def _series_chapters(self, series_id):
        data = self._api_post("/v2.5/series/chapters", {"series_id": int(series_id)})
        if isinstance(data, dict):
            return data.get("chapters") or []
        return []

    def _series_detail(self, sid):
        """写真集/漫画合集/剧集详情：章节列表作为播放集数"""
        try:
            sid = int(sid)
        except Exception:
            return self._ret({"list": []})
        data = self._api_post("/v2.5/series/chapters", {"series_id": sid})
        if not isinstance(data, dict) or not data.get("chapters"):
            return self._ret({"list": []})
        chs = data.get("chapters") or []
        title = data.get("title") or ""
        thumb = data.get("thumb") or ""
        author = data.get("author") or ""
        remark = " · ".join([x for x in [
            author, "共%d章" % len(chs) if chs else "",
            ("已完结" if data.get("end") else "连载中"),
        ] if x])

        # 探测首章类型：视频剧集 → mv:；图片写真/漫画 → pics:
        kind = "pics"
        label = "图集"
        if chs:
            dd = self._detail_cached(chs[0].get("id"))
            if dd:
                if dd.get("video_file") and (dd.get("model_id") or 0) in (3, 6):
                    kind = "mv"
                    label = "剧集"
                elif (dd.get("series_category") or 0) == 2:
                    label = "漫画"
                elif (dd.get("series_category") or 0) == 1:
                    label = "写真"
        eps = []
        for i, ch in enumerate(chs[:120]):
            n = ch.get("chapter") or (i + 1)
            eps.append(("第%s话" % n if kind == "pics" else "第%s集" % n,
                        "%s:%s" % (kind, ch.get("id"))))
        vod = {
            "vod_id": "s:%d" % sid,
            "vod_name": title,
            "vod_pic": self._pic(thumb),
            "vod_remarks": remark,
            "vod_content": ("作者：%s\n" % author if author else "") +
                           "共 %d 个章节，点击集数播放" % len(chs),
            "vod_play_from": label if eps else "",
            "vod_play_url": "#".join("%s$%s" % (n, u) for n, u in eps),
        }
        if eps and kind == "pics":
            vod["vod_player"] = "pics"
        return self._ret({"list": [vod]})

    def _serial_video_eps(self, series_id, exclude=0, cap=12):
        """剧集视频：并发拉取每章详情取 MP4 直链"""
        chs = self._series_chapters(series_id)
        eps = []
        targets = [c for c in chs if c.get("id") and c.get("id") != exclude][:cap]
        if not targets:
            return eps
        results = {}

        def _work(ch):
            try:
                dd = self._detail_cached(ch.get("id"))
                if dd and dd.get("video_file"):
                    results[ch.get("id")] = dd
            except Exception:
                pass

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=6) as ex:
                list(ex.map(_work, targets))
        except Exception:
            for ch in targets:
                _work(ch)
        for ch in targets:
            dd = results.get(ch.get("id"))
            if dd:
                eps.append(("第%d集" % (ch.get("chapter") or 0), "mv:%s" % ch.get("id")))
        return eps

    def _actor_detail(self, aid):
        try:
            aid = int(aid)
        except Exception:
            return self._ret({"list": []})
        d = self._api_post("/v2.5/actor/detail", {"id": aid})
        if not isinstance(d, dict):
            return self._ret({"list": []})
        name = d.get("main_name") or d.get("nickname") or ""
        info = []
        for k, label in (("japanese_name", "日文名"), ("nickname", "昵称"),
                         ("height", "身高"), ("bust_waist_hip", "三围"),
                         ("cup_size", "罩杯"), ("birth_date", "生日")):
            if d.get(k):
                info.append("%s: %s" % (label, d.get(k)))
        desc = "；".join(info)
        if d.get("desc"):
            desc += "\n" + _strip_tags(d.get("desc"))[:600]
        # 作品列表（前 10 部，并发解析为可播放集数）
        arts = self._api_post("/v2.5/actor/getActorArticles",
                              {"id": aid, "page": 1, "size": 10, "keyword": "", "sort": ""})
        lst = (arts or {}).get("list") if isinstance(arts, dict) else arts
        lst = lst or []
        eps = []
        titles = []

        def _work(it):
            try:
                dd = self._detail_cached(it.get("id"))
                if not dd:
                    return
                m = dd.get("model_id") or 0
                if dd.get("video_file") and m != 4:
                    eps.append((it.get("title") or "", "mv:%s" % it.get("id")))
                elif (dd.get("content") and re.search(r"<img", dd.get("content") or "")) or m in (4, 1):
                    eps.append((it.get("title") or "", "pics:%s" % it.get("id")))
            except Exception:
                pass

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=6) as ex:
                list(ex.map(_work, lst[:10]))
        except Exception:
            for it in lst[:10]:
                _work(it)
        for it in lst:
            titles.append(str(it.get("title") or ""))
        if titles:
            desc += "\n\n作品：" + "、".join(titles[:20])
        vod = {
            "vod_id": "a:%d" % aid,
            "vod_name": name,
            "vod_pic": self._pic(d.get("thumb") or ""),
            "vod_remarks": "演员作品",
            "vod_content": desc[:1500],
            "vod_play_from": "作品集" if eps else "",
            "vod_play_url": "#".join("%s$%s" % (n, u) for n, u in eps),
        }
        if eps:
            vod["vod_player"] = "pics" if any(u.startswith("pics:") for _, u in eps) else ""
        return self._ret({"list": [vod]})

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick=False, pg="1"):
        key = str(key or "").strip()
        if not key:
            return self._ret({"list": []})
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        # 六模型并行聚合（视频/写真/漫画/图文/文章/音频）
        jobs = [
            {"keyword": key, "model_id": 3, "page": pg, "size": 20},
            {"keyword": key, "model_id": 4, "series_category": 1, "page": pg, "size": 20},
            {"keyword": key, "model_id": 4, "series_category": 2, "page": pg, "size": 20},
            {"keyword": key, "model_id": 1, "page": pg, "size": 20},
            {"keyword": key, "model_id": 2, "page": pg, "size": 20},
            {"keyword": key, "model_id": 5, "page": pg, "size": 20},
        ]
        results = {}

        def _work(f):
            try:
                d = self._api_post("/v2.5/article/search", f)
                if isinstance(d, list):
                    for x in d:
                        results[str(x.get("id"))] = x
            except Exception:
                pass

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=6) as ex:
                list(ex.map(_work, jobs))
        except Exception:
            for f in jobs:
                _work(f)
        # 按发布日期倒序聚合（搜索结果字段为 published_at）
        merged = sorted(results.values(),
                        key=lambda x: str(x.get("published_at") or ""), reverse=True)
        items = [self._from_discovery(x) for x in merged]
        return self._ret({"list": items, "page": pg,
                          "pagecount": 9999 if items else pg,
                          "limit": 20, "total": len(items)})

    # ---------------- 播放 ----------------
    def _probe_media(self, kind, path):
        """多域探测可用的媒体域（HEAD/Range 轻请求），返回完整 URL"""
        doms = Spider._CACHE["domains"].get(kind) or []
        if not doms:
            return (self._dom(kind) + path) if path else ""
        cands = [d.rstrip("/") + path for d in doms]
        for u in cands[:3]:
            try:
                req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": APP_UA})
                r = urllib.request.urlopen(req, timeout=8, context=_SSL)
                if r.status in (200, 206):
                    return u
            except Exception:
                try:
                    req = urllib.request.Request(u, headers={"User-Agent": APP_UA,
                                                             "Range": "bytes=0-0"})
                    r = urllib.request.urlopen(req, timeout=8, context=_SSL)
                    if r.status in (200, 206):
                        return u
                except Exception:
                    continue
        return cands[0]

    def playerContent(self, flag="", id="", vipFlags=""):
        pid = str(id or "")
        header = {"User-Agent": APP_UA}

        if pid.startswith("mv:"):
            aid = pid[3:]
            d = self._detail_cached(aid)
            vf = (d or {}).get("video_file")
            if not vf:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": "该视频暂无 MP4 直链（仅加密 HLS 源）"})
            url = self._probe_media("video", vf)
            header["Referer"] = (self._dom("video") or "https://46e9nz.mfpt8g.com") + "/"
            return self._ret({"parse": 0, "url": url, "header": header})

        if pid.startswith("au:"):
            aid = pid[3:]
            d = self._detail_cached(aid)
            af = (d or {}).get("audio_file") or (d or {}).get("video_file")
            if not af:
                return self._ret({"parse": 0, "url": "", "header": header, "msg": "暂无音频"})
            url = self._probe_media("audio", af)
            header["Referer"] = (self._dom("audio") or "") + "/"
            return self._ret({"parse": 0, "url": url, "header": header})

        if pid.startswith("pics:"):
            aid = pid[5:]
            d = self._detail_cached(aid)
            imgs = self._content_images(d) if d else []
            if not imgs and d:
                # 单图图文：content 无内嵌图时用封面兜底（thumb 去 _thumbnail 取原图）
                t = str(d.get("thumbnail") or d.get("thumb") or "").strip()
                if t:
                    imgs = [self._img_url(t.replace("_thumbnail", ""))]
            if not imgs:
                return self._ret({"parse": 0, "url": "", "header": header, "msg": "该章节暂无图片"})
            wrapped = [self._proxy_wrap(u) for u in imgs]
            return self._ret({
                "parse": 0,
                "url": "pics://" + "&&".join(wrapped),
                "header": {"User-Agent": APP_UA,
                           "Referer": (self._dom("image") or "") + "/"},
            })

        # webview:// 图文混排（FongMi/TVBox 客户端用内置 WebView 加载
        # 本地代理生成的 HTML 页面 → 文字与图片一起显示）。
        # 原理（逆向自 FongMi/TV PlaybackActivity.startWebPlayback）：
        #   url 以 webview:// 开头 → unwrap 出真实 http(s) 地址 →
        #   BrowserWebView.loadPlayback(url) 加载；页面无视频时正常渲染。
        #   HTML 由 localProxy 的 html 分支生成（do=py&html=<id>）。
        #   三线路设计：本线路失败（未开代理等）时给提示，用户可切其他线路。
        if pid.startswith("wv:"):
            aid = pid[3:]
            try:
                int(aid)
            except Exception:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": "无效的文章ID"})
            d = self._detail_cached(aid)
            if not d:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": "详情获取失败"})
            base = self._proxy_base or self._get_proxy_base()
            if not base:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": "请开启源的「本地代理」开关后重试"})
            sep = "&" if "?" in base else "?"
            return self._ret({
                "parse": 0,
                "url": "webview://" + base + sep + "html=" + str(aid),
                "header": header,
            })

        # novel:// 纯文本阅读（参照速读谷 novel:// 协议）：TVBox 内置
        # 阅读器为纯文本渲染，不解析 <img>，故图片位置只放「【第N图】」
        # 标记；图文混排请走 wv: 线路（webview:// + HTML 页面）。
        if pid.startswith("rd:"):
            aid = pid[3:]
            try:
                int(aid)
            except Exception:
                return self._ret({"parse": 0, "url": "", "header": header,
                                  "msg": "无效的文章ID"})
            return self._novel_ret(aid, header)

        if pid.startswith("http"):
            return self._ret({"parse": 0, "url": pid, "header": header})
        return self._ret({"parse": 0, "url": pid, "header": header})

    # ---------------- 本地代理：图片 AES 解密 / 图文混排 HTML ----------------
    def localProxy(self, param):
        if not isinstance(param, dict):
            return [404, "text/plain", b""]
        url = param.get("url") or param.get("u") or ""
        if not url:
            # 图文混排 HTML 页面（webview:// 播放）：?do=py&html=<文章id>
            # 由客户端 WebView 加载，文字与 <img>（代理解密图）一起渲染
            aid = str(param.get("html") or param.get("page") or "").strip()
            if not aid:
                return [404, "text/plain", b""]
            try:
                aid = int(aid)
            except Exception:
                return [404, "text/plain", b""]
            d = self._detail_cached(aid)
            if not d:
                return [404, "text/plain", b"detail not found"]
            doc = self._rich_html(d)
            if not doc:
                return [404, "text/plain", b""]
            return [200, "text/html; charset=utf-8", doc.encode("utf-8")]
        if not url.startswith("http"):
            return [404, "text/plain", b""]
        data = None
        # 图片域轮换拉取
        doms = Spider._CACHE["domains"].get("image") or []
        hosts = []
        try:
            pu = urllib.parse.urlparse(url)
            for d in doms:
                hosts.append(pu._replace(netloc=urllib.parse.urlparse(d).netloc).geturl())
        except Exception:
            pass
        hosts.insert(0, url)
        for u in hosts[:4]:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": APP_UA})
                r = urllib.request.urlopen(req, timeout=20, context=_SSL)
                data = r.read()
                if data:
                    break
            except Exception:
                continue
        if not data:
            return [502, "text/plain", b"img fetch failed"]
        # 非图片魔数 → AES 解密（加密集面）
        if data[:3] not in IMG_MAGIC and data[:4] != b"RIFF":
            try:
                dec = aes_cbc_decrypt(IMG_AES_KEY, IMG_AES_IV, data)
                if dec and (dec[:3] in IMG_MAGIC or dec[:4] == b"RIFF"):
                    data = dec
            except Exception:
                pass
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
