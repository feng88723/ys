# -*- coding: utf-8 -*-
# ============================================================
# 适配 https://y1e5egkh.x8t5h2vn.buzz 的 TVBox 爬虫脚本
# 网站：麻豆TV (自研CMS)
# 功能：首页 / 分类 / 详情 / 播放 / 搜索
# ============================================================

import re
import json
import html
import urllib.request
import urllib.parse
import ssl
from urllib.parse import urljoin, quote, unquote

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): pass
        def homeVideoContent(self): pass
        def categoryContent(self, tid, pg, filter, extend): pass
        def detailContent(self, ids): pass
        def playerContent(self, flag, id, vipFlags=None): pass
        def searchContent(self, key, quick, pg='1'): pass
        def isVideoFormat(self, url): pass
        def manualVideoCheck(self): pass
        def localProxy(self, param): pass


def clean_text(text):
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fix_url(url, host):
    if not url:
        return ""
    url = url.strip()
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        return urljoin(host, url)
    if url.startswith(('http://', 'https://')):
        return url
    return urljoin(host, '/' + url)


class Spider(BaseSpider):

    def __init__(self):
        super().__init__()
        self.host = "https://y1e5egkh.x8t5h2vn.buzz"
        self.name = "madou_spider"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def init(self, extend=""):
        if extend and extend.startswith("http"):
            self.host = extend.rstrip("/")

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return any(x in url for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "video/MP2T", b"", {}]

    def _fetch(self, url, referer=None):
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.host, url)

        try:
            headers = {"User-Agent": self.user_agent}
            if referer:
                headers["Referer"] = referer

            req = urllib.request.Request(url, headers=headers)
            r = urllib.request.urlopen(req, timeout=15)
            return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[{self.name}] 请求失败: {e}")
            return ""

    # ============================================================
    # 解析视频列表 (修复标题提取)
    # ============================================================

    def _parse_video_items(self, html_text):
        """从HTML中解析视频列表项"""
        if not html_text:
            return []

        videos = []
        
        # 匹配 .z-video-item 中的视频信息
        # 从 a 标签提取 href 和 title，从 img 提取 src，从 h3 提取标题
        pattern = r'<div[^>]*class="[^"]*z-video-item[^"]*"[^>]*>.*?<a[^>]*href="/maoplay/([^"]+)/"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*alt="[^"]*"[^>]*>.*?<h3[^>]*class="[^"]*z-video-title[^"]*"[^>]*>(.*?)</h3>'
        matches = re.findall(pattern, html_text, re.DOTALL)
        
        if not matches:
            # 备用：更宽松的匹配
            pattern_simple = r'<a[^>]*href="/maoplay/([^"]+)/"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*>.*?<h3[^>]*>(.*?)</h3>'
            matches_simple = re.findall(pattern_simple, html_text, re.DOTALL)
            for vid, pic, title in matches_simple:
                vid = vid.strip()
                title = clean_text(title)
                pic = fix_url(pic, self.host)
                if vid and title:
                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": ""
                    })
            print(f"[_parse_video_items] 备用匹配到 {len(videos)} 个视频项")
            return videos
        
        print(f"[_parse_video_items] 匹配到 {len(matches)} 个视频项")
        
        for match in matches:
            try:
                if len(match) == 4:
                    vid, title_attr, pic, title_h3 = match
                    # 优先使用 h3 中的标题，其次使用 a 标签的 title 属性
                    title = clean_text(title_h3 or title_attr)
                    pic = fix_url(pic, self.host)
                    
                    if vid and title:
                        videos.append({
                            "vod_id": vid.strip(),
                            "vod_name": title,
                            "vod_pic": pic,
                            "vod_remarks": ""
                        })
            except Exception as e:
                print(f"解析单个视频失败: {e}")
                continue
        
        return videos

    # ============================================================
    # 首页分类
    # ============================================================

    def homeContent(self, filter):
        classes = [
            {"type_id": "20", "type_name": "91国产"},
            {"type_id": "21", "type_name": "日本无码"},
            {"type_id": "22", "type_name": "日本有码"},
            {"type_id": "23", "type_name": "中文字幕"},
            {"type_id": "24", "type_name": "91三级"},
            {"type_id": "25", "type_name": "巨乳系列"},
            {"type_id": "26", "type_name": "人妻激情"},
            {"type_id": "27", "type_name": "欧美极品"},
            {"type_id": "28", "type_name": "制服诱惑"},
            {"type_id": "29", "type_name": "自拍偷拍"},
            {"type_id": "30", "type_name": "强奸乱伦"},
            {"type_id": "31", "type_name": "人妖视频"},
            {"type_id": "32", "type_name": "绝美少女"},
            {"type_id": "33", "type_name": "首次亮相"},
            {"type_id": "34", "type_name": "HEY诱惑"},
            {"type_id": "35", "type_name": "独家DMM"},
            {"type_id": "36", "type_name": "91主播"},
            {"type_id": "37", "type_name": "日韩精品"},
            {"type_id": "38", "type_name": "激情口交"},
            {"type_id": "39", "type_name": "动漫电影"},
            {"type_id": "40", "type_name": "极骚萝莉"},
            {"type_id": "41", "type_name": "HEYZO"},
            {"type_id": "42", "type_name": "高潮喷吹"},
            {"type_id": "43", "type_name": "自慰颜射"},
        ]
        
        return {
            "class": classes,
            "filters": {}
        }

    # ============================================================
    # 首页推荐视频
    # ============================================================

    def homeVideoContent(self):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}
        html_text = self._fetch("/")
        if html_text:
            result["list"] = self._parse_video_items(html_text)
            result["total"] = len(result["list"])
        return result

    # ============================================================
    # 分类页视频列表
    # ============================================================

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

        if int(pg) <= 1:
            url = f"/maotype/{tid}/"
        else:
            url = f"/maotype/{tid}/page/{pg}/"

        print(f"[{self.name}] 请求分类页: {url}")

        html_text = self._fetch(url)
        if not html_text:
            return result

        videos = self._parse_video_items(html_text)
        result["list"] = videos

        page_info = re.search(r'第\s*\d+\s*/\s*(\d+)\s*页', html_text)
        if page_info:
            result["pagecount"] = int(page_info.group(1))
        else:
            page_links = re.findall(r'/maotype/\d+/page/(\d+)/', html_text)
            if page_links:
                result["pagecount"] = max([int(p) for p in page_links])
            else:
                result["pagecount"] = 1

        result["total"] = len(videos)
        return result

    # ============================================================
    # 播放页 (返回播放页URL)
    # ============================================================

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        result = {"list": []}

        if not vid:
            return result

        # vid格式: 2087696-1-1
        play_url = f"/maoplay/{vid}/"
        
        # 尝试从播放页提取标题
        html_text = self._fetch(play_url)
        title = f"视频 {vid}"
        pic = ""
        
        if html_text:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html_text)
            if title_match:
                title = clean_text(title_match.group(1))

        vod_data = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "默认线路",
            "vod_play_url": f"默认线路${play_url}",
        }

        result["list"].append(vod_data)
        return result

    # ============================================================
    # 播放页解析 (修复：提取 m3u8 地址)
    # ============================================================

    def playerContent(self, flag, id, vipFlags=None):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}

        # 如果id本身就是直链，直接返回
        if self.isVideoFormat(id):
            result["url"] = id
            result["header"] = json.dumps({
                "Referer": self.host + "/",
                "User-Agent": self.user_agent
            })
            return result

        # 如果id是播放页URL，请求并提取
        if not id.startswith('http'):
            id = urljoin(self.host, id)

        print(f"[{self.name}] 请求播放页: {id}")

        html_text = self._fetch(id)
        if not html_text:
            result["url"] = id
            return result

        # 方法1：从 player_aaaa 中提取 url
        # 匹配 var player_aaaa={"flag":"play",...,"url":"https:\/\/...m3u8",...}
        player_pattern = r'player_aaaa\s*=\s*(\{[^}]*"url"\s*:\s*"([^"]+)"[^}]*\})'
        player_match = re.search(player_pattern, html_text)
        
        if player_match:
            try:
                json_str = player_match.group(1).replace('\\/', '/')
                player_data = json.loads(json_str)
                play_url = player_data.get('url', '')
                if play_url and self.isVideoFormat(play_url):
                    result["url"] = play_url
                    result["header"] = json.dumps({
                        "Referer": self.host + "/",
                        "User-Agent": self.user_agent
                    })
                    print(f"[{self.name}] ✅ 从 player_aaaa 提取到播放地址: {play_url}")
                    return result
            except Exception as e:
                print(f"[{self.name}] 解析 player_aaaa 失败: {e}")
                # 如果JSON解析失败，直接用正则提取 url 字段
                url_match = re.search(r'"url"\s*:\s*"([^"]+)"', player_match.group(1))
                if url_match:
                    play_url = url_match.group(1).replace('\\/', '/')
                    if play_url and self.isVideoFormat(play_url):
                        result["url"] = play_url
                        result["header"] = json.dumps({
                            "Referer": self.host + "/",
                            "User-Agent": self.user_agent
                        })
                        print(f"[{self.name}] ✅ 正则提取到播放地址: {play_url}")
                        return result

        # 方法2：直接匹配 m3u8 地址
        m3u8_pattern = r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)'
        m3u8_match = re.search(m3u8_pattern, html_text)
        if m3u8_match:
            play_url = m3u8_match.group(1)
            result["url"] = play_url
            result["header"] = json.dumps({
                "Referer": self.host + "/",
                "User-Agent": self.user_agent
            })
            print(f"[{self.name}] ✅ 直接匹配到 m3u8: {play_url}")
            return result

        print(f"[{self.name}] ❌ 未能提取到播放地址")
        result["url"] = id
        return result

    # ============================================================
    # 搜索功能
    # ============================================================

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
        
        if not key:
            return result

        search_url = f"/vod/search/wd/{quote(key)}/"
        if int(pg) > 1:
            search_url += f"?page={pg}"

        print(f"[{self.name}] 请求搜索: {search_url}")

        html_text = self._fetch(search_url)
        if html_text:
            videos = self._parse_video_items(html_text)
            result["list"] = videos
            result["total"] = len(videos)

            page_info = re.search(r'第\s*\d+\s*/\s*(\d+)\s*页', html_text)
            if page_info:
                result["pagecount"] = int(page_info.group(1))

        return result