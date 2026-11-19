# -*- coding: utf-8 -*-
import base64
import gzip
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.path.append("..")
    from base.spider import BaseSpider
except Exception:
    class BaseSpider:
        pass

try:
    import requests as _requests
except Exception:
    _requests = None

UA = ("Mozilla/5.0 (Linux; Android 13; SM-A205GN) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")
TIMEOUT = 20
RETRY = 3
BASE = "https://api.yewlowxe.cc"

_AES_KEY = b"f95277cfbbimgkcusimcuekd3b777pwa"
_AES_IV = b"f95277cfbbimgkcu"
_SIGN_SECRET = "8DH2lusir4W6uhqFjbCkudNDosdfghjH"
_BIZ_DEFAULTS = {
    "oauth_id": "zwmLGswGWjXy61JY_1749114098063",
    "bundleId": "com.tvlutv",
    "version": "2.4.0",
    "oauth_type": "web",
    "app_type": "rn",
    "img_type": "new",
    "client": "pwa",
}
_HOST_RE = re.compile(r"hf-[^.]+\.")

# ---------------------------------------------------------------------------
# AES (FIPS-197) pure-python fallback; pycryptodome is used when available.
# ---------------------------------------------------------------------------
def _aes_tables():
    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x ^= ((x << 1) & 0xFF) ^ (0x1B if x & 0x80 else 0)
        x &= 0xFF
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    sbox = [0] * 256
    inv = [0] * 256
    for i in range(256):
        ii = 0 if i == 0 else exp[255 - log[i]]
        s = ii
        s ^= ((ii << 1) | (ii >> 7)) & 0xFF
        s ^= ((ii << 2) | (ii >> 6)) & 0xFF
        s ^= ((ii << 3) | (ii >> 5)) & 0xFF
        s ^= ((ii << 4) | (ii >> 4)) & 0xFF
        s = (s ^ 0x63) & 0xFF
        sbox[i] = s
        inv[s] = i
    return exp, log, sbox, inv


_EXP, _LOG, _SBOX, _INV_SBOX = _aes_tables()
_RCON = [0, 1, 2, 4, 8, 16, 32, 64, 128, 27, 54, 108, 216, 171, 77]


