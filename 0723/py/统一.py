"""

作者 繁华🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================kaiyuebinguan====================

"""

import requests
from bs4 import BeautifulSoup
import re
from base.spider import Spider
import sys
import json
import base64
import urllib.parse

sys.path.append('..')

xurl = "https://ty1010.com"

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
        result = {"class": [{"type_id": "1", "type_name": "电视剧🌠"},
                            {"type_id": "2", "type_name": "电影🌠"},
                            {"type_id": "3", "type_name": "动漫🌠"},
                            {"type_id": "4", "type_name": "综艺🌠"},
                            {"type_id": "41", "type_name": "短剧🌠"},
                            {"type_id": "5", "type_name": "体育赛事🌠"}],

                  "list": [],
                  "filters": {"1": [{"key": "类型", "name": "类型", "value": [

                                    {"n": "全部", "v": ""},
                                    {"n": "剧情", "v": "剧情"},
                                    {"n": "悬疑", "v": "悬疑"},
                                    {"n": "爱情", "v": "爱情"},
                                    {"n": "历史", "v": "历史"},
                                    {"n": "犯罪", "v": "犯罪"},
                                    {"n": "动作", "v": "动作"},
                                    {"n": "奇幻", "v": "奇幻"},
                                    {"n": "青春", "v": "青春"},
                                    {"n": "战争", "v": "战争"},
                                    {"n": "科幻", "v": "科幻"},
                                    {"n": "古装", "v": "古装"},
                                    {"n": "冒险", "v": "冒险"},
                                    {"n": "恐怖", "v": "恐怖"},
                                    {"n": "武侠", "v": "武侠"},
                                    {"n": "偶像", "v": "偶像"}
                                ]},
                                {"key": "地区", "name": "地区", "value": [
                                    {"n": "全部", "v": ""},
                                    {"n": "大陆", "v": "大陆"},
                                    {"n": "香港", "v": "香港"},
                                    {"n": "台湾", "v": "台湾"},
                                    {"n": "韩国", "v": "韩国"},
                                    {"n": "日本", "v": "日本"},
                                    {"n": "美国", "v": "美国"},
                                    {"n": "英国", "v": "英国"},
                                    {"n": "泰国", "v": "泰国"},
                                    {"n": "新加坡", "v": "新加坡"},
                                    {"n": "马来西亚", "v": "马来西亚"},
                                    {"n": "印度", "v": "印度"},
                                    {"n": "法国", "v": "法国"},
                                    {"n": "德国", "v": "德国"},
                                    {"n": "意大利", "v": "意大利"},
                                    {"n": "加拿大", "v": "加拿大"},
                                    {"n": "澳大利亚", "v": "澳大利亚"},
                                    {"n": "其他", "v": "其他"}
                                ]},
                                {"key": "年代", "name": "年代", "value": [
                                     {"n": "全部", "v": ""},
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
                                    {"n": "2010", "v": "2010"}
                                ]},
                                {"key": "语言", "name": "语言", "value": [
                                     {"n": "全部", "v": ""},
                                    {"n": "国语", "v": "国语"},
                                    {"n": "粤语", "v": "粤语"},
                                    {"n": "闽南语", "v": "闽南语"},
                                    {"n": "普通话", "v": "普通话"},
                                    {"n": "英语", "v": "英语"},
                                    {"n": "韩语", "v": "韩语"},
                                    {"n": "日语", "v": "日语"},
                                    {"n": "泰语", "v": "泰语"},
                                    {"n": "法语", "v": "法语"},
                                    {"n": "德语", "v": "德语"},
                                    {"n": "意大利语", "v": "意大利语"},
                                    {"n": "西班牙语", "v": "西班牙语"},
                                    {"n": "俄语", "v": "俄语"},
                                    {"n": "葡萄牙语", "v": "葡萄牙语"},
                                    {"n": "印地语", "v": "印地语"}
                                ]}
                            ],
                              "2":  [{"key": "类型", "name": "类型", "value": [

                                    {"n": "全部", "v": ""},
                                    {"n": "动作", "v": "动作"},
                                    {"n": "喜剧", "v": "喜剧"},
                                    {"n": "爱情", "v": "爱情"},
                                    {"n": "科幻", "v": "科幻"},
                                    {"n": "恐怖", "v": "恐怖"},
                                    {"n": "剧情", "v": "剧情"},
                                    {"n": "惊悚", "v": "惊悚"},
                                    {"n": "犯罪", "v": "犯罪"},
                                    {"n": "冒险", "v": "冒险"},
                                    {"n": "战争", "v": "战争"},
                                    {"n": "悬疑", "v": "悬疑"},
                                    {"n": "武侠", "v": "武侠"},
                                    {"n": "奇幻", "v": "奇幻"},
                                    {"n": "动画", "v": "动画"},
                                    {"n": "纪录", "v": "纪录"},
                                    {"n": "传记", "v": "传记"},
                                    {"n": "历史", "v": "历史"},
                                    {"n": "歌舞", "v": "歌舞"},
                                    {"n": "灾难", "v": "灾难"}
                                ]},
                                {"key": "地区", "name": "地区", "value": [
                                    {"n": "全部", "v": ""},
                                    {"n": "大陆", "v": "大陆"},
                                    {"n": "香港", "v": "香港"},
                                    {"n": "台湾", "v": "台湾"},
                                    {"n": "韩国", "v": "韩国"},
                                    {"n": "日本", "v": "日本"},
                                    {"n": "美国", "v": "美国"},
                                    {"n": "英国", "v": "英国"},
                                    {"n": "泰国", "v": "泰国"},
                                    {"n": "新加坡", "v": "新加坡"},
                                    {"n": "马来西亚", "v": "马来西亚"},
                                    {"n": "印度", "v": "印度"},
                                    {"n": "法国", "v": "法国"},
                                    {"n": "德国", "v": "德国"},
                                    {"n": "意大利", "v": "意大利"},
                                    {"n": "加拿大", "v": "加拿大"},
                                    {"n": "澳大利亚", "v": "澳大利亚"},
                                    {"n": "俄罗斯", "v": "俄罗斯"},
                                    {"n": "西班牙", "v": "西班牙"},
                                    {"n": "其他", "v": "其他"}
                                ]},
                                {"key": "年代", "name": "年代", "value": [
                                     {"n": "全部", "v": ""},
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
                                    {"n": "2010", "v": "2010"}
                                ]},
                                {"key": "语言", "name": "语言", "value": [
                                      {"n": "全部", "v": ""},
                                    {"n": "国语", "v": ""},
                                    {"n": "粤语", "v": "粤语"},
                                    {"n": "英语", "v": "英语"},
                                    {"n": "韩语", "v": "韩语"},
                                    {"n": "普通话", "v": "普通话"},
                                    {"n": "日语", "v": "日语"},
                                    {"n": "泰语", "v": "泰语"},
                                    {"n": "法语", "v": "法语"},
                                    {"n": "德语", "v": "德语"},
                                    {"n": "意大利语", "v": "意大利语"},
                                    {"n": "西班牙语", "v": "西班牙语"},
                                    {"n": "俄语", "v": "俄语"}
                                ]}
                            ],
                              "3": [{"key": "类型", "name": "类型", "value": [

                                    {"n": "全部", "v": ""},
                                    {"n": "热血", "v": "热血"},
                                    {"n": "冒险", "v": "冒险"},
                                    {"n": "奇幻", "v": "奇幻"},
                                    {"n": "魔法", "v": "魔法"},
                                    {"n": "家庭", "v": "家庭"},
                                    {"n": "剧情", "v": "剧情"},
                                    {"n": "恐怖", "v": "恐怖"},
                                    {"n": "校园", "v": "校园"},
                                    {"n": "搞笑", "v": "搞笑"},
                                    {"n": "青春", "v": "青春"},
                                    {"n": "战斗", "v": "战斗"},
                                    {"n": "科幻", "v": "科幻"},
                                    {"n": "悬疑", "v": "悬疑"},
                                    {"n": "恋爱", "v": "恋爱"}
                                ]},
                                {"key": "地区", "name": "地区", "value": [
                                    {"n": "全部", "v": ""},
                                    {"n": "日本", "v": "日本"},
                                    {"n": "大陆", "v": "大陆"},
                                    {"n": "国产", "v": "国产"},
                                    {"n": "美国", "v": "美国"},
                                    {"n": "韩国", "v": "韩国"},
                                    {"n": "法国", "v": "法国"},
                                    {"n": "台湾", "v": "台湾"},
                                    {"n": "英国", "v": "英国"},
                                    {"n": "俄罗斯", "v": "俄罗斯"},
                                    {"n": "加拿大", "v": "加拿大"},
                                    {"n": "德国", "v": "德国"},
                                    {"n": "其他", "v": "其他"}
                                ]},
                                {"key": "年代", "name": "年代", "value": [
                                     {"n": "全部", "v": ""},
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
                                    {"n": "2010", "v": "2010"}
                                ]},
                                {"key": "语言", "name": "语言", "value": [
                                     {"n": "全部", "v": ""},
                                        {"n": "日语", "v": "日语"},
                                        {"n": "国语", "v": "国语"},
                                        {"n": "普通话", "v": "普通话"},
                                        {"n": "英语", "v": "英语"},
                                        {"n": "韩语", "v": "韩语"},
                                        {"n": "法语", "v": "法语"},
                                        {"n": "粤语", "v": "粤语"},
                                        {"n": "德语", "v": "德语"}
                                ]}
                            ],
                              "4":  [{"key": "类型", "name": "类型", "value": [

                                     {"n": "全部", "v": ""},
                                    {"n": "真人秀", "v": "真人秀"},
                                    {"n": "音乐", "v": "音乐"},
                                    {"n": "家庭", "v": "家庭"},
                                    {"n": "脱口秀", "v": "脱口秀"}
                                ]},
                                {"key": "地区", "name": "地区", "value": [
                                     {"n": "全部", "v": ""},
                                    {"n": "大陆", "v": "大陆"},
                                    {"n": "日本", "v": "日本"},
                                    {"n": "韩国", "v": "韩国"},
                                    {"n": "欧美", "v": "欧美"},
                                    {"n": "香港", "v": "香港"},
                                    {"n": "台湾", "v": "台湾"}
                                ]},
                                {"key": "年代", "name": "年代", "value": [
                                     {"n": "全部", "v": ""},
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
                                    {"n": "2010", "v": "2010"}
                                ]},
                                {"key": "语言", "name": "语言", "value": [
                                      {"n": "全部", "v": ""},
                                        {"n": "普通话", "v": "普通话"},
                                        {"n": "国语", "v": "国语"},
                                        {"n": "英语", "v": "英语"},
                                        {"n": "粤语", "v": "粤语"},
                                        {"n": "闽南语", "v": "闽南语"},
                                        {"n": "韩语", "v": "韩语"},
                                        {"n": "日语", "v": "日语"}
                                ]}
                                     ],
                              "5":  [{"key": "类型", "name": "类型", "value": [

                                     {"n": "全部", "v": ""},
                                    {"n": "真人秀", "v": "真人秀"},
                                    {"n": "音乐", "v": "音乐"},
                                    {"n": "家庭", "v": "家庭"},
                                    {"n": "脱口秀", "v": "脱口秀"}
                                ]},
                                {"key": "地区", "name": "地区", "value": [
                                     {"n": "全部", "v": ""},
                                    {"n": "大陆", "v": "大陆"},
                                    {"n": "日本", "v": "日本"},
                                    {"n": "韩国", "v": "韩国"},
                                    {"n": "欧美", "v": "欧美"},
                                    {"n": "香港", "v": "香港"},
                                    {"n": "台湾", "v": "台湾"}
                                ]},
                                {"key": "年代", "name": "年代", "value": [
                                     {"n": "全部", "v": ""},
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
                                    {"n": "2010", "v": "2010"}
                                ]},
                                {"key": "语言", "name": "语言", "value": [
                                      {"n": "全部", "v": ""},
                                        {"n": "普通话", "v": "普通话"},
                                        {"n": "国语", "v": "国语"},
                                        {"n": "英语", "v": "英语"},
                                        {"n": "粤语", "v": "粤语"},
                                        {"n": "闽南语", "v": "闽南语"},
                                        {"n": "韩语", "v": "韩语"},
                                        {"n": "日语", "v": "日语"}
                                ]},
                                     ],
                              "41":  [{"key": "类型", "name": "类型", "value": [

                                     {"n": "全部", "v": ""}
                                ]},
                                {"key": "地区", "name": "地区", "value": [
                                     {"n": "全部", "v": ""},
                                    {"n": "大陆", "v": "大陆"}
                                ]},
                                {"key": "年代", "name": "年代", "value": [
                                     {"n": "全部", "v": ""},
                                    {"n": "2024", "v": "2024"},
                                    {"n": "2023", "v": "2023"},
                                    {"n": "2022", "v": "2022"},
                                    {"n": "2021", "v": "2021"}
                                ]},
                                {"key": "语言", "name": "语言", "value": [
                                       {"n": "全部", "v": ""},
                                        {"n": "国语", "v": "国语"},
                                        {"n": "汉语", "v": "汉语"},
                                        {"n": "普通话", "v": "普通话"}
                                ]}
                                     ]


                              }}

        return result

    def homeVideoContent(self):  # SHOUYE
        videos = []
        try:
            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="border-box")

            # =====================================================

            # if soups and len(soups) > 1:
            #     soups = soups[0]
            #     vods = soups.find_all('div', class_="public-list-box")
            # ==============================================
            for soup in soups:
                vods = soup.find_all('div', class_="public-list-box")

            # for soup in soups:
            #     vods = soup.find_all('a')

                #  =======================================

                for vod in vods:
                    names = vod.find('a', class_="public-list-exp")
                    # name = names.text.strip()
                    name = names['title']
                    # name = names.find('a').text
                    # name = names.find('a')['title']

                    # name = vod.find('a')['title']

                    # names = vod.find_all('img')
                    # name = names[1]['title']

                    # name = self.extract_middle_text(str(vod), 'alt="', '"', 0)

                    # name= vod.select_one('div a')['title']
                    # print(name)
                    # name = vod['title']

                    #  =======================================

                    ids = vod.find('a', class_="public-list-exp")
                    id = ids['href']

                    # id = vod.find('a')['href']

                    # ids = vod.find_all('a')
                    # id = ids[1]['href']

                    # id = self.extract_middle_text(str(vod), 'href="', '"', 0)

                    # id = vod.select_one('h3 a')['href']

                    # id = vod['href']

                    #  =======================================

                    pics = vod.find('img', class_="lazy")
                    pic = pics['data-src']

                    # pic = vod.find('a')['data-original']

                    # pics = vod.find_all('a')
                    # pic = pics[1]['data-original']

                    # pic = self.extract_middle_text(str(vod), 'lay-src="', '"', 0)

                    # pic = vod.select_one('div img')['src']

                    # pic = vod['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    #  =======================================

                    remarks = vod.find('div', class_="public-list-subtitle")
                    remark = remarks.text.strip()
                    # remark = remarks.find('span').text

                    # remarks = vod.find_all('div')
                    # remark = remarks[2].text

                    # remark = self.extract_middle_text(str(vod), '<div class="state">', '</span>', 0)
                    # remark = remark.replace('\n', '').replace(' ','')

                    # remark = vod.select_one('a img').text

                    #  =======================================

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks":  remark
                             }
                    videos.append(video)

            #  =======================================

            result = {'list': videos}
            return result
        except:
            pass

    def categoryContent(self, cid, pg, filter, ext):  # FENYE
        result = {}
        if pg:
            page = int(pg)
        else:
            page = 1
        page = int(pg)
        videos = []
        cid='id/'+cid
        if '类型' in ext.keys():
            lxType = '/class/' + ext['类型']
        else:
            lxType = ''
        if '地区' in ext.keys():
            DqType = '/area/'+ext['地区']
        else:
            DqType = ''
        if '语言' in ext.keys():
            YyType = '/lang/'+ext['语言']
        else:
            YyType = ''
        if '年代' in ext.keys():
            NdType = '/year/'+ ext['年代']
        else:
            NdType = ''
        if '剧情' in ext.keys():
            JqType = ext['剧情']
        else:
            JqType = ''
        if '状态' in ext.keys():
            ztType = ext['状态']
        else:
            ztType = ''
        if '排序' in ext.keys():
            pxType = ext['排序']
        else:
            pxType = ''

        if page == '1':
            url = f'{xurl}/index.php/vod/show/id/{cid}.html'
         #{xurl}/index.php/vod/show/id/{cid}.html--
        #{xurl}/index.php/vod/show/area//class/{lxType}/id/{cid}/lang/{YyType}/page/{str(page)}/year/{NdType}.html
        else:
            url = f'{xurl}/index.php/vod/show/{DqType}{lxType}{cid}{YyType}/page/{str(page)}{NdType}.html'
                    #{xurl}/index.php/vod/show/id/{cid}/page/{str(page)}/year/{NdType}.html

        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="list-vod")

            for soup in soups:
                vods = soup.find_all('div', class_="public-list-box")

            # for soup in soups:
            #     vods = soup.find_all('div')

                #  =======================================

                for vod in vods:
                    names = vod.find('a', class_="time-title")
                    name = names.text.strip()
                    # name = names['title']
                    # name = names.find('a').text
                    # name = names.find('a')['title']

                    # name = vod.find('a')['title']

                    # names = vod.find_all('img')
                    # name = names[1]['title']

                    # name = self.extract_middle_text(str(vod), '<div class="name">', '</div>', 0)

                    # name = vod.select_one('a img')['alt']

                    # name = vod['title']

                    #  =======================================

                    ids = vod.find('a', class_="time-title")
                    id = ids['href']

                    # id = vod.find('a')['href']

                    # ids = vod.find_all('a')
                    # id = ids[1]['href']

                    # id = self.extract_middle_text(str(vod), 'href="', '"', 0)

                    # id = vod.select_one('h3 a')['href']

                    # id = vod['href']

                    #  =======================================

                    # pics = vod.find('div', class_="module-card")
                    # pic = pics.find('a')['data-original']

                    pic = vod.find('img')['data-src']

                    # pics = vod.find_all('a')
                    # pic = pics[1]['data-original']

                    # pic = self.extract_middle_text(str(vod), 'lay-src="', '"', 0)

                    # pic = vod.select_one('a img')['data-original']

                    # pic = vod['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    #  =======================================

                    remarks = vod.find('span', class_="public-list-prb")
                    remark = remarks.text.strip()
                    # remark = remarks.find('span').text

                    # remarks = vod.find_all('div')
                    # remark = remarks[2].text

                    # remark = self.extract_middle_text(str(vod), '<div class="state">', '</span>', 0)
                    # remark = remark.replace('\n', '').replace(' ', '')

                    # remark = vod.select_one('a img').text

                    #  =======================================

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks":  remark
                            }
                    videos.append(video)

        #  =======================================

        except:
            pass
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):  # XIANGQINGYE
        global pm
        did = ids[0]
        result = {}
        videos = []
        playurl = ''
        if 'http' not in did:
            did = xurl + did
        res1 = requests.get(url=did, headers=headerx)
        res1.encoding = "utf-8"
        res = res1.text

        #  =======================================

        tiaozhuan = '0'
        if tiaozhuan == '1':
            did = self.extract_middle_text(res, '<p class="play">', '</p>', 1, 'href="(.*?)"')
            if 'http' not in did:
                did = xurl + did
                res1 = requests.get(url=did, headers=headerx)
                res1.encoding = "utf-8"
                res = res1.text

        #  =======================================

        duoxian = '0'
        if duoxian == '1':
            doc = BeautifulSoup(res, 'lxml')
            soups = doc.find('span', class_='mxianlu animate__animated animate__fadeInUp')
            vods = soups.find_all('a')[0:]
            for vod in vods:
                url = 'https://www.mjzj.me/ ' + self.extract_middle_text(str(vod), '<a href="', '"', 0)
                res1 = requests.get(url, headers=headerx)
                res1.encoding = 'utf-8'
                res = res + res1.text

        #  =======================================

        content = '😸繁华🎉为您介绍剧情📢' + self.extract_middle_text(res,'class="text cor3">','</div>', 0)

        content = content.replace('\u3000\u3000', '')

        xianlu = self.extract_middle_text(res, '<div class="swiper-wrapper">','</div>',2, 'class=".*?"></i>&nbsp;(.*?)<span')
        #  class=".*?"></i>&nbsp;(.*?)<span

        xianlu=xianlu.replace('（点击切换', '').replace('）', '')

        bofang = self.extract_middle_text(res, '<ul class="anthology-list-play', '</ul>', 3,'href="(.*?)">(.*?)</a>')
        #  href="(.*?)">(.*?)</a>

        # bofang = bofang.replace(' ', '').replace('&nbsp;', '').replace('', '')

        # 提取演员和导演
        actors= self.extract_middle_text(res, '<strong class="cor6 r6">演员 :</strong><a', '</div>', 1, 'target="_blank">(.*?)<')
        # actors = actors.replace('/index.php/vod/search/actor/', '').replace('&nbsp;', '').replace('\xa0', '')

        # 提取导演信息
        director= self.extract_middle_text(res, '<strong class="cor6 r6">导演 :</strong><a', '</div>', 1, '>(.*?)</a>')

        # >(.*?)</a>
        # director = director.replace('\xa0', '')


        #  =======================================

        videos.append({
            "vod_id": did,
            "vod_actor": actors,
            "vod_director": director,
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
                     })

        #  =======================================

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):  # BOFANGYE
        parts = id.split("http")
        xiutan = 0
        if xiutan == 0:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]
            res = requests.get(url=after_https, headers=headerx)
            res = res.text

            url = self.extract_middle_text(res, '},"url":"', '"', 0).replace('', '')
            #  =======================================

            # url = base64.b64decode(url).decode('utf-8')

            # from urllib.parse import unquote
            # url = unquote(url)

            # from urllib.parse import unquote
            # import base64
            # base64_decoded_bytes = base64.b64decode(url)
            # base64_decoded_string = base64_decoded_bytes.decode('utf-8')
            # url = unquote(base64_decoded_string)
            # url="https://"+self.extract_middle_text(url,'https://','.m3u8',0)+'.m3u8'

            #  =======================================

            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
            return result

        #  =======================================

        if xiutan == 1:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]
            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = after_https
            result["header"] = headerx
            return result

    def searchContentPage(self, key, quick, page):  # SOUSOUYE
        result = {}
        videos = []
        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/index.php/vod/search.html?wd={key}'
            #  {xurl}/index.php/vod/search.html?wd={key}

        else:
            url = f'{xurl}/index.php/vod/search/page/{str(page)}/wd/{key}.html'
            #  {xurl}/index.php/vod/search/page/{str(page)}/wd/{key}.html

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="row-right hide")

        for soup in soups:
            vods = soup.find_all('div', class_="search-box")

        # for item in soups:
        #     vods = item.find_all('a')

            #  =======================================

            for vod in vods:
                names = vod.find('div', class_="thumb-txt")
                name = names.text.strip()
            #     name = names['title']
            #     name = names.find('a').text
            #     name = names.find('a')['title']


                # name = vod.find('a')['title']

                # names = vod.find_all('img')
                # name = names[1]['title']

                # name = self.extract_middle_text(str(vod), '<div class="name">', '</div>', 0)

                # name = vod.select_one('a img')['alt']

                # name = vod['title']

                #  =======================================

                ids = vod.find('div', class_="thumb-menu")
                id = ids.find('a')['href']

                # id = vod.find('a')['href']

                # ids = vod.find_all('a')
                # id = ids[1]['href']

                # id = self.extract_middle_text(str(vod), 'href="', '"', 0)

                # id = vod.select_one('h3 a')['href']

                # id = vod['href']

                #  =======================================

                # pics = vod.find('div', class_="module-card")
                # pic = pics.find('a')['data-original']

                pic = vod.find('img')['data-src']


                # pics = vod.find_all('a')
                # pic = pics[1]['data-original']

                # pic = self.extract_middle_text(str(vod), 'lay-src="', '"', 0)

                # pic = vod.select_one('a img')['data-original']

                # pic = vod['data-original']

                if 'http' not in pic:
                    pic = xurl + pic

                #  =======================================

                remarks = vod.find('span', class_="public-list-prb")
                remark = remarks.text.strip()
                # remark = remarks.find('span').text

                # remarks = vod.find_all('div')
                # remark = remarks[2].text

                # remark = self.extract_middle_text(str(vod), '<div class="state">', '</span>', 0)
                # remark = remark.replace('\n', '').replace(' ', '')

                # remark = vod.select_one('a img').text

                #  =======================================

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                        }
                videos.append(video)

        #  =======================================

        result['list'] = videos
        result['page'] = page
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None

