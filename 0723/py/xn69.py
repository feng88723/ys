import base64
import gzip
import http.cookiejar
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import zlib

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):

    def init(self, extend=""):
        self.site_url = "https://xn--69-6tia3cb.net"
        self.cookie_jar = http.cookiejar.CookieJar()

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=ctx)
        )

    def _fetch(self, url, headers=None, data=None, timeout=15):
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate"
        }
        if headers:
            req_headers.update(headers)

        post_bytes = None
        if data is not None:
            if isinstance(data, (dict, list)):
                post_bytes = json.dumps(data).encode("utf-8")
                if "Content-Type" not in req_headers:
                    req_headers["Content-Type"] = "application/json;charset=UTF-8"
            elif isinstance(data, str):
                post_bytes = data.encode("utf-8")
            elif isinstance(data, bytes):
                post_bytes = data

        req = urllib.request.Request(url, data=post_bytes, headers=req_headers)
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                final_url = resp.geturl()
                status_code = resp.getcode()
                raw = resp.read()
                encoding = resp.headers.get("Content-Encoding", "").lower()
                if "gzip" in encoding:
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                elif "deflate" in encoding:
                    try:
                        raw = zlib.decompress(raw)
                    except Exception:
                        pass
                try:
                    html_text = raw.decode("utf-8")
                except Exception:
                    html_text = raw.decode("gbk", errors="ignore")
                return {
                    "code": status_code,
                    "final_url": final_url,
                    "html": html_text,
                    "headers": dict(resp.headers)
                }
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_raw = e.read()
                err_body = err_raw.decode("utf-8", errors="ignore")
            except Exception:
                pass
            return {
                "code": e.code,
                "error": str(e),
                "final_url": url,
                "html": err_body,
                "headers": dict(e.headers) if hasattr(e, "headers") else {}
            }
        except Exception as e:
            return {
                "code": 0,
                "error": str(e),
                "final_url": url,
                "html": "",
                "headers": {}
            }

    def _parse_card_list(self, html):
        cards = []
        card_blocks = re.findall(r'<div[^>]*data-post-id=["\']\d+["\'][^>]*class=["\'][^"\']*loop-video[^"\']*["\'][^>]*>.*?(?=<div[^>]*data-post-id=|<nav[^>]*pagination|<footer>|$)', html, re.S)

        if not card_blocks:
            card_blocks = re.findall(r'<div[^>]*class=["\'][^"\']*loop-video[^"\']*["\'][^>]*>.*?(?=<div[^>]*class=["\'][^"\']*loop-video|<nav[^>]*pagination|<footer>|$)', html, re.S)

        for block in card_blocks:
            if "hot-video-loop" in block or "swiper-slide" in block:
                continue

            href_match = re.search(r'<a[^>]*class=["\']post-video["\'][^>]*href=["\']([^"\']+)["\']', block)
            if not href_match:
                href_match = re.search(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\']post-video["\']', block)
            if not href_match:
                continue
            detail_url = href_match.group(1).strip()

            title_match = re.search(r'title=["\']([^"\']+)["\']', block)
            title = title_match.group(1).strip() if title_match else ""
            if not title:
                alt_match = re.search(r'alt=["\']([^"\']+)["\']', block)
                title = alt_match.group(1).strip() if alt_match else "无标题"

            img_match = re.search(r'<img[^>]*data-src=["\']([^"\']+)["\']', block)
            if not img_match:
                img_match = re.search(r'<img[^>]*data-default-src=["\']([^"\']+)["\']', block)
            if not img_match:
                img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', block)
            pic = img_match.group(1).strip() if img_match else ""
            if pic.startswith("//"):
                pic = "https:" + pic
            elif pic.startswith("/"):
                pic = self.site_url + pic

            dur_match = re.search(r'class=["\']post-duration["\'][^>]*>\s*<span>(.*?)</span>', block, re.S)
            duration = dur_match.group(1).strip() if dur_match else ""

            view_match = re.search(r'class=["\']post-views["\'][^>]*>.*?<span>(.*?)</span>', block, re.S)
            views = view_match.group(1).strip() if view_match else ""

            if duration and views:
                remarks = "蝴蝶影视 | %s · %s" % (duration, views)
            elif duration:
                remarks = "蝴蝶影视 | %s" % duration
            elif views:
                remarks = "蝴蝶影视 | %s" % views
            else:
                remarks = "蝴蝶影视"

            cards.append({
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })
        return cards

    def homeContent(self, filter):
        classes = [
            {"type_id": "คลิปหลุด", "type_name": "偷拍泄密"},
            {"type_id": "onlyfans", "type_name": "OnlyFans"},
            {"type_id": "mlive", "type_name": "Mlive直播"},
            {"type_id": "thlive", "type_name": "THLive直播"},
            {"type_id": "jav", "type_name": "日本JAV"},
            {"type_id": "xxx", "type_name": "欧美XXX"},
            {"type_id": "หนังโป๊ไทย", "type_name": "泰国本土"},
            {"type_id": "เอวีจีน", "type_name": "华人AV"},
            {"type_id": "ห้องเชือด", "type_name": "私房约炮"}
        ]
        return {
            "class": classes,
            "filters": {},
            "style": {"type": "rect", "ratio": 1.78}
        }

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page == 1:
            url = "%s/category/%s/" % (self.site_url, urllib.parse.quote(tid))
        else:
            url = "%s/category/%s/page/%d/" % (self.site_url, urllib.parse.quote(tid), page)

        resp = self._fetch(url, headers={"Referer": self.site_url + "/"})
        html = resp.get("html", "")
        cards = self._parse_card_list(html)

        has_next = ('class="pagination-next"' in html) or ('/page/%d/' % (page + 1) in html)
        total_pages = page + 1 if has_next else page

        return {
            "page": page,
            "pagecount": total_pages,
            "limit": 20,
            "total": total_pages * 20,
            "style": {"type": "rect", "ratio": 1.78},
            "list": cards
        }

    def detailContent(self, ids):
        detail_url = ids[0] if isinstance(ids, list) else ids

        resp = self._fetch(detail_url, headers={"Referer": self.site_url + "/"})
        html = resp.get("html", "")

        og_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html)
        if og_match:
            title = og_match.group(1).strip()
        else:
            t_match = re.search(r'<title>(.*?)</title>', html, re.S)
            title = t_match.group(1).strip() if t_match else "正片播放"

        title = re.sub(r'\s*-\s*หี.*$', '', title, flags=re.IGNORECASE).strip()

        img_match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
        pic = img_match.group(1).strip() if img_match else ""

        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        iframe_url = iframe_match.group(1).strip() if iframe_match else ""

        vod_play_url = "正片$%s" % (iframe_url if iframe_url else detail_url)

        vod = {
            "vod_id": detail_url,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "蝴蝶影视",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "蝴蝶影视",
            "vod_actor": "🦋 TG群: @tvshare23",
            "vod_director": "🦋 蝴蝶影视",
            "vod_content": "🦋 官方交流TG群: @tvshare23 | 严禁盗链贩卖。已接入原盘高清直链秒播。",
            "vod_play_from": "蝴蝶专线",
            "vod_play_url": vod_play_url
        }

        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        target_url = id
        play_url = ""
        player_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://lumierecore.com/",
            "Origin": "https://lumierecore.com"
        }

        resp = self._fetch(target_url, headers={"Referer": self.site_url + "/"})
        html = resp.get("html", "")

        config_match = re.search(r'<script[^>]+src=["\']([^"\']*player-config/v2/[^"\']+)["\']', html)
        if config_match:
            config_url = config_match.group(1)
            if config_url.startswith("//"):
                config_url = "https:" + config_url
            elif config_url.startswith("/"):
                config_url = "https://lumierecore.com" + config_url

            cfg_resp = self._fetch(config_url, headers={"Referer": target_url})
            cfg_js = cfg_resp.get("html", "")

            p2p_token = ""
            p2p_match = re.search(r'p2p=([a-f0-9]+)', config_url)
            if p2p_match:
                p2p_token = p2p_match.group(1)

            proxy_api_match = re.search(r'PLAYER_PROXY_SELECTION_URL\s*=\s*["\']([^"\']+)["\']', cfg_js)
            if proxy_api_match:
                proxy_url = proxy_api_match.group(1).replace("\\/", "/")
                post_headers = {
                    "User-Agent": player_headers["User-Agent"],
                    "Referer": target_url,
                    "Origin": "https://lumierecore.com",
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json;charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest"
                }

                payload = {"p2p": p2p_token} if p2p_token else {}
                post_resp = self._fetch(proxy_url, headers=post_headers, data=payload)
                if post_resp.get("code") == 200 and post_resp.get("html"):
                    try:
                        res_json = json.loads(post_resp.get("html"))
                        if "masterUrl" in res_json and res_json["masterUrl"].startswith("http"):
                            play_url = res_json["masterUrl"]
                        elif "url" in res_json and res_json["url"].startswith("http"):
                            play_url = res_json["url"]
                        elif "file" in res_json and res_json["file"].startswith("http"):
                            play_url = res_json["file"]
                    except Exception:
                        pass

                    if not play_url:
                        m_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', post_resp.get("html"))
                        if m_matches:
                            play_url = m_matches[0]

        if not play_url:
            return {
                "parse": 1,
                "url": target_url,
                "header": player_headers
            }

        return {
            "parse": 0,
            "url": play_url,
            "header": player_headers
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        if page == 1:
            url = "%s/?s=%s" % (self.site_url, urllib.parse.quote(key))
        else:
            url = "%s/page/%d/?s=%s" % (self.site_url, page, urllib.parse.quote(key))

        resp = self._fetch(url, headers={"Referer": self.site_url + "/"})
        html = resp.get("html", "")
        cards = self._parse_card_list(html)

        has_next = ('class="pagination-next"' in html) or ('/page/%d/' % (page + 1) in html)
        total_pages = page + 1 if has_next else page

        return {
            "page": page,
            "pagecount": total_pages,
            "limit": 20,
            "total": total_pages * 20,
            "style": {"type": "rect", "ratio": 1.78},
            "list": cards
        }

    def action(self, action):
        return ""

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        return False

    def destroy(self):
        pass