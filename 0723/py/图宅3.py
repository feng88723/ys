import sys, re, json, requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from base.spider import Spider

requests.packages.urllib3.disable_warnings()

class Spider(Spider):
    def getName(self): return "图宅"
    
    def init(self, extend=""):
        super().init(extend)
        self.siteUrl = "https://www.tuzac.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36',
            'Referer': 'https://www.tuzac.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        self.sess = requests.Session()
        self.sess.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])))

    def fetch(self, url):
        try: 
            # 处理年龄验证
            # 减少超时时间，提高请求速度
            r = self.sess.get(url, headers=self.headers, timeout=5, verify=False, stream=False)
            if r and r.ok:
                # 检查是否有年龄验证
                if '您是否已满18岁' in r.text or 'age verify' in r.text.lower() or 'age-modal' in r.text:
                    # 提交年龄验证
                    data = {'age_verify': '1'}
                    # 更新请求头，添加表单提交相关的头
                    post_headers = self.headers.copy()
                    post_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                    r = self.sess.post(url, data=data, headers=post_headers, timeout=5, verify=False, stream=False)
                    # 再次获取页面
                    if r and r.ok:
                        r = self.sess.get(url, headers=self.headers, timeout=5, verify=False, stream=False)
                return r
            return r
        except Exception as e:
            return None

    def homeContent(self, filter):
        cats = [
            {"type_name":"最新","type_id":"newest"},
            {"type_name":"女神","type_id":"tags/女神"},
            {"type_name":"美胸","type_id":"tags/美胸"},
            {"type_name":"AI","type_id":"tags/ai美女"},
            {"type_name":"黑丝","type_id":"tags/黑丝"},
            {"type_name":"大尺度","type_id":"tags/大尺度"},
            {"type_name":"无圣光","type_id":"tags/无圣光"},
            {"type_name":"萝莉","type_id":"tags/萝莉"},
            {"type_name":"Cosplay","type_id":"tags/Cosplay"},
            {"type_name":"私房","type_id":"tags/私房"},
            {"type_name":"尤物","type_id":"tags/尤物"},
            {"type_name":"全部分类","type_id":"all-tags"}
        ]
        return {'class': cats}

    def categoryContent(self, tid, pg, filter, extend):
        # 构建分类URL
        if tid == 'newest':
            url = f"{self.siteUrl}/{tid}/{pg}"
        elif tid == 'all-tags':
            url = f"{self.siteUrl}/{tid}"
        else:
            # 处理标签分类
            url = f"{self.siteUrl}/{tid}/{pg}"
        return self.postList(url, int(pg))

    def postList(self, url, pg):
        r = self.fetch(url)
        l = []
        if r and r.ok:
            h = r.text
            # 尝试多种文章匹配方式
            article_patterns = [
                r'<article[^>]*>(.*?)</article>',
                r'<div[^>]*class=["\']?post["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?entry["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?item["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?article["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?post-item["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?article-item["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?item-card["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?card["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?post-card["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?tag-item["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?tag-card["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?category-item["\']?[^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']?category-card["\']?[^>]*>(.*?)</div>'
            ]
            
            # 去重集合
            seen_urls = set()
            
            for pattern in article_patterns:
                for m in re.finditer(pattern, h, re.S):
                    t = m.group(1)
                    href = re.search(r'href=["\']([^"\']+)["\']', t)
                    img = re.search(r'data-src=["\']([^"\']+)["\']', t) or re.search(r'src=["\']([^"\']+)["\']', t)
                    title = re.search(r'title=["\']([^"\']+)["\']', t) or re.search(r'<h\d[^>]*>(.*?)</h\d>', t, re.S) or re.search(r'<span[^>]*>(.*?)</span>', t, re.S) or re.search(r'<div[^>]*>(.*?)</div>', t, re.S)
                    note = re.search(r'teaser-file-info"[^>]*>(.*?)<', t, re.S) or re.search(r'<p[^>]*>(.*?)<', t, re.S)
                    
                    # 过滤条件
                    if href and href.group(1) not in seen_urls:
                        u = href.group(1)
                        # 过滤掉导航链接和非文章链接
                        if any(keyword in u.lower() for keyword in ['#', 'javascript:', 'search', 'login', 'register', 'home', 'about', 'contact']):
                            continue
                        
                        # 提取标题
                        title_text = ""
                        if title:
                            title_text = title.group(1).strip()
                            # 过滤掉导航相关的标题
                            if any(keyword in title_text.lower() for keyword in ['go back', 'search', '返回', '搜索']):
                                continue
                            # 过滤掉空标题或只有空格的标题
                            if not title_text or title_text.isspace():
                                continue
                        else:
                            continue
                        
                        # 提取图片
                        p = ""
                        if img:
                            p = img.group(1)
                            # 处理图片URL
                            if p.startswith("//"): p = "https:" + p
                            if not p.startswith("http") and p:
                                if p.startswith("/"):
                                    p = self.siteUrl + p
                                else:
                                    p = self.siteUrl + '/' + p
                        else:
                            # 跳过没有图片的项目
                            continue
                        
                        # 提取备注
                        note_text = note.group(1).strip() if note else ""
                        
                        # 添加到列表
                        seen_urls.add(u)
                        l.append({
                            'vod_id': self.siteUrl + u if u.startswith("/") else u,
                            'vod_name': title_text,
                            'vod_pic': p,
                            'vod_remarks': note_text,
                            'style': {"type": "rect", "ratio": 1.33}
                        })
        return {'list': l, 'page': pg, 'pagecount': pg + 1 if len(l) else pg, 'limit': 20, 'total': 9999}

    def detailContent(self, ids):
        return {'list': [{'vod_id': ids[0], 'vod_name': '', 'type_name': '美图', 'vod_play_from': '图宅', 'vod_play_url': '点击浏览$' + ids[0]}]}

    def searchContent(self, key, quick, pg=1):
        # 构建搜索URL
        url = f"{self.siteUrl}/search/page/{pg}?s={key}"
        return self.postList(url, int(pg))

    def playerContent(self, flag, id, vipFlags):
        seen = set()
        imgs = []
        
        # 处理第一页
        r = self.fetch(id)
        if r and r.ok:
            h = r.text
            
            # 提取当前页面的图片
            page_imgs = self.getImgs(h)
            for img in page_imgs:
                if img not in seen:
                    seen.add(img)
                    imgs.append(img)
            
            # 提取分页信息
            try:
                # 查找末页链接，获取最大页码
                max_pg = 1
                last_page_match = re.search(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>末页', h)
                if last_page_match:
                    last_url = last_page_match.group(1)
                    # 从末页URL中提取at参数
                    at_match = re.search(r'\?at=(\d+)', last_url)
                    if at_match:
                        max_pg = int(at_match.group(1))
                else:
                    # 如果没有末页链接，查找显示的页码
                    page_numbers = re.findall(r'<a[^>]*href=["\'][^"\']*\?at=(\d+)["\'][^>]*>\d+</a>', h)
                    if page_numbers:
                        max_pg = max(map(int, page_numbers))
                
                # 遍历所有分页
                if max_pg > 1:
                    for i in range(2, max_pg + 1):
                        # 直接构造分页URL
                        if '?at=' in id:
                            page_url = re.sub(r'\?at=\d+', f'?at={i}', id)
                        elif '?page=' in id:
                            page_url = re.sub(r'\?page=\d+', f'?page={i}', id)
                        elif '?' in id:
                            page_url = f"{id}&at={i}"
                        else:
                            page_url = f"{id}?at={i}"
                        # 获取分页内容
                        r2 = self.fetch(page_url)
                        if r2 and r2.ok:
                            page_imgs = self.getImgs(r2.text)
                            for img in page_imgs:
                                if img not in seen:
                                    seen.add(img)
                                    imgs.append(img)
            except Exception as e:
                pass
        
        return {"parse": 0, "url": "pics://" + "&&".join(imgs) if imgs else "", "header": ""}

    def getImgs(self, h):
        seen = set()
        imgs = []
        
        # 提取主要内容区域，减少匹配范围
        content_match = re.search(r'<div class="file-detail">(.*?)<div id="pager"', h, re.S)
        if not content_match:
            content_match = re.search(r'<div class="file-detail">(.*?)<div class="related-file">', h, re.S)
        if not content_match:
            content_match = re.search(r'<div class="file-detail">(.*?)</div>', h, re.S)
        
        if content_match:
            t = content_match.group(1)
        else:
            # 如果没有找到主要内容区域，使用整个页面
            t = h
        
        # 优化正则表达式，减少回溯
        # 提取data-src属性
        data_src_pattern = re.compile(r'<img[^>]*data-src=["\']([^"\']+)["\']')
        data_src_imgs = data_src_pattern.findall(t)
        for img_url in data_src_imgs:
            if self._process_image_url(img_url, seen):
                imgs.append(img_url)
        
        # 提取src属性
        src_pattern = re.compile(r'<img[^>]*src=["\']([^"\']+)["\']')
        src_imgs = src_pattern.findall(t)
        for img_url in src_imgs:
            if self._process_image_url(img_url, seen):
                imgs.append(img_url)
        
        return imgs
    
    def _process_image_url(self, img_url, seen):
        """处理图片URL并去重"""
        if not img_url:
            return False
        
        # 过滤掉小图标和无关图片
        if any(ext in img_url.lower() for ext in ['.gif', '.ico', 'avatar', 'logo']):
            return False
        
        # 处理相对URL
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif not img_url.startswith("http"):
            # 尝试构造绝对URL
            if img_url.startswith("/"):
                img_url = self.siteUrl + img_url
            else:
                # 相对路径
                img_url = self.siteUrl + '/' + img_url
        
        # 去重
        if img_url in seen:
            return False
        seen.add(img_url)
        return True
