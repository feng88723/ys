#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ysp-live 央视频直播 (浮生影院 Spider 版)

兼容 IJK / ExoPlayer / MPV 三种播放器的 HLS 直播版本:
    - playlist 带 #EXT-X-PROGRAM-DATE-TIME, Exo/MPV 才能定位直播点
    - 带 #EXT-X-START:TIME-OFFSET=-15, 从直播点前 15 秒开始播
    - playlist 窗口 8 片 (~50 秒), 兼顾 IJK 小窗口特性与 Exo 最小窗口要求
    - 分片 URL 指向本地 /chunk/<slug>/<seq>.ts, 由本地实时转发
    - 后台每 2 秒刷新, playlist 请求不触发额外刷新 (避免 media-seq 跳变)
    - 频道 Logo 来自 live.fanmingming.cn 图标库

协议: JCE PidTimeShift + bkliveinfo(cKey) 自动切换
仅标准库。
"""

import base64, gzip, json, os, random, re, struct, threading, time
import urllib.error, urllib.parse, urllib.request, uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


def format_remarks(brand="央视频", meta=""):
    clean_meta = str(meta or "").strip()
    clean_meta = re.sub(r"[\r\n\t]+", " ", clean_meta).strip()
    return ("%s | %s" % (brand, clean_meta)) if clean_meta else brand


# ================================================================ JCE 协议

class W:
    def __init__(self): self.b = bytearray()
    def head(self, typ, tag):
        if tag < 15: self.b.append(((tag & 0xf) << 4) | (typ & 0xf))
        else: self.b.append(0xf0 | (typ & 0xf)); self.b.append(tag)
    def byte(self, v, tag):
        v = int(v)
        if v == 0: self.head(12, tag)
        else: self.head(0, tag); self.b += struct.pack('>b', v)
    def short(self, v, tag):
        v = int(v)
        if -128 <= v <= 127: self.byte(v, tag)
        else: self.head(1, tag); self.b += struct.pack('>h', v)
    def int(self, v, tag):
        v = int(v)
        if -32768 <= v <= 32767: self.short(v, tag)
        else: self.head(2, tag); self.b += struct.pack('>i', v)
    def long(self, v, tag):
        v = int(v)
        if -2147483648 <= v <= 2147483647: self.int(v, tag)
        else: self.head(3, tag); self.b += struct.pack('>q', v)
    def float(self, v, tag): self.head(4, tag); self.b += struct.pack('>f', float(v))
    def double(self, v, tag): self.head(5, tag); self.b += struct.pack('>d', float(v))
    def string(self, s, tag):
        if s is None: return
        data = str(s).encode('utf-8')
        if len(data) > 255: self.head(7, tag); self.b += struct.pack('>i', len(data)); self.b += data
        else: self.head(6, tag); self.b.append(len(data)); self.b += data
    def bytes(self, data, tag):
        data = bytes(data); self.head(13, tag); self.head(0, 0); self.int(len(data), 0); self.b += data
    def struct(self, fn, tag): self.head(10, tag); fn(self); self.head(11, 0)
    def list(self, items, tag, wf): self.head(9, tag); self.int(len(items), 0)
    def out(self): return bytes(self.b)


class R:
    def __init__(self, data): self.d = memoryview(data); self.p = 0
    def rem(self): return len(self.d) - self.p
    def get(self, n):
        if self.p + n > len(self.d): raise EOFError
        b = self.d[self.p:self.p + n].tobytes(); self.p += n; return b
    def u8(self): return self.get(1)[0]
    def head(self):
        b = self.u8(); typ = b & 0xf; tag = (b & 0xf0) >> 4
        if tag == 15: tag = self.u8()
        return typ, tag
    def value(self, typ):
        if typ == 0: return struct.unpack('>b', self.get(1))[0]
        if typ == 1: return struct.unpack('>h', self.get(2))[0]
        if typ == 2: return struct.unpack('>i', self.get(4))[0]
        if typ == 3: return struct.unpack('>q', self.get(8))[0]
        if typ == 4: return struct.unpack('>f', self.get(4))[0]
        if typ == 5: return struct.unpack('>d', self.get(8))[0]
        if typ == 6: n = self.u8(); return self.get(n).decode('utf-8', 'replace')
        if typ == 7: n = struct.unpack('>i', self.get(4))[0]; return self.get(n).decode('utf-8', 'replace')
        if typ == 8: n = self._int(); return {self._fv(): self._fv() for _ in range(n)}
        if typ == 9: n = self._int(); return [self._fv() for _ in range(n)]
        if typ == 10: return self.struct()
        if typ == 11: return None
        if typ == 12: return 0
        if typ == 13: t, _ = self.head(); n = self._int(); return self.get(n)
        raise ValueError('type %d' % typ)
    def _fv(self): t, _ = self.head(); return self.value(t)
    def _int(self): t, _ = self.head(); return int(self.value(t))
    def struct(self):
        m = {}
        while self.rem() > 0:
            t, tag = self.head()
            if t == 11: break
            m[tag] = self.value(t)
        return m


VER_NAME, VER_CODE = '3.2.7.26212', '302070'
APP_ID, QMF_APP_ID, QMF_PLATFORM, BIZ_ID = '1200013', 10012, 1, 0
CHAN_ID = '10070'
GUID = ''.join(random.choice('0123456789abcdef') for _ in range(32))


def _qua(w):
    w.string(VER_NAME, 0); w.string(VER_CODE, 1)
    w.int(1080, 2); w.int(2400, 3); w.int(3, 4); w.string('12', 5)
    w.int(1, 6); w.int(1, 7); w.int(420, 8); w.string(CHAN_ID, 9)
    for i in range(10, 15): w.string('', i)
    w.struct(lambda ww: (ww.int(0, 0), ww.byte(0, 1), ww.string('', 2)), 15)
    w.string('', 16); w.string('', 17); w.string('', 18)
    w.struct(lambda ww: (ww.int(0, 0), ww.float(0, 1), ww.float(0, 2), ww.double(0, 3)), 19)
    w.string(GUID[:16], 20); w.string('Pixel 6', 21)
    w.int(1, 22)
    for i in range(23, 27): w.int(0, i)
    w.string('', 27); w.string('', 28); w.string(GUID, 29)


def _head(w, cmd, reqid):
    w.int(reqid, 0); w.int(cmd, 1)
    w.struct(lambda ww: _qua(ww), 2)
    w.string(APP_ID, 3); w.string(GUID, 4)
    w.list([], 5, None); w.struct(lambda ww: None, 6)
    w.list([], 7, None)
    w.int(0, 8); w.int(0, 9); w.int(0, 10)


def _wrap(cmd, body, reqid):
    w = W()
    w.struct(lambda ww: _head(ww, cmd, reqid), 0)
    w.bytes(body, 1)
    reqcmd = w.out()
    inner = bytearray([38]) + struct.pack('>i', len(reqcmd) + 17) + bytes([1]) + b'\x00' * 10 + reqcmd + bytes([40])
    comp = gzip.compress(bytes(inner))
    out = bytearray([19]) + struct.pack('>i', 0) + struct.pack('>H', 2) + struct.pack('>H', 65281)
    out += struct.pack('>H', cmd) + struct.pack('>H', 0) + struct.pack('>q', reqid)
    out += struct.pack('>i', 531) + struct.pack('>i', QMF_APP_ID) + struct.pack('>q', BIZ_ID)
    g = GUID.encode()[:32]; out += g + b'\x00' * (32 - len(g))
    out += struct.pack('>b', QMF_PLATFORM) + struct.pack('>i', int(VER_CODE)) + b'\x00' * 6
    out += bytes([0]) + struct.pack('>H', 0) + struct.pack('>H', 0)
    out += struct.pack('>i', len(inner)) + comp + bytes([3])
    struct.pack_into('>i', out, 1, len(out))
    return bytes(out)


def _unwrap(data):
    if data[:1] != b'\x13' or len(data) < 90: return None
    flags = struct.unpack('>i', data[21:25])[0]
    payload = data[89:-1]
    if flags & 2: payload = gzip.decompress(payload)
    if payload[:1] != b'&' or payload[-1:] != b'(': return None
    rc = R(payload[16:-1]).struct()
    return rc.get(1) or b''


class DeadHostError(RuntimeError):
    pass


def jce_timeshift_url(pid, sid, start, end, stream='fhd'):
    w = W()
    w.string(pid, 0); w.string(sid, 1); w.long(start, 2); w.long(end, 3); w.string(stream, 4)
    body = w.out()
    CMD = 25312
    reqid = int(time.time() * 1000) & 0x7fffffff
    packet = _wrap(CMD, body, reqid)
    req = urllib.request.Request('https://jacc.ysp.cctv.cn', data=packet, method='POST')
    req.add_header('Content-Type', 'application/octet-stream')
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    resp_body = _unwrap(raw)
    if not resp_body: raise RuntimeError('bad response')
    m = R(resp_body).struct()
    err = m.get(0, 0)
    if err != 0: raise RuntimeError(m.get(1, 'errCode=%s' % err))
    url = m.get(2, '')
    if not url: raise RuntimeError('empty m3u8')
    if 'liverecord.video.cloud.cctv.com' in url:
        raise DeadHostError('dead cdn host')
    return url


# ================================================================ cKey + bkliveinfo

_CK_PLATFORM = 4330403
_CK_APPVER = 'V8.22.1035.3031'
_CK_TEA = bytes.fromhex('59b2f7cf725ef43c34fdd7c123411ed3')
_CK_GTEA = bytes.fromhex('110DBEC10C23E7D2E56A1CAD6914EF1B')
_CK_XOR = bytes([0x84, 0x2e, 0xed, 0x08, 0xf0, 0x66, 0xe6, 0xea, 0x48, 0xb4, 0xca, 0xa9, 0x91, 0xed, 0x6f, 0xf3])
_CK_GXOR = bytes([0xb3, 0xc9, 0x53, 0xa0, 0x69, 0x13, 0xad, 0x4d])


def _u32(v): return v & 0xFFFFFFFF


def _tea_blk(blk, key):
    y, z = struct.unpack('>2I', blk)
    k = struct.unpack('>4I', key)
    s = 0
    for _ in range(16):
        s = _u32(s + 0x9e3779b9)
        y = _u32(y + _u32(_u32(_u32(z << 4) + k[0]) ^ _u32(z + s) ^ _u32((z >> 5) + k[1])))
        z = _u32(z + _u32(_u32(_u32(y << 4) + k[2]) ^ _u32(y + s) ^ _u32((y >> 5) + k[3])))
    return struct.pack('>2I', y, z)


def _cksum(buf):
    v = 0
    for b in buf: v = (0x83 * v + b) & 0x7fffffff
    return v


def _tea_pkt(data, key):
    pad = (8 - ((len(data) + 10) % 8)) % 8
    plain = bytes([(os.urandom(1)[0] & 0xf8) | pad]) + os.urandom(pad) + os.urandom(2) + data + bytes(7)
    out, pp, pc = b'', bytes(8), bytes(8)
    for off in range(0, len(plain), 8):
        mixed = bytes(a ^ b for a, b in zip(plain[off:off + 8], pc))
        enc = _tea_blk(mixed, key)
        cipher = bytes(a ^ b for a, b in zip(enc, pp))
        out += cipher
        pp, pc = mixed, cipher
    return out


def _lp(s):
    d = s.encode() if isinstance(s, str) else s
    return struct.pack('>H', len(d)) + d


def _ck_guard(ts, guid):
    def tail(v):
        t = str(v); return t[-5:] if len(t) >= 5 else ''
    body = struct.pack('>I', ts) + _lp(tail(guid)) + _lp(tail('null')) + _lp(tail('null')) + _lp('-1')
    plain = _lp(body)
    enc = _tea_pkt(plain, _CK_GTEA) + struct.pack('>I', _cksum(plain))
    enc = bytes(a ^ _CK_GXOR[i & 7] for i, a in enumerate(enc))
    return enc.hex().upper()


def _ckey(channel_id):
    ts = int(time.time())
    guid = os.urandom(16).hex()
    guard = _ck_guard(ts, guid)
    uid = os.urandom(4).hex().upper()
    body = (bytes.fromhex('0000004200000004000004d2') + struct.pack('>I', _CK_PLATFORM)
            + struct.pack('>I', 0) + struct.pack('>I', ts) + _lp('dcgh')
            + _lp('_zj1A5Gh6QYcxWjIUGos2w==') + _lp(_CK_APPVER) + _lp(str(channel_id))
            + _lp(guid) + struct.pack('>I', 1) + struct.pack('>I', 1) + _lp(uid) + _lp('nil')
            + _lp('57eab0c4-2c58-44c6-8ae9-dd2757525dc5') + _lp('nil') + _lp('v0.1.000')
            + _lp('com.cctv.yangshipin.app.iphone') + _lp(str(_CK_PLATFORM))
            + _lp('ex_json_bus') + _lp('ex_json_vs') + _lp(guard))
    pkt = bytearray(struct.pack('>H', len(body)) + body)
    pkt[18:22] = struct.pack('>I', _cksum(bytes(pkt)))
    pkt = bytes(pkt)
    enc = _tea_pkt(pkt, _CK_TEA) + struct.pack('>I', _cksum(pkt))
    enc = bytes(a ^ _CK_XOR[i & 15] for i, a in enumerate(enc))
    b64 = base64.b64encode(enc).decode().replace('+', '_').replace('/', '-').rstrip('=')
    return {'cKey': '--01' + b64, 'guid': guid, 'ts': ts,
            'flowId': '%s_%d' % (uuid.uuid4().hex.upper(), _CK_PLATFORM)}


_BK_H264 = base64.b64encode(b'H(30:1080,60:1080|30:1080,60:1080)').decode()


def bk_playurls(channel_id, live_pid, defn='fhd'):
    t = _ckey(channel_id)
    q = urllib.parse.urlencode({
        'atime': '120', 'livepid': live_pid, 'cnlid': channel_id,
        'appVer': _CK_APPVER, 'app_version': '300090', 'caplv': '1', 'cmd': '2',
        'defn': defn, 'device': 'iPhone', 'encryptVer': '4.2', 'getpreviewinfo': '0',
        'hevclv': '0', 'lang': 'zh-Hans_CN', 'livequeue': '0', 'logintype': '1',
        'nettype': '1', 'newnettype': '1', 'newplatform': str(_CK_PLATFORM),
        'platform': str(_CK_PLATFORM), 'sdtfrom': 'v3021', 'spacode': '23',
        'spaudio': '1', 'spdemuxer': '6', 'spdrm': '2', 'spdynamicrange': '1',
        'spflv': '1', 'spflvaudio': '1', 'sphdrfps': '60', 'sphttps': '1',
        'spvcode': _BK_H264, 'spvideo': '4', 'stream': '1', 'system': '1',
        'sysver': 'ios18.2.1', 'uhd_flag': '0', 'cKey': t['cKey'], 'guid': t['guid'],
        'fntick': str(t['ts']), 'flowid': t['flowId'], 'playbacktime': '0',
    })
    req = urllib.request.Request('https://bkliveinfo.ysp.cctv.cn/?' + q,
                                 headers={'User-Agent': 'qqlive', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        p = json.loads(r.read().decode())
    if int(p.get('iretcode', -1)) != 0:
        raise RuntimeError('iretcode=%s %s' % (p.get('iretcode'), p.get('errinfo', '')))
    urls = []
    if p.get('playurl'): urls.append(p['playurl'])
    bu = p.get('backurl_list') or p.get('backurlList') or p.get('backurl')
    if isinstance(bu, list):
        for it in bu: urls.append(it if isinstance(it, str) else (it.get('url') or it.get('playurl') or ''))
    elif isinstance(bu, str):
        urls += [x for x in re.split(r'[;,]', bu) if x.strip()]
    urls = [u for u in dict.fromkeys(urls) if u and '.cctv.' in u]
    if not urls: raise RuntimeError('no playurl')
    urls.sort(key=lambda u: (0 if 'bklive-' in u else 1, u))
    return urls


# ================================================================ 频道表

CHANNELS = [
    ('cctv1', 'CCTV-1', '2024078201', '600001859', 'fhd'),
    ('cctv2', 'CCTV-2', '2024075401', '600001800', 'fhd'),
    ('cctv3', 'CCTV-3', '2024068501', '600001801', 'fhd'),
    ('cctv4', 'CCTV-4', '2029797101', '600001814', 'fhd'),
    ('cctv5', 'CCTV-5', '2024078401', '600001818', 'fhd'),
    ('cctv5p', 'CCTV-5+', '2024078001', '600001817', 'fhd'),
    ('cctv6', 'CCTV-6', '2013693901', '600108442', 'fhd'),
    ('cctv7', 'CCTV-7', '2024072001', '600004092', 'fhd'),
    ('cctv8', 'CCTV-8', '2029793001', '600001803', 'fhd'),
    ('cctv9', 'CCTV-9', '2024078601', '600004078', 'fhd'),
    ('cctv10', 'CCTV-10', '2024078701', '600001805', 'fhd'),
    ('cctv11', 'CCTV-11', '2027248701', '600001806', 'fhd'),
    ('cctv12', 'CCTV-12', '2027248801', '600001807', 'fhd'),
    ('cctv13', 'CCTV-13', '2029797201', '600001811', 'fhd'),
    ('cctv14', 'CCTV-14', '2027248901', '600001809', 'fhd'),
    ('cctv15', 'CCTV-15', '2027249001', '600001815', 'fhd'),
    ('cctv16', 'CCTV-16', '2027249101', '600098637', 'fhd'),
    ('cctv164k', 'CCTV-16 4K', '2027249301', '600099502', 'fhd'),
    ('cctv17', 'CCTV-17', '2027249401', '600001810', 'fhd'),
    ('cctv4k', 'CCTV-4K', '2029810301', '600002264', 'fhd'),
    ('cctv8k', 'CCTV-8K', '2026774101', '600156816', 'fhd'),
    ('cgtn', 'CGTN', '2024181701', '600014550', 'fhd'),
    ('cgtnfr', 'CGTN法语', '2024181801', '600084704', 'fhd'),
    ('cgtnru', 'CGTN俄语', '2024181901', '600084758', 'fhd'),
    ('cgtnar', 'CGTN阿拉伯语', '2024182001', '600084782', 'fhd'),
    ('cgtnes', 'CGTN西班牙语', '2024182101', '600084744', 'fhd'),
    ('cgtndoc', 'CGTN 纪录', '2024182301', '600084781', 'fhd'),
    ('cctvfyjc', 'CCTV 风云剧场', '2025637103', '600099658', 'shd'),
    ('cctvdyjc', 'CCTV 第一剧场', '2026874203', '600099655', 'shd'),
    ('cctvhjjc', 'CCTV 怀旧剧场', '2026874303', '600099620', 'shd'),
    ('bjws', '北京卫视', '2024052703', '600002309', 'fhd'),
    ('jsws', '江苏卫视', '2024171103', '600002521', 'fhd'),
    ('dfws', '东方卫视', '2024054503', '600002483', 'fhd'),
    ('zjws', '浙江卫视', '2024054703', '600002520', 'fhd'),
    ('hnws', '湖南卫视', '2024054803', '600002475', 'fhd'),
    ('hbws', '湖北卫视', '2024171203', '600002508', 'fhd'),
    ('gdws', '广东卫视', '2024060903', '600002485', 'fhd'),
    ('gxws', '广西卫视', '2024060703', '600002509', 'fhd'),
    ('hljws', '黑龙江卫视', '2029797003', '600002498', 'fhd'),
    ('hainanws', '海南卫视', '2024055603', '600002506', 'fhd'),
    ('cqws', '重庆卫视', '2024061103', '600002531', 'fhd'),
    ('szws', '深圳卫视', '2024061303', '600002481', 'fhd'),
    ('scws', '四川卫视', '2024061403', '600002516', 'fhd'),
    ('henanws', '河南卫视', '2029797303', '600002525', 'fhd'),
    ('dnws', '东南卫视', '2024061503', '600002484', 'fhd'),
    ('gzws', '贵州卫视', '2024061603', '600002490', 'fhd'),
    ('jxws', '江西卫视', '2024061703', '600002503', 'fhd'),
    ('lnws', '辽宁卫视', '2024171303', '600002505', 'fhd'),
    ('ahws', '安徽卫视', '2024171403', '600002532', 'fhd'),
    ('hebws', '河北卫视', '2024171503', '600002493', 'fhd'),
    ('sdws', '山东卫视', '2029787903', '600002513', 'fhd'),
    ('tjws', '天津卫视', '2019927003', '600152137', 'fhd'),
    ('jlws', '吉林卫视', '2025561503', '600190405', 'fhd'),
    ('saxws', '陕西卫视', '2029795103', '600190400', 'fhd'),
    ('nxws', '宁夏卫视', '2025608503', '600190737', 'fhd'),
    ('nmgws', '内蒙古卫视', '2025561203', '600190401', 'fhd'),
    ('ynws', '云南卫视', '2025561303', '600190402', 'fhd'),
    ('shanxiws', '山西卫视', '2025560803', '600190407', 'fhd'),
    ('qhws', '青海卫视', '2025559103', '600190406', 'fhd'),
    ('xizangws', '西藏卫视', '2025558003', '600190403', 'fhd'),
    ('xjws', '新疆卫视', '2019927403', '600152138', 'fhd'),
    ('cetv1', 'CETV-1', '2022823801', '600171827', 'fhd'),
    ('guoxue', '国学频道', '2029360403', '600213139', 'fhd'),
]

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

WINDOW = 300
REFRESH_INTERVAL = 2              # 后台刷新间隔, 越短越不容易断
IDLE_TIMEOUT = 300
MAX_SEGS = 400
PLAYLIST_WINDOW = 8               # ★ 关键: playlist 返回 8 片 (~50 秒)
LOCAL_PORT_PREFERRED = 19876
LOCAL_PORT_RANGE = 50

CHANNEL_MAP = {c[0]: {'slug': c[0], 'name': c[1], 'sid': c[2], 'pid': c[3], 'defn': c[4]} for c in CHANNELS}

FORCE_BK = {'cctv11', 'cctv12', 'cctv14', 'cctv15', 'cctv16', 'cctv164k',
            'cctv17', 'cctv4k', 'cctvfyjc', 'cctvdyjc', 'cctvhjjc'}

BACKEND_CHANNELS = {
    'cctv1', 'cctv2', 'cctv3', 'cctv4', 'cctv5', 'cctv5p',
    'cctv7', 'cctv8', 'cctv9', 'cctv10', 'cctv11', 'cctv12',
    'cctv13', 'cctv14', 'cctv15', 'cctv16', 'cctv17',
    'cctv4k', 'cctv8k', 'cctv164k',
    'cgtn', 'cgtnfr', 'cgtnru', 'cgtnar', 'cgtnes', 'cgtndoc',
}

TRUE_4K_CHANNELS = {'cctv4k', 'cctv8k', 'cctv164k'}


# ================================================================ 频道 Logo
# 来源: live.fanmingming.cn 图标库 (永久免费直连)

_LOGO_BASE = "https://gitee.com/mytv-android/myTVlogo/raw/main/img/"

CHANNEL_LOGOS = {
    # ---- CCTV 央视 ----
    "cctv1":    _LOGO_BASE + "CCTV1.png",
    "cctv2":    _LOGO_BASE + "CCTV2.png",
    "cctv3":    _LOGO_BASE + "CCTV3.png",
    "cctv4":    _LOGO_BASE + "CCTV4.png",
    "cctv5":    _LOGO_BASE + "CCTV5.png",
    "cctv5p":   _LOGO_BASE + "CCTV5+.png",
    "cctv6":    _LOGO_BASE + "CCTV6.png",
    "cctv7":    _LOGO_BASE + "CCTV7.png",
    "cctv8":    _LOGO_BASE + "CCTV8.png",
    "cctv9":    _LOGO_BASE + "CCTV9.png",
    "cctv10":   _LOGO_BASE + "CCTV10.png",
    "cctv11":   _LOGO_BASE + "CCTV11.png",
    "cctv12":   _LOGO_BASE + "CCTV12.png",
    "cctv13":   _LOGO_BASE + "CCTV13.png",
    "cctv14":   _LOGO_BASE + "CCTV14.png",
    "cctv15":   _LOGO_BASE + "CCTV15.png",
    "cctv16":   _LOGO_BASE + "CCTV16.png",
    "cctv164k": _LOGO_BASE + "CCTV164K.png",
    "cctv17":   _LOGO_BASE + "CCTV17.png",
    "cctv4k":   _LOGO_BASE + "CCTV4K.png",
    "cctv8k":   _LOGO_BASE + "CCTV8K.png",
    # ---- CGTN ----
    "cgtn":     _LOGO_BASE + "CGTN.png",
    "cgtnfr":   _LOGO_BASE + "CGTN法语.png",
    "cgtnru":   _LOGO_BASE + "CGTN俄语.png",
    "cgtnar":   _LOGO_BASE + "CGTN阿拉伯语.png",
    "cgtnes":   _LOGO_BASE + "CGTN西班牙语.png",
    "cgtndoc":  _LOGO_BASE + "CGTN纪录.png",
    # ---- 央视付费/剧场 ----
    "cctvfyjc": _LOGO_BASE + "CCTV风云剧场.png",
    "cctvdyjc": _LOGO_BASE + "CCTV第一剧场.png",
    "cctvhjjc": _LOGO_BASE + "CCTV怀旧剧场.png",
    # ---- 卫视频道 ----
    "bjws":     _LOGO_BASE + "北京卫视.png",
    "jsws":     _LOGO_BASE + "江苏卫视.png",
    "dfws":     _LOGO_BASE + "东方卫视.png",
    "zjws":     _LOGO_BASE + "浙江卫视.png",
    "hnws":     _LOGO_BASE + "湖南卫视.png",
    "hbws":     _LOGO_BASE + "湖北卫视.png",
    "gdws":     _LOGO_BASE + "广东卫视.png",
    "gxws":     _LOGO_BASE + "广西卫视.png",
    "hljws":    _LOGO_BASE + "黑龙江卫视.png",
    "hainanws": _LOGO_BASE + "海南卫视.png",
    "cqws":     _LOGO_BASE + "重庆卫视.png",
    "szws":     _LOGO_BASE + "深圳卫视.png",
    "scws":     _LOGO_BASE + "四川卫视.png",
    "henanws":  _LOGO_BASE + "河南卫视.png",
    "dnws":     _LOGO_BASE + "东南卫视.png",
    "gzws":     _LOGO_BASE + "贵州卫视.png",
    "jxws":     _LOGO_BASE + "江西卫视.png",
    "lnws":     _LOGO_BASE + "辽宁卫视.png",
    "ahws":     _LOGO_BASE + "安徽卫视.png",
    "hebws":    _LOGO_BASE + "河北卫视.png",
    "sdws":     _LOGO_BASE + "山东卫视.png",
    "tjws":     _LOGO_BASE + "天津卫视.png",
    "jlws":     _LOGO_BASE + "吉林卫视.png",
    "saxws":    _LOGO_BASE + "陕西卫视.png",
    "nxws":     _LOGO_BASE + "宁夏卫视.png",
    "nmgws":    _LOGO_BASE + "内蒙古卫视.png",
    "ynws":     _LOGO_BASE + "云南卫视.png",
    "shanxiws": _LOGO_BASE + "山西卫视.png",
    "qhws":     _LOGO_BASE + "青海卫视.png",
    "xizangws": _LOGO_BASE + "西藏卫视.png",
    "xjws":     _LOGO_BASE + "新疆卫视.png",
    # ---- CETV / 其他 ----
    "cetv1":    _LOGO_BASE + "CETV1.png",
    "guoxue":   _LOGO_BASE + "国学频道.png",
}


# ================================================================ 活流状态

class _ChannelState:
    def __init__(self, slug, name, sid, pid, defn):
        self.slug = slug
        self.name = name
        self.sid = sid
        self.pid = pid
        self.defn = defn
        self.lock = threading.Lock()
        self.segments = {}
        self.order = deque()
        self.seq = 0
        self.last_access = 0.0
        self.thread = None
        self.last_error = ''
        self.mode = 'bk' if slug in FORCE_BK else 'jce'
        self._starting = False


CHANNEL_STATE = {c[0]: _ChannelState(c[0], c[1], c[2], c[3], c[4]) for c in CHANNELS}


def _log(msg):
    try:
        print('[ysp] %s' % msg, flush=True)
    except Exception:
        pass


def _seg_key(url, pdt):
    if pdt:
        return 'pdt:' + pdt
    p = urllib.parse.urlsplit(url)
    return p.scheme + '://' + p.netloc + p.path


def _append_segments(ch, segs):
    with ch.lock:
        for dur, pdt, url in segs:
            key = _seg_key(url, pdt)
            if key in ch.segments:
                ch.segments[key][3] = url
                continue
            ch.seq += 1
            ch.segments[key] = [ch.seq, dur, pdt, url]
            ch.order.append(key)
        while len(ch.order) > MAX_SEGS:
            ch.segments.pop(ch.order.popleft(), None)
        ch.last_error = ''


def _parse_m3u8(text, base_url):
    segs, dur, pdt = [], 6.0, ''
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#EXTINF:'):
            try:
                dur = float(line[len('#EXTINF:'):].split(',')[0])
            except ValueError:
                dur = 6.0
        elif line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
            pdt = line[len('#EXT-X-PROGRAM-DATE-TIME:'):]
        elif line and not line.startswith('#'):
            segs.append((dur, pdt, urllib.parse.urljoin(base_url, line)))
            pdt = ''
    return segs


def _jce_refresh(ch):
    now = int(time.time())
    m3u8_url = jce_timeshift_url(ch.pid, ch.sid, now - WINDOW, now, ch.defn)
    req = urllib.request.Request(m3u8_url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        text = r.read().decode('utf-8', 'replace')
    segs = _parse_m3u8(text, m3u8_url)
    if not segs:
        raise RuntimeError('empty playlist')
    _append_segments(ch, segs)
    return True


def _bk_refresh(ch):
    urls = bk_playurls(ch.sid, ch.pid, ch.defn)
    last_err = ''
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={
                'User-Agent': UA,
                'Referer': 'https://live.cctv.cn/',
                'Accept': 'application/vnd.apple.mpegurl,application/json,*/*',
            })
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode('utf-8', 'replace')
                final = r.geturl()
            lines = text.splitlines()
            for i, ln in enumerate(lines):
                if ln.strip().startswith('#EXT-X-STREAM-INF'):
                    for j in range(i + 1, len(lines)):
                        s = lines[j].strip()
                        if s and not s.startswith('#'):
                            sub = urllib.parse.urljoin(final, s)
                            req2 = urllib.request.Request(sub, headers={'User-Agent': UA})
                            with urllib.request.urlopen(req2, timeout=20) as r2:
                                text = r2.read().decode('utf-8', 'replace')
                                final = r2.geturl()
                            break
                    break
            segs = _parse_m3u8(text, final)
            if segs:
                _append_segments(ch, segs)
                return True
        except Exception as e:
            last_err = '%s: %s' % (type(e).__name__, e)
            continue
    raise RuntimeError(last_err or 'bk playlist failed')


def _refresh_once(ch):
    try:
        if ch.mode == 'bk':
            return _bk_refresh(ch)
        try:
            return _jce_refresh(ch)
        except DeadHostError:
            ch.mode = 'bk'
            _log('%s JCE 坏域名, 切换 bkliveinfo' % ch.slug)
            return _bk_refresh(ch)
    except Exception as e:
        ch.last_error = ('%s: %s' % (type(e).__name__, e))[:120]
        return False


def _refresh_loop(ch):
    fails = 0
    while time.time() - ch.last_access < IDLE_TIMEOUT:
        ok = _refresh_once(ch)
        fails = 0 if ok else fails + 1
        time.sleep(REFRESH_INTERVAL if fails < 3 else 15)


def _ensure_channel(ch):
    ch.last_access = time.time()
    with ch.lock:
        if ch._starting:
            return
        need_fetch = not ch.segments
        need_thread = ch.thread is None or not ch.thread.is_alive()
        if need_fetch or need_thread:
            ch._starting = True
        else:
            return
    try:
        if need_fetch:
            _refresh_once(ch)
        if need_thread:
            ch.thread = threading.Thread(target=_refresh_loop, args=(ch,), daemon=True)
            ch.thread.start()
    finally:
        with ch.lock:
            ch._starting = False


# ================================================================ 本地 HTTP 服务

_LOCAL_PORT = None
_LOCAL_LOCK = threading.Lock()


class _LocalHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'ysp-live-spider'

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype='text/plain; charset=utf-8', extra=None):
        data = body.encode('utf-8') if isinstance(body, str) else body
        try:
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            if extra:
                for k, v in extra.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_HEAD(self):
        path = urllib.parse.urlparse(self.path).path
        m = re.match(r'^/([\w]+)\.m3u8$', path)
        if m:
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
            self.send_header('Cache-Control', 'no-cache, no-store')
            self.end_headers()
            return
        m = re.match(r'^/([\w]+)\.ts$', path)
        if m:
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')
            self.send_header('Cache-Control', 'no-cache, no-store')
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/health':
            self._send(200, 'ok')
            return
        if path == '/diag':
            lines = []
            for slug, ch in CHANNEL_STATE.items():
                with ch.lock:
                    n = len(ch.order)
                lines.append('%s mode=%s segs=%d err=%s' % (slug, ch.mode, n, ch.last_error))
            self._send(200, '\n'.join(lines) + '\n')
            return

        m = re.match(r'^/([\w]+)\.m3u8$', path)
        if m:
            self._serve_m3u8(m.group(1))
            return

        m = re.match(r'^/([\w]+)\.ts$', path)
        if m:
            self._serve_ts(m.group(1))
            return

        m = re.match(r'^/chunk/([\w]+)/(\d+)\.ts$', path)
        if m:
            self._serve_chunk(m.group(1), int(m.group(2)))
            return

        self._send(404, 'not found\n')

    # ---------- HLS playlist ----------

    def _serve_m3u8(self, slug):
        ch = CHANNEL_STATE.get(slug)
        if not ch:
            self._send(404, 'unknown channel\n')
            return
        _ensure_channel(ch)

        # ★ 不在请求时刷新, 由后台线程负责, 避免 media-seq 跳变
        for _ in range(60):
            with ch.lock:
                if ch.order:
                    break
            time.sleep(0.2)

        with ch.lock:
            keys = list(ch.order)
            segs = [ch.segments[k] for k in keys if k in ch.segments]
            window = segs[-PLAYLIST_WINDOW:] if segs else []

        if not window:
            self._send(503, 'no data: %s\n' % (ch.last_error or 'fetching'))
            return

        ch.last_access = time.time()
        port = _LOCAL_PORT
        target = max(6, int(max(s[1] for s in window) + 0.5))

        out = [
            '#EXTM3U',
            '#EXT-X-VERSION:3',
            '#EXT-X-PLAYLIST-TYPE:EVENT',
            '#EXT-X-TARGETDURATION:%d' % target,
            '#EXT-X-MEDIA-SEQUENCE:%d' % window[0][0],
            '#EXT-X-DISCONTINUITY-SEQUENCE:0',
            '#EXT-X-START:TIME-OFFSET=-15.0',   # ★ 从直播点前 15 秒开始 (Exo/MPV)
        ]
        for seq, dur, pdt, _url in window:
            if pdt:
                out.append('#EXT-X-PROGRAM-DATE-TIME:' + pdt)   # ★ 加回 PDT
            out.append('#EXTINF:%.3f,' % dur)
            out.append('http://127.0.0.1:%d/chunk/%s/%d.ts' % (port, slug, seq))

        self._send(200, '\n'.join(out) + '\n', 'application/vnd.apple.mpegurl')

    # ---------- 分片转发 ----------

    def _serve_chunk(self, slug, seq):
        ch = CHANNEL_STATE.get(slug)
        if not ch:
            self._send(404, 'unknown\n')
            return

        ch.last_access = time.time()

        with ch.lock:
            url = None
            for k in ch.order:
                s = ch.segments.get(k)
                if s and s[0] == seq:
                    url = s[3]
                    break

        if not url:
            self._send(404, 'chunk expired\n')
            return

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Referer': 'https://live.cctv.cn/',
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read()
            self._send(200, body, 'video/mp2t')
        except urllib.error.HTTPError as e:
            self._send(e.code, 'chunk HTTP %d\n' % e.code)
        except Exception as e:
            self._send(502, 'chunk error: %s\n' % e)

    # ---------- TS 无限流中继 (备用) ----------

    def _serve_ts(self, slug):
        ch = CHANNEL_STATE.get(slug)
        if not ch:
            self._send(404, 'unknown\n')
            return
        _ensure_channel(ch)

        for _ in range(60):
            with ch.lock:
                if ch.order:
                    break
            time.sleep(0.25)
        else:
            self._send(503, 'no data\n')
            return

        try:
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')
            self.send_header('Transfer-Encoding', 'chunked')
            self.send_header('Cache-Control', 'no-cache, no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            return

        try:
            self.connection.settimeout(120)
        except Exception:
            pass

        def _write_chunk(data):
            if not data:
                return
            self.wfile.write(('%x\r\n' % len(data)).encode('ascii'))
            self.wfile.write(data)
            self.wfile.write(b'\r\n')

        with ch.lock:
            keys = list(ch.order)
            start_keys = keys[-2:] if len(keys) > 2 else keys
            start_segs = [(ch.segments[k][0], ch.segments[k][3]) for k in start_keys if k in ch.segments]
        last_seq = (min(s[0] for s in start_segs) - 1) if start_segs else 0

        empty = 0
        fail = 0
        try:
            while True:
                with ch.lock:
                    cur = [(s[0], s[3]) for k in ch.order
                           for s in [ch.segments.get(k)] if s and s[0] > last_seq]
                cur.sort(key=lambda x: x[0])
                if not cur:
                    empty += 1
                    if empty > 600:
                        break
                    time.sleep(0.3)
                    continue
                empty = 0
                for seq, url in cur:
                    try:
                        req = urllib.request.Request(url, headers={
                            'User-Agent': UA,
                            'Referer': 'https://live.cctv.cn/',
                        })
                        with urllib.request.urlopen(req, timeout=15) as r:
                            while True:
                                chunk = r.read(64 * 1024)
                                if not chunk:
                                    break
                                _write_chunk(chunk)
                        self.wfile.flush()
                        last_seq = seq
                        ch.last_access = time.time()
                        fail = 0
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        return
                    except Exception:
                        fail += 1
                        last_seq = seq
                        if fail > 20:
                            return
                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            _log('%s ts err %s' % (ch.slug, e))


def _ensure_local_server():
    global _LOCAL_PORT
    with _LOCAL_LOCK:
        if _LOCAL_PORT is not None:
            return _LOCAL_PORT
        ports = list(range(LOCAL_PORT_PREFERRED, LOCAL_PORT_PREFERRED + LOCAL_PORT_RANGE)) + [0]
        last_err = None
        for port in ports:
            try:
                srv = ThreadingHTTPServer(('127.0.0.1', port), _LocalHandler)
                srv.daemon_threads = True
                _LOCAL_PORT = srv.server_address[1]
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                _log('本地服务已启动: http://127.0.0.1:%d/' % _LOCAL_PORT)
                return _LOCAL_PORT
            except OSError as e:
                last_err = e
                continue
        raise RuntimeError('无法绑定端口: %s' % last_err)


# ================================================================ Spider

class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.brandActor = "📺 央视频直播"
        self.brandDirector = "ysp-live"

    def init(self, extend=""):
        try:
            _ensure_local_server()
        except Exception as e:
            _log('本地服务启动失败: %s' % e)
        return True

    def getName(self): return "央视频直播"
    def isVideoFormat(self, url): return True
    def manualVideoCheck(self): return False
    def destroy(self): pass

    def homeContent(self, filter):
        return {"class": [
            {"type_name": "央视频道", "type_id": "cctv"},
            {"type_name": "卫视频道", "type_id": "satellite"},
            {"type_name": "CGTN",     "type_id": "cgtn"},
            {"type_name": "4K超清",    "type_id": "4k"},
            {"type_name": "付费剧场",  "type_id": "premium"},
            {"type_name": "其他",      "type_id": "other"},
        ], "filters": {}}

    def homeVideoContent(self): return {"list": []}

    def _classify(self, slug):
        cats = []
        if (re.match(r'^cctv\d', slug) or slug == 'cctv5p') and slug not in TRUE_4K_CHANNELS:
            cats.append('cctv')
        if slug in TRUE_4K_CHANNELS:
            cats.append('4k')
        if slug in ('cctvfyjc', 'cctvdyjc', 'cctvhjjc'):
            cats.append('premium')
        if slug.endswith('ws') or slug == 'cetv1':
            cats.append('satellite')
        if slug.startswith('cgtn'):
            cats.append('cgtn')
        if slug == 'guoxue':
            cats.append('other')
        return cats

    def _make_card(self, slug, name):
        tag = ''
        if slug in TRUE_4K_CHANNELS:
            tag = '真4K'
        elif slug in BACKEND_CHANNELS:
            tag = '高码率'
        logo = CHANNEL_LOGOS.get(slug, '')
        return {"vod_id": slug, "vod_name": name, "vod_pic": logo,
                "vod_remarks": format_remarks("央视频", tag),
                "style": {"type": "rect", "ratio": 1.78}}

    def categoryContent(self, tid, pg, filter, extend):
        cards = [self._make_card(s, n) for s, n, _s, _p, _d in CHANNELS if tid in self._classify(s)]
        return {"page": 1, "pagecount": 1, "limit": len(cards), "total": len(cards), "list": cards}

    def detailContent(self, ids):
        slug = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        info = CHANNEL_MAP.get(slug)
        if not info:
            return {"list": []}
        name = info['name']

        try:
            _ensure_local_server()
            ch = CHANNEL_STATE.get(slug)
            if ch:
                _ensure_channel(ch)
        except Exception:
            pass

        full_desc = (
            "【📺 央视频直播】\n"
            "频道: %s\n"
            "HLS 直播, 本地分片转发。"
        ) % name
        escaped_desc = (full_desc.replace("&", "&amp;")
                                .replace("<", "&lt;")
                                .replace(">", "&gt;"))

        logo = CHANNEL_LOGOS.get(slug, '')

        vod = {
            "vod_id": slug,
            "vod_name": name,
            "vod_pic": logo,
            "vod_actor": self.brandActor,
            "vod_director": self.brandDirector,
            "vod_remarks": format_remarks("央视频", "直播"),
            "vod_content": escaped_desc,
            "vod_play_from": "央视频",
            "vod_play_url": "超清$%s" % slug,
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        del flag, vipFlags
        slug = str(id).strip()
        if slug.startswith('http://') or slug.startswith('https://'):
            return {"parse": 0, "playUrl": "", "url": slug,
                    "header": {"User-Agent": UA, "Referer": "https://live.cctv.cn/"}}
        if slug not in CHANNEL_STATE:
            return {"parse": 0, "playUrl": "", "url": "", "header": {}}

        try:
            port = _ensure_local_server()
        except Exception:
            info = CHANNEL_MAP[slug]
            url = ''
            try:
                now = int(time.time())
                url = jce_timeshift_url(info['pid'], info['sid'], now - WINDOW, now, info['defn'])
            except Exception:
                pass
            return {"parse": 0, "playUrl": "", "url": url,
                    "header": {"User-Agent": UA, "Referer": "https://live.cctv.cn/"}}

        ch = CHANNEL_STATE[slug]
        _ensure_channel(ch)
        for _ in range(40):
            with ch.lock:
                if ch.order:
                    break
            time.sleep(0.5)

        return {
            "parse": 0,
            "playUrl": "",
            "url": "http://127.0.0.1:%d/%s.m3u8" % (port, slug),
            "header": {
                "User-Agent": UA,
                "Referer": "https://live.cctv.cn/",
            },
        }

    def searchContent(self, key, quick, pg="1"):
        del quick, pg
        key = (key or "").strip().lower()
        cards = []
        if key:
            for slug, name, _s, _p, _d in CHANNELS:
                if key in name.lower() or key in slug.lower():
                    cards.append(self._make_card(slug, name))
        return {"page": 1, "pagecount": 1, "limit": len(cards), "total": len(cards), "list": cards}

    def action(self, action): return {"msg": "ok"}
    def liveContent(self): return ""
    def localProxy(self, params): return [404, "text/plain; charset=utf-8", "Proxy not configured"]


# ================================================================ 本地调试

if __name__ == '__main__':
    import argparse, sys
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=LOCAL_PORT_PREFERRED)
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--test-slug', default='cctv1')
    args = ap.parse_args()
    LOCAL_PORT_PREFERRED = args.port

    sp = Spider(); sp.init()
    print("homeContent:", json.dumps(sp.homeContent({}), ensure_ascii=False))
    cc = sp.categoryContent('cctv', 1, {}, {})
    print("cctv: %d 个频道" % cc['total'])
    for c in cc['list'][:3]:
        print("  ", c['vod_id'], c['vod_name'], "->", c['vod_pic'])
    dc = sp.detailContent([args.test_slug])
    if dc['list']:
        print("detail:", dc['list'][0]['vod_name'], dc['list'][0]['vod_pic'])
    pc = sp.playerContent('', args.test_slug, [])
    print("playerContent:", json.dumps(pc, ensure_ascii=False))

    if args.once:
        time.sleep(3)
        try:
            with urllib.request.urlopen(pc['url'], timeout=10) as r:
                print(r.read().decode('utf-8', 'replace')[:800])
        except Exception as e:
            print("错误:", e)
        sys.exit(0)

    port = _LOCAL_PORT
    print("\n" + "=" * 60)
    print("常驻模式 (Ctrl+C 退出)")
    print("  m3u8 : http://127.0.0.1:%d/%s.m3u8" % (port, args.test_slug))
    print("  diag : http://127.0.0.1:%d/diag" % port)
    print("=" * 60)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass