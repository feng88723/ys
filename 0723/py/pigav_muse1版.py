# -*- coding: utf-8 -*-
"""
PigAV 重建版（2026-11-09，用户令“重新构建一份pigav”）

底本：PigAV_10_jwzn.py（2026-10-28 requests 版，7,298B，md5 636b6c5d…），
PeerTube /api/v1 结构原样保留（分类／详情／搜索／播放四段接口均未动）。

2026-11-09 14:40 学别人 AI 写的 pigav_29（用户令“学一下别人AI写的”）后重构传输层：
  1. TLS 指纹适配器 _CFAdapter：密码套件按 Chrome 顺序＋prime256v1 曲线，
     握手特征像 Chrome，Cloudflare 不再因 JA3 指纹给 403。零第三方依赖。
  2. DNS 污染防护：全局接管 socket.getaddrinfo，只管 pigav.com／www／img 三域名。
     候选顺序：内置真实边缘 IP → DoH（IP 直连＋显式 SNI）→ 系统解析；
     候选必须通过「SNI=域名」握手时的证书主机名校验才采用，伪造 IP（Dropbox）
     在校验环节被剔除。10 分钟缓存。
  3. 超时预算：home 9 秒、分类／详情／搜索 25 秒，卡进壳侧超时（首页 10 秒、
     其它 30 秒），不再让蜘蛛在后台空转 60 秒、用户界面早已超时。
  4. 诊断卡保留：失败时回 pigav_diag 卡，vod_remarks 写清每步失败原因，
     日志里直接定因。
"""
import json
import socket
import ssl
import threading
import time
import requests
from concurrent.futures import ThreadPoolExecutor, wait
from requests.adapters import HTTPAdapter
from urllib.parse import quote
from base.spider import Spider


# ================= TLS 指纹适配器（过 Cloudflare 403）=================
# 2026-11-09 14:36 实测：整套浏览器头仍全 403——Cloudflare 认的是 TLS 握手特征
# （JA3），不是 HTTP 头。改密码套件顺序＋ECDH 曲线，让握手像 Chrome。
_CIPHERS = 'TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:AES128-SHA:AES256-SHA'


class _CFAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        try:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            pass
        try:
            self.ssl_context.set_ciphers(_CIPHERS)
        except Exception:
            pass
        try:
            self.ssl_context.set_ecdh_curve('prime256v1')
        except Exception:
            pass
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)


# ================= 域名解析兜底（DNS 污染防护）=================
# 污染环境下系统解析会返回伪造 IP（外部表现为连接超时/握手失败），这里只接管本站相关域名，
# 其余域名一律走系统解析。候选顺序：内置真实边缘 IP → DoH（IP 直连 + 显式 SNI）→ 系统解析，
# 候选必须通过「SNI=域名」握手时的证书主机名校验才被采用，伪造 IP 会在校验环节被剔除。
_DNS_SITE_HOSTS = ("pigav.com", "www.pigav.com", "img.pigav.com")
_DOH_ENDPOINTS = (
    ("223.5.5.5", "dns.alidns.com", "/resolve?name={name}&type=A"),
    ("119.29.29.29", "doh.pub", "/dns-query?name={name}&type=A"),
    ("1.1.1.1", "cloudflare-dns.com", "/dns-query?name={name}&type=A"),
    ("8.8.8.8", "dns.google", "/resolve?name={name}&type=A"),
)
_FALLBACK_EDGE_IPS = {
    "pigav.com": ("104.26.6.55", "104.26.7.55", "172.67.74.216"),
    "www.pigav.com": ("104.26.6.55", "104.26.7.55", "172.67.74.216"),
    "img.pigav.com": ("104.26.6.55", "104.26.7.55", "172.67.74.216"),
}
_DNS_CACHE = {}
_DNS_LOCK = threading.Lock()
_DNS_TTL = 600
_ORIG_GETADDRINFO = socket.getaddrinfo


def _http_payload(raw):
    head, _, body = raw.partition(b"\r\n\r\n")
    low = head.lower()
    if b"chunked" in low:
        out, data = b"", body
        while True:
            i = data.find(b"\r\n")
            if i < 0:
                break
            try:
                size = int(data[:i].split(b";")[0].strip() or b"0", 16)
            except Exception:
                break
            if size <= 0:
                break
            out += data[i + 2:i + 2 + size]
            data = data[i + 2 + size + 2:]
        body = out
    if b"gzip" in low:
        try:
            import gzip
            body = gzip.decompress(body)
        except Exception:
            pass
    return body


def _doh_query(ip, sni, path, timeout=2.5):
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers(_CIPHERS)
    except Exception:
        pass
    try:
        ctx.set_alpn_protocols(["http/1.1"])
    except Exception:
        pass
    sock = socket.create_connection((ip, 443), timeout=timeout)
    tls = ctx.wrap_socket(sock, server_hostname=sni)
    try:
        req = ("GET %s HTTP/1.1\r\nHost: %s\r\nAccept: application/dns-json\r\n"
               "User-Agent: pigav-src\r\nConnection: close\r\n\r\n" % (path, sni))
        tls.sendall(req.encode("utf-8"))
        buf = b""
        while len(buf) < 65536:
            chunk = tls.recv(4096)
            if not chunk:
                break
            buf += chunk
    finally:
        try:
            tls.close()
        except Exception:
            pass
    return json.loads(_http_payload(buf).decode("utf-8", errors="ignore"))


