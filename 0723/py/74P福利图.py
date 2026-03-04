import re
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from base.spider import Spider

# 忽略 SSL 警告
requests.packages.urllib3.disable_warnings()

class Spider(Spider):
    def getName(self): return "74P福利"
    
    def init(self, extend=""):
        super().init(extend)
        self.base_url = "https://www.74p.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.base_url + '/',
            'Connection': 'keep-alive'
        }
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def destroy(self):
        if hasattr(self, 'session'): self.session.close()

    def fetch(self, url):
        try:
            return self.session.get(url, headers=self.headers, timeout=10, verify=False)
        except:
            return None

    def homeContent(self, filter):
        cats = [
            {"type_name": "=== 写真 ===", "type_id": "ignore"},
            {"type_name": "秀人网", "type_id": "xiurenwang"},
            {"type_name": "语画界", "type_id": "yuhuajie"},
            {"type_name": "花漾", "type_id": "huayang"},
            {"type_name": "星颜社", "type_id": "xingyanshe"},
            {"type_name": "嗲囡囡", "type_id": "feilin"},
            {"type_name": "爱蜜社", "type_id": "aimishe"},
            {"type_name": "波萝社", "type_id": "boluoshe"},
            {"type_name": "尤物馆", "type_id": "youwuguan"},
            {"type_name": "优星馆", "type_id": "uxing"},
            {"type_name": "影私荟", "type_id": "wings"}, 
            {"type_name": "星乐园", "type_id": "xingleyuan"},
            {"type_name": "蜜桃社", "type_id": "miitao"},
            {"type_name": "顽味生活", "type_id": "taste"},
            {"type_name": "魅妍社", "type_id": "meiyanshe"},
            {"type_name": "美媛馆", "type_id": "meiyuanguan"},
            {"type_name": "糖果画报", "type_id": "candyhuabao"},
            {"type_name": "花の颜", "type_id": "huayan"},
            {"type_name": "模范学院", "type_id": "mofanxueyuan"},
            {"type_name": "艺图语", "type_id": "yituyu"},
            {"type_name": "爱美足", "type_id": "mzsock"}, 
            {"type_name": "=== 漫画 ===", "type_id": "ignore"},
            {"type_name": "日本漫画", "type_id": "comic/category/jp"},
            {"type_name": "韩国漫画", "type_id": "comic/category/kr"},
            {"type_name": "=== 小说 ===", "type_id": "ignore"},
            {"type_name": "都市", "type_id": "novel/category/Urban"},
            {"type_name": "校园", "type_id": "novel/category/campus"},
            {"type_name": "乱伦", "type_id": "novel/category/Incestuous"},
            {"type_name": "玄幻", "type_id": "novel/category/Xuanhuan"},
            {"type_name": "系统", "type_id": "novel/category/Goldfinger"},
            {"type_name": "穿越", "type_id": "novel/category/traverse"},
            {"type_name": "武侠", "type_id": "novel/category/Wuxia"},
            {"type_name": "奇幻", "type_id": "novel/category/Fantasy"},
            {"type_name": "乡村", "type_id": "novel/category/Rural"},
            {"type_name": "历史", "type_id": "novel/category/Historical"},
            {"type_name": "明星", "type_id": "novel/category/Celebrity"},
            {"type_name": "异能", "type_id": "novel/category/Superpower"},
            {"type_name": "科幻", "type_id": "novel/category/Science"},
            {"type_name": "同人", "type_id": "novel/category/Fan"}
        ]
        return {'class': [c for c in cats if c['type_id'] != 'ignore']}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.base_url}/{tid}/page/{pg}"
        return self._get_post_list(url, int(pg))

    def _get_post_list(self, url, pg):
        resp = self.fetch(url)
        vlist = []
        if resp and resp.status_code == 200:
            resp.encoding = 'utf-8'
            html = resp.text
            
            # 定位列表区域
            list_block = html
            main_block = re.search(r'(?:id="index_ajax_list"|class="site-main")[^>]*>(.*?)<(?:footer|aside)', html, re.S)
            if main_block: list_block = main_block.group(1)
            
            items = re.findall(r'<li[^>]*>(.*?)</li>', list_block, re.S)
            for item in items:
                href_match = re.search(r'href=["\']([^"\']+)["\']', item)
                if not href_match: continue
                href = href_match.group(1)
                
                # 过滤无效链接
                if any(x in href for x in ['.css', '.js', 'templates/', 'wp-includes']): continue

                # 提取图片
                img_match = re.search(r'data-original=["\']([^"\']+)["\']', item) or re.search(r'src=["\']([^"\']+)["\']', item)
                pic = img_match.group(1) if img_match else "https://www.74p.net/static/images/cover.png"
                
                # 提取标题
                title_match = re.search(r'title=["\']([^"\']+)["\']', item)
                name = title_match.group(1) if title_match else re.sub(r'<[^>]+>', '', item).strip().split('\n')[0]
                if name.startswith('.') or '{' in name or len(name) > 100: continue
                
                # 补全链接
                if href.startswith('//'): href = 'https:' + href
                elif href.startswith('/'): href = self.base_url + href

                vlist.append({
                    'vod_id': href,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': '点击查看',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        
        return {'list': vlist, 'page': pg, 'pagecount': pg + 1 if len(vlist) >= 15 else pg, 'limit': 20, 'total': 9999}

    def searchContent(self, key, quick, pg=1):
        search_path = f"/search/{key}"
        # 根据搜索词调整 Referer，模拟真实行为
        self.headers['Referer'] = f"{self.base_url}/comic" if "漫画" in key else f"{self.base_url}/novel"
        url = f"{self.base_url}{search_path}/page/{pg}" if int(pg) > 1 else f"{self.base_url}{search_path}"
        return self._get_post_list(url, int(pg))

    def detailContent(self, ids):
        url = ids[0]
        resp = self.fetch(url)
        if not resp: return {'list': []}

        resp.encoding = 'utf-8'
        html = resp.text
        
        vod = {
            'vod_id': url,
            'vod_name': '',
            'vod_pic': '',
            'type_name': '资源',
            'vod_content': '',
            'vod_play_from': '74P资源',
            'vod_play_url': ''
        }

        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        if h1: vod['vod_name'] = h1.group(1)
        
        desc_match = re.search(r'<div class="entry-content"[^>]*>(.*?)</div>', html, re.S)
        if desc_match: 
            vod['vod_content'] = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()[:200]
        
        # 抓取并排序章节
        raw_links = re.findall(r'<a[^>]+href=["\']([^"\']*/(?:comic|novel)/chapter/[^"\']+)["\'][^>]*>(.*?)</a>', html)
        
        if raw_links:
            # 去重
            unique_map = {}
            for href, name in raw_links:
                if href.startswith('//'): href = 'https:' + href
                elif href.startswith('/'): href = self.base_url + href
                unique_map[href] = name.strip()
            
            # 排序：提取章节名里的数字进行升序排列
            link_list = list(unique_map.items())
            try:
                link_list.sort(key=lambda x: int(re.findall(r'(\d+)', x[1])[0]) if re.findall(r'(\d+)', x[1]) else 0)
            except: pass
            
            vod['vod_play_url'] = "#".join([f"{name}${href}" for href, name in link_list])
        else:
            vod['vod_play_url'] = f"在线观看${url}"

        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        # 协议分流：小说走 novel://，图片走 pics://
        if "novel" in id:
            novel_data = self._scrape_novel_content(id)
            ret = f"novel://{json.dumps(novel_data, ensure_ascii=False)}"
        else:
            images = self._scrape_all_images(id)
            ret = f'pics://{"&&".join(images)}'

        return {"parse": 0, "playUrl": "", "url": ret, "header": ""}

    def _scrape_novel_content(self, url):
        data = {'title': "加载中", 'content': "内容读取失败"}
        resp = self.fetch(url)
        if resp and resp.status_code == 200:
            resp.encoding = 'utf-8'
            html = resp.text
            
            h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html)
            if h1: data['title'] = h1.group(1).strip()

            content = re.search(r'(?:class="entry-content"|id="content"|class="single-content")[^>]*>(.*?)<(?:div class="related|footer|section|div id="comments")', html, re.S)
            if content:
                raw = content.group(1)
                # 清洗：去脚本 -> 标签转换行 -> 去标签 -> 处理实体 -> 规范换行
                raw = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw, flags=re.S | re.I)
                raw = re.sub(r'(<br\s*?/?>|</p>|</div>)', '\n', raw, flags=re.I)
                raw = re.sub(r'<[^>]+>', '', raw)
                raw = raw.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace(u'\u3000', ' ')
                data['content'] = re.sub(r'\n\s*\n', '\n\n', raw).strip()
        return data

    def _scrape_all_images(self, url):
        images = []
        visited = set()
        current_url = url
        page = 1
        
        while page <= 100: # 限制最大页数防止死循环
            if current_url in visited: break
            visited.add(current_url)
            
            resp = self.fetch(current_url)
            if not resp or resp.status_code != 200: break
            resp.encoding = 'utf-8'
            html = resp.text
            
            # 提取正文图片
            content_match = re.search(r'(?:id="content"|class="entry-content"|class="single-content"|class="post-content")[^>]*>(.*?)<(?:div class="related|footer|section|div id="comments")', html, re.S)
            content_html = content_match.group(1) if content_match else html
            
            img_matches = re.findall(r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+)["\']', content_html)
            has_new_image = False
            
            for src in img_matches:
                # 过滤杂图
                if any(x in src.lower() for x in ['.gif', '.svg', 'logo', 'avatar', 'icon', 'loader']): continue
                if '/covers/' in src: continue
                
                # 补全链接
                if src.startswith('//'): src = 'https:' + src
                elif src.startswith('/'): src = self.base_url + src
                
                # 过滤外链广告
                if src.startswith('http') and '74p.net' not in src: continue
                
                if src not in images:
                    images.append(src)
                    has_new_image = True

            if not has_new_image and page > 1: break

            # 翻页查找
            next_url = None
            # 匹配各种形式的下一页链接
            next_patterns = [
                r'<a[^>]+class=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']', 
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*next[^"\']*["\']',
                r'<a[^>]+rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']',
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(?:下一页|Next|»|&raquo;)'
            ]
            for pat in next_patterns:
                match = re.search(pat, html, re.I)
                if match:
                    href = match.group(1)
                    if href.startswith('//'): next_url = 'https:' + href
                    elif href.startswith('/'): next_url = self.base_url + href
                    else: next_url = href
                    break
            
            # 备用翻页逻辑：尝试构造URL
            if not next_url and ('page-numbers' in html or 'pagination' in html):
                if "/page/" in current_url:
                    next_url = re.sub(r'/page/(\d+)', lambda m: f"/page/{int(m.group(1))+1}", current_url)
                else:
                    clean = current_url.rstrip('/')
                    next_url = clean.replace('.html', f'/page/{page+1}.html') if clean.endswith('.html') else f"{clean}/page/{page+1}"
            
            if not next_url: break
            current_url = next_url
            page += 1
            
        return images
