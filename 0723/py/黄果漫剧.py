# -*- coding: utf-8 -*-
"""
黄果漫剧 TVBox 爬虫源（修复优化版）
"""

import json
import base64
import time
import hashlib
import re
import gzip
import urllib.request as ur
import urllib.parse as up
import urllib.error as ue
from concurrent.futures import ThreadPoolExecutor


class Spider:

    MARK_VIP = True      # VIP 集标题后加「·VIP」标记
    VIP_FALLBACK = True  # 是否开启 VIP 播放推导
    PROBE_RANGE = 2      # 推导地址探测范围（左右偏移）

    def __init__(self):
        self.api_bases = [
            "https://hgxml.00api-agy5u.com/api",
            "https://rules.googlexml.com/api",
            "https://awsapi.ipa001-7hzktt.com/api",
        ]
        self.img_base = "https://haguapi.huangguo.top"
        self.domain_key = "HgApiCache#e0ae36"
        self.token = None
        self.token_expire = 0
        self.cache = {}
        self.cache_ttl = 300
        self.ep_index = {}
        self.ua = ("Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
        self.classical_map = {
            "成人": "风月", "淫乱": "荒淫", "婊": "贱", "强奸": "强占",
            "无码": "素纱", "有码": "遮面", "熟女": "徐娘", "人妻": "罗敷",
            "护士": "药女", "教师": "先生", "丝袜": "丝履", "巨乳": "丰盈",
            "偷拍": "窥帘", "乱伦": "禁脔", "激情": "云雨", "色情": "春宫",
            "淫秽": "秽乱", "赌博": "孤注", "广告": "告示", "荡妇": "淫娃",
            "出轨": "逾墙", "偷情": "私会", "绿帽": "翠冠", "娇妻": "美眷",
            "嫩": "稚", "骚": "浪", "欲": "念", "肉": "身", "穴": "谷",
        }
        self.minor_map = {
            "萝莉": "豆蔻", "幼女": "玉蕊", "少女": "碧玉", "学生": "书生",
            "童": "稚子", "未成年": "未及笄", "teen": "豆蔻", "loli": "豆蔻",
            "schoolgirl": "书生",
        }

    def getDependence(self):
        return ""

    def init(self, extend=""):
        try:
            if isinstance(extend, str):
                cfg = json.loads(extend)
            elif isinstance(extend, dict):
                cfg = extend
            else:
                cfg = {}
            if cfg.get("api_bases"):
                self.api_bases = cfg["api_bases"]
            if cfg.get("img_base"):
                self.img_base = cfg["img_base"]
            if "mark_vip" in cfg:
                self.MARK_VIP = bool(cfg["mark_vip"])
            if "vip_fallback" in cfg:
                self.VIP_FALLBACK = bool(cfg["vip_fallback"])
        except Exception:
            pass

    def destroy(self):
        self.token = None
        self.cache.clear()
        self.ep_index.clear()

    def action(self, action):
        return ""

    def isVideoFormat(self, url):
        return bool(url) and ".m3u8" in url

    def manualVideoCheck(self):
        return False

    def _xor_decrypt(self, text):
        if not text or not text.startswith("h1."):
            return text
        try:
            raw = base64.b64decode(text[3:])
            key = self.domain_key.encode("utf-8")
            result = bytearray()
            for i, b in enumerate(raw):
                result.append(b ^ key[i % len(key)])
            return result.decode("utf-8", errors="ignore")
        except Exception:
            return text

    def _ensure_token(self):
        if self.token and time.time() < self.token_expire:
            return
        for base in self.api_bases:
            try:
                body = json.dumps({
                    "device_id": "web_tvbox_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
                }).encode("utf-8")
                req = ur.Request(base + "/app/auth/device", data=body, method="POST")
                req.add_header("User-Agent", self.ua)
                req.add_header("Content-Type", "application/json")
                req.add_header("Accept", "application/json")
                resp = ur.urlopen(req, timeout=5)
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("token"):
                    self.token = data["token"]
                    self.token_expire = time.time() + 86400
                    return
            except Exception:
                continue

    def _request(self, url, auth=True, method="GET", body=None):
        cache_key = url + "|" + method + "|" + (body or "")
        hit = self.cache.get(cache_key)
        if hit and time.time() - hit["ts"] < self.cache_ttl:
            return hit["data"]
        if auth:
            self._ensure_token()
        last_err = None
        for base in self.api_bases:
            full_url = base + url if url.startswith("/app/") else url
            for attempt in (1, 2):
                try:
                    data = body.encode("utf-8") if body else None
                    req = ur.Request(full_url, data=data, method=method)
                    req.add_header("User-Agent", self.ua)
                    req.add_header("Accept", "application/json")
                    req.add_header("Referer", "https://google.huge1-7wnjsk.com/")
                    if auth and self.token:
                        req.add_header("Authorization", "Bearer " + self.token)
                    if body:
                        req.add_header("Content-Type", "application/json")
                    resp = ur.urlopen(req, timeout=8)
                    result = json.loads(resp.read().decode("utf-8"))
                    self.cache[cache_key] = {"ts": time.time(), "data": result}
                    return result
                except ue.HTTPError as e:
                    last_err = e
                    if e.code == 401 and auth and attempt == 1:
                        self.token = None
                        self.token_expire = 0
                        self._ensure_token()
                        continue
                    break
                except Exception as e:
                    last_err = e
                    break
        if last_err:
            raise last_err
        return None

    def _fix_cover(self, cover):
        if not cover:
            return ""
        if cover.startswith("http"):
            return cover
        if cover.startswith("//"):
            return "https:" + cover
        return self.img_base + "/" + cover.lstrip("/")

    def _is_minor(self, text):
        if not text:
            return False
        low = text.lower()
        for k in self.minor_map:
            if k.lower() in low:
                return True
        return False

    def desensitize(self, text):
        if not text:
            return text
        if not any(k in text for k in self.classical_map):
            return text
        result = text
        for k, v in self.classical_map.items():
            result = result.replace(k, v)
        return result

    def _storage_of(self, play_url):
        if not play_url:
            return None, None
        m = re.search(r"(https?://[^/]+)/storage/(\d+)/", play_url)
        if not m:
            return None, None
        return m.group(1), int(m.group(2))

    def _m3u8_ok(self, url):
        try:
            req = ur.Request(url)
            req.add_header("User-Agent", self.ua)
            resp = ur.urlopen(req, timeout=4)
            if getattr(resp, "status", 200) != 200:
                return False
            raw = resp.read(4096)
            resp.close()
            if raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    return False
            head = raw.decode("utf-8", errors="ignore")
            return "#EXTM3U" in head
        except Exception:
            return False

    def _anchor(self, drama_id, eps_data=None):
        ck = "anchor:" + str(drama_id)
        hit = self.cache.get(ck)
        if hit and time.time() - hit["ts"] < 3600:
            return hit["data"]
        if eps_data is None:
            eps_data = self._request("/app/dramas/%s/episodes" % drama_id)
        eps = (eps_data or {}).get("list") or []
        free = [e for e in eps if not e.get("need_vip")]
        if not free:
            free = eps
        best = None
        for e in reversed(free):
            try:
                pd = self._request("/app/play/%s" % e.get("id"))
            except Exception:
                continue
            host, sid = self._storage_of((pd or {}).get("play_url"))
            if host and sid:
                best = {"host": host, "sid": sid, "ep": int(e.get("ep") or 0)}
                break
        if best:
            self.cache[ck] = {"ts": time.time(), "data": best}
        return best

    def _vip_url(self, drama_id, ep_no, eps_data=None):
        anchor = self._anchor(drama_id, eps_data)
        if not anchor:
            return ""
        base = anchor["sid"] + (int(ep_no) - anchor["ep"])
        rng = max(0, int(self.PROBE_RANGE))
        offsets = [0]
        for i in range(1, rng + 1):
            offsets.append(i)
            offsets.append(-i)

        candidate_urls = []
        for off in offsets:
            cand = base + off
            if cand > 0:
                candidate_urls.append("%s/storage/%d/index.m3u8" % (anchor["host"], cand))

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(lambda u: (u, self._m3u8_ok(u)), candidate_urls)
            for url, ok in results:
                if ok:
                    return url
        return ""

    def _ep_suffix(self, ep):
        return "·VIP" if (self.MARK_VIP and ep.get("need_vip")) else ""

    def _vod_from_item(self, item):
        if not item:
            return None
        title = item.get("title", "")
        if self._is_minor(title):
            return None
        return {
            "vod_id": str(item.get("id", "")),
            "vod_name": self.desensitize(title),
            "vod_pic": self._fix_cover(item.get("cover", "")),
            "vod_remarks": str(item.get("episode_count", "1")) + "集",
            "vod_year": item.get("year", ""),
            "vod_area": "",
            "vod_author": "",
            "vod_content": "",
            "vod_play_from": "",
            "vod_play_url": "",
        }

    def homeContent(self, filter=False):
        classes = []
        filters = {}
        common_filter = [
            {"key": "badge", "name": "标签", "init": "", "value": [
                {"n": "全部", "v": ""},
                {"n": "18+", "v": "18+"},
                {"n": "漫剧", "v": "漫剧"},
                {"n": "擦边", "v": "擦边"},
                {"n": "都市", "v": "都市"},
                {"n": "古装", "v": "古装"},
                {"n": "悬疑", "v": "悬疑"}
            ]},
            {"key": "status", "name": "状态", "init": "", "value": [
                {"n": "全部", "v": ""},
                {"n": "完结", "v": "ended"},
                {"n": "连载", "v": "ongoing"}
            ]},
            {"key": "sort", "name": "排序", "init": "", "value": [
                {"n": "最新", "v": "latest"},
                {"n": "最热", "v": "hot"},
                {"n": "推荐", "v": "recommend"}
            ]}
        ]
        try:
            cat_data = self._request("/app/categories")
            for c in (cat_data or {}).get("list") or []:
                cid = str(c["id"])
                cname = self.desensitize(c.get("name", ""))
                if self._is_minor(cname):
                    continue
                classes.append({"type_id": cid, "type_name": cname})
                filters[cid] = common_filter
        except Exception:
            pass
            
        if not classes:
            classes = [
                {"type_id": "1", "type_name": "精选短剧"},
                {"type_id": "2", "type_name": "热播漫剧"},
                {"type_id": "3", "type_name": "擦边风月"}
            ]
            for c in classes:
                filters[c["type_id"]] = common_filter

        videos = []
        try:
            home_data = self._request("/app/home?page=1&pageSize=20")
            for item in (home_data or {}).get("latest") or []:
                v = self._vod_from_item(item)
                if v:
                    videos.append(v)
        except Exception:
            pass
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        videos = []
        try:
            home_data = self._request("/app/home?page=1&pageSize=20")
            for item in (home_data or {}).get("latest") or []:
                v = self._vod_from_item(item)
                if v:
                    videos.append(v)
        except Exception:
            pass
        return {"page": 1, "pagecount": 1, "limit": 20, "total": len(videos), "list": videos}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        params = [("category_id", tid), ("page", str(page)), ("pageSize", "20")]
        if isinstance(extend, dict):
            for k, v in extend.items():
                if v:
                    params.append((k, v))
        videos = []
        total = 0
        pagecount = page
        try:
            data = self._request("/app/filter?" + up.urlencode(params)) or {}
            for item in data.get("list") or []:
                v = self._vod_from_item(item)
                if v:
                    videos.append(v)
            has_more = data.get("hasMore")
            total = data.get("total") or 0
            if isinstance(has_more, bool):
                pagecount = page + 1 if has_more else page
            elif total:
                pagecount = (int(total) + 19) // 20
            else:
                pagecount = page + 1 if len(videos) >= 20 else page
            if not total:
                total = len(videos) + (page - 1) * 20
        except Exception:
            pass
        return {"page": page, "pagecount": max(page, pagecount), "limit": 20,
                "total": total, "list": videos}

    def searchContent(self, key, pg=False):
        page = 1
        if isinstance(pg, bool):
            page = 1
        elif isinstance(pg, int):
            page = pg if pg > 0 else 1
        elif isinstance(pg, str) and pg.isdigit():
            page = int(pg) or 1
        videos = []
        pagecount = 1
        try:
            url = "/app/search?" + up.urlencode([("q", key), ("page", str(page)), ("pageSize", "20")])
            data = self._request(url) or {}
            for item in data.get("list") or []:
                v = self._vod_from_item(item)
                if v:
                    videos.append(v)
            if data.get("hasMore"):
                pagecount = page + 1
        except Exception:
            pass
        return {"page": page, "pagecount": pagecount, "limit": 20,
                "total": len(videos), "list": videos}

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        elif not isinstance(ids, (list, tuple)):
            ids = [str(ids)]
        results = []
        for vid in ids:
            try:
                detail = self._request("/app/dramas/" + str(vid))
                if not detail:
                    continue
                title = self.desensitize(detail.get("title", ""))
                if self._is_minor(title):
                    continue
                eps_data = self._request("/app/dramas/" + str(vid) + "/episodes")
                play_list = []
                for ep in (eps_data or {}).get("list") or []:
                    ep_no = ep.get("ep")
                    ep_title = self.desensitize(ep.get("title", "第" + str(ep_no) + "集"))
                    ep_title = ep_title + self._ep_suffix(ep)
                    play_list.append(ep_title + "$" + str(ep["id"]))
                    self.ep_index[str(ep["id"])] = (str(detail.get("id", vid)), int(ep_no or 0))
                cat_name = ""
                if detail.get("category"):
                    cat_name = self.desensitize(detail["category"].get("name", ""))
                results.append({
                    "vod_id": str(detail.get("id", "")),
                    "vod_name": title,
                    "vod_pic": self._fix_cover(detail.get("cover", "")),
                    "vod_remarks": detail.get("remarks", "") or detail.get("status_text", ""),
                    "vod_year": detail.get("year", ""),
                    "vod_area": "",
                    "vod_author": "",
                    "vod_content": self.desensitize(detail.get("description", "") or title),
                    "vod_play_from": "黄果漫剧",
                    "vod_play_url": "#".join(play_list),
                    "type_name": cat_name,
                })
            except Exception:
                continue
        return {"list": results}

    def playerContent(self, flag, id, vipFlags):
        eid = str(id).split("#")[0].strip()
        data = None
        try:
            data = self._request("/app/play/" + eid)
        except Exception:
            data = None

        if data and data.get("can_play") and data.get("play_url"):
            return {
                "parse": 0,
                "jx": 0,
                "url": data["play_url"],
                "header": {
                    "User-Agent": self.ua,
                    "Referer": "https://google.huge1-7wnjsk.com/",
                },
                "format": "application/x-mpegURL",
            }

        if self.VIP_FALLBACK:
            drama_id = (data or {}).get("drama_id")
            ep_no = (data or {}).get("ep")
            if not drama_id or not ep_no:
                info = self.ep_index.get(eid)
                if info:
                    drama_id, ep_no = info
            if drama_id and ep_no:
                try:
                    url = self._vip_url(drama_id, ep_no)
                except Exception:
                    url = ""
                if url:
                    return {
                        "parse": 0,
                        "jx": 0,
                        "url": url,
                        "header": {"User-Agent": self.ua},
                        "format": "application/x-mpegURL",
                    }

        return {"parse": 0, "jx": 0, "url": "", "header": {}}

    def localProxy(self, param):
        try:
            if not param:
                return [404, "text/plain", ""]
            url = param
            if param.startswith("cover/"):
                url = self.img_base + "/storage/series/" + param[6:]
            req = ur.Request(url)
            req.add_header("User-Agent", self.ua)
            req.add_header("Referer", "https://google.huge1-7wnjsk.com/")
            resp = ur.urlopen(req, timeout=8)
            content = resp.read()
            ctype = resp.headers.get("Content-Type", "image/jpeg")
            return [200, ctype, content]
        except Exception:
            return [404, "text/plain", ""]

if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("黄果漫剧脚本测试通过！")
