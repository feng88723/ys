# -*- coding: utf-8 -*-
# by @嗷呜
import json
import random
import re
import sys
import threading
import time
from base64 import b64decode, b64encode
from urllib.parse import urlparse, urljoin
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        try:self.proxies = json.loads(extend).get('proxy',{})
        except:self.proxies = {}
        
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        self.session.headers.update(self.headers)
        
        main_host = "https://51cg1.com"
        try:
            fetched_host = self.host_late(self.gethosts())
            self.host = fetched_host if fetched_host else main_host
        except Exception:
            self.host = main_host
            
        self.session.headers.update({'Origin': self.host, 'Referer': f"{self.host}/"})
        try: self.getcnh()
        except: pass

    def getName(self): pass
    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass
    def destroy(self): pass

    def homeContent(self, filter):
        res = self.session.get(self.host, proxies=self.proxies, timeout=10)
        data = self.getpq(res.text)
        result = {}
        classes = []
        filters = {}

        # 构造选择页码菜单
        page_options = [{'n': f'第 {i} 页', 'v': str(i)} for i in range(1, 51)]
        
        for k in list(data('.navbar-nav.mr-auto').children('li').items())[1:-3]:
            if k('ul'):
                for j in k('ul li').items():
                    href = j('a').attr('href')
                    if href:
                        clean_href = urlparse(href).path.strip('/')
                        if clean_href:
                            classes.append({'type_name': j('a').text().strip(), 'type_id': clean_href})
                            filters[clean_href] = [{'key': 'p', 'name': '选择页码', 'value': page_options}]
            else:
                href = k('a').attr('href')
                if href:
                    clean_href = urlparse(href).path.strip('/')
                    if clean_href:
                        classes.append({'type_name': k('a').text().strip(), 'type_id': clean_href})
                        filters[clean_href] = [{'key': 'p', 'name': '选择页码', 'value': page_options}]
                        
        result['class'] = classes
        result['filters'] = filters
        
        items = data('#index article a')
        if not items: items = data('article a')
        result['list'] = self.getlist(items)
        return result

    def getcnh(self):
        res = self.session.get(f"{self.host}/homeway.html", proxies=self.proxies, timeout=5)
        data = self.getpq(res.text)
        url = data('.post-content[itemprop="articleBody"] blockquote p').eq(0)('a').attr('href')
        parsed_url = urlparse(url)
        host = parsed_url.scheme + "://" + parsed_url.netloc
        self.setCache('host_51cn', host)

    def homeVideoContent(self): pass

    def categoryContent(self, tid, pg, filter, extend):
        # 1. 优先获取 extend 筛选菜单里的页码，否则使用 pg 参数
        target_pg = pg
        ext_dict = {}
        if isinstance(extend, str) and extend.strip():
            try: ext_dict = json.loads(extend)
            except: pass
        elif isinstance(extend, dict):
            ext_dict = extend

        if 'p' in ext_dict:
            target_pg = ext_dict['p']

        try:
            pg_int = int(target_pg)
        except:
            pg_int = 1

        if '@folder' in tid:
            id = tid.replace('@folder','')
            videos = self.getfod(id)
            pagecount = 1
        else:
            clean_tid = tid.replace(self.host, '').strip('/')
            
            # 🎯 构建备选 URL 列表：兼顾 /snsn/2/ 与 /snsn/page/2/ 两种路径模式
            urls_to_try = []
            if pg_int > 1:
                urls_to_try.append(f"{self.host}/{clean_tid}/{pg_int}/")
                urls_to_try.append(f"{self.host}/{clean_tid}/page/{pg_int}/")
            else:
                urls_to_try.append(f"{self.host}/{clean_tid}/")

            videos = []
            pagecount = 999

            for url in urls_to_try:
                try:
                    res = self.session.get(url, proxies=self.proxies, timeout=8)
                    res_text = res.text
                    data = self.getpq(res_text)
                    
                    items = data('#archive article a')
                    if not items: items = data('#index article a')
                    if not items: items = data('article a')
                    if not items: items = data('.post-list a')
                    if not items: items = data('.entry-media a')
                    if not items: items = data('a[itemprop="url"]')
                    
                    temp_videos = self.getlist(items, tid)
                    if temp_videos:
                        videos = temp_videos
                        try:
                            page_match = re.search(r'\d+/(\d+)', res_text)
                            if page_match:
                                pagecount = int(page_match.group(1))
                        except:
                            pagecount = 999
                        break
                except Exception:
                    continue

        result = {}
        result['list'] = videos
        result['page'] = pg_int
        result['pagecount'] = pagecount
        result['limit'] = len(videos) if len(videos) > 0 else 10
        result['total'] = pagecount * 20
        return result

    def getfod(self, id):
        url = f"{self.host}/{id.strip('/')}/"
        data = self.getpq(self.session.get(url, proxies=self.proxies).text)
        vdata=data('.post-content[itemprop="articleBody"]')
        r=['.txt-apps','.line','blockquote','.tags','.content-tabs']
        for i in r:vdata.remove(i)
        p=vdata('p')
        videos=[]
        for i,x in enumerate(vdata('h2').items()):
            c=i*2
            videos.append({
                'vod_id': p.eq(c)('a').attr('href'),
                'vod_name': p.eq(c).text(),
                'vod_pic': f"{self.getProxyUrl()}&url={p.eq(c+1)('img').attr('data-xkrkllgl')}&type=img",
                'vod_remarks':x.text()
                })
        return videos

    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}" if not ids[0].startswith('http') else ids[0]
        data = self.getpq(self.session.get(url, proxies=self.proxies).text)
        vod = {'vod_play_from': '51吃瓜'}
        try:
            clist = []
            if data('.tags .keywords a'):
                for k in data('.tags .keywords a').items():
                    title = k.text()
                    href = k.attr('href')
                    clist.append('[a=cr:' + json.dumps({'id': href, 'name': title}) + '/]' + title + '[/a]')
            vod['vod_content'] = ' '.join(clist)
        except:
            vod['vod_content'] = data('.post-title').text()
        try:
            plist=[]
            if data('.dplayer'):
                for c, k in enumerate(data('.dplayer').items(), start=1):
                    config = json.loads(k.attr('data-config'))
                    plist.append(f"视频{c}${config['video']['url']}")
            vod['vod_play_url']='#'.join(plist)
        except:
            vod['vod_play_url']=f"可能没有视频${url}"
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        try:
            pg_int = int(pg)
        except:
            pg_int = 1
        data=self.getpq(self.session.get(f"{self.host}/search/{key}/{pg_int}/", proxies=self.proxies).text)
        items = data('#archive article a')
        if not items: items = data('article a')
        return {'list':self.getlist(items),'page':pg_int}

    def playerContent(self, flag, id, vipFlags):
        p=1
        if '.m3u8' in id:p,id=0,self.proxy(id)
        return  {'parse': p, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        if param.get('type') == 'img':
            res=self.session.get(param['url'], proxies=self.proxies, timeout=10)
            return [200,res.headers.get('Content-Type'),self.aesimg(res.content)]
        elif param.get('type') == 'm3u8':return self.m3Proxy(param['url'])
        else:return self.tsProxy(param['url'])

    def proxy(self, data, type='m3u8'):
        if data and len(self.proxies):return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:return data

    def m3Proxy(self, url):
        url=self.d64(url)
        ydata = self.session.get(url, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = self.session.get(url, proxies=self.proxies).content.decode('utf-8')
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc
        iskey=True
        for index, string in enumerate(lines):
            if iskey and 'URI' in string:
                pattern = r'URI="([^"]*)"'
                match = re.search(pattern, string)
                if match:
                    lines[index] = re.sub(pattern, f'URI="{self.proxy(match.group(1), "mkey")}"', string)
                    iskey=False
                    continue
            if '#EXT' not in string:
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    def tsProxy(self, url):
        url = self.d64(url)
        data = self.session.get(url, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def d64(self, encoded_text):
        try:
            return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except: return ""

    def gethosts(self):
        url='https://cg51.com'
        curl=self.getCache('host_51cn')
        if curl:
            try:
                data=self.getpq(self.session.get(curl, proxies=self.proxies, timeout=3).text)('a').attr('href')
                if data:
                    parsed_url = urlparse(data)
                    url = parsed_url.scheme + "://" + parsed_url.netloc
            except: pass
        try:
            html = self.getpq(self.session.get(url, proxies=self.proxies, timeout=3).text)
            html_pattern = r"Base64\.decode\('([^']+)'\)"
            html_match = re.search(html_pattern, html('script').eq(-1).text(), re.DOTALL)
            if not html_match:raise Exception("未找到html")
            # 🛠️ 修复了这里的语法误写
            html = self.getpq(b64decode(html_match.group(1)).decode())('script').eq(-4).text()
            return self.hstr(html)
        except Exception as e:
            return ""

    def hstr(self, html):
        pattern = r"(backupLine\s*=\s*\[\])\s+(words\s*=)"
        replacement = r"\1, \2"
        html = re.sub(pattern, replacement, html)
        data = f"""
        var Vx = {{ range: function(s, e) {{ const r = []; for (let i = s; i < e; i++) r.push(i); return r; }}, map: function(a, c) {{ const r = []; for (let i = 0; i < a.length; i++) r.push(c(a[i], i, a)); return r; }} }};
        Array.prototype.random = function() {{ return this[Math.floor(Math.random() * this.length)]; }};
        var location = {{ protocol: "https:" }};
        function executeAndGetResults() {{ var allLines = lineAry.concat(backupLine); return JSON.stringify(allLines); }};
        {html}
        executeAndGetResults();
        """
        return self.p_qjs(data)

    def p_qjs(self, js_code):
        try:
            from com.whl.quickjs.wrapper import QuickJSContext
            ctx = QuickJSContext.create()
            result_json = ctx.evaluate(js_code)
            ctx.destroy()
            return json.loads(result_json)
        except: return []

    def get_domains(self): return []

    def host_late(self, url_list):
        if isinstance(url_list, str): urls = [u.strip() for u in url_list.split(',') if u.strip()]
        else: urls = url_list
        if not urls: return ''
        if len(urls) == 1: return urls[0]
        results = {}
        threads = []
        def test_host(url):
            try:
                start_time = time.time()
                self.session.head(url, timeout=1.5, allow_redirects=False)
                results[url] = (time.time() - start_time) * 1000
            except: results[url] = float('inf')
        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()
        for t in threads: t.join()
        valid = {k: v for k, v in results.items() if v != float('inf')}
        return min(valid.items(), key=lambda x: x[1])[0] if valid else urls[0]

    def getlist(self, data, tid=''):
        videos = []
        l = '/mrdg' in tid
        ad_keywords = ['loadbannerdirect', 'pg娱乐', 'pg电子', '同城', '约炮', '上门', '注册', '5888', '812.cc', '613.cc', '官方认证', '放水', '加微']
        
        for k in data.items():
            a = k.attr('href')
            b = k('h2').text() or k('h3').text() or k.attr('title') or k.text()
            c = k('span[itemprop="datePublished"]').text() or k('.date').text() or '最近'
            
            if a and b:
                title_clean = str(b).replace('\n', ' ').strip()
                title_lower = title_clean.lower()
                
                if any(kw in title_lower for kw in ad_keywords):
                    continue
                    
                vod_id = urlparse(a).path if a.startswith('http') else a
                vod_id = vod_id if vod_id.startswith('/') else f"/{vod_id}"
                
                videos.append({
                    'vod_id': f"{vod_id}{'@folder' if l else ''}",
                    'vod_name': title_clean,
                    'vod_pic': self.getimg(k('script').text()),
                    'vod_remarks': str(c).strip(),
                    'vod_tag': 'folder' if l else '',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def getimg(self, text):
        match = re.search(r"loadBannerDirect\('([^']+)'", text)
        if match:
            url = match.group(1)
            return f"{self.getProxyUrl()}&url={url}&type=img"
        else: return ''

    def aesimg(self, word):
        key = b'f5d965df75336270'
        iv = b'97b60394abc2fbe1'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(word), AES.block_size)
        return decrypted

    def getpq(self, data):
        try: return pq(data)
        except: return pq(data.encode('utf-8'))
