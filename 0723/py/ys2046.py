import requests
from bs4 import BeautifulSoup
import re
import sys
import json
import urllib.parse

sys.path.append('..')

from base.spider import Spider

xurl = "https://ys2046.lat"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': xurl + '/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}


def fetch(url):
    """GET 请求：关闭证书校验、宽松响应判断、失败重试一次"""
    for attempt in (1, 2):
        try:
            resp = requests.get(url=url, headers=headerx, timeout=12, verify=False)
            if resp.status_code < 500:
                return resp.text
        except Exception:
            pass
    return ''


def getList(html):
    """列表页卡片 ul.fed-list-info li.fed-list-item"""
    videos = []
    if not html:
        return videos
    源码 = BeautifulSoup(html, "html.parser")
    卡片列表 = 源码.select('ul.fed-list-info li.fed-list-item')
    for 卡片 in 卡片列表:
        vod = {}
        链接 = 卡片.select_one('a.fed-list-pics')
        标题元素 = 卡片.select_one('a.fed-list-title')
        if not 链接 or not 标题元素:
            continue
        href = 链接.get('href', '')
        m = re.search(r'/detail/(.+?)\.html$', href)
        if not m:
            continue
        vod["vod_id"] = m.group(1)
        vod["vod_name"] = 标题元素.get_text(strip=True)
        pic = (链接.get('data-original') or 链接.get('src') or '').strip()
        if not pic:
            vod["vod_pic"] = ''
        elif pic.startswith('//'):
            vod["vod_pic"] = 'https:' + pic
        elif 'http' not in pic:
            vod["vod_pic"] = xurl + pic
        else:
            vod["vod_pic"] = pic
        备注元素 = 卡片.select_one('.fed-list-remarks')
        备注 = 备注元素.get_text(strip=True) if 备注元素 else ''
        分数元素 = 卡片.select_one('.fed-list-score')
        if 分数元素 and 分数元素.get_text(strip=True):
            备注 = (备注 + ' ' + 分数元素.get_text(strip=True)).strip()
        vod["vod_remarks"] = 备注
        videos.append(vod)
    return videos


def getSearchList(html):
    """搜索页卡片 dl.fed-deta-info"""
    videos = []
    if not html:
        return videos
    源码 = BeautifulSoup(html, "html.parser")
    卡片列表 = 源码.select('dl.fed-deta-info')
    for 卡片 in 卡片列表:
        vod = {}
        标题链接 = 卡片.select_one('h1 a')
        if not 标题链接:
            continue
        href = 标题链接.get('href', '')
        m = re.search(r'/detail/(.+?)\.html$', href)
        if not m:
            continue
        vod["vod_id"] = m.group(1)
        vod["vod_name"] = 标题链接.get_text(strip=True)
        pic = ''
        for el in 卡片.select('[data-original]'):
            u = el.get('data-original', '')
            if u and u != '/' and u.startswith('http'):
                pic = u
                break
        vod["vod_pic"] = pic
        备注元素 = 卡片.select_one('dt')
        vod["vod_remarks"] = 备注元素.get_text(strip=True) if 备注元素 else ''
        videos.append(vod)
    return videos


def getPagecount(html):
    """从分类分页链接 type/xxx-{n}.html 提取最大页码"""
    源码 = BeautifulSoup(html, "html.parser")
    max_page = 1
    for a in 源码.select('a[href*="/type/"]'):
        href = a.get('href', '')
        m = re.search(r'/type/[^/]+?-(\d+)\.html$', href)
        if m:
            p = int(m.group(1))
            if p > max_page:
                max_page = p
    return max_page


