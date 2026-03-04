# coding=utf-8
# !/usr/bin/python

"""

作者 丢丢喵 内容均从互联网收集而来 仅供交流学习使用 严禁用于商业用途 请于24小时内删除
         ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import urlparse
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
import concurrent.futures
import urllib.request
import urllib.parse
import datetime
import binascii
import requests
import hashlib
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://www.sunnafh.com"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

class Spider(Spider):

    def getName(self):
        return "丢丢喵"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "1", "type_name": "丢丢🌠电影"},
                            {"type_id": "2", "type_name": "丢丢🌠剧集"},
                            {"type_id": "3", "type_name": "丢丢🌠综艺"},
                            {"type_id": "4", "type_name": "丢丢🌠动漫"}],
                  "list": [],
                  "filters": {"1": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "中国大陆", "v": "中国大陆"},
                                              {"n": "中国香港", "v": "中国香港"},
                                              {"n": "中国台湾", "v": "中国台湾"},
                                              {"n": "美国", "v": "美国"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "印度", "v": "印度"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "英国", "v": "英国"},
                                              {"n": "法国", "v": "法国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "类型",
                                    "name": "类型",
                                    "value": [{"n": "喜剧", "v": "22"},
                                              {"n": "动作", "v": "23"},
                                              {"n": "科幻", "v": "30"},
                                              {"n": "爱情", "v": "26"},
                                              {"n": "悬疑", "v": "27"},
                                              {"n": "奇幻", "v": "87"},
                                              {"n": "剧情", "v": "37"},
                                              {"n": "恐怖", "v": "36"},
                                              {"n": "犯罪", "v": "35"},
                                              {"n": "动画", "v": "33"},
                                              {"n": "惊悚", "v": "34"},
                                              {"n": "战争", "v": "25"},
                                              {"n": "冒险", "v": "31"},
                                              {"n": "灾难", "v": "81"},
                                              {"n": "伦理", "v": "83"},
                                              {"n": "其他", "v": "43"}]},
                                    {"key": "语言",
                                    "name": "语言",
                                    "value": [{"n": "国语", "v": "国语"},
                                              {"n": "英语", "v": "英语"},
                                              {"n": "粤语", "v": "粤语"},
                                              {"n": "韩语", "v": "韩语"},
                                              {"n": "日语", "v": "日语"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "上映", "v": "1"},
                                              {"n": "人气", "v": "3"},
                                              {"n": "评分", "v": "4"}]},
                                    {"key": "剧情",
                                    "name": "剧情",
                                    "value": [{"n": "爱情", "v": "爱情"},
                                              {"n": "动作", "v": "动作"},
                                              {"n": "喜剧", "v": "喜剧"},
                                              {"n": "战争", "v": "战争"},
                                              {"n": "科幻", "v": "科幻"},
                                              {"n": "剧情", "v": "剧情"},
                                              {"n": "武侠", "v": "武侠"},
                                              {"n": "冒险", "v": "冒险"},
                                              {"n": "枪战", "v": "枪战"},
                                              {"n": "恐怖", "v": "恐怖"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "2015", "v": "2015"},
                                              {"n": "2014", "v": "2014"},
                                              {"n": "2013", "v": "2013"},
                                              {"n": "2012", "v": "2012"},
                                              {"n": "2011", "v": "2011"},
                                              {"n": "2010", "v": "2010"},
                                              {"n": "2009~2000", "v": "2009~2000"}]}],
                              "2": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "中国大陆", "v": "中国大陆"},
                                              {"n": "中国香港", "v": "中国香港"},
                                              {"n": "中国台湾", "v": "中国台湾"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "美国", "v": "美国"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "类型",
                                    "name": "类型",
                                    "value": [{"n": "国产剧", "v": "14"},
                                              {"n": "欧美剧", "v": "15"},
                                              {"n": "港台剧", "v": "16"},
                                              {"n": "日韩剧", "v": "62"},
                                              {"n": "其他剧", "v": "68"}]},
                                    {"key": "语言",
                                    "name": "语言",
                                    "value": [{"n": "国语", "v": "国语"},
                                              {"n": "英语", "v": "英语"},
                                              {"n": "粤语", "v": "粤语"},
                                              {"n": "韩语", "v": "韩语"},
                                              {"n": "日语", "v": "日语"},
                                              {"n": "泰语", "v": "泰语"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最近", "v": "1"},
                                              {"n": "时间", "v": "2"},
                                              {"n": "人气", "v": "3"},
                                              {"n": "评分", "v": "4"}]},
                                    {"key": "剧情",
                                    "name": "剧情",
                                    "value": [{"n": "古装", "v": "古装"},
                                              {"n": "战争", "v": "战争"},
                                              {"n": "喜剧", "v": "喜剧"},
                                              {"n": "家庭", "v": "家庭"},
                                              {"n": "犯罪", "v": "犯罪"},
                                              {"n": "动作", "v": "动作"},
                                              {"n": "奇幻", "v": "奇幻"},
                                              {"n": "剧情", "v": "剧情"},
                                              {"n": "历史", "v": "历史"},
                                              {"n": "短片", "v": "短片"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "2015", "v": "2015"},
                                              {"n": "2014", "v": "2014"},
                                              {"n": "2013", "v": "2013"},
                                              {"n": "2012", "v": "2012"},
                                              {"n": "2011", "v": "2011"},
                                              {"n": "2010", "v": "2010"}]}],
                              "3": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "中国大陆", "v": "中国大陆"},
                                              {"n": "中国香港", "v": "中国香港"},
                                              {"n": "中国台湾", "v": "中国台湾"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "美国", "v": "美国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "类型",
                                    "name": "类型",
                                    "value": [{"n": "国产综艺", "v": "69"},
                                              {"n": "港台综艺", "v": "70"},
                                              {"n": "日韩综艺", "v": "72"},
                                              {"n": "欧美综艺", "v": "73"}]},
                                    {"key": "语言",
                                    "name": "语言",
                                    "value": [{"n": "国语", "v": "国语"},
                                              {"n": "英语", "v": "英语"},
                                              {"n": "粤语", "v": "粤语"},
                                              {"n": "韩语", "v": "韩语"},
                                              {"n": "日语", "v": "日语"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最近", "v": "1"},
                                              {"n": "时间", "v": "2"},
                                              {"n": "人气", "v": "3"},
                                              {"n": "评分", "v": "4"}]},
                                    {"key": "剧情",
                                    "name": "剧情",
                                    "value": [{"n": "真人秀", "v": "真人秀"},
                                              {"n": "音乐", "v": "音乐"},
                                              {"n": "脱口秀", "v": "脱口秀"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"}]}],
                              "4": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "中国大陆", "v": "中国大陆"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "美国", "v": "美国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "类型",
                                    "name": "类型",
                                    "value": [{"n": "国产动漫", "v": "75"},
                                              {"n": "日韩动漫", "v": "76"},
                                              {"n": "欧美动漫", "v": "77"}]},
                                    {"key": "语言",
                                    "name": "语言",
                                    "value": [{"n": "国语", "v": "国语"},
                                              {"n": "英语", "v": "英语"},
                                              {"n": "粤语", "v": "粤语"},
                                              {"n": "韩语", "v": "韩语"},
                                              {"n": "日语", "v": "日语"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最近", "v": "1"},
                                              {"n": "时间", "v": "2"},
                                              {"n": "人气", "v": "3"},
                                              {"n": "评分", "v": "4"}]},
                                    {"key": "剧情",
                                    "name": "剧情",
                                    "value": [{"n": "喜剧", "v": "喜剧"},
                                              {"n": "科幻", "v": "科幻"},
                                              {"n": "热血", "v": "热血"},
                                              {"n": "冒险", "v": "冒险"},
                                              {"n": "动作", "v": "动作"},
                                              {"n": "运动", "v": "运动"},
                                              {"n": "战争", "v": "战争"},
                                              {"n": "动画", "v": "动画"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "2015", "v": "2015"},
                                              {"n": "2014", "v": "2014"},
                                              {"n": "2013", "v": "2013"},
                                              {"n": "2012", "v": "2012"},
                                              {"n": "2011", "v": "2011"},
                                              {"n": "2010", "v": "2010"}]}]}}

        return result

    def homeVideoContent(self):
        res = self.get_home_page()
        raw_json_str = self.extract_raw_json(res)
        clean_str = self.clean_json_string(raw_json_str)
        data = self.parse_json(clean_str)
        content_dict = self.get_content_dict(data)
        videos = self.process_content_sections(content_dict)
        result = self.build_home_video_result(videos)
        return result

    def get_home_page(self):
        detail = requests.get(url=xurl, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def extract_raw_json(self, res):
        pattern = r'self\.__next_f\.push\(\[1,"6:(.*?)"\]\)'
        match = re.search(pattern, res, re.S)
        return match.group(1)

    def clean_json_string(self, raw_json_str):
        return json.loads(f'"{raw_json_str}"')

    def parse_json(self, clean_str):
        return json.loads(clean_str)

    def get_content_dict(self, data):
        return data[3]['children'][3]['data']['data']

    def process_content_sections(self, content_dict):
        videos = []
        for key in content_dict:
            section = content_dict[key]
            if isinstance(section, dict) and 'list' in section:
                for vod in section['list']:
                    video = self.parse_video_info(vod)
                    videos.append(video)
        return videos

    def build_home_video_result(self, videos):
        return {'list': videos}

    def categoryContent(self, cid, pg, filter, ext):
        page = self.get_page_number(pg)
        NdType = self.get_ext_value(ext, '年代')
        DqType = self.get_ext_value(ext, '地区')
        LxType = self.get_ext_value(ext, '类型')
        JqType = self.get_ext_value(ext, '剧情')
        YyType = self.get_ext_value(ext, '语言')
        LbType = self.get_ext_value(ext, '列表')
        url_2 = self.build_category_url(cid, LxType, JqType, DqType, NdType, YyType, LbType, page)
        res = self.get_category_page(url_2)
        raw_json_str = self.extract_raw_json(res)
        clean_str = self.clean_json_string(raw_json_str)
        data = self.parse_json(clean_str)
        videos = self.process_video_list(data)
        result = self.build_category_result(videos, pg)
        return result

    def get_page_number(self, pg):
        return int(pg) if pg else 1

    def get_ext_value(self, ext, key):
        return ext[key] if key in ext else ''

    def build_category_url(self, cid, LxType, JqType, DqType, NdType, YyType, LbType, page):
        base_url = f"{xurl}/vod/show"
        data_missing_class = {'id': cid, 'type': LxType, 'class': JqType, 'area': DqType, 'year': NdType, 'lang': YyType, 'sortType': LbType, 'page': page}
        keys_order = ['id', 'type', 'class', 'area', 'year', 'lang', 'sortType', 'page']
        url_parts = [base_url]
        for key in keys_order:
            value = data_missing_class.get(key)
            if value and str(value) not in ['']:
                url_parts.append(f"{key}/{quote(str(value))}")
        return "/".join(url_parts)

    def get_category_page(self, url_2):
        detail = requests.get(url=url_2, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def extract_raw_json(self, res):
        pattern = r'self\.__next_f\.push\(\[1,"6:(.*?)"\]\)'
        match = re.search(pattern, res, re.S)
        return match.group(1)

    def clean_json_string(self, raw_json_str):
        return json.loads(f'"{raw_json_str}"')

    def parse_json(self, clean_str):
        return json.loads(clean_str)

    def process_video_list(self, data):
        videos = []
        for vod in data[3]['videoList']['data']['list']:
            video = self.parse_video_info(vod)
            videos.append(video)
        return videos

    def build_category_result(self, videos, pg):
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        did = self.get_first_id(ids)
        url = self.build_detail_url(did)
        res = self.get_detail_page(url)
        raw_json_str = self.extract_raw_json(res)
        clean_str = self.clean_json_string(raw_json_str)
        data = self.parse_json(clean_str)
        content = self.build_vod_content(data)
        director = self.get_nested_value(data, 'vodDirector')
        actor = self.get_nested_value(data, 'vodActor')
        remarks = self.get_nested_value(data, 'vodRemarks')
        year = self.get_nested_value(data, 'vodYear')
        area = self.get_nested_value(data, 'vodArea')
        bofang = self.build_play_string(data, did)
        videos = self.build_video_info(did, director, actor, remarks, year, area, content, bofang)
        result = self.build_detail_result(videos)
        return result

    def get_first_id(self, ids):
        return ids[0]

    def build_detail_url(self, did):
        return f"{xurl}/detail/{did}"

    def get_detail_page(self, url):
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def extract_raw_json(self, res):
        pattern = r'self\.__next_f\.push\(\[1,"6:(.*?)"\]\)'
        match = re.search(pattern, res, re.S)
        return match.group(1)

    def clean_json_string(self, raw_json_str):
        return json.loads(f'"{raw_json_str}"')

    def parse_json(self, clean_str):
        return json.loads(clean_str)

    def build_vod_content(self, data):
        vod_content = data[3].get('data', {}).get('data', {}).get('vodContent', '')
        return '😸丢丢为您介绍剧情📢' + vod_content.replace('<p>', '').replace('</p>', '')

    def get_nested_value(self, data, key):
        return data[3].get('data', {}).get('data', {}).get(key)

    def build_play_string(self, data, did):
        bofang = ''
        for vod in data[3]['data']['data']['episodeList']:
            name = vod.get('name')
            id = f"{vod.get('nid')}@{did}"
            bofang = bofang + f"{name}${id}#"
        return bofang[:-1]

    def build_video_info(self, did, director, actor, remarks, year, area, content, bofang):
        return [{
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": "丢丢新视讯专线",
            "vod_play_url": bofang
               }]

    def build_detail_result(self, videos):
        result = {}
        result['list'] = videos
        return result

    def generate_sign(self, params):
        sign_key = self.get_sign_key()
        t = self.get_timestamp_ms()
        u = self.build_sign_string(params, sign_key, t)
        md5_val = self.compute_md5(u)
        sign = self.compute_sha1(md5_val)
        return sign, t

    def get_sign_key(self):
        return "cb808529bae6b6be45ecfab29a4889bc"

    def get_timestamp_ms(self):
        return str(int(time.time() * 1000))

    def build_sign_string(self, params, sign_key, t):
        if not params:
            return f"key={sign_key}&t={t}"
        h = "&".join([f"{k}={params[k]}" for k in sorted(params.keys())])
        return f"{h}&key={sign_key}&t={t}"

    def compute_md5(self, u):
        return hashlib.md5(u.encode('utf-8')).hexdigest()

    def compute_sha1(self, md5_val):
        return hashlib.sha1(md5_val.encode('utf-8')).hexdigest()

    def playerContent(self, flag, id, vipFlags):
        fenge = self.split_id(id)
        params = self.build_player_params(fenge)
        new_sign, new_t = self.generate_sign(params)
        headers = self.build_player_headers(new_sign, new_t)
        data = self.get_player_data(params, headers)
        url = self.extract_play_url(data)
        result = self.build_player_result(url)
        return result

    def split_id(self, id):
        return id.split("@")

    def build_player_params(self, fenge):
        return {
            "clientType": "1",
            "id": fenge[1],
            "nid": fenge[0]
               }

    def build_player_headers(self, new_sign, new_t):
        return {
            'sign': new_sign,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            't': new_t,
               }

    def get_player_data(self, params, headers):
        detail = requests.get(f'{xurl}/api/mw-movie/anonymous/v2/video/episode/url', params=params, headers=headers)
        detail.encoding = "utf-8"
        return detail.json()

    def extract_play_url(self, data):
        return data['data']['list'][0]['url']

    def build_player_result(self, url):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = url
        result["header"] = headerx
        return result

    def parse_video_info(self,vod):
        video = {
            "vod_id": vod.get('vodId'),
            "vod_name": vod.get('vodName'),
            "vod_pic": vod.get('vodPic'),
            "vod_year": vod.get('vodPubdate'),
            "vod_remarks": vod.get('vodRemarks') or vod.get('vodDoubanScore')
                }
        return video

    def searchContentPage(self, key, quick, pg):
        page = self.get_page_number(pg)
        params = self.build_search_params(key, page)
        new_sign, new_t = self.generate_sign(params)
        headers = self.build_search_headers(new_sign, new_t)
        data = self.get_search_data(params, headers)
        videos = self.process_search_results(data)
        result = self.build_search_result(videos, pg)
        return result

    def get_page_number(self, pg):
        return int(pg) if pg else 1

    def build_search_params(self, key, page):
        return {
            'keyword': key,
            'pageNum': page,
            'pageSize': '8',
            'sourceCode': '1',
               }

    def build_search_headers(self, new_sign, new_t):
        return {
            'sign': new_sign,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            't': new_t,
               }

    def get_search_data(self, params, headers):
        detail = requests.get(f'{xurl}/api/mw-movie/anonymous/video/searchByWord', params=params, headers=headers)
        detail.encoding = "utf-8"
        return detail.json()

    def process_search_results(self, data):
        videos = []
        for vod in data['data']['result']['list']:
            video = self.parse_video_info(vod)
            videos.append(video)
        return videos

    def build_search_result(self, videos, pg):
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None







