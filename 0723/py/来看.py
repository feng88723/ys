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

xurl = "https://lkvod.me"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
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

    def decode_url(self,encoded_url):
        decoded_bytes = base64.b64decode(encoded_url)
        decoded_url = decoded_bytes.decode('latin1')
        final_url = urllib.parse.unquote(decoded_url)
        return final_url

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "1", "type_name": "电影"},
                            {"type_id": "2", "type_name": "剧集"},
                            {"type_id": "4", "type_name": "动漫"},
                            {"type_id": "3", "type_name": "综艺"}],

                  "list": [],
                  "filters": {"1": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2025", "v": "2025"},
                                               {"n": "2024", "v": "2024"},
                                               {"n": "2023", "v": "2023"},
                                               {"n": "2022", "v": "2022"},
                                               {"n": "2021", "v": "2021"},
                                               {"n": "2020", "v": "2020"},
                                               {"n": "2019", "v": "2019"},
                                               {"n": "2018", "v": "2018"}]}],
                              "2": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2025", "v": "2025"},
                                               {"n": "2024", "v": "2024"},
                                               {"n": "2023", "v": "2023"},
                                               {"n": "2022", "v": "2022"},
                                               {"n": "2021", "v": "2021"},
                                               {"n": "2020", "v": "2020"},
                                               {"n": "2019", "v": "2019"},
                                               {"n": "2018", "v": "2018"}]}],
                              "3": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2025", "v": "2025"},
                                               {"n": "2024", "v": "2024"},
                                               {"n": "2023", "v": "2023"},
                                               {"n": "2022", "v": "2022"},
                                               {"n": "2021", "v": "2021"},
                                               {"n": "2020", "v": "2020"},
                                               {"n": "2019", "v": "2019"},
                                               {"n": "2018", "v": "2018"}]}],
                              "4": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2025", "v": "2025"},
                                               {"n": "2024", "v": "2024"},
                                               {"n": "2023", "v": "2023"},
                                               {"n": "2022", "v": "2022"},
                                               {"n": "2021", "v": "2021"},
                                               {"n": "2020", "v": "2020"},
                                               {"n": "2019", "v": "2019"},
                                               {"n": "2018", "v": "2018"}]}]}}

        return result

    def homeVideoContent(self):
        videos = []

        try:
            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="border-box")

            for soup in soups:
                vods = soup.find_all('div', class_="public-list-box")

                for vod in vods:
                    names = vod.find('a', class_="public-list-exp")
                    name = names['title']

                    id = names['href']

                    pic = vod.find('img')['data-src']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('div', class_="public-list-subtitle")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": remark
                             }
                    videos.append(video)

            result = {'list': videos}
            return result
        except:
            pass

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        if pg:
            page = int(pg)
        else:
            page = 1

        if '年代' in ext.keys():
            NdType = ext['年代']
        else:
            NdType = ''

        if page == 1:
            url = f'{xurl}/show/{cid}-----------.html'

        else:
            url = f'{xurl}/show/{cid}--------{str(page)}---{NdType}.html'

        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="border-box")

            for soup in soups:
                vods = soup.find_all('div', class_="public-list-box")

                for vod in vods:
                    names = vod.find('a', class_="public-list-exp")
                    name = names['title']

                    id = names['href']

                    pic = vod.find('img')['data-src']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('div', class_="public-list-subtitle")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": remark
                            }
                    videos.append(video)

        except:
            pass
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

        content = '集多🎉为您介绍剧情📢本资源来源于网络🚓侵权请联系删除👉' + self.extract_middle_text(res,'class="text cor3">','</div>', 0)

        director = self.extract_middle_text(res, '导演 :', '</div>',1,'target=".*?">(.*?)</a>')

        actor = self.extract_middle_text(res, '演员 :', '</div>',1,'target=".*?">(.*?)</a>')

        remarks = self.extract_middle_text(res, '备注 :</strong>', '</div>', 0)

        year = self.extract_middle_text(res, '年份：</em>', '</li>', 0)

        area = self.extract_middle_text(res, '地区：</em>', '</li>', 0)

        if name not in content:
            bofang = Jumps
        else:
            doc=BeautifulSoup(res, "lxml")
            soups = doc.find('div', class_="swiper-wrapper")
            soup=soups.find_all('a')
            j=0
            x=[]
            gl=[]
            playforms=''
            for soup1 in soup:
                j += 1
                if '新自建' in soup1.text:
                    name=soup1.text[:6]
                else:
                    name = soup1.text[:5]
                if any(item in name for item in gl):
                    continue
                x.append(j)
                playforms=playforms+name+'$$$'
            playforms=playforms[:-3]

            playurl=''
            for i in x:
                j=int(i)-1
                soups = doc.find_all('ul', class_="anthology-list-play size")[j]
                soup=soups.find_all('a')
                for q in soup:
                    id=xurl+q['href']
                    name=q.text
                    playurl=playurl+name+'$'+id+'#'
                playurl=playurl[:-1]+'$$$'
            playurl=playurl[:-3]

        videos.append({
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": playforms,
            "vod_play_url": playurl
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags): 
        parts = id.split("http")

        xiutan = 0

        if xiutan == 0:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]

            if '239755956819.mp4' in after_https:
                url = after_https
            else:
                res = requests.get(url=after_https, headers=headerx)
                res = res.text
                url = self.extract_middle_text(res, '},"url":"', '"', 0).replace('\\', '')
                if 'm3u8' not in url:
                    url = "https://op.xn--it-if7c19g5s4bps5c.com/pi.php?url=" + url
                    res = requests.get(url=url, headers=headerx)
                    res.encoding = "utf-8"
                    html_content = res.text
                    pattern = r'getrandom\(\'(.*?)\'\)'
                    match = re.search(pattern, html_content)
                    extracted_string = match.group(1)
                    detail = self.decode_url(extracted_string)
                    url = 'http'+detail.split("http")[1].split('&btag=')[0]
                    if "UFID=" in url:
                        url2=url.split("UFID=")[1]
                        if len(url2)>20:
                            url=url[:-8]


            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
            return result

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []
        if not page:
            page = 1
        url = f'https://51souju1.com/vodsearch/{key}----------{str(page)}---.html'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")
        soups = doc.find_all('div', class_="hl-item-wrap clearfix")
        for soup in soups:
            lys = soup.find_all('div', class_="search-01-main")
            for item in lys:
                ly = item.find('span', class_="search-09-name").text
                if ly == "来看点播":
                    dw = soup.find('div', class_="hl-item-pic")
                    name = dw.find('a')['title']
                    id = item.find('a')['href']
                    pic = dw.find('a')['data-original']
                    remark = dw.find('span')
                    if remark:
                        remark = remark.text
                    else:
                        remark = ''
                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": remark
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





