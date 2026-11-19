# -*- coding: utf-8 -*-
import gzip
import json
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

SOURCES = {
    "main": "http://api.maiyoux.com:81/mf",
    "backup": "http://api.vipmisss.com:81/xcdsw",
}
SOURCE_ORDER = ["main", "backup"]

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")
TIMEOUT = 15

_plat_cache = {"ts": 0.0, "data": None}
_room_meta = {}


def _fetch(url):
    headers = {"User-Agent": UA}
    if _requests is not None:
        try:
            r = _requests.get(url, headers=headers, timeout=TIMEOUT)
            return r.status_code, r.content
        except Exception:
            pass
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return r.status, raw


def _get_json(path, prefer="main"):
    order = [prefer] + [s for s in SOURCE_ORDER if s != prefer]
    last = None
    for src in order:
        url = SOURCES[src].rstrip("/") + "/" + str(path).lstrip("/")
        try:
            st, raw = _fetch(url)
            if st and st < 400 and raw:
                data = json.loads(raw.decode("utf-8", "ignore"))
                if isinstance(data, dict):
                    return data
        except Exception as e:
            last = e
    if last is not None:
        raise last
    return {}


def _platforms(prefer="main"):
    now = time.time()
    if _plat_cache["data"] is not None and now - _plat_cache["ts"] < 600:
        return _plat_cache["data"]
    data = _get_json("json.txt", prefer)
    out = []
    for p in data.get("pingtai") or []:
        if isinstance(p, dict) and p.get("address") and p.get("title"):
            out.append({"type_id": str(p["address"]), "type_name": str(p["title"]),
                        "pic": str(p.get("xinimg") or ""), "number": str(p.get("Number") or "")})
    if out:
        _plat_cache["ts"] = now
        _plat_cache["data"] = out
    return out


def _rooms(address, prefer="main"):
    data = _get_json(address, prefer)
    out = []
    for r in data.get("zhubo") or []:
        if isinstance(r, dict) and r.get("address"):
            item = {"vod_id": str(r["address"]), "vod_name": str(r.get("title") or "直播"),
                    "vod_pic": str(r.get("img") or ""), "vod_remarks": "直播"}
            out.append(item)
            _room_meta[item["vod_id"]] = item
    return out


def _norm_ids(ids):
    if isinstance(ids, (list, tuple)):
        parts = [str(x) for x in ids]
    else:
        parts = str(ids or "").split(",")
    return [p.strip() for p in parts if p and p.strip()]


def _norm_extend(extend):
    if not extend:
        return {}
    if isinstance(extend, dict):
        return extend
    try:
        out = json.loads(str(extend))
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _norm_pg(pg, default=1):
    try:
        n = int(str(pg))
        return n if n >= 1 else default
    except Exception:
        return default


def _clean_name(s):
    return str(s or "").replace(",", " ").replace("\r", " ").replace("\n", " ").strip()


def _live_text(prefer="main"):
    lines = []
    for p in _platforms(prefer):
        try:
            rooms = _rooms(p["type_id"], prefer)
        except Exception:
            continue
        if not rooms:
            continue
        lines.append(_clean_name(p["type_name"]) + ",#genre#")
        for r in rooms:
            lines.append(_clean_name(r["vod_name"]) + "," + r["vod_id"])
    return "\n".join(lines) + ("\n" if lines else "")