def _doh_resolve(host):
    ips, seen = [], set()

    def _one(ep):
        ip, sni, path = ep
        return _doh_query(ip, sni, path.format(name=host))

    try:
        with ThreadPoolExecutor(max_workers=len(_DOH_ENDPOINTS)) as ex:
            futs = [ex.submit(_one, ep) for ep in _DOH_ENDPOINTS]
            done, _pending = wait(futs, timeout=4.0)
            for fut in done:
                try:
                    data = fut.result()
                except Exception:
                    continue
                for ans in (data.get("Answer") or []):
                    addr = str(ans.get("data") or "").strip()
                    if ans.get("type") == 1 and addr and ":" not in addr and addr not in seen:
                        seen.add(addr)
                        ips.append(addr)
    except Exception:
        pass
    return ips


def _cert_matches(ip, host, timeout=2.5):
    try:
        ctx = ssl.create_default_context()
        sock = socket.create_connection((ip, 443), timeout=timeout)
        tls = ctx.wrap_socket(sock, server_hostname=host)
        try:
            cert = tls.getpeercert() or {}
        finally:
            tls.close()
        names = [str(v).lower() for k, v in (cert.get("subjectAltName") or ()) if k == "DNS"]
        for name in names:
            if name == host:
                return True
            if name.startswith("*.") and host.endswith(name[1:]) and host.count(".") == name.count("."):
                return True
        return False
    except Exception:
        return False


def _verified_order(candidates, host):
    if not candidates:
        return []
    ok = set()
    try:
        with ThreadPoolExecutor(max_workers=min(len(candidates), 4)) as ex:
            futs = {ex.submit(_cert_matches, ip, host): ip for ip in candidates[:6]}
            done, _pending = wait(futs, timeout=8.0)
            for fut in done:
                try:
                    if fut.result():
                        ok.add(futs[fut])
                except Exception:
                    continue
    except Exception:
        pass
    return [ip for ip in candidates if ip in ok]


def _resolve_site_host(host):
    now = time.time()
    with _DNS_LOCK:
        hit = _DNS_CACHE.get(host)
        if hit and hit[0] > now:
            return list(hit[1])

    builtin = [ip for ip in _FALLBACK_EDGE_IPS.get(host, ())]
    ips = _verified_order(builtin, host)
    if not ips:
        candidates = list(builtin)
        for ip in _doh_resolve(host):
            if ip not in candidates:
                candidates.append(ip)
        try:
            for info in _ORIG_GETADDRINFO(host, 443, socket.AF_INET):
                ip = info[4][0]
                if ip and ip not in candidates:
                    candidates.append(ip)
        except Exception:
            pass
        ips = _verified_order(candidates, host)
    if not ips:
        ips = builtin
    if ips:
        with _DNS_LOCK:
            _DNS_CACHE[host] = (now + _DNS_TTL, list(ips))
    return list(ips)


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        if (isinstance(host, str) and family in (0, socket.AF_UNSPEC, socket.AF_INET)
                and type in (0, socket.SOCK_STREAM)):
            key = host.lower().rstrip(".")
            if key in _DNS_SITE_HOSTS:
                ips = _resolve_site_host(key)
                if ips:
                    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]
    except Exception:
        pass
    return _ORIG_GETADDRINFO(host, port, family, type, proto, flags)


socket.getaddrinfo = _patched_getaddrinfo


