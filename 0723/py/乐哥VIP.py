"""

作者 乐哥 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================lege====================

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

xurl = "https://pze--eephouquoc.chuvvip6m16.xyz"

xurl2 = "https://pze--eephouquoc.chuvvip6m16.xyz/hflvvip"

headerx = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}

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
                            output += f"#{'📽️乐哥👉' + match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{'📽️乐哥👉' + match[1]}${number}{match[0]}"
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
                new_list = [f'✨乐哥👉{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "1", "type_name": "乐哥解说🌠"},
                            {"type_id": "3", "type_name": "乐哥中文🌠"},
                            {"type_id": "4", "type_name": "乐哥传媒🌠"},
                            {"type_id": "20", "type_name": "乐哥有码🌠"},
                            {"type_id": "21", "type_name": "乐哥无码🌠"},
                            {"type_id": "22", "type_name": "乐哥欧美🌠"},
                            {"type_id": "23", "type_name": "乐哥素人🌠"},
                            {"type_id": "24", "type_name": "乐哥乱伦🌠"},
                            {"type_id": "47", "type_name": "乐哥国产🌠"},
                            {"type_id": "29", "type_name": "乐哥网红🌠"},
                            {"type_id": "26", "type_name": "乐哥主播🌠"},
                            {"type_id": "28", "type_name": "乐哥三级🌠"},
                            {"type_id": "30", "type_name": "乐哥换脸🌠"},
                            {"type_id": "31", "type_name": "乐哥抖阴🌠"},
                            {"type_id": "75", "type_name": "乐哥SWAG🌠"},
                            {"type_id": "27", "type_name": "乐哥丝袜🌠"},
                            {"type_id": "52", "type_name": "乐哥动漫🌠"},
                            {"type_id": "25", "type_name": "乐哥制服🌠"},
                            {"type_id": "54", "type_name": "乐哥调教🌠"},
                            {"type_id": "55", "type_name": "乐哥主播🌠"},
                            {"type_id": "56", "type_name": "乐哥美乳🌠"},
                            {"type_id": "58", "type_name": "乐哥人妻🌠"},
                            {"type_id": "60", "type_name": "乐哥偷拍🌠"},
                            {"type_id": "62", "type_name": "乐哥明星🌠"},
                            {"type_id": "84", "type_name": "乐哥精选🌠"},
                            {"type_id": "80", "type_name": "乐哥探花🌠"},
                            {"type_id": "78", "type_name": "乐哥网红🌠"},
                            {"type_id": "77", "type_name": "乐哥cosplay🌠"},
                            {"type_id": "82", "type_name": "乐哥事件🌠"},
                            {"type_id": "79", "type_name": "乐哥网爆🌠"},
                            {"type_id": "81", "type_name": "乐哥萝莉🌠"},
                            {"type_id": "83", "type_name": "乐哥女优🌠"}],

                  "list": [],
                  "filters": {"1": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2018", "v": "2018"}]}],
                              "2": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2018", "v": "2018"}]}],
                              "3": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2018", "v": "2018"}]}],
                              "4": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2018", "v": "2018"}]}]}}

        return result

    def homeVideoContent(self):
        videos = []
        try:
            detail = requests.get(url=xurl2, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('ul', class_="thumbnail-group")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:
                    names = vod.find('div', class_="video-info")
                    name = names.find('h5').text

                    id = vod.find('a')['href']

                    pic = vod.find('img')['data-original']

                    video = {
                        "vod_id": id,
                        "vod_name": '乐哥📽️' + name,
                        "vod_pic": pic
                             }
                    videos.append(video)

            result = {'list': videos}
            return result
        except:
            pass

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        if pg:
            page = int(pg)
        else:
            page = 1
        page = int(pg)
        videos = []

        if '年代' in ext.keys():
            NdType = ext['年代']
        else:
            NdType = ''

        if page == '1':
            url = f'{xurl}/vodtype/{cid}/'

        else:
            url = f'{xurl}/vodtype/{cid}-{str(page)}/'

        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('ul', class_="thumbnail-group")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:
                    names = vod.find('div', class_="video-info")
                    name = names.find('h5').text

                    id = vod.find('a')['href']

                    pic = vod.find('img')['data-original']

                    video = {
                        "vod_id": id,
                        "vod_name": '乐哥📽️' + name,
                        "vod_pic": pic
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
        playurl = ''
        if 'http' not in did:
            did = xurl + did
        res1 = requests.get(url=did, headers=headerx)
        res1.encoding = "utf-8"
        res = res1.text

        encoded_string = self.extract_middle_text(res,'<li><label>&#26469;&#28304;: </label>','</li>', 0)
        import html
        content = html.unescape(encoded_string)
        content = content.replace('国产高清无码-免费福利视频分享大全', '乐哥的成就，如同一部波澜壮阔的史诗，让人心潮澎湃。在璀璨的聚光灯下，他终于站在了舞台的中央，成为了那颗最耀眼的星。他的成功，不仅仅是因为他的天赋异禀，更是因为他不懈的努力和坚持。从贫苦的出身到今日的辉煌，乐哥的每一步都充满了艰辛。他的童年，没有奢华的玩具，没有舒适的环境，有的只是对梦想的执着追求。在那些艰难的日子里，他以坚韧不拔的意志，一遍又一遍地磨练自己的演技。他欣赏了无数前辈的影片，从每一个角色、每一场戏中汲取灵感，不断学习，不断进步。乐哥的奋斗史，是一部充满汗水与泪水的励志篇章。他的成功，是对所有追梦人的最好启示：无论出身如何，只要有足够的努力和坚持，梦想总有实现的一天。他的成就，不仅仅是个人的荣耀，更是对所有坚持不懈、努力奋斗的人的鼓舞。今天，我们为乐哥欢呼，为他的成功喝彩。他的成功，不仅仅是因为他的才华，更是因为他的勤奋和毅力。他的故事告诉我们，成功从来不是偶然，而是无数次努力和坚持的结果。乐哥的今天，是对他过去所有努力的最好回报。我们期待乐哥在未来的日子里，能够继续以他的才华和努力，为我们带来更多优秀的作品。他的故事，将继续激励着每一个有梦想的人，去追逐，去实现。让我们为乐哥的成就鼓掌，为他的未来祝福，期待他在未来的日子里，能够继续发光发热，成为更多人心中的明星。')
        content = '😸乐哥🎉为您介绍剧情📢' + content

        encoded_string = self.extract_middle_text(res, '<li class="active"><a>','</a>',0, )
        import html
        xianlu = html.unescape(encoded_string)
        xianlu = xianlu.replace('HD在线点播地址', '😸乐哥专线')

        bofang = self.extract_middle_text(res, '<ul class="detail-play-list clearfix', '</ul>', 3,'href="(.*?)" class=".*?" style=".*?">(.*?)</a>')
        bofang = bofang.replace('在线播放', '性福一生')
        
        videos.append({
            "vod_id": did,
            "vod_actor": '😸乐哥 😸某女郎',
            "vod_director": '😸乐哥',
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
            res = requests.get(url=after_https, headers=headerx)
            res = res.text

            url = self.extract_middle_text(res, '"","url":"', '"', 0).replace('\\', '')


            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
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