class Spider(BaseSpider):
    def __init__(self):
        self.ext = {}

    def getName(self):
        return "欲火聚合直播"

    def getDependence(self):
        return []

    def init(self, extend=""):
        self.ext = _norm_extend(extend)
        return None

    def destroy(self):
        return None

    def isVideoFormat(self, url=None):
        u = str(url or "").lower()
        return (".m3u8" in u) or (".mp4" in u) or (".flv" in u)

    def manualVideoCheck(self):
        return False

    def action(self, action=None):
        return {}

    def localProxy(self, param=None):
        try:
            p = param
            if isinstance(p, str):
                s = p.strip()
                if s.startswith("{"):
                    try:
                        p = json.loads(s)
                    except Exception:
                        p = dict(urllib.parse.parse_qsl(s))
                else:
                    p = dict(urllib.parse.parse_qsl(s))
            if not isinstance(p, dict):
                p = {}
            src = str(p.get("src") or "main").lower()
            if src not in SOURCES:
                src = "main"
            txt = _live_text(src)
            if not txt:
                return [502, "text/plain; charset=utf-8", "livetext empty", {}]
            return [200, "text/plain; charset=utf-8", txt, {}]
        except Exception:
            return [502, "text/plain; charset=utf-8", "livetext error", {}]

    def homeContent(self, filter=None):
        try:
            cats = _platforms()
        except Exception:
            cats = []
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in cats]
        lst = []
        if cats:
            try:
                lst = _rooms(cats[0]["type_id"])
            except Exception:
                lst = []
        return {"class": classes, "list": lst, "filters": {}}

    def homeVideoContent(self):
        try:
            cats = _platforms()
            if cats:
                return {"list": _rooms(cats[0]["type_id"])}
        except Exception:
            pass
        return {"list": []}

    def categoryContent(self, tid=None, pg=1, filter=None, extend=None):
        pg = _norm_pg(pg)
        if pg > 1 or not tid:
            return {"list": [], "page": pg, "pagecount": pg, "limit": 0, "total": 0}
        try:
            items = _rooms(str(tid))
        except Exception:
            items = []
        return {"list": items, "page": pg, "pagecount": pg,
                "limit": len(items), "total": len(items)}

    def detailContent(self, ids=None):
        vids = _norm_ids(ids)
        if not vids:
            return {"list": []}
        vid = vids[0]
        meta = _room_meta.get(vid) or {}
        name = meta.get("vod_name") or "直播"
        pic = meta.get("vod_pic") or ""
        return {"list": [{"vod_id": vid, "vod_name": name, "vod_pic": pic,
                          "vod_remarks": "直播", "type_name": "直播",
                          "vod_content": name,
                          "vod_play_from": "直播",
                          "vod_play_url": "正片$" + vid}]}

    def searchContent(self, key=None, quick=False, pg="1"):
        kw = str(key or "").strip().lower()
        if not kw:
            return {"list": [], "page": _norm_pg(pg)}
        try:
            cats = _platforms()
        except Exception:
            return {"list": [], "page": _norm_pg(pg)}
        hits, seen = [], set()

        def _add(item):
            if item["vod_id"] not in seen and len(hits) < 60:
                seen.add(item["vod_id"])
                hits.append(item)

        matched = [c for c in cats if kw in c["type_name"].lower()]
        rest = [c for c in cats if c not in matched]
        for c in matched:
            try:
                for r in _rooms(c["type_id"]):
                    _add(r)
            except Exception:
                continue
            if len(hits) >= 60:
                return {"list": hits, "page": _norm_pg(pg)}
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=16) as ex:
                futs = {ex.submit(_rooms, c["type_id"]): c for c in rest}
                try:
                    for f in as_completed(futs, timeout=25):
                        try:
                            rooms = f.result()
                        except Exception:
                            continue
                        for r in rooms:
                            if kw in r["vod_name"].lower():
                                _add(r)
                        if len(hits) >= 60:
                            break
                except Exception:
                    pass
        except Exception:
            for c in rest:
                try:
                    for r in _rooms(c["type_id"]):
                        if kw in r["vod_name"].lower():
                            _add(r)
                except Exception:
                    continue
                if len(hits) >= 60:
                    break
        return {"list": hits, "page": _norm_pg(pg)}

    def playerContent(self, flag=None, id=None, vipFlags=None):
        url = str(id or "")
        if "$" in url and not url.startswith("http"):
            url = url.split("$", 1)[1]
        return {"parse": 0, "jx": 0, "playUrl": "", "url": url,
                "header": {"User-Agent": UA}}
