# coding = utf-8
# !/usr/bin/python

"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
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
import datetime
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://www.xuan688.top"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; U; Android 8.0.0; zh-cn; Mi Note 2 Build/OPR1.170623.032) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.128 Mobile Safari/537.36 XiaoMi/MiuiBrowser/10.1.1'
          }

pm = ''

class Spider(Spider):
    global xurl
    global headerx
    global headers

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
            return middle_text

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
        result = {"class": [{"type_id": "8", "type_name": "国产剧🌠"},
                            {"type_id": "9", "type_name": "港台剧🌠"},
                            {"type_id": "10", "type_name": "欧美剧🌠"},
                            {"type_id": "11", "type_name": "日韩剧🌠"},
                            {"type_id": "21", "type_name": "海外剧🌠"},
                            {"type_id": "1", "type_name": "动作片🌠"},
                            {"type_id": "2", "type_name": "科幻片🌠"},
                            {"type_id": "3", "type_name": "爱情片🌠"},
                            {"type_id": "4", "type_name": "喜剧片🌠"},
                            {"type_id": "5", "type_name": "剧情片🌠"},
                            {"type_id": "6", "type_name": "恐怖片🌠"},
                            {"type_id": "7", "type_name": "战争片🌠"},
                            {"type_id": "14", "type_name": "纪录片🌠"},
                            {"type_id": "20", "type_name": "短剧🌠"},
                            {"type_id": "13", "type_name": "动漫🌠"},
                            {"type_id": "12", "type_name": "综艺🌠"},
                            {"type_id": "26", "type_name": "视频一🌠"},
                            {"type_id": "22", "type_name": "视频二🌠"},
                            {"type_id": "23", "type_name": "视频三🌠"},
                            {"type_id": "32", "type_name": "视频四🌠"},
                            {"type_id": "36", "type_name": "视频五🌠"},
                            {"type_id": "37", "type_name": "视频六🌠"},
                            {"type_id": "30", "type_name": "原创一🌠"},
                            {"type_id": "38", "type_name": "原创二🌠"},
                            {"type_id": "41", "type_name": "原创三🌠"},
                            {"type_id": "27", "type_name": "字幕一🌠"},
                            {"type_id": "28", "type_name": "字幕二🌠"},
                            {"type_id": "17", "type_name": "骑兵一🌠"},
                            {"type_id": "33", "type_name": "骑兵二🌠"},
                            {"type_id": "24", "type_name": "步兵区🌠"},
                            {"type_id": "31", "type_name": "主播一🌠"},
                            {"type_id": "34", "type_name": "主播二🌠"},
                            {"type_id": "39", "type_name": "主播三🌠"},
                            {"type_id": "29", "type_name": "欧美区🌠"},
                            {"type_id": "25", "type_name": "H动漫🌠"},
                            {"type_id": "35", "type_name": "水果派🌠"},
                            {"type_id": "40", "type_name": "传媒区🌠"}],
                 }

        return result

    def homeVideoContent(self):
        videos = []
        detail = requests.get(url=xurl, headers=headerx)
        detail.encoding = "GBK"
        res = detail.text

        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="img")

        for soup in soups:
            vods = soup.find_all('li')

            for vod in vods:

                name = vod.find('img')['alt']

                id = vod.find('a')['href']

                pic = vod.find('img')['src']

                if 'http' not in pic:
                    pic = xurl + pic

                remark = self.extract_middle_text(str(vod), '<em>', '</em>', 0)

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": '集多▶️' + remark
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

        check_numbers = {'26', '22', '23', '32', '36', '37', '30', '38', '41', '27', '28', '17', '33', '24', '31', '34', '39', '29', '25', '35', '40'}
        if any(num in cid for num in check_numbers):
            if page == 1:
                url = f'{xurl}/M/{cid}.html'

            else:
                url = f'{xurl}/M/{cid}_{str(page)}.html'

            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "GBK"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="channel-content")

            for item in soups:
                vods = item.find_all('li')

                for vod in vods:
                    names = vod.find('a', class_="ah")
                    name = names['title']

                    id = names['href']

                    pic = vod.find('img')['src']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remark = self.extract_middle_text(str(vod), 'class="time">', '<', 0)

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多▶️' + remark
                            }
                    videos.append(video)

        else:
            if page == 1:
                url = f'{xurl}/M/{cid}.html'

            else:
                url = f'{xurl}/M/{cid}_{str(page)}.html'

            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "GBK"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="limg")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:

                    name = vod.find('img')['alt']

                    id = vod.find('a')['href']

                    pic = vod.find('img')['src']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remark = self.extract_middle_text(str(vod), '<em>', '</em>', 0)

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多▶️' + remark
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
        res.encoding = "GBK"
        res = res.text

        url = 'https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1732707176882/jiduo.txt'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)

        content = '集多为您介绍剧情📢' + self.extract_middle_text(res,'剧情：</em>','<', 0)
        content = content.replace("\u3000", '')

        actor = self.extract_middle_text(res, '主演：', '</li>',1,'href=".*?">(.*?)</a>')

        remarks = self.extract_middle_text(res, '状态：', '<', 0)

        year = self.extract_middle_text(res, '年代：', '<', 0)

        area = self.extract_middle_text(res, '地区：', '<', 0)

        if name not in content:
            bofang = Jumps
            xianlu = '1'
        else:
            doc = BeautifulSoup(res, "lxml")
            soups = doc.find('div', class_="movurl")
            vods = soups.find('a')
            href_value = xurl + vods.get('href')

            res = requests.get(url=href_value, headers=headerx)
            res.encoding = "GBK"
            res = res.text

            doc = BeautifulSoup(res, "lxml")
            soups = doc.find_all('div', class_="palx")
            for soup in soups:
                vods = soup.find_all('script')
                if vods:
                    vod = vods[0]
                    url = xurl + vod.get('src')

            res = requests.get(url=url, headers=headers)
            res.encoding = "utf-8"
            res = res.text
            res = self.extract_middle_text(res, 'VideoListJson=', ',urlinfo', 0).replace("'", '"')
            data = json.loads(res)

            for sou in data[0][1]:

                ids = sou.replace("$ffm3u8", '')

                bofang = bofang + ids + '#'

            bofang = bofang[:-1]

            xianlu = '集多专线'

        videos.append({
            "vod_id": did,
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

        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = id
        result["header"] = headerx
        return result

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []

        key = urllib.parse.quote(key.encode('gbk'))

        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/search.asp?searchword={key}'

        else:
            url = f'{xurl}/search.asp?page={str(page)}&searchword={key}&searchtype=-1'

        detail = requests.get(url=url, headers=headers)
        detail.encoding = "GBK"
        res = detail.text

        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="channel-content")

        for item in soups:
            vods = item.find_all('li')

            for vod in vods:
                names = vod.find('a', class_="ah")
                name = names['title']

                id = names['href']

                pic = vod.find('img')['src']

                if 'http' not in pic:
                    pic = xurl + pic

                remark = self.extract_middle_text(str(vod), 'class="time">', '<', 0)

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": '集多▶️' + remark
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