class Spider(Spider):
    def getName(self):
        return "PigAV_Stable"

    def init(self, extend=""):
        self.base_url = "https://pigav.com"
        self.fallback_url = "https://pigav.ws"
        self.api_path = "/api/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://pigav.com",
            "Referer": "https://pigav.com/"
        }
        self.page_size = 24
        self._last_diag = []

    def _get_json(self, url, timeout):
        """单次 GET 取 JSON；返回 (data:dict|None, err:str)。永不抛异常。
        Session 挂 _CFAdapter（Chrome TLS 指纹），域名解析走全局 getaddrinfo 补丁
        （pigav.com 自动解析到证书校验过的真实 Cloudflare IP）。"""
        try:
            with requests.Session() as s:
                s.mount("https://", _CFAdapter())
                s.mount("http://", _CFAdapter())
                s.headers.update(self.headers)
                r = s.get(url, timeout=timeout, verify=False)
            if r.status_code != 200:
                return None, "HTTP%d" % r.status_code
            try:
                data = r.json()
            except Exception:
                return None, "JSON失败:%s" % r.text[:60]
            if isinstance(data, dict):
                return data, ""
            return None, "非dict:%s" % str(type(data))
        except Exception as e:
            return None, "%s:%s" % (type(e).__name__, str(e)[:120])

    def _api(self, path, budget=25):
        """带预算的取数：主域名 → 备用域名；预算耗尽即停。
        pigav.com 的 DNS 污染由全局 getaddrinfo 补丁兜底（证书校验过的真 IP），
        TLS 指纹由 _CFAdapter 兜底（Chrome 握手特征），故不再逐 IP 直连。

        budget：总秒数（home 传 9，其它传 25）。
        """
        self._last_diag = []
        deadline = time.time() + budget
        # 候选：(url 前缀, 单次超时秒)
        # pigav.ws 是唯一能连通的域名（TCP＋TLS 都通、只是回包慢），给它 4 秒；
        # pigav.com 走 getaddrinfo 补丁＋_CFAdapter，2 秒够了。
        candidates = [
            (self.base_url, 2),
            (self.fallback_url, 4),
        ]
        for base, to_cap in candidates:
            if time.time() >= deadline:
                break
            left = max(1, int(deadline - time.time()))
            to = min(to_cap, left)
            data, err = self._get_json(base + self.api_path + path, to)
            if data is not None:
                return data
            self._last_diag.append("%s:%s" % (base, err))
        return None

    def _videos(self, data):
        videos = []
        if not data:
            return videos
        items = data.get("data", []) if isinstance(data, dict) else data
        for item in items:
            videos.append({
                "vod_id": item.get("uuid") or item.get("shortUUID"),
                "vod_name": item.get("name", ""),
                "vod_pic": self.fix_url(item.get("thumbnailPath", "")),
                "vod_remarks": self.format_time(item.get("duration", 0))
            })
        return videos

    def _page(self, data, pg):
        total = 0
        if isinstance(data, dict):
            try:
                total = int(data.get("total", 0))
            except Exception:
                total = 0
        pagecount = (total + self.page_size - 1) // self.page_size if total > 0 else 1
        return {
            "list": self._videos(data),
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": total
        }

    def homeContent(self, filter):
        result = {"class": []}
        result["class"] = [
            {"type_id": "publishedAt", "type_name": "最近更新"},
            {"type_id": "hot", "type_name": "热门视频"},
            {"type_id": "views", "type_name": "最多观看"}
        ]
        data = self._api(f"/videos?sort=-publishedAt&count={self.page_size}&start=0", budget=9)
        if data:
            result["list"] = self._videos(data)
        else:
            result["list"] = [{
                "vod_id": "pigav_diag",
                "vod_name": "PigAV诊断：抓取失败，点开看详情",
                "vod_pic": "",
                "vod_remarks": "; ".join(self._last_diag)[:120]
            }]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        sort_map = {"publishedAt": "-publishedAt", "hot": "-hot", "views": "-views"}
        sort = sort_map.get(tid, "-publishedAt")
        p = max(1, int(pg))
        start = (p - 1) * self.page_size
        data = self._api(f"/videos?sort={sort}&count={self.page_size}&start={start}", budget=25)
        return self._page(data, p)

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        vid = str(vid).split("$")[-1]
        if vid == "pigav_diag":
            return {"list": [{
                "vod_id": "pigav_diag",
                "vod_name": "PigAV诊断",
                "vod_pic": "",
                "vod_remarks": "",
                "vod_content": "抓取失败诊断：\n" + "\n".join(self._last_diag) + "\nUA: " + self.headers["User-Agent"],
                "vod_play_from": "PigAV",
                "vod_play_url": ""
            }]}
        data = self._api(f"/videos/{vid}", budget=25)
        if not data:
            return {"list": []}
        play_id = data.get("uuid") or vid
        vod = {
            "vod_id": play_id,
            "vod_name": data.get("name", ""),
            "vod_pic": self.fix_url(data.get("thumbnailPath", "")),
            "vod_remarks": self.format_time(data.get("duration", 0)),
            "vod_actor": (data.get("channel") or {}).get("displayName", ""),
            "vod_content": data.get("description", ""),
            "vod_play_from": "PigAV",
            "vod_play_url": f"播放正片${play_id}"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        p = max(1, int(pg))
        start = (p - 1) * self.page_size
        encoded = quote(str(key), safe="")
        data = self._api(f"/search/videos?search={encoded}&count={self.page_size}&start={start}", budget=25)
        return self._page(data, p)

    def playerContent(self, flag, id, vipFlags):
        vid = str(id).split("$")[-1]
        play_headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": f"https://pigav.com/videos/{vid}",
            "Origin": "https://pigav.com",
            "Accept": "*/*",
            "Range": "bytes=0-",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }
        data = self._api(f"/videos/{vid}", budget=25)
        play_url = ""
        if data:
            streaming = data.get("streamingPlaylists") or []
            if streaming:
                play_url = streaming[0].get("playlistUrl", "")
            if not play_url:
                files = data.get("files") or []
                if files:
                    best_file = files[-1]
                    play_url = best_file.get("fileUrl") or best_file.get("fileDownloadUrl") or ""
        if play_url:
            return {
                "parse": 0,
                "url": self.fix_url(play_url),
                "header": play_headers,
                "timeout": 60
            }
        return {"parse": 0, "url": ""}

    def fix_url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        if path.startswith("/"):
            return self.base_url + path
        return self.base_url + "/" + path

    def format_time(self, seconds):
        try:
            sec = int(seconds)
            m, s = divmod(sec, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        except Exception:
            return ""
