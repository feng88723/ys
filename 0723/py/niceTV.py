"""

作者 乐哥🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================春色满园关不住,你是乐哥的小宝贝====================

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

xurl = "https://www.nice15578.cyou"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
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
        result = {"class": [{"type_id": "14", "type_name": "国产传媒🌠"},
                            {"type_id": "1", "type_name": "中文字幕🌠"},
                            {"type_id": "2", "type_name": "日本有码🌠"},
                            {"type_id": "3", "type_name": "日本无码🌠"},
                            {"type_id": "4", "type_name": "AV解说🌠"},
                            {"type_id": "5", "type_name": "cosplay🌠"},
                            {"type_id": "6", "type_name": "黑丝诱惑🌠"},
                            {"type_id": "7", "type_name": "SWAG🌠"},
                            {"type_id": "8", "type_name": "自拍偷拍🌠"},
                            {"type_id": "9", "type_name": "激情动漫🌠"},
                            {"type_id": "10", "type_name": "网红主播🌠"},
                            {"type_id": "11", "type_name": "探花系列🌠"},
                            {"type_id": "12", "type_name": "三级伦理🌠"},
                            {"type_id": "13", "type_name": "VR视角"},
                            {"type_id": "14", "type_name": "素人搭讪🌠"},
                            {"type_id": "10", "type_name": " 门事件🌠"}],

                  "list": [],

                  "filters": {"result": []}}

        return result

    def homeVideoContent(self):  
        videos = []
        try:
            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="row gutter-20")
  

            for soup in soups:
                vods = soup.find_all('div', class_="col-6")

        

                for vod in vods:
                    names = vod.find('img', class_="lazyload")

                    name = names['alt']
              

                    id = vod.find('a')['href']

                 

                    pic = vod.find('img')['data-src']

                

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('span', class_="label")
                    remark = remarks.text.strip()
             

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

    def categoryContent(self, cid, pg, filter, ext):  
        result = {}
        if pg:
            page = int(pg)
        else:
            page = 1

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
            url = f'{xurl}/index.php/vod/type/id/{cid}.html'
    

        else:
            url = f'{xurl}/index.php/vod/type/id/{cid}/page/{str(page)}.html'
 


        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="row gutter-20")

            for soup in soups:
                vods = soup.find_all('div', class_="video-img-box")


                for vod in vods:
                    names = vod.find('img', class_="lazyload")
                    
                    name = names['alt']
                

                    id = vod.find('a')['href']

  

                    pic = vod.find('img')['data-src']


                    if 'http' not in pic:
                        pic = xurl + pic

 

                    remarks = vod.find('span', class_="label")
                    remark = remarks.text.strip()
 

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks":  remark
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

    


   
        bofang = did
    

        videos.append({
            "vod_id": did,
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "乐哥专线",
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

            url = self.extract_middle_text(res, '"","url":"', '"', 0)
       

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
            page = '1'
        if page == '1':
            url = f'{xurl}/index.php/vod/search.html?wd={key}'
   

        else:
            url = f'{xurl}/index.php/vod/search/page/{str(page)}/wd/{key}.html'
       

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="row gutter-20")

        for soup in soups:
            vods = soup.find_all('div', class_="video-img-box")

     

            for vod in vods:
                names = vod.find('img', class_="lazyload")
     
                name = names['alt']
         

                id = vod.find('a')['href']

             

                pic = vod.find('img')['data-src']

          

                if 'http' not in pic:
                    pic = xurl + pic

            

                remarks = vod.find('span', class_="label")
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



