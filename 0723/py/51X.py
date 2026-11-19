# -*- coding: utf-8 -*-
# 51xz.vip (51X) TVBox source
# framework: Next.js server-rendered SPA; cards + JSON-LD episode list
# stream chain (direct, no cookie / no referer required):
#   single video  -> https://xvideoapi.datashubcenter.com/media/hls/{videoId}/index.m3u8
#   drama episode -> https://xvideoapi.datashubcenter.com/media/hls/drama/{dramaId}/{epId}/index.m3u8
#   both are AES-128 HLS; key / ts hosted on source.datashubcenter.com
# RE_PATH: / (home), /m/{tag} (category, ?page=N), /video/{id}/{slug} (single),
#          /drama/{id}/{slug} (per-episode url carries ?ep={epId}), /search?q= (search)
# RE_OBSTACLE: anti-bot / cloudflare challenge on datacenter IP -> egress via residential SOCKS5

import re
import gzip
import urllib.parse
import urllib.request
import threading
import concurrent.futures

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        def __init__(self):
            pass

SITE = "https://51xz.vip"
API = "https://xvideoapi.datashubcenter.com"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

RE_CARD = re.compile(
    r'<a class="media-card-link"[^>]*title="([^"]*)"[^>]*href="(/[^"]+)"', re.I)
RE_NAV = re.compile(
    r'<a class="site-nav-sub-link"[^>]*title="([^"]*)"[^>]*href="(/m/[^"]*)"', re.I)
RE_EPI = re.compile(
    r'"@type":"TVEpisode","episodeNumber":(\d+),"name":"[^"]*","url":"[^"]*?ep=([a-z0-9]+)"', re.I)
RE_TITLE = re.compile(r'<title>([^<]*)</title>', re.I)
RE_OGIMG = re.compile(r'og:image" content="([^"]+)"', re.I)
RE_VID = re.compile(r'/(?:video|drama)/([a-z0-9]+)/', re.I)

CARD_PREFIX = "免费观看影片《"
CARD_SUFFIX = "》"


def _clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def _card_name(title):
    t = _clean(title)
    if t.startswith(CARD_PREFIX):
        t = t[len(CARD_PREFIX):]
    if t.endswith(CARD_SUFFIX):
        t = t[:-len(CARD_SUFFIX)]
    return t or "未知"


class Spider(_BaseSpider):
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()

    def getDependence(self):
        return ""

    def getName(self):
        return "51X"

    def init(self, extend=""):
        return ""

    def getCategory(self):
        return ""

    def getFilter(self):
        return {}

    def action(self, action):
        return ""

    def destroy(self):
        with self._lock:
            self._cache.clear()
        return ""

    def localProxy(self, param):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        text = str(url or "").lower()
        return bool(re.search(r"\.(?:m3u8|mp4|mkv|flv|avi|ts)(?:[?#]|$)", text))

    def _fetch(self, url):
        with self._lock:
            cached = self._cache.get(url)
        if cached is not None:
            return cached
        headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": SITE + "/",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                body = raw.decode("utf-8", "ignore")
        except Exception:
            body = ""
        with self._lock:
            self._cache[url] = body
        return body

    def _cards(self, body):
        out = []
        seen = set()
        for m in RE_CARD.finditer(body):
            title, href = m.group(1), m.group(2).strip()
            if href in seen:
                continue
            seen.add(href)
            out.append({
                "vod_id": SITE + href,
                "vod_name": _card_name(title),
                "vod_pic": "",
                "vod_remarks": "",
            })
        return out

    def homeContent(self, *args):
        body = self._fetch(SITE + "/")
        classes = []
        for m in RE_NAV.finditer(body):
            name, href = m.group(1), m.group(2).strip()
            tid = urllib.parse.quote(href[3:])  # strip leading "/m/"
            classes.append({"type_id": tid, "type_name": name})
        vods = self._cards(body)
        return {
            "class": classes,
            "list": vods,
            "page": 1,
            "pagecount": 999,
            "limit": len(vods),
            "total": 9999,
        }

    def categoryContent(self, tid, pg, filter, extend, *args):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        url = "%s/m/%s?page=%d" % (SITE, tid, pg)
        vods = self._cards(self._fetch(url))
        return {"list": vods, "page": pg, "pagecount": 999, "limit": len(vods), "total": 9999}

    def _detail_one(self, vid):
        url = vid if vid.startswith("http") else (SITE + vid if vid.startswith("/") else SITE + "/" + vid)
        body = self._fetch(url)
        tm = RE_TITLE.search(body)
        name = _clean(tm.group(1).split(" · ")[0]) if tm else "未知"
        pm = RE_OGIMG.search(body)
        pic = pm.group(1) if pm else ""
        idm = RE_VID.search(url)
        mid = idm.group(1) if idm else ""
        if "/drama/" in url:
            eps = []
            for m in RE_EPI.finditer(body):
                num = int(m.group(1))
                m3u8 = "%s/media/hls/drama/%s/%s/index.m3u8" % (API, mid, m.group(2))
                eps.append((num, "第%d集" % num, m3u8))
            eps.sort()
            play_url = "#".join("%s$%s" % (lbl, u) for _, lbl, u in eps)
            remarks = "共%d集" % len(eps)
        else:
            m3u8 = "%s/media/hls/%s/index.m3u8" % (API, mid)
            play_url = "高清$%s" % m3u8
            remarks = "单集"
        if not play_url:
            return None
        return {
            "vod_id": url,
            "vod_name": name,
            "vod_pic": pic,
            "vod_play_from": "51X",
            "vod_play_url": play_url,
            "vod_remarks": remarks,
        }

    def detailContent(self, ids, *args):
        out = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            for r in ex.map(self._detail_one, ids):
                if r:
                    out.append(r)
        return {"list": out, "page": 1, "pagecount": 1, "limit": len(out), "total": len(out)}

    def playerContent(self, flag, id, vipFlags, *args):
        return {"parse": 0, "url": id if str(id).startswith("http") else SITE + id}

    def searchContent(self, key, quick=False, pg=1, *args):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        q = urllib.parse.quote(key)
        url = "%s/search?q=%s&page=%d" % (SITE, q, pg)
        vods = self._cards(self._fetch(url))
        return {"list": vods, "page": pg, "pagecount": 999, "limit": len(vods), "total": 9999}