"""

   =======================================

   换行 \n    零个或者多个空格 \s+    数字型 int    文本型 str    分页{} '年代':'2021'       

   性能要求高"lxml"   处理不规范的HTML"html5lib"   简单应用"html.parser"   解析XML"xml"

   =======================================

   /rss/index.xml?wd=爱情&page=1                                搜索有验证

   /index.php/ajax/suggest?mid=1&wd=爱情&page=1&limit=30        搜索有验证

   /index.php/ajax/data?mid=1&tid={cateId}&class={class}&area={area}&page={catePg}&limit=30   分类有验证

   =======================================

   aaa = self.extract_middle_text(res, 'bbb', 'ccc', 0)
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （不循环)   截取项  （不循环)   长用于直链  二次截取                0号子程序

   aaa =self.extract_middle_text(res, 'bbb', 'ccc',1,'html">(.*?)<')
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （不循环)   截取项  （循环)     长用于详情  和2号区别没有$$$        1号子程序

   aaa = self.extract_middle_text(res, 'bbb','ccc', 2,'<span class=".*?" id=".*?">(.*?)</span>')
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （不循环)   截取项  （循环)     只能用于线路数组  里面包含$$$       2号子程序

   aaa = self.extract_middle_text(res, 'bbb', 'ccc', 3,'href="(.*?)" class=".*?">(.*?)</a>')
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （循环)     截取项  （循环)    长用于播放数组                     3号子程序

   =======================================

"""

if __name__ == '__main__':
    spider_instance = Spider()

    # res=spider_instance.homeContent('filter')  #  分类🚨

    # res = spider_instance.homeVideoContent()  # 首页🚨

    # res=spider_instance.categoryContent('2', 2, 'filter', {})  #  分页🚨
    #
    res = spider_instance.detailContent(['https://ty1010.com/index.php/vod/detail/id/26.html'])  #  详情页🚨
    #
    # res = spider_instance.playerContent('1', '0https://ty1010.com/index.php/vod/play/id/72929/sid/8/nid/1.html', 'vipFlags')  #  播放页🚨

    # res = spider_instance.searchContentPage('爱情', 'quick', '2')  # 搜索页🚨

    print(res)

