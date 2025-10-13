"""

作者 繁华 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
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

xurl = "https://www.jiaozi.me"

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
        result = {"class": [{"type_id": "1", "type_name": "电影🌠"},
                            {"type_id": "2", "type_name": "剧集🌠"},
                            {"type_id": "41", "type_name": "动画🌠"}],

                   "list": [],
        "filters": {
            "1": [
                {"key": "剧情", "name": "剧情", "value": [

                    {"n": "战争", "v": "战争"},
                    {"n": "同性", "v": "同性"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "爱情", "v": "爱情"},
                    {"n": "家庭", "v": "家庭"},
                    {"n": "励志", "v": "励志"},
                    {"n": "悬疑", "v": "悬疑"},
                    {"n": "动作", "v": "动作"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "历史", "v": "历史"},
                    {"n": "惊悚", "v": "惊悚"},
                    {"n": "音乐", "v": "音乐"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "喜剧", "v": "喜剧"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "美国", "v": "美国"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "英国", "v": "英国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "中国", "v": "中国"},
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
                    {"n": "more", "v": "more"}
                ]},
                {"key": "状态", "name": "状态", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "完结", "v": "完结"},
                    {"n": "连载中", "v": "连载中"}
                ]},
                {"key": "排序", "name": "排序", "value": [
                    {"n": "时间", "v": "time"},
                    {"n": "评分", "v": "score"}
                ]}
            ],
            "2": [
                {"key": "剧情", "name": "剧情", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "战争", "v": "战争"},
                    {"n": "同性", "v": "同性"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "爱情", "v": "爱情"},
                    {"n": "家庭", "v": "家庭"},
                    {"n": "励志", "v": "励志"},
                    {"n": "悬疑", "v": "悬疑"},
                    {"n": "动作", "v": "动作"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "历史", "v": "历史"},
                    {"n": "惊悚", "v": "惊悚"},
                    {"n": "音乐", "v": "音乐"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "喜剧", "v": "喜剧"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "美国", "v": "美国"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "英国", "v": "英国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "中国", "v": "中国"},
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
                    {"n": "more", "v": "more"}
                ]},
                {"key": "状态", "name": "状态", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "完结", "v": "完结"},
                    {"n": "连载中", "v": "连载中"}
                ]},
                {"key": "排序", "name": "排序", "value": [
                    {"n": "时间", "v": "time"},
                    {"n": "评分", "v": "score"}
                ]}
            ],
            "41": [
                {"key": "剧情", "name": "剧情", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "战争", "v": "战争"},
                    {"n": "同性", "v": "同性"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "爱情", "v": "爱情"},
                    {"n": "家庭", "v": "家庭"},
                    {"n": "励志", "v": "励志"},
                    {"n": "悬疑", "v": "悬疑"},
                    {"n": "动作", "v": "动作"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "历史", "v": "历史"},
                    {"n": "惊悚", "v": "惊悚"},
                    {"n": "音乐", "v": "音乐"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "喜剧", "v": "喜剧"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "美国", "v": "美国"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "英国", "v": "英国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "中国", "v": "中国"},
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
                    {"n": "more", "v": "more"}
                ]},
                {"key": "状态", "name": "状态", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "完结", "v": "完结"},
                    {"n": "连载中", "v": "连载中"}
                ]},
                {"key": "排序", "name": "排序", "value": [
                    {"n": "时间", "v": "time"},
                    {"n": "评分", "v": "score"}
                ]}
            ]
        }
    }


        return result

    def homeVideoContent(self):  # SHOUYE
        videos = []
        try:
            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")
            soups = doc.find_all('ul', class_="myui-vodlist clearfix")

            # for soup in soups:
            #     vods = soup.find_all('a', class_="pic-img")

            for soup in soups:
                vods = soup.find_all('li')

                #  =======================================

                for vod in vods:
                    # names = vod.find('div', class_="name")
                    # name = names.text.strip()
                    # name = names['title']
                    # name = names.find('a').text
                    # name = names.find('a')['title']

                    name = vod.find('a')['title']

                    # names = vod.find_all('img')
                    # name = names[1]['title']

                    # name = self.extract_middle_text(str(vod), 'alt="', '"', 0)

                    # name= vod.select_one('div img')['alt']

                    # name = vod['title']

                    #  =======================================

                    # ids = vod.find('div', class_="name")
                    # id = ids.find('a')['href']

                    id = vod.find('a')['href']

                    # ids = vod.find_all('a')
                    # id = ids[1]['href']

                    # id = self.extract_middle_text(str(vod), 'href="', '"', 0)

                    # id = vod.select_one('h3 a')['href']

                    # id = vod['href']

                    #  =======================================

                    # pics = vod.find('div', class_="module-card")
                    # pic = pics.find('a')['data-original']

                    pic = vod.find('a')['data-original']

                    # pics = vod.find_all('a')
                    # pic = pics[1]['data-original']

                    # pic = self.extract_middle_text(str(vod), 'lay-src="', '"', 0)

                    # pic = vod.select_one('div img')['src']

                    # pic = vod['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    #  =======================================

                    remarks = vod.find('span', class_="pic-text text-right")
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
                        "vod_remarks": remark
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
        if '状态' in ext.keys():
            ztType = ext['状态']
        else:
            ztType = ''
        if '排序' in ext.keys():
            pxType = ext['排序']
        else:
            pxType = ''

        if page == '1':
            url = f'{xurl}/search.php?searchtype=5&tid={cid}'
         #{xurl}/search.php?searchtype=5&tid={cid}

        else:
            url = f'{xurl}/search.php?page={str(page)}&searchtype=5&order={pxType}&tid={cid}&area={DqType}&year={NdType}&letter=&yuyan=&state={ztType}&money=&ver=&jq={JqType}'
             # {xurl}/search.php?page={str(page)}&searchtype=5&order={pxType}&tid={cid}&area={DqType?&year={NdType}&letter=&yuyan=&state={ztType}&money=&ver=&jq={JqType}
           
        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('ul', class_="myui-vodlist clearfix")

            for soup in soups:
                vods = soup.find_all('a', class_="pic-img")

            for soup in soups:
                vods = soup.find_all('li')

                #  =======================================

                for vod in vods:
                    # names = vod.find('a', class_="lazyload")
                #     # name = names.text.strip()
                #     name = names['title']
                    # name = names.find('a').text
                    # na me = names.find('a')['title']

                    name = vod.find('a')['title']

                    # names = vod.find_all('img')
                    # name = names[1]['title']

                    # name = self.extract_middle_text(str(vod), '<div class="name">', '</div>', 0)

                    # name = vod.select_one('a img')['alt']

                    # name = vod['title']

                    #  =======================================

                    # ids = vod.find('a', class_="lazyload")
                    # id = ids['href']

                    id = vod.find('a')['href']

                    # ids = vod.find_all('a')
                    # id = ids[1]['href']

                    # id = self.extract_middle_text(str(vod), 'href="', '"', 0)

                    # id = vod.select_one('h3 a')['href']

                    # id = vod['href']

                    #  =======================================

                    # pics = vod.find('a', class_="lazyload")
                    # pic = pics['data-original']

                    pic = vod.find('a')['data-original']

                    # pics = vod.find_all('a')
                    # pic = pics[1]['data-original']

                    # pic = self.extract_middle_text(str(vod), 'lay-src="', '"', 0)

                    # pic = vod.select_one('a img')['data-original']

                    # pic = vod['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    #  =======================================

                    remarks = vod.find('span', class_="pic-text text-right")
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

        content = '😸繁华🎉为您介绍剧情📢' + self.extract_middle_text(res,'</font>，剧情：','</p>', 0)
        content = content.replace('&emsp;&emsp', '').replace('\n\t\t\t', '')


        xianlu = self.extract_middle_text(res, '<ul class="nav nav-tabs active">','</ul>',2, 'data-toggle=".*?">(.*?)</a>')
        #  data-toggle="tab">(.*?)</a>

        # xianlu = xianlu.replace(' ', '').replace('&nbsp;', '').replace('', '')

        bofang = self.extract_middle_text(res, '<ul class="myui-content__list', '</ul>', 3,'href="(.*?)" target=".*?">(.*?)</a>')
        #  href="(.*?)" target=".*?">(.*?)</a>

        # bofang = bofang.replace(' ', '').replace('&nbsp;', '').replace('', '')

        # 提取演员和导演
        actors= self.extract_middle_text(res, '<span class="text-muted">演员：</span>', '</p>', 0, '>(.*?)</a>')
        actors = actors.replace('/search.php?searchword=', '').replace('&nbsp;', '').replace('\xa0', '')
        # print(actors)
        # 提取导演信息
        director= self.extract_middle_text(res, '<span class="text-muted">导演：</span>', '</p>', 0, '>(.*?)</a>')
        director = director.replace('\xa0', '')
        # print(director)


        #  =======================================
        #
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

        if len(parts) > 1:
            before_https, after_https = parts[0], 'http' + parts[1]
            res = requests.get(url=after_https, headers=headerx)
            res = res.text

            url = self.extract_middle_text(res, 'var now="', '"', 0).replace('\\', '')

            headerx2 = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36',
                'Referer': 'https://www.jiaozi.me/'
            }
            url2 = 'https://www.jiaozi.me/static/js/Dplayer/play.js?v=1.998'

            res2 = requests.get(url2, headers=headerx2).text
            url2 = self.extract_middle_text(res2, 'jxAapi="', '"', 0).replace('\\', '')

            url3 = url2 + url

            if 'mp4' in url3:
                xiutan = 0
            else:
                xiutan = 1

        result = {}
        result["parse"] = xiutan
        result["playUrl"] = ''
        result["url"] = url3 if xiutan == 0 else after_https
        result["header"] = headerx2 if xiutan == 0 else headerx
        return result

    def searchContentPage(self, key, quick, page):  # SOUSOUYE
        result = {}
        videos = []
        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/search.php?searchword={key}&submit='
            #  {xurl}/search.php?searchword={key}&submit=

        else:
            url = f'{xurl}/search.php?page={str(page)}&searchword={key}&searchtype='
            #  {xurl}/search.php?page={str(page)}&searchword={key}&searchtype=

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('ul', class_="clearfix")

        for soup in soups:
            vods = soup.find_all('a', class_="lazyload")

        # for item in soups:
        #     vods = item.find_all('li')

            #  =======================================

            for vod in vods:
            #     names = vod.find('div', class_="name")
            #     name = names.text.strip()
            #     name = names['title']
            #     name = names.find('a').text
            #     name = names.find('a')['title']

                # name = vod.find('a')['title']

                # names = vod.find_all('img')
                # name = names[1]['title']

                # name = self.extract_middle_text(str(vod), '<div class="name">', '</div>', 0)

                # name = vod.select_one('a img')['alt']

                name = vod['title']

                #  =======================================

                # ids = vod.find('div', class_="name")
                # id = ids.find('a')['href']

                # id = vod.find('a')['href']

                # ids = vod.find_all('a')
                # id = ids[1]['href']

                # id = self.extract_middle_text(str(vod), 'href="', '"', 0)

                # id = vod.select_one('h3 a')['href']

                id = vod['href']

                #  =======================================

                # pics = vod.find('div', class_="module-card")
                # pic = pics.find('a')['data-original']

                # pic = vod.find('a')['data-original']

                # pics = vod.find_all('a')
                # pic = pics[1]['data-original']

                # pic = self.extract_middle_text(str(vod), 'lay-src="', '"', 0)

                # pic = vod.select_one('a img')['data-original']

                pic = vod['data-original']

                if 'http' not in pic:
                    pic = xurl + pic

                #  =======================================

                remarks = vod.find('span', class_="pic-text")
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
                    "vod_name":  name,
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


if __name__ == '__main__':
    spider_instance = Spider()

    # res=spider_instance.homeContent('filter')  #  分类🚨

    # res = spider_instance.homeVideoContent()  # 首页🚨

    res=spider_instance.categoryContent('2', 2, 'filter', {})  #  分页🚨

    # res = spider_instance.detailContent(['https://www.jiaozi.me/movie/index2332.html'])  #  详情页🚨

    # res = spider_instance.playerContent('1', '0https://www.mjzj.me/74354-1-1.html', 'vipFlags')  #  播放页🚨

    # res = spider_instance.searchContentPage('爱情', 'quick', '2')  # 搜索页🚨

    print(res)
