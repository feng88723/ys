# coding = utf-8
# !/usr/bin/python

"""

作者 繁华🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================fanhua====================

"""

from Crypto.Util.Padding import unpad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from bs4 import BeautifulSoup
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

xurl = "https://www.ynsx.com.cn"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

# headerx = {
#     'User-Agent': 'Linux; Android 12; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36'
#           }

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
                            output += f"#{ match[1]}${number}{match[0]}"
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
        result = {"class": [{"type_id": "36", "type_name": "短剧🌠"},
                            {"type_id": "1", "type_name": "电影🌠"},
                            {"type_id": "2", "type_name": "连续剧🌠"},
                            {"type_id": "3", "type_name": "综艺🌠"},
                            {"type_id": "4", "type_name": "动漫🌠"}],

                  "list": [],
                  "filters": {"1": [

                      {
                          "key": "地区",
                          "name": "地区",
                          "value": [
                                    {
                                        "n": "全部",
                                        "v": ""
                                    },
                                    {
                                        "n": "内地",
                                        "v": "内地"
                                    },
                                    {
                                        "n": "香港",
                                        "v": "香港"
                                    },
                                    {
                                        "n": "韩国",
                                        "v": "韩国"
                                    },
                                    {
                                        "n": "美国",
                                        "v": "美国"
                                    },
                                    {
                                        "n": "日本",
                                        "v": "日本"
                                    },
                                    {
                                        "n": "法国",
                                        "v": "法国"
                                    },
                                    {
                                        "n": "英国",
                                        "v": "英国"
                                    },
                                    {
                                        "n": "德国",
                                        "v": "德国"
                                    },
                                    {
                                        "n": "台湾",
                                        "v": "台湾"
                                    },
                                    {
                                        "n": "泰国",
                                        "v": "泰国"
                                    },
                                    {
                                        "n": "印度",
                                        "v": "印度"
                                    },
                                    {
                                        "n": "新加坡",
                                        "v": "新加坡"
                                    },
                                    {
                                        "n": "其他",
                                        "v": "其他"
                                    }
                                ]

                      },

                      {"key": "年代",
                                     "name": "年代",
                                     "value": [ {"n": "全部", "v": ""},
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
                                            {"n": "2009", "v": "2009"},
                                            {"n": "2008", "v": "2008"}
                                ]

                      },

                      {
                          "key": "语言",
                          "name": "语言",
                          "value": [
                              {
                                  "n": "全部",
                                  "v": ""
                              },
                              {
                                  "n": "国语",
                                  "v": "国语"
                              },
                              {
                                  "n": "粤语",
                                  "v": "粤语"
                              },
                              {
                                  "n": "英语",
                                  "v": "英语"
                              },
                              {
                                  "n": "日语",
                                  "v": "日语"
                              },
                              {
                                  "n": "韩语",
                                  "v": "韩语"
                              },
                              {
                                  "n": "法语",
                                  "v": "法语"
                              },
                              {
                                  "n": "其他",
                                  "v": "其他"
                              }
                          ]
                      }],
                              "2": [

                                  {
                          "key": "地区",
                          "name": "地区",
                          "value": [
                                    {
                                        "n": "全部",
                                        "v": ""
                                    },
                                    {
                                        "n": "内地",
                                        "v": "内地"
                                    },
                                    {
                                        "n": "香港",
                                        "v": "香港"
                                    },
                                    {
                                        "n": "韩国",
                                        "v": "韩国"
                                    },
                                    {
                                        "n": "美国",
                                        "v": "美国"
                                    },
                                    {
                                        "n": "日本",
                                        "v": "日本"
                                    },
                                    {
                                        "n": "法国",
                                        "v": "法国"
                                    },
                                    {
                                        "n": "英国",
                                        "v": "英国"
                                    },
                                    {
                                        "n": "德国",
                                        "v": "德国"
                                    },
                                    {
                                        "n": "台湾",
                                        "v": "台湾"
                                    },
                                    {
                                        "n": "泰国",
                                        "v": "泰国"
                                    },
                                    {
                                        "n": "印度",
                                        "v": "印度"
                                    },
                                    {
                                        "n": "新加坡",
                                        "v": "新加坡"
                                    },
                                    {
                                        "n": "其他",
                                        "v": "其他"
                                    }
                                ]

                      },

                      {"key": "年代",
                                     "name": "年代",
                                     "value": [ {"n": "全部", "v": ""},
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
                                            {"n": "2009", "v": "2009"},
                                            {"n": "2008", "v": "2008"}
                                ]

                      },

                      {
                          "key": "语言",
                          "name": "语言",
                          "value": [
                              {
                                  "n": "全部",
                                  "v": ""
                              },
                              {
                                  "n": "国语",
                                  "v": "国语"
                              },
                              {
                                  "n": "粤语",
                                  "v": "粤语"
                              },
                              {
                                  "n": "英语",
                                  "v": "英语"
                              },
                              {
                                  "n": "日语",
                                  "v": "日语"
                              },
                              {
                                  "n": "韩语",
                                  "v": "韩语"
                              },
                              {
                                  "n": "法语",
                                  "v": "法语"
                              },
                              {
                                  "n": "其他",
                                  "v": "其他"
                              }
                          ]
                      }],
                      "3": [


                          {
                          "key": "地区",
                          "name": "地区",
                          "value": [
                              {
                                  "n": "全部",
                                  "v": ""
                              },
                              {
                                  "n": "内地",
                                  "v": "内地"
                              },
                              {
                                  "n": "港台",
                                  "v": "港台"
                              },
                              {
                                  "n": "日韩",
                                  "v": "日韩"
                              },
                              {
                                  "n": "欧美",
                                  "v": "欧美"
                              },

                          ]

                      },

                          {"key": "年代",
                           "name": "年代",
                           "value": [{"n": "全部", "v": ""},
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
                                     {"n": "2009", "v": "2009"},
                                     {"n": "2008", "v": "2008"}
                                     ]

                           },

                          {
                              "key": "语言",
                              "name": "语言",
                              "value": [
                                  {
                                      "n": "全部",
                                      "v": ""
                                  },
                                  {
                                      "n": "国语",
                                      "v": "国语"
                                  },
                                  {
                                      "n": "粤语",
                                      "v": "粤语"
                                  },
                                  {
                                      "n": "英语",
                                      "v": "英语"
                                  },
                                  {
                                      "n": "日语",
                                      "v": "日语"
                                  },
                                  {
                                      "n": "韩语",
                                      "v": "韩语"
                                  },
                                  {
                                      "n": "法语",
                                      "v": "法语"
                                  },
                                  {
                                      "n": "其他",
                                      "v": "其他"
                                  }
                              ]
                          }],
                      "4": [
                          {
                              "key": "类型",
                              "name": "类型",
                              "value": [
                                  {
                                      "n": "全部",
                                      "v": ""
                                  },
                                  {
                                      "n": "国产动漫",
                                      "v": "国产动漫"
                                  },
                                  {
                                      "n": "日本动漫",
                                      "v": "日本动漫"
                                  },
                                  {
                                      "n": "欧美动漫",
                                      "v": "欧美动漫"
                                  }
                              ]
                          },

                          {
                          "key": "地区",
                          "name": "地区",
                          "value": [
                              {
                                  "n": "全部",
                                  "v": ""
                              },
                              {
                                  "n": "国产",
                                  "v": "国产"
                              },
                              {
                                  "n": "日本",
                                  "v": "日本"
                              },
                              {
                                  "n": "欧美",
                                  "v": "欧美"
                              },
                              {
                                  "n": "其他",
                                  "v": "其他"
                              },
                      ]
                  }]}}

        return result

    def homeVideoContent(self):
        videos = []

        try:
            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")
            soups = doc.find_all('ul', class_="hl-vod-list")

            for soup in soups:
                vods = soup.find_all('li')
                print(vods)
                for vod in vods:
                    name = vod.find('a')['title']
                    id = vod.find('a')['href']
                    pic = vod.find('a')['data-original']
                    if 'http' not in pic:
                        pic = xurl + pic
                    remarks = vod.find('span', class_="remarks")
                    remark = remarks.text.strip()
                    video = {
                        "vod_id": id,
                        "vod_name":name,
                        "vod_pic": pic,
                        "vod_remarks":  remark
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
        if '类型' in ext.keys():
            lxType = ext['类型']
        else:
            lxType = ''
        if '地区' in ext.keys():
            DqType = ext['地区']
        else:
            DqType = ''
        if '语言' in ext.keys():
            YyType = ext['语言']
        else:
            YyType = ''
        if '年代' in ext.keys():
            NdType = ext['年代']
        else:
            NdType = ''
        if '剧情' in ext.keys():
            JqType = ext['剧情']
        else:
            JqType = ''
        if '排序' in ext.keys():
            pxType = ext['排序']
        else:
            pxType = ''

            url = f'{xurl}/vodshow/{cid}-{DqType}---{YyType}----{str(page)}---{NdType}.html'
        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")
            soups = doc.find_all('ul', class_="hl-vod-list")
            for soup in soups:
                vods = soup.find_all('li')
                for vod in vods:
                    name = vod.find('a')['title']
                    id = vod.find('a')['href']
                    pic = vod.find('a')['data-original']
                    if 'http' not in pic:
                        pic = xurl + pic
                    remarks = vod.find('span', class_="remarks")
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
        tiaozhuan = '0'
        if tiaozhuan == '1':
            didt = self.extract_middle_text(res, 'class="play">', '</p>', 1, 'href="(.*?)"')
            if 'http' not in didt:
                didt = xurl + didt
                ress = requests.get(url=didt, headers=headerx)
                ress.encoding = "utf-8"
                ress = ress.text
        duoxian = '0'
        if duoxian == '1':
            doc = BeautifulSoup(ress, 'lxml')
            soups = doc.find('span', class_='animate__animated')
            vods = soups.find_all('a')[1:]
            res1 = ''
            for vod in vods:
                url = self.extract_middle_text(str(vod), 'href="', '"', 0)
                if 'http' not in url:
                    url = xurl + url
                    resss = requests.get(url, headers=headerx)
                    resss.encoding = 'utf-8'
                    resss = resss.text
                    res1 = res1 + resss
            res2 = ress + res1
        url = 'https://9071.kstore.vip/py/yz.txt'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)
        content = '😸繁华🎉为您介绍剧情📢本资源来源于网络🚓侵权请联系删除👉' + self.extract_middle_text(res,'<span class="hl-content-text"><em>','</em></span>', 0)
        if name not in content:
            bofang = Jumps
        else:
            bofang = self.extract_middle_text(res, '<ul class="hl-plays-list', '</ul>', 3, 'href="(.*?)">(.*?)</a></li>')
        xianlu = self.extract_middle_text(res, '<ul class="hl-from-list">','</ul>',2, 'data-href=".*?"><i class=".*?"></i><span class=".*?">(.*?)</span>')
        actors = self.extract_middle_text(res, '<li class="hl-col-xs-12"><em class="hl-text-muted">主演：', '</li>', 1, 'href=".*?" target=".*?">(.*?)</a>')
        director = self.extract_middle_text(res, 'class="hl-text-muted">导演：</em>', '</li>', 1, '<a href=".*?" target=".*?">(.*?)</a>')
        videos.append({
            "vod_id": did,
            "vod_actor": actors,
            "vod_director": director,
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

            if '239755956819.mp4' in after_https:
                url = after_https
            else:
                res = requests.get(url=after_https, headers=headerx)
                res = res.text
                url = self.extract_middle_text(res, '},"url":"', '"', 0).replace('\\', '')
            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
            return result
        if xiutan == 1:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]
            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = after_https
            result["header"] = headerx
            return result
    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []
        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/vodsearch/-------------.html?wd={key}&submit='
        else:
            url = f'{xurl}/vodsearch/{key}----------{str(page)}---.html'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")
        soups = doc.find_all('ul', class_="hl-one-list")
        for item in soups:
            vods = item.find_all('li')
            for vod in vods:
                name = vod.find('a')['title']
                id = vod.find('a')['href']
                pic = vod.find('a')['data-original']
                remarks = vod.find('span', class_="remarks")
                remark = remarks.text.strip()
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