def _gmul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _expand_key(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[i * 4:(i + 1) * 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = list(w[i - 1])
        if i % nk == 0:
            t = [_SBOX[t[1]] ^ _RCON[i // nk], _SBOX[t[2]], _SBOX[t[3]], _SBOX[t[0]]]
        elif nk > 6 and i % nk == 4:
            t = [_SBOX[c] for c in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    rk = bytes(w[r * 4 + c][row] for r in range(nr + 1) for c in range(4) for row in range(4))
    return rk, nr


def _enc_block(blk, rk, nr):
    s = [blk[i] ^ rk[i] for i in range(16)]
    for rnd in range(1, nr + 1):
        s = [_SBOX[b] for b in s]
        s = [s[r + 4 * ((c + r) % 4)] for c in range(4) for r in range(4)]
        if rnd < nr:
            out = [0] * 16
            for c in range(4):
                a = s[4 * c:4 * c + 4]
                out[4 * c + 0] = _gmul(a[0], 2) ^ _gmul(a[1], 3) ^ a[2] ^ a[3]
                out[4 * c + 1] = a[0] ^ _gmul(a[1], 2) ^ _gmul(a[2], 3) ^ a[3]
                out[4 * c + 2] = a[0] ^ a[1] ^ _gmul(a[2], 2) ^ _gmul(a[3], 3)
                out[4 * c + 3] = _gmul(a[0], 3) ^ a[1] ^ a[2] ^ _gmul(a[3], 2)
            s = out
        base = rnd * 16
        s = [s[i] ^ rk[base + i] for i in range(16)]
    return bytes(s)


def _aes_cfb_crypt(data, decrypt=False):
    try:
        from Crypto.Cipher import AES as _AES
        mode = _AES.MODE_CFB
        c = _AES.new(_AES_KEY, mode, _AES_IV, segment_size=128)
        return c.decrypt(data) if decrypt else c.encrypt(data)
    except Exception:
        rk, nr = _expand_key(_AES_KEY)
        out = bytearray()
        prev = _AES_IV
        for i in range(0, len(data), 16):
            blk = bytes(data[i:i + 16])
            ks = _enc_block(prev, rk, nr)
            res = bytes(a ^ b for a, b in zip(blk, ks))
            out += res
            prev = blk if decrypt else bytes(res)
        return bytes(out)


# ---------------------------------------------------------------------------
# 封面解密:图床 kfws.xeqyy.com 的封面字节是 AES-128-CBC/NoPadding 加密的
# (原 App 的 Glide 取图器 x3/d 内嵌解密:Cipher AES/CBC/NoPadding、key 与
# IV 均为混淆串解码实证)。直出原址在普通壳上只会显示密文,必须经本蜘蛛
# localProxy 取图解密后回明文。
# ---------------------------------------------------------------------------
_IMG_KEY = b"f5d965df75336270"
_IMG_IV = b"97b60394abc2fbe1"


def _dec_block(blk, rk, nr):
    s = [blk[i] ^ rk[nr * 16 + i] for i in range(16)]
    for rnd in range(nr - 1, 0, -1):
        s = [s[r + 4 * ((c - r) % 4)] for c in range(4) for r in range(4)]
        s = [_INV_SBOX[b] for b in s]
        base = rnd * 16
        s = [s[i] ^ rk[base + i] for i in range(16)]
        out = [0] * 16
        for c in range(4):
            a = s[4 * c:4 * c + 4]
            out[4 * c + 0] = _gmul(a[0], 14) ^ _gmul(a[1], 11) ^ _gmul(a[2], 13) ^ _gmul(a[3], 9)
            out[4 * c + 1] = _gmul(a[0], 9) ^ _gmul(a[1], 14) ^ _gmul(a[2], 11) ^ _gmul(a[3], 13)
            out[4 * c + 2] = _gmul(a[0], 13) ^ _gmul(a[1], 9) ^ _gmul(a[2], 14) ^ _gmul(a[3], 11)
            out[4 * c + 3] = _gmul(a[0], 11) ^ _gmul(a[1], 13) ^ _gmul(a[2], 9) ^ _gmul(a[3], 14)
        s = out
    s = [s[r + 4 * ((c - r) % 4)] for c in range(4) for r in range(4)]
    s = [_INV_SBOX[b] for b in s]
    s = [s[i] ^ rk[i] for i in range(16)]
    return bytes(s)


def _aes_cbc_decrypt(data):
    if not data or len(data) % 16:
        return b""
    try:
        from Crypto.Cipher import AES as _AES
        return _AES.new(_IMG_KEY, _AES.MODE_CBC, _IMG_IV).decrypt(data)
    except Exception:
        rk, nr = _expand_key(_IMG_KEY)
        out = bytearray()
        prev = _IMG_IV
        for i in range(0, len(data), 16):
            blk = bytes(data[i:i + 16])
            dec = _dec_block(blk, rk, nr)
            out += bytes(a ^ b for a, b in zip(dec, prev))
            prev = blk
        return bytes(out)


def _img_mime(data):
    if not data:
        return ""
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"GIF8":
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:2] == b"BM":
        return "image/bmp"
    return ""


def _img_plain(data):
    """原始字节 -> (明文图片字节, mime);已是明文图原样过,密文解密后认魔数,
    服务端按 PKCS#7 补齐的尾巴在校验通过后剥掉。认不出返回 None。"""
    if not data:
        return None
    mime = _img_mime(data)
    if mime:
        return data, mime
    if len(data) % 16:
        return None
    dec = _aes_cbc_decrypt(data)
    if not dec:
        return None
    pad = dec[-1]
    if 0 < pad <= 16 and dec[-pad:] == bytes([pad]) * pad:
        dec = dec[:-pad]
    mime = _img_mime(dec)
    if mime:
        return dec, mime
    return None


_IMG_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif|bmp)$", re.I)


def _proxy_params(param):
    """壳派发 localProxy 的三种入参方言:dict / JSON 串 / query 串。"""
    if isinstance(param, dict):
        return param
    if isinstance(param, (list, tuple)):
        try:
            return dict(param)
        except Exception:
            return {}
    s = "" if param is None else str(param)
    if not s:
        return {}
    try:
        d = json.loads(s)
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    try:
        return dict(urllib.parse.parse_qsl(s))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 协议层:POST /api.php 表单 {client,timestamp,data,sign},data 为业务 JSON 的
# AES-256-CFB 加密 hex;响应 data 同法解密。付费口径:price>0 的条目不进
# 列表、付费详情不解析播放(服务端 privilege 明示付费解锁)。
# ---------------------------------------------------------------------------
def _post_form(url, form):
    body = urllib.parse.urlencode(form).encode("utf-8")
    hdrs = {"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
            "Referer": BASE + "/"}
    last = None
    for _ in range(RETRY):
        try:
            if _requests is not None:
                r = _requests.post(url, data=body, headers=hdrs, timeout=TIMEOUT)
                if r.status_code == 200:
                    return r.content
                last = Exception("http %s" % r.status_code)
                continue
        except Exception as e:
            last = e
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except Exception as e:
            last = e
        time.sleep(1)
    raise last if last else Exception("post failed")


def _call(biz):
    b = dict(_BIZ_DEFAULTS)
    b.update(biz)
    plain = json.dumps(b, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    data = _aes_cfb_crypt(plain).hex()
    ts = str(int(time.time()))
    inner = hashlib.sha256(
        ("client=pwa&data=" + data + "&timestamp=" + ts + _SIGN_SECRET).encode("utf-8")
    ).hexdigest()
    sign = hashlib.md5(inner.encode("utf-8")).hexdigest()
    url = "%s/api.php?t=%d" % (BASE, int(time.time() * 1000))
    raw = _post_form(url, {"client": "pwa", "timestamp": ts, "data": data, "sign": sign})
    outer = json.loads(raw.decode("utf-8", "ignore"))
    enc = outer.get("data")
    if isinstance(enc, str) and enc:
        return json.loads(_aes_cfb_crypt(bytes.fromhex(enc), decrypt=True).decode("utf-8", "ignore"))
    return outer


def _norm_pg(pg):
    try:
        p = int(pg)
    except Exception:
        p = 1
    return p if p >= 1 else 1


def _norm_extend(extend):
    if extend is None:
        return {}
    if isinstance(extend, dict):
        return extend
    if isinstance(extend, str):
        try:
            d = json.loads(extend)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    return {}


def _is_paid(rec):
    try:
        return float(rec.get("price") or 0) > 0
    except Exception:
        return False


def _detail_paid(j):
    d = j.get("data") or {}
    if not _is_paid(d):
        return False
    if d.get("isfree") == 2 or d.get("is_pay") == 1:
        return True
    priv = d.get("privilege") or {}
    look = priv.get("can_change_look") or {}
    return "付费" in str(look.get("msg") or "")


def _play_url(j):
    for ln in j.get("line") or []:
        inner = (ln or {}).get("line") or {}
        u = inner.get("s720") or inner.get("s240") or ""
        if u:
            return _HOST_RE.sub("hf-long.", u)
    return ""


class Spider(BaseSpider):
    def __init__(self):
        self._tags = None
        self._site_key = "luxiansheng"

    # ---------- 基础 ----------
    def getName(self):
        return "撸先生"

    def getDependence(self):
        return []

    def init(self, extend=None):
        ext = _norm_extend(extend)
        k = ext.get("siteKey") or ext.get("key")
        if k:
            self._site_key = str(k)
        return None

    def destroy(self):
        return None

    # ---------- 封面 ----------
    def _pic(self, url):
        """封面字节在图床上是 AES 加密的,直出原址普通壳显示不出,统一改走
        本蜘蛛 localProxy 解密端点:在壳内优先用 BaseSpider.getProxyUrl 拼
        壳代理址,拿不到(裸跑/旧壳基类)回退 proxy:// 方言串。没有本地代理
        图片链的壳这两式都解析不了——那种壳上封面仍不出,属壳能力边界。"""
        u = ("" if url is None else str(url)).strip()
        if not u.startswith("http"):
            return u
        try:
            return self.getProxyUrl({"u": u, "t": "img"})
        except Exception:
            pass
        return "proxy://do=py&siteKey=%s&t=img&u=%s" % (
            self._site_key, urllib.parse.quote(u, safe=""))

    # ---------- 分类(与站点导航 1:1:视频标签 + AV 标签 + 女优) ----------
    def _load_tags(self):
        if self._tags is not None:
            return self._tags
        tags = []
        try:
            j = _call({"code": "homePage", "mod": "down"})
            d = j.get("data") or {}
            for key in ("xiaoTag", "avTag"):
                for t in d.get(key) or []:
                    typ, tag, name = t.get("type"), t.get("tag"), t.get("name")
                    if typ and tag and name:
                        tags.append({"type": typ, "tag": tag, "name": name})
        except Exception:
            tags = []
        self._tags = tags
        return tags

    def _classes(self):
        classes = []
        for t in self._load_tags():
            label = t["name"] if t["type"] == "xiao" else "AV·" + t["name"]
            classes.append({"type_id": "%s|%s" % (t["type"], t["tag"]),
                            "type_name": label})
        classes.append({"type_id": "actors", "type_name": "女优"})
        return classes

    # ---------- 卡片 ----------
    def _card(self, v):
        vid = v.get("id")
        title = v.get("title")
        if vid is None or not title:
            return None
        if _is_paid(v):
            return None
        pic = v.get("cover_full") or v.get("cover_thumb") or ""
        if "/ads/" in pic:
            return None
        mod = v.get("mv_type") or "xiao"
        remarks = ""
        dur = v.get("duration")
        if isinstance(dur, (int, float)) and dur > 0:
            remarks = "%d:%02d" % (int(dur) // 60, int(dur) % 60)
        return {
            "vod_id": "%s:%s" % (mod, vid),
            "vod_name": str(title),
            "vod_pic": self._pic(pic),
            "vod_remarks": remarks,
            "type_name": str(v.get("category") or ""),
        }

    def _list_result(self, j, pg):
        cards = []
        for v in j.get("data") or []:
            c = self._card(v)
            if c:
                cards.append(c)
        page = j.get("page") or {}
        try:
            total = int(page.get("total") or len(cards))
        except Exception:
            total = len(cards)
        try:
            size = int(page.get("pagesize") or 20)
        except Exception:
            size = 20
        pagecount = pg + 1 if pg * size < total else pg
        return {"list": cards, "page": pg, "pagecount": pagecount,
                "limit": size, "total": total}

    # ---------- 主页 ----------
    def homeContent(self, filter=False):
        result = {"class": self._classes(), "filters": {}}
        try:
            j = _call({"code": "search", "mod": "xiao", "tag": "new", "page": "1"})
            result["list"] = self._list_result(j, 1)["list"]
        except Exception:
            result["list"] = []
        return result

    def homeVideoContent(self):
        try:
            j = _call({"code": "search", "mod": "xiao", "tag": "new", "page": "1"})
            return self._list_result(j, 1)
        except Exception:
            return {"list": []}

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        tid = "" if tid is None else str(tid)
        page = _norm_pg(pg)
        try:
            if tid == "actors":
                j = _call({"mod": "actor", "filter": "", "page": str(page)})
                out = []
                for a in j.get("data") or []:
                    aid, name = a.get("id"), a.get("name")
                    if aid is None or not name:
                        continue
                    out.append({
                        "vod_id": "actor:%s|%s" % (aid, name),
                        "vod_name": str(name),
                        "vod_pic": self._pic(a.get("cover") or ""),
                        "vod_remarks": "女优",
                        "vod_tag": "folder",
                    })
                return {"list": out, "page": page,
                        "pagecount": page + 1 if len(out) >= 100 else page,
                        "limit": 100, "total": len(out)}
            if tid.startswith("actor:"):
                rest = tid[len("actor:"):]
                aid, _, name = rest.partition("|")
                j = _call({"mod": "actor", "code": "eq", "id": aid,
                           "actor": name or aid, "page": str(page)})
                return self._list_result(j, page)
            typ, _, tag = tid.partition("|")
            if not typ or not tag:
                typ, tag = "xiao", "new"
            j = _call({"code": "search", "mod": typ, "tag": tag, "page": str(page)})
            return self._list_result(j, page)
        except Exception:
            return {"list": [], "page": page, "pagecount": page,
                    "limit": 20, "total": 0}

    # ---------- 详情 ----------
    def detailContent(self, ids):
        if ids is None:
            id_list = []
        elif isinstance(ids, (list, tuple)):
            id_list = [str(x) for x in ids]
        else:
            id_list = [s.strip() for s in str(ids).split(",") if s.strip()]
        out = []
        for raw_id in id_list:
            if raw_id.startswith("actor:"):
                rest = raw_id[len("actor:"):]
                aid, _, name = rest.partition("|")
                try:
                    j = _call({"mod": "actor", "code": "eq", "id": aid,
                               "actor": name or aid, "page": "1"})
                    eps = []
                    for v in j.get("data") or []:
                        c = self._card(v)
                        if c:
                            eps.append("%s$%s" % (c["vod_name"], c["vod_id"]))
                    out.append({
                        "vod_id": raw_id,
                        "vod_name": name or aid,
                        "vod_actor": name or aid,
                        "type_name": "女优",
                        "vod_play_from": "撸先生",
                        "vod_play_url": "#".join(eps),
                    })
                except Exception:
                    continue
                continue
            mod, _, vid = raw_id.partition(":")
            if not vid:
                mod, vid = "xiao", mod
            try:
                j = _call({"code": "detail", "mod": mod, "id": vid})
            except Exception:
                continue
            d = j.get("data") or {}
            if not d:
                continue
            tags = d.get("tags") or []
            if isinstance(tags, list):
                tags = ",".join(str(t) for t in tags if t)
            actors = d.get("actors")
            if isinstance(actors, list):
                actors = ",".join(str(a) for a in actors if a)
            paid = _detail_paid(j)
            play = "" if paid else _play_url(j)
            vod = {
                "vod_id": raw_id,
                "vod_name": str(d.get("title") or ""),
                "vod_pic": self._pic(d.get("cover_full") or d.get("cover_thumb") or ""),
                "vod_remarks": "付费" if paid else "",
                "vod_actor": str(actors or ""),
                "vod_class": str(tags or ""),
                "type_name": str(d.get("category") or ""),
                "vod_content": str(d.get("desc") or ""),
                "vod_play_from": "撸先生",
                "vod_play_url": "正片$%s" % play if play else "",
            }
            out.append(vod)
        return {"list": out}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick=False, pg=1, extend=None):
        page = _norm_pg(pg)
        kw = "" if key is None else str(key)
        if not kw:
            return {"list": [], "page": page, "pagecount": page,
                    "limit": 20, "total": 0}
        cards = []
        for typ in ("xiao", "av"):
            try:
                j = _call({"mod": "search", "type": typ, "code": "index",
                           "order": "new", "sort": "desc", "tag": kw,
                           "page": str(page)})
                for v in j.get("data") or []:
                    c = self._card(v)
                    if c:
                        cards.append(c)
            except Exception:
                continue
        return {"list": cards, "page": page, "pagecount": page,
                "limit": 20, "total": len(cards)}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags=None):
        pid = "" if id is None else str(id)
        if "$" in pid:
            pid = pid.split("$", 1)[1]
        if pid.startswith("http"):
            return {
                "parse": 0,
                "playUrl": "",
                "url": pid,
                "header": {"User-Agent": UA, "Referer": BASE + "/"},
                "flag": flag or "",
            }
        mod, _, vid = pid.partition(":")
        if not vid:
            mod, vid = "xiao", mod
        url = ""
        try:
            j = _call({"code": "detail", "mod": mod, "id": vid})
            if not _detail_paid(j):
                url = _play_url(j)
        except Exception:
            url = ""
        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": {"User-Agent": UA, "Referer": BASE + "/"},
            "flag": flag or "",
        }

    # ---------- 其它协议 ----------
    def localProxy(self, param):
        p = _proxy_params(param)
        url = p.get("u") or p.get("url") or ""
        is_img = p.get("t") == "img" or bool(_IMG_EXT_RE.search(url.split("?")[0]))
        if not url:
            if is_img:
                return [404, "text/plain", ""]
            return [404, "text/plain", "missing url", {}]
        body = None
        last = None
        for _ in range(2):  # 出口偶发断流,取图重试一次(与 _post_form 同口径)
            try:
                hdrs = {"User-Agent": UA, "Referer": BASE + "/"}
                if _requests is not None:
                    r = _requests.get(url, headers=hdrs, timeout=TIMEOUT)
                    body = r.content
                else:
                    req = urllib.request.Request(url, headers=hdrs)
                    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                        body = resp.read()
                        if resp.headers.get("Content-Encoding") == "gzip":
                            body = gzip.decompress(body)
                break
            except Exception as e:
                last = e
                body = None
        if body is None:
            if is_img:
                return [502, "text/plain", ""]
            return [500, "text/plain", str(last), {}]
        if is_img:
            # FongMi proxy:// 图片链方言:五项式,body 为 base64 串、末位标志 1
            plain = _img_plain(body)
            if not plain:
                return [404, "text/plain", ""]
            data, mime = plain
            return [200, mime, base64.b64encode(data).decode("ascii"),
                    {"Cache-Control": "public, max-age=86400"}, 1]
        mime = "application/octet-stream"
        if url.split("?")[0].endswith(".m3u8"):
            mime = "application/vnd.apple.mpegurl"
        return [200, mime, body, {}]

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).split("?")[0].lower()
        return u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".mp3", ".m4a"))

    def manualVideoCheck(self):
        return False

    def action(self, action=None, value=None):
        return {}
