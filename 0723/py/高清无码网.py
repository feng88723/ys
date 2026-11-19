# -*- coding: utf-8 -*-
"""
高清无码网 四壳通用 Python Spider
站点: https://fghi.gqwmw40.top/gqwmw/ (苹果CMS v10 + jsjiami v7 + AES壳)
破壳: 页面div#app密文 base64 -> AES-128-CBC 解密 -> 明文HTML
      AES key=1234567898882222, iv=8NONwyJtHesysWpM (全站统一)
播放: play页 player_aaaa JSON -> url 百分号编码(encrypt:1) -> unquote -> m3u8
结构: 列表 <li><a class="thumbnail" href="detail/id/{vid}.html"><img src="封面" alt="标题">
      详情 detail页含播放链接 vod/play/id/{vid}/sid/1/nid/1.html
防护: 无 (直连200), 仅JS加密壳
"""
import re
import base64
import json

try:
    from base.spider import Spider
except Exception:
    class Spider(object):
        def __init__(self):
            pass


# ---------- 纯Python AES-128 实现 (TVBox无加密库兜底) ----------
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_RSBOX = [0] * 256
for _i in range(256):
    _RSBOX[_SBOX[_i]] = _i
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]


def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11b
    return a & 0xff


def _gmul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r & 0xff


def _key_expand(key):
    key = list(key)
    rk = list(key)
    nk = len(key) // 4
    i = nk
    while i < 44:
        t = rk[(i - 1) * 4:(i - 1) * 4 + 4]
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= _RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [_SBOX[b] for b in t]
        for j in range(4):
            rk.append(rk[(i - nk) * 4 + j] ^ t[j])
        i += 1
    return rk


def _aes_block_decrypt(block, rk):
    state = list(block)
    nr = 10
    # AddRoundKey(rk[10])
    for j in range(16):
        state[j] ^= rk[nr * 16 + j]
    # rounds 9..0
    for rnd in range(nr - 1, -1, -1):
        # inv shift rows
        for r in range(1, 4):
            row = [state[r], state[r + 4], state[r + 8], state[r + 12]]
            row = row[-r:] + row[:-r]
            for c in range(4):
                state[r + c * 4] = row[c]
        # inv sub bytes
        for j in range(16):
            state[j] = _RSBOX[state[j]]
        # add round key
        for j in range(16):
            state[j] ^= rk[rnd * 16 + j]
        # inv mix columns (最后一轮不做)
        if rnd != 0:
            for c in range(4):
                col = state[c * 4:c * 4 + 4]
                state[c * 4 + 0] = _gmul(col[0], 0x0e) ^ _gmul(col[1], 0x0b) ^ _gmul(col[2], 0x0d) ^ _gmul(col[3], 0x09)
                state[c * 4 + 1] = _gmul(col[0], 0x09) ^ _gmul(col[1], 0x0e) ^ _gmul(col[2], 0x0b) ^ _gmul(col[3], 0x0d)
                state[c * 4 + 2] = _gmul(col[0], 0x0d) ^ _gmul(col[1], 0x09) ^ _gmul(col[2], 0x0e) ^ _gmul(col[3], 0x0b)
                state[c * 4 + 3] = _gmul(col[0], 0x0b) ^ _gmul(col[1], 0x0d) ^ _gmul(col[2], 0x09) ^ _gmul(col[3], 0x0e)
    return bytes(state)


def _aes_cbc_decrypt(data, key, iv):
    rk = _key_expand(key)
    out = b""
    prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i + 16]
        if len(blk) < 16:
            blk = blk + b"\x00" * (16 - len(blk))
        dec = _aes_block_decrypt(blk, rk)
        out += bytes(a ^ b for a, b in zip(dec, prev))
        prev = blk
    return out