class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "2046影视大全"

    def init(self, extend):
        pass

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        pass

    def homeContent(self, filter):
        result = {"class": [
            {"type_id": "dianying", "type_name": "电影"},
            {"type_id": "lianxuju", "type_name": "连续剧"},
            {"type_id": "zongyi", "type_name": "综艺"},
            {"type_id": "dongman", "type_name": "动漫"},
            {"type_id": "duanju", "type_name": "短剧"},
            {"type_id": "lunli", "type_name": "伦理"},
        ]}
        return result

    def homeVideoContent(self):
        # 主入口：电影分类页，空时回退站点首页
        html = fetch(xurl + '/type/dianying.html')
        lst = getList(html)
        if not lst:
            html = fetch(xurl)
            lst = getList(html)
        result = {'list': lst}
        return result

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        page = int(pg) if pg else 1
        if page <= 1:
            url = '%s/type/%s.html' % (xurl, cid)
        else:
            url = '%s/type/%s-%d.html' % (xurl, cid, page)
        resp = fetch(url)
        result['list'] = getList(resp)
        result['page'] = page
        result['pagecount'] = getPagecount(resp)
        result['limit'] = 24
        result['total'] = result['pagecount'] * 24
        return result

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else str(ids)
        url = '%s/detail/%s.html' % (xurl, vid)
        html = fetch(url)
        if not html:
            return {"list": []}
        源码 = BeautifulSoup(html, "html.parser")

        h1 = 源码.select_one('h1')
        名称 = h1.get_text(strip=True) if h1 else vid

        pic = ''
        ogi = 源码.select_one('meta[property="og:image"]')
        if ogi and ogi.get('content'):
            pic = ogi['content']
        if not pic:
            for el in 源码.select('[data-original]'):
                u = el.get('data-original', '')
                if 'upload' in u:
                    pic = u
                    break

        # 详情字段（主演/导演/类型/地区/年份）
        fields = {}
        dl = 源码.select_one('dl.fed-deta-info')
        if dl:
            lines = [ln.strip() for ln in dl.get_text('\n').split('\n') if ln.strip()]
            键前缀 = ('主演：', '导演：', '类型：', '地区：', '语言：', '年份：')
            for i, ln in enumerate(lines):
                if ln.startswith(键前缀):
                    key = ln[:-1]
                    vals = []
                    for l2 in lines[i + 1:]:
                        if l2.startswith(键前缀) or l2.startswith('简介：'):
                            break
                        if l2 in ('立即播放', '查看详情'):
                            break
                        vals.append(l2)
                    if vals:
                        fields[key] = ' '.join(vals)

        director = fields.get('导演', '')
        actor = fields.get('主演', '')
        cls_type = fields.get('类型', '')
        area = fields.get('地区', '')
        year = fields.get('年份', '')

        # 简介（meta description）
        content = ''
        mdesc = 源码.select_one('meta[name="description"]')
        if mdesc and mdesc.get('content'):
            c = mdesc['content']
            c = re.sub(r'^.*?剧情介绍', '剧情介绍', c, flags=re.S)
            content = c.strip()[:500]

        # 播放源面板 + 源名按钮
        items = 源码.select('.fed-play-item')
        btns = [b.get_text(strip=True)
                for b in 源码.select('.fed-drop-btns a')]
        play_from, play_url = [], []
        for i, it in enumerate(items):
            eps = it.select('a[href*="/play/"]')
            if not eps:
                continue
            if i < len(btns) and btns[i]:
                flag = btns[i]
            else:
                flag = '线路%d' % (i + 1)
            urls = []
            for a in eps:
                href = a.get('href', '')
                m = re.search(r'/play/(.+?)\.html$', href)
                if not m:
                    continue
                urls.append(xurl + '/play/' + m.group(1) + '.html')
            if not urls:
                continue
            play_from.append(flag)
            play_url.append(flag + '$' + '#'.join(urls))
        if not play_url:
            return {"list": []}

        v = {
            'vod_id': vid,
            'vod_name': 名称,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }
        if director:
            v['vod_director'] = director
        if actor:
            v['vod_actor'] = actor
        if cls_type:
            v['vod_class'] = cls_type
        if area:
            v['vod_area'] = area
        if year:
            v['vod_year'] = year[:4]
        return {"list": [v]}

    def playerContent(self, flag, id, vipFlags):
        # id = 选集URL（detailContent 中已存完整播放页 URL），flag = 线路名
        p = str(id).strip()
        if not p:
            return {}
        if 'http' not in p:
            p = xurl + '/play/' + p + '.html'
        html = fetch(p)
        if not html:
            return {}
        m = re.search(r'data-play="([^"]+)"', html)
        if not m or not m.group(1):
            mm = re.search(r'https?://[^"\\\s]+?\.m3u8[^"\\\s]*', html)
            return {'parse': 0, 'url': mm.group(0) if mm else '',
                    'header': {'User-Agent': headerx['User-Agent'],
                               'Referer': xurl + '/'}}
        return {'parse': 0, 'url': m.group(1),
                'header': {'User-Agent': headerx['User-Agent'],
                           'Referer': xurl + '/'}}

    def searchContent(self, key, quick, pg="1"):
        result = {}
        编码 = urllib.parse.quote(key)
        url = '%s/search/%s---.html' % (xurl, 编码)
        resp = fetch(url)
        result['list'] = getSearchList(resp)
        result['page'] = pg
        result['pagecount'] = 1
        result['limit'] = 24
        result['total'] = 999999
        return result

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)


if __name__ == "__main__":
    spider = Spider()
    spider.init("")

    # res = spider.homeVideoContent()
    # res = spider.categoryContent("dianying", "1", {}, {})
    # res = spider.detailContent(["dianying-4470"])
    # res = spider.searchContent("女友", False)
    # print(json.dumps(res, ensure_ascii=False, indent=2))