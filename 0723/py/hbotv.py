# coding = utf-8
# !/usr/bin/python

"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
import urllib.request
import urllib.parse
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://wwww.hbotv6.top"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
          }

pm = ''

class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "movie", "type_name": "🍅电影"},
                            {"type_id": "tv", "type_name": "🍅剧集"},
                            {"type_id": "cartoon", "type_name": "🍅动漫"},
                            {"type_id": "shorts", "type_name": "🍅短剧"},
                            {"type_id": "variety", "type_name": "🍅综艺"}],
                 }

        return result

    def homeVideoContent(self):
        videos = []

        detail = requests.get(url=xurl, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text

        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('ul', class_="stui-vodlist")

        for soup in soups:
            vods = soup.find_all('li')

            for vod in vods:
                names = vod.find('a', class_="stui-vodlist__thumb")
                name = names['title']

                id = names['href']

                pic = vod.find('img')['data-original']

                if 'http' not in pic:
                    pic = xurl + pic

                remarks = vod.find('span', class_="pic-text")
                remark = remarks.text.strip()

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": '🍅' + remark
                         }
                videos.append(video)

        result = {'list': videos}
        return result

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        if pg:
            page = int(pg)
        else:
            page = 1

        if page == 1:
            url = f'{xurl}/{cid}/'

        else:
            url = f'{xurl}/{cid}/index_{str(page)}.html'

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text

        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('ul', class_="stui-vodlist")

        for soup in soups:
            vods = soup.find_all('li')

            for vod in vods:

                name = vod.find('img')['title']

                ids = vod.find('a', class_="stui-vodlist__thumb")
                id = ids['href']

                pic = vod.find('img')['data-original']

                if 'http' not in pic:
                    pic = xurl + pic

                remarks = vod.find('span', class_="pic-text")
                remark = remarks.text.strip()

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": '🍅' + remark
                        }
                videos.append(video)

        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        global pm
        did = ids[0]
        result = {}
        videos = []
        xianlu = ''
        bofang = ''

        if 'http' not in did:
            did = xurl + did

        res = requests.get(url=did, headers=headerx)
        res.encoding = "utf-8"
        res = res.text

        url = 'https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1732707176882/jiduo.txt'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)

        content = '😸集多🎉为您介绍剧情📢' + self.extract_middle_text(res,'style="display:none">','</div>', 0)

        director = self.extract_middle_text(res, '导演：', '</p>',1,'<a href=".*?">(.*?)</')

        actor = self.extract_middle_text(res, '主演：', '</p>',1,'<a href=".*?">(.*?)</')

        remarks = self.extract_middle_text(res, '类型：', 'a>', 1,'<a href=".*?">(.*?)</')

        year = self.extract_middle_text(res, '年份：', '</p>', 1,'<a href=".*?">(.*?)</')

        area = self.extract_middle_text(res, '地区：', 'a>', 1,'<a href=".*?">(.*?)</')

        if name not in content:
            bofang = Jumps
            xianlu = '1'
        else:
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="stui-pannel_hd")[:-1]

            for item in soups:

                vods = item.find_all('h3')

                for vod in vods:

                    name = vod.text.strip()

                    xianlu = xianlu + name + '$$$'

            xianlu = xianlu[:-3]

            soups = doc.find_all('ul', class_="stui-content__playlist")

            for item in soups:

                vods = item.find_all('a')

                for vod in vods:

                    id = vod['href']

                    if 'http' not in id:
                        id = xurl + id

                    name = vod.text.strip()

                    bofang = bofang + name + '$' + id + '#'

                bofang = bofang[:-1] + '$$$'

            bofang = bofang[:-3]

        videos.append({
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("http")

        xiutan = 0

        if xiutan == 0:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]

            if '/tp/jd.m3u8' in after_https:
                url = after_https
            else:
                res = requests.get(url=after_https, headers=headerx)
                res = res.text

                headerz = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
                    'Referer': after_https
                           }

                did = "https://wwww.hbotv6.top/player/?url=" + self.extract_middle_text(res, 'var a0 = "', '"', 0)
                res = requests.get(url=did, headers=headerz)
                res.encoding = "utf-8"
                res = res.text

                headerd = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
                    'Referer': did
                          }

                did1 = "https://wwww.hbotv6.top" + self.extract_middle_text(res, '<iframe name ="iframe-player" src="', '"',0)
                res = requests.get(url=did1, headers=headerd)
                res.encoding = "utf-8"
                res = res.text

                url = self.extract_middle_text(res, 'var url = "','"', 0)

            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
            return result

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []

        page = int(page) - 1

        current_time = int(datetime.now().timestamp())

        payload = {
            'keyboard': key,
            'show': 'title',
            'tempid': 1,
            'tbname': 'news',
            'mid': 1,
            'dopost': 'search'
                  }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
            'Cookie': f'pyfxelastsearchtime={current_time}'
                  }

        response = requests.post("https://wwww.hbotv6.top/e/search/index.php", headers=headers, data=payload, allow_redirects=False)
        if response.status_code == 302:
            url =response.headers.get('Location')
            url = xurl + url.replace('0/', '') + f'{page}/'

            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find('div', class_="stui-pannel_bd")

            soup = soups.find_all('ul', class_="stui-vodlist__media")

            for item in soup:
                vods = item.find_all('li')

                for vod in vods:
                    names = vod.find('a', class_="v-thumb")
                    name = names['title']

                    id = names['href']

                    pic = names['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('span', class_="pic-text")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '🍅' + remark
                            }
                    videos.append(video)

        result['list'] = videos
        result['page'] = page
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