def _decrypt_page(cipher_b64, key, iv):
    enc = base64.b64decode(cipher_b64)
    try:
        from Crypto.Cipher import AES
        c = AES.new(key, AES.MODE_CBC, iv)
        out = c.decrypt(enc)
    except Exception:
        out = _aes_cbc_decrypt(enc, key, iv)
    pad = out[-1] if out else 0
    if 1 <= pad <= 16:
        out = out[:-pad]
    return out.decode("utf-8", errors="ignore")


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://fghi.gqwmw40.top"
        self.rawSite = "https://fghi.gqwmw40.top"
        self.HOST = self.siteUrl
        self.base = "/gqwmw/index.php"
        self.key = b"1234567898882222"
        self.iv = bytes.fromhex("384e4f4e77794a74486573797357704d")
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        self.ext = {}
        # 分类 (父+子, 铁律7; 萝莉少女301未成年跳过)
        self.categories = [
            {"type_id": "265", "type_name": "视频一区"},
            {"type_id": "247", "type_name": "视频一区-国产视频"},
            {"type_id": "248", "type_name": "视频一区-主播直播"},
            {"type_id": "254", "type_name": "视频一区-自拍偷拍"},
            {"type_id": "289", "type_name": "视频一区-中文字幕"},
            {"type_id": "291", "type_name": "视频一区-高清无码"},
            {"type_id": "292", "type_name": "视频一区-麻豆传媒"},
            {"type_id": "293", "type_name": "视频一区-制服诱惑"},
            {"type_id": "267", "type_name": "视频二区"},
            {"type_id": "269", "type_name": "视频二区-乱伦毁三观"},
            {"type_id": "270", "type_name": "视频二区-嫖妓全过程"},
            {"type_id": "271", "type_name": "视频二区-黑料不打烊"},
            {"type_id": "273", "type_name": "视频二区-燃烧荷尔蒙"},
            {"type_id": "290", "type_name": "视频二区-剧情故事"},
            {"type_id": "300", "type_name": "视频二区-熟女人妻"},
            {"type_id": "302", "type_name": "视频二区-女同性爱"},
            {"type_id": "303", "type_name": "视频二区-多人群交"},
            {"type_id": "277", "type_name": "视频三区"},
            {"type_id": "252", "type_name": "视频三区-媚黑母狗"},
            {"type_id": "294", "type_name": "视频三区-三级伦理"},
            {"type_id": "295", "type_name": "视频三区-AI换脸"},
            {"type_id": "296", "type_name": "视频三区-卡通动漫"},
            {"type_id": "297", "type_name": "视频三区-欧美系列"},
            {"type_id": "298", "type_name": "视频三区-美女主播"},
            {"type_id": "299", "type_name": "视频三区-国产自拍"},
            {"type_id": "283", "type_name": "视频四区"},
            {"type_id": "304", "type_name": "视频四区-美乳巨乳"},
            {"type_id": "305", "type_name": "视频四区-强奸乱伦"},
            {"type_id": "306", "type_name": "视频四区-抖音视频"},
            {"type_id": "307", "type_name": "视频四区-韩国主播"},
            {"type_id": "308", "type_name": "视频四区-网红头条"},
            {"type_id": "309", "type_name": "视频四区-网爆黑料"},
            {"type_id": "310", "type_name": "视频四区-SM调教"},
            {"type_id": "311", "type_name": "视频四区-AV解说"},
        ]
        self.filter_dict = {}
        for c in self.categories:
            self.filter_dict[c["type_id"]] = []
        self._minor_re = re.compile(r"(萝莉|幼女|少女|童|teen|loli|schoolgirl|\d{1,2}岁|小学生|初中|未成年)", re.I)

    def getDependence(self):
        return ""

    def init(self, *args):
        extend = args[0] if args else None
        if not extend:
            return
        self.ext = extend
        if extend.get("siteUrl"):
            self.siteUrl = extend["siteUrl"].rstrip("/")
            self.HOST = self.siteUrl

    def homeContent(self, *args):
        result = {"class": self.categories, "filters": self.filter_dict, "list": []}
        try:
            html = self._fetch(self.siteUrl + self.base + "/vod/type/id/265.html")
            vod_list = self._parse_list(html)
            if vod_list:
                result["list"] = vod_list
        except Exception:
            pass
        return result

    def categoryContent(self, *args):
        tid = args[0] if args else "265"
        pg = args[1] if len(args) > 1 else 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        url = f"{self.siteUrl}{self.base}/vod/type/id/{tid}.html"
        if pg > 1:
            url = f"{self.siteUrl}{self.base}/vod/type/id/{tid}/page/{pg}.html"
        html = self._fetch(url)
        vod_list = self._parse_list(html)
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 36,
            "total": 9999,
            "list": vod_list,
        }

    def detailContent(self, *args):
        ids = args[0] if args else ""
        if isinstance(ids, (list, tuple)):
            ids = ids[0]
        ids = str(ids)
        m = re.search(r"id/(\d+)", ids)
        vid = m.group(1) if m else ids
        # 详情页: 提取标题+播放链接
        url = f"{self.siteUrl}{self.base}/vod/detail/id/{vid}.html"
        try:
            html = self._fetch(url)
        except Exception:
            return {"list": []}
        vod = self._parse_detail(html, vid)
        return {"list": [vod]}

    def searchContent(self, *args):
        wd = args[0] if args else ""
        pg = args[1] if len(args) > 1 else 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        from urllib.parse import quote
        kw = quote(wd)
        url = f"{self.siteUrl}{self.base}/vod/search/wd/{kw}.html"
        if pg > 1:
            url = f"{self.siteUrl}{self.base}/vod/search/wd/{kw}/page/{pg}.html"
        try:
            html = self._fetch(url)
        except Exception:
            return {"list": []}
        vod_list = self._parse_list(html)
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 36,
            "total": 9999,
            "list": vod_list,
        }

    def playerContent(self, *args):
        flag = args[0] if args else ""
        pid = args[1] if len(args) > 1 else ""
        vip = args[2] if len(args) > 2 else ""
        url = pid
        if pid and "/vod/play/" in pid:
            # pid是play页URL: 抓play页取player_aaaa
            try:
                ph = self._fetch(pid if pid.startswith("http") else self.siteUrl + pid)
                pm = re.search(r"var player_aaaa\s*=\s*(\{.*?\});", ph, re.S)
                if pm:
                    data = json.JSONDecoder().raw_decode(pm.group(1))[0]
                    u = data.get("url", "") or ""
                    if u:
                        from urllib.parse import unquote
                        url = unquote(u)
            except Exception:
                pass
        return {
            "parse": 0,
            "jx": 0,
            "url": url,
            "header": {
                "User-Agent": self.ua,
                "Referer": self.rawSite + "/",
            },
        }

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    # ---------- 内部方法 ----------

    def _is_minor(self, text):
        return bool(self._minor_re.search(text))

    def _fetch(self, url, timeout=12):
        hdrs = {
            "User-Agent": self.ua,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.rawSite + "/",
        }
        raw = ""
        # 通道1: curl_cffi
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(url, headers=hdrs, timeout=timeout, impersonate="chrome131", verify=False)
            if resp.status_code == 200:
                raw = resp.text
        except Exception:
            pass
        if not raw:
            try:
                import requests as req_lib
                resp = req_lib.get(url, headers=hdrs, timeout=timeout, verify=False)
                if resp.status_code == 200:
                    raw = resp.text
            except Exception:
                pass
        if not raw:
            import urllib.request
            import ssl
            req = urllib.request.Request(url, headers=hdrs)
            ctx = ssl.create_default_context()
            try:
                ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            except Exception:
                pass
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                resp = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout)
                body = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if enc == "gzip" or body[:2] == b"\x1f\x8b":
                    import gzip
                    body = gzip.decompress(body)
                raw = body.decode("utf-8", errors="ignore")
            except Exception:
                pass
        if not raw:
            return ""
        # 破壳: div#app密文 -> AES解密
        m = re.search(r'<div id="app"[^>]*>(.*?)</div>', raw, re.S)
        if m:
            cipher_b64 = m.group(1).strip()
            if len(cipher_b64) > 32:
                try:
                    return _decrypt_page(cipher_b64, self.key, self.iv)
                except Exception:
                    pass
        return raw

    def _parse_list(self, html):
        vod_list = []
        if not html:
            return vod_list
        # <li><a class="thumbnail" href="detail/id/{vid}.html"><img src="封面" alt="标题">...
        items = re.findall(r'<li><a class="thumbnail" href="([^"]+)"[^>]*><img src="([^"]+)" alt="([^"]*)"', html)
        for href, pic, title in items:
            if not title:
                continue
            if self._is_minor(title):
                continue
            if not href.startswith("/"):
                href = "/" + href.lstrip("/")
            if pic.startswith("/"):
                pic = self.siteUrl + pic
            vod_list.append({
                "vod_id": href,
                "vod_name": title[:80],
                "vod_pic": pic,
                "vod_remarks": "",
            })
            if len(vod_list) >= 36:
                break
        # 兜底: 任意detail链接
        if not vod_list:
            dts = re.findall(r'href="(/gqwmw/index\.php/vod/detail/id/(\d+)\.html)"[^>]*>', html)
            for href, vid in dts:
                vod_list.append({"vod_id": href, "vod_name": "视频" + vid, "vod_pic": "", "vod_remarks": ""})
                if len(vod_list) >= 36:
                    break
        return vod_list

    def _parse_detail(self, html, vid):
        title = ""
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not title:
            m2 = re.search(r'<title>(.*?)</title>', html, re.S)
            if m2:
                title = m2.group(1).split("--")[0].strip()
        # 播放链接
        pm = re.findall(r'href="(/gqwmw/index\.php/vod/play/id/(\d+)/sid/1/nid/1\.html)"', html)
        play_url = ""
        if pm:
            play_url = pm[0][0]
        vod_name = title if title else f"视频{vid}"
        return {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "m3u8",
            "vod_play_url": f"{vod_name}${play_url}" if play_url else "",
        }
