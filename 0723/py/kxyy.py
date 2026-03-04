# coding=utf-8
#!/usr/bin/python

"""
内容均从互联网收集而来 仅供交流学习使用 严禁用于商业用途 请于24小时内删除
"""

import sys
import json
import re
import urllib.parse
import requests

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def getName(self):
        return "开心影院"

    def init(self, extend=""):
        self.host = "https://www.kxyytv.com"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host,
        }
        self.classes = []
        self.filters = {}
        self.home_videos = None
        self._load_config()
        print(f"[开心影院] 初始化完成, 分类: {len(self.classes)}")
    
    def _load_config(self):
        """加载分类配置"""
        self.classes = [
            {'type_id': 'dianshiju', 'type_name': '电视剧'},
            {'type_id': 'dianying', 'type_name': '电影'},
            {'type_id': 'duanju', 'type_name': '短剧'},
            {'type_id': 'zongyi', 'type_name': '综艺'},
            {'type_id': 'dongman', 'type_name': '动漫'},
        ]

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        """首页内容"""
        result = {}
        result['class'] = self.classes
        result['filters'] = self.filters
        
        if self.home_videos is not None:
            result['list'] = self.home_videos
            return result
        
        try:
            videos = self._fetch_category_videos('dianshiju', '1', {})
            self.home_videos = videos
            result['list'] = videos
        except Exception as e:
            print(f"[开心影院] Home content error: {e}")
            result['list'] = []
            
        return result

    def homeVideoContent(self):
        return {'list': self.home_videos or []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类视频列表"""
        result = {}
        try:
            videos = self._fetch_category_videos(tid, pg, extend)
            result['list'] = videos
            result['page'] = int(pg)
            result['pagecount'] = 999
            result['limit'] = 84
            result['total'] = 99999
        except Exception as e:
            print(f"[开心影院] Category error: {e}")
            result['list'] = []
        return result

    def detailContent(self, ids):
        """获取视频详情和播放列表"""
        try:
            vid = ids[0]
            url = f"{self.host}/voddetail/{vid}.html"
            print(f"[开心影院] 获取详情: {url}")
            
            res = self.session.get(url, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            title = ''
            m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if m:
                title = re.sub(r'\s*\(\d+\)\s*$', '', m.group(1).strip())
            
            pic = ''
            m = re.search(r'<img[^>]+src="([^"]+)"[^>]+referrerPolicy', html)
            if m:
                pic = m.group(1)
            
            type_name = ''
            m = re.search(r'<strong>类型：</strong>(.*?)</p>', html, re.DOTALL)
            if m:
                types = re.findall(r'>([^<]+)</a>', m.group(1))
                type_name = ','.join(types)
            
            area = ''
            m = re.search(r'<strong>制片国家/地区：</strong>\[([^\]]+)\]', html)
            if m:
                area = m.group(1).strip()
            
            year = ''
            m = re.search(r'\((\d{4})\)', html)
            if m:
                year = m.group(1)
            
            remarks = ''
            m = re.search(r'<span class="text-orange">([^<]+)</span>', html)
            if m:
                remarks = m.group(1).strip()
            
            actor = ''
            m = re.search(r'<strong>主演：</strong>(.*?)</p>', html, re.DOTALL)
            if m:
                actors = re.findall(r'>([^<]+)</a>', m.group(1))
                actor = ','.join(actors[:10])
            
            director = ''
            m = re.search(r'<strong>导演：</strong>(.*?)</p>', html, re.DOTALL)
            if m:
                dirs = re.findall(r'>([^<]+)</a>', m.group(1))
                director = ','.join(dirs)
            
            desc = ''
            m = re.search(r'<div class="card-body"><p>(.*?)</p></div>', html, re.DOTALL)
            if m:
                desc = re.sub(r'<br\s*/?>', '\n', m.group(1).strip())
                desc = re.sub(r'　+', '', desc)
            
            play_from = []
            play_url = []
            
            sources = re.findall(r'<a href="#tabs-home-(\d+)"[^>]*>.*?</svg>\s*([^&<]+)\s*&nbsp;', html, re.DOTALL)
            
            for sid, sname in sources:
                sname = sname.strip()
                pattern = rf'id="tabs-home-{sid}"[^>]*>.*?<div class="(?:btn-group|d-flex)">(.*?)</div>'
                m = re.search(pattern, html, re.DOTALL)
                if m:
                    eps = re.findall(r'href="(/vodplay/[^"]+)"[^>]*>([^<]+)</a>', m.group(1))
                    if eps:
                        play_from.append(sname)
                        ep_list = [f"{ep[1].strip()}${self.host}{ep[0]}" for ep in eps]
                        play_url.append('#'.join(ep_list))
            
            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name,
                'vod_year': year,
                'vod_area': area,
                'vod_remarks': remarks,
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url)
            }
            
            print(f"[开心影院] 详情: {title}, 线路: {len(play_from)}")
            return {'list': [vod]}
            
        except Exception as e:
            print(f"[开心影院] Detail error: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索视频 - 使用无验证码的API接口"""
        result = {'list': [], 'page': 1, 'pagecount': 1, 'limit': 500, 'total': 0}
        try:
            encoded_key = urllib.parse.quote(key)
            search_url = f"{self.host}/index.php/ajax/suggest?mid=1&wd={encoded_key}&limit=500"
            
            print(f"[开心影院] 搜索: {search_url}")
            
            res = self.session.get(search_url, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            
            try:
                data = res.json()
                if data.get('code') == 1 and data.get('list'):
                    videos = []
                    for item in data['list']:
                        videos.append({
                            'vod_id': str(item.get('id', '')),
                            'vod_name': item.get('name', ''),
                            'vod_pic': item.get('pic', '').replace('\\/', '/'),
                            'vod_remarks': ''
                        })
                    result['list'] = videos
                    result['total'] = len(videos)
                    print(f"[开心影院] 搜索到 {len(videos)} 个结果")
            except:
                print("[开心影院] 搜索结果解析失败")
            
        except Exception as e:
            print(f"[开心影院] Search error: {e}")
            
        return result

    def playerContent(self, flag, id, vipFlags):
        """获取播放链接"""
        try:
            print(f"[开心影院] 获取播放: {id}")
            
            res = self.session.get(id, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            m = re.search(r'var\s+player_data\s*=\s*(\{.*?\});', html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    play_url = data.get('url', '').replace('\\/', '/')
                    if play_url:
                        print(f"[开心影院] 播放URL: {play_url[:80]}...")
                        header = {'User-Agent': 'Mozilla/5.0', 'Referer': self.host}
                        if '.m3u8' in play_url or '.mp4' in play_url:
                            return {'parse': 0, 'url': play_url, 'header': header}
                        else:
                            return {'parse': 1, 'url': play_url, 'header': header}
                except:
                    pass
            
            m = re.search(r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"', html)
            if m:
                play_url = m.group(1).replace('\\/', '/')
                return {'parse': 0, 'url': play_url, 'header': {'User-Agent': 'Mozilla/5.0', 'Referer': self.host}}
            
            return {'parse': 1, 'url': id}
            
        except Exception as e:
            print(f"[开心影院] Player error: {e}")
            return {'parse': 1, 'url': id}

    def _fetch_category_videos(self, tid, pg, extend):
        """获取分类视频列表"""
        page = int(pg) if pg else 1
        
        if page == 1:
            url = f"{self.host}/vodtype/{tid}.html"
        else:
            url = f"{self.host}/vodtype/{tid}-{page}.html"
        
        print(f"[开心影院] 获取列表: {url}")
        
        try:
            res = self.session.get(url, headers=self.headers, timeout=15)
            res.encoding = 'utf-8'
            return self._extract_videos_from_html(res.text)
        except Exception as e:
            print(f"[开心影院] Fetch error: {e}")
            return []

    def _extract_videos_from_html(self, html):
        """从HTML提取视频列表"""
        videos = []
        seen = set()
        
        pattern = r'<a[^>]+title="([^"]+)"[^>]+href="/voddetail/(\d+)\.html"[^>]*class="[^"]*cover[^"]*"[^>]*>.*?data-src="([^"]+)"'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for title, vid, pic in matches:
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': title.strip(),
                'vod_pic': pic,
                'vod_remarks': ''
            })
            if len(videos) >= 60:
                break
        
        print(f"[开心影院] 提取视频: {len(videos)} 个")
        return videos

    def localProxy(self, param):
        return None
