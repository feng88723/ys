# coding=utf-8
try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        def getName(self): return ""
        def init(self, extend=""): pass
        def homeContent(self, filter=None): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter=None, extend=None): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick=False, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags=None): return {}
        def localProxy(self, param): return [404, "text/plain", ""]
        def getDependence(self): return ""
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False

import re, json, time, hashlib, urllib.request
from urllib.parse import quote, urlencode

class Spider(BaseSpider):
    def getName(self):
        return "香蕉短剧"

    def init(self, extend=""):
        self.host = "https://xjai1.com"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.token = None
        self.device_id = "tvbox-" + hashlib.md5(b"xjai-banana-device").hexdigest()[:16]
        self._ensure_guest()
        # 跳过可能敏感分类
        self.skip_slugs = {"xiaoyuanqingchun"}

    def getDependence(self):
        return ""

    def _headers(self, auth=True):
        h = {
            "User-Agent": self.ua,
            "Accept": "application/json",
            "Referer": self.host + "/",
            "Origin": self.host,
        }
        if auth and self.token:
            h["Authorization"] = "Bearer " + self.token
        return h

    def _ensure_guest(self):
        try:
            data = json.dumps({"device_id": self.device_id}).encode()
            req = urllib.request.Request(
                self.host + "/api/guest-sessions",
                data=data,
                headers={**self._headers(False), "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                body = json.loads(resp.read().decode())
            self.token = (body.get("data") or {}).get("access_token")
        except Exception:
            self.token = None

    def _api(self, path, method="GET", data=None, retry=1):
        if not self.token:
            self._ensure_guest()
        for i in range(retry + 1):
            try:
                body = None
                headers = self._headers(True)
                if data is not None:
                    body = json.dumps(data).encode()
                    headers["Content-Type"] = "application/json"
                req = urllib.request.Request(
                    self.host + path, data=body, headers=headers, method=method
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e:
                code = getattr(e, "code", None)
                if code in (401, 403) and i < retry:
                    self._ensure_guest()
                    continue
                return None
        return None

    def homeContent(self, filter=None):
        data = self._api("/api/categories") or {}
        cats = data.get("data") or []
        classes = []
        for c in cats:
            slug = c.get("slug") or ""
            if slug in self.skip_slugs:
                continue
            classes.append({
                "type_id": c.get("id") or slug,
                "type_name": c.get("name") or slug,
            })
        # 加一个全部
        classes.insert(0, {"type_id": "all", "type_name": "全部热门"})
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self.categoryContent("all", "1")

    def categoryContent(self, tid, pg, filter=None, extend=None):
        pg = int(pg or 1)
        if tid == "all" or not tid:
            path = "/api/theater"
            if pg > 1:
                # theater uses cursor; approximate with rankings/hot for page1 only
                path = "/api/theater"
            data = self._api(path) or {}
        else:
            path = f"/api/theater?category_id={quote(str(tid))}"
            data = self._api(path) or {}
        items = ((data.get("data") or {}).get("items")) or []
        videos = []
        for it in items:
            videos.append({
                "vod_id": it.get("id"),
                "vod_name": it.get("title") or "",
                "vod_pic": it.get("cover_url") or "",
                "vod_remarks": f"{it.get('episode_count') or 0}集",
            })
        # theater 单页约50，无稳定翻页时 pagecount 按有无 next_cursor
        has_more = bool((data.get("data") or {}).get("next_cursor"))
        pagecount = pg + 1 if has_more else pg
        return {
            "page": pg,
            "pagecount": max(pagecount, 1),
            "limit": len(videos) or 50,
            "total": (data.get("data") or {}).get("total") or len(videos),
            "list": videos,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        did = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        detail = self._api(f"/api/dramas/{did}") or {}
        d = detail.get("data") or {}
        eps_data = self._api(f"/api/dramas/{did}/episodes") or {}
        eps = eps_data.get("data") or []
        # 只列可播放（免费/已拥有）
        playable = []
        for e in eps:
            c = e.get("commerce") or {}
            if c.get("can_play") is False and c.get("reason") == "purchase_required":
                # 仍尝试 free 全集；付费集也列出，播放时再判断
                pass
            playable.append(e)
        if not playable:
            playable = eps
        name = d.get("title") or f"短剧{did}"
        pic = d.get("cover_url") or ""
        parts = []
        for e in playable:
            en = e.get("episode_number") or e.get("title") or ""
            eid = e.get("id")
            # player id: drama_id|episode_id
            parts.append(f"第{en}集${did}|{eid}")
        play_url = "#".join(parts) if parts else f"正片${did}"
        remarks = f"{d.get('episode_count') or len(eps)}集"
        return {
            "list": [{
                "vod_id": did,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": d.get("description") or name,
                "vod_remarks": remarks,
                "vod_play_from": "线路1",
                "vod_play_url": play_url,
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        q = quote(key)
        data = self._api(f"/api/search?q={q}") or {}
        items = ((data.get("data") or {}).get("items")) or []
        videos = []
        for it in items:
            if it.get("type") and it.get("type") != "drama":
                continue
            videos.append({
                "vod_id": it.get("id"),
                "vod_name": it.get("title") or "",
                "vod_pic": it.get("cover_url") or "",
                "vod_remarks": it.get("subtitle") or "",
            })
        return {"list": videos, "page": int(pg or 1), "pagecount": 1, "limit": 40, "total": len(videos)}

    def _get_play_url(self, drama_id, episode_id):
        if not episode_id:
            # 取第一集
            eps = (self._api(f"/api/dramas/{drama_id}/episodes") or {}).get("data") or []
            if not eps:
                return ""
            episode_id = eps[0].get("id")
        sess = self._api("/api/playback/sessions", method="POST", data={"episode_id": episode_id}, retry=1)
        if not sess:
            self._ensure_guest()
            sess = self._api("/api/playback/sessions", method="POST", data={"episode_id": episode_id}, retry=1)
        media = ((sess or {}).get("data") or {}).get("media") or {}
        return media.get("manifest_url") or ""

    def playerContent(self, flag, id, vipFlags=None):
        raw = id or ""
        drama_id, episode_id = "", ""
        if "|" in raw:
            drama_id, episode_id = raw.split("|", 1)
        elif raw.startswith("http"):
            return {
                "parse": 0, "jx": 0, "url": raw,
                "header": {"User-Agent": self.ua, "Referer": self.host + "/"},
            }
        else:
            drama_id = raw
        url = self._get_play_url(drama_id, episode_id)
        header = {
            "User-Agent": self.ua,
            "Referer": self.host + "/",
            "Origin": self.host,
        }
        if not url:
            return {"parse": 0, "jx": 0, "url": "", "header": header, "message": "需要会员或购买，或暂不可播"}
        # 直链 m3u8 已绝对路径，一般可不走 proxy；仍给 proxy 兼容
        if hasattr(self, "getProxyUrl") and self.getProxyUrl():
            base = self.getProxyUrl()
            if "?" in base:
                proxy = base + "&url=" + quote(url) + "&type=m3u8"
            else:
                proxy = base + "?url=" + quote(url) + "&type=m3u8"
            return {"parse": 0, "jx": 0, "url": proxy, "header": header}
        return {"parse": 0, "jx": 0, "url": url, "header": header}

    def localProxy(self, param):
        try:
            url = param.get("url") if isinstance(param, dict) else str(param or "")
            if not url:
                return [404, "text/plain", ""]
            req = urllib.request.Request(url, headers={
                "User-Agent": self.ua,
                "Referer": self.host + "/",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8", "ignore")
            # 已是绝对 ts/key，原样返回
            return [200, "application/vnd.apple.mpegurl", body]
        except Exception as e:
            return [500, "text/plain", str(e)[:200]]

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False
