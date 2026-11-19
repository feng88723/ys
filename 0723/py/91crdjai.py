try:
    from base.spider import BaseSpider
except Exception:
    class BaseSpider:
        pass


import re
import html as _html
import urllib.request
import urllib.parse
import urllib.error
import http.client

try:
    import requests
    _HAS_REQ = True
except Exception:
    _HAS_REQ = False


BASE = 'https://91crdjai.com'
UA = 'Mozilla/5.0 (Linux; Android 14; HarmonyOS; HUAWEI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
CHANNELS = [
    ('duanju', '成人短剧'),
    ('manju', '成人漫剧'),
    ('zhenrenju', '真人剧'),
    ('shipin', '成人视频'),
]
CH_RE = r'(?:duanju|manju|zhenrenju|shipin)'
BOILER = '本页提供剧情简介、作品资料、标签与完整选集，点击选集进入播放页。'


def _clean(t):
    if not t:
        return ''
    t = re.sub(r'<[^>]+>', ' ', t)
    return _html.unescape(re.sub(r'\s+', ' ', t)).strip()


def _abs(u):
    if not u:
        return ''
    u = u.strip()
    if u.startswith('//'):
        return 'https:' + u
    if u.startswith('/'):
        return BASE + u
    return u


def _fix_url(u):
    if not u:
        return ''
    u = _html.unescape(u)
    u = u.replace('\\u0026', '&').replace('\\u002F', '/')
    return u


class Spider(BaseSpider):
    def getName(self):
        return '🔞91成人短剧'

    def getDependence(self):
        return []

    def init(self, extend=''):
        pass

    def destroy(self):
        pass

    def _get(self, url, headers=None):
        h = {'User-Agent': UA, 'Referer': BASE + '/'}
        if headers:
            h.update(headers)
        if _HAS_REQ:
            r = requests.get(url, headers=h, timeout=25)
            return r.text
        req = urllib.request.Request(url, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                try:
                    return r.read().decode('utf-8', 'ignore')
                except http.client.IncompleteRead as e:
                    return e.partial.decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            try:
                return e.read().decode('utf-8', 'ignore')
            except http.client.IncompleteRead as ie:
                return ie.partial.decode('utf-8', 'ignore')

    def _cards(self, src):
        out = []
        seen = set()
        pat = re.compile(r'<a[^>]*href="(/' + CH_RE + r'/\d+-[^"/]+/)"[^>]*>(.*?)</a>', re.S)
        for m in pat.finditer(src):
            path = m.group(1)
            if path in seen:
                continue
            seen.add(path)
            body = m.group(2)
            name = ''
            am = re.search(r'alt="([^"]+)"', body)
            if am:
                name = _clean(am.group(1))
            if not name:
                continue
            pic = ''
            pm = re.search(r'(?<![-\w])data-src="([^"]+)"', body)
            if pm:
                pic = _abs(_fix_url(pm.group(1)))
            out.append({
                'vod_id': path,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return out

    def homeContent(self, filter=''):
        return {
            'class': [{'type_id': tid, 'type_name': name} for tid, name in CHANNELS],
            'filters': {},
        }

    def homeVideoContent(self):
        try:
            src = self._get(BASE + '/')
            return {'list': self._cards(src)}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        tid = (tid or 'duanju').strip()
        if tid not in ('duanju', 'manju', 'zhenrenju', 'shipin'):
            tid = 'duanju'
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        url = BASE + '/' + tid + '/' if pg == 1 else BASE + '/' + tid + '/page/' + str(pg) + '/'
        try:
            src = self._get(url)
            items = self._cards(src)
            pages = re.findall(r'/' + tid + r'/page/(\d+)/', src)
            pagecount = max([int(p) for p in pages]) if pages else pg
            return {'list': items, 'page': pg, 'pagecount': pagecount, 'total': 0}
        except Exception:
            return {'list': [], 'page': pg, 'pagecount': pg, 'total': 0}

    def detailContent(self, ids):
        path = ids[0] if isinstance(ids, list) else ids
        if not path:
            return {'list': []}
        if not path.startswith('http'):
            url = BASE + path if path.startswith('/') else BASE + '/' + path
        else:
            url = path
        try:
            src = self._get(url)
        except Exception:
            return {'list': []}
        name = ''
        pic = ''
        im = re.search(r'<img[^>]*class="p-img"[^>]*>', src)
        if im:
            tag = im.group(0)
            am = re.search(r'alt="([^"]+)"', tag)
            if am:
                name = _clean(am.group(1))
            pm = re.search(r'(?<![-\w])data-src="([^"]+)"', tag)
            if pm:
                pic = _abs(_fix_url(pm.group(1)))
        if not name:
            tm = re.search(r'<title[^>]*>(.*?)</title>', src, re.S)
            if tm:
                name = _clean(tm.group(1)).split(' - ')[0]
        content = ''
        dm = re.search(r'<meta name="description"[^>]*content="([^"]+)"', src)
        if dm:
            content = _clean(dm.group(1)).replace(BOILER, '').strip()
        bits = []
        sm = re.search(r'<dt>状态</dt>\s*<dd>(.*?)</dd>', src, re.S)
        jm = re.search(r'<dt>集数</dt>\s*<dd>(.*?)</dd>', src, re.S)
        if sm:
            bits.append(_clean(sm.group(1)))
        if jm:
            bits.append(_clean(jm.group(1)))
        remarks = ' '.join(bits)
        eps = []
        seen = set()
        base_path = path if path.startswith('/') else '/' + path
        if not base_path.endswith('/'):
            base_path += '/'
        ep_pat = re.compile(r'<a[^>]*href="(' + re.escape(base_path) + r'\d+/)"[^>]*>(.*?)</a>', re.S)
        for m in ep_pat.finditer(src):
            ep_url = m.group(1)
            txt = _clean(m.group(2))
            if not txt.isdigit():
                continue
            if ep_url in seen:
                continue
            seen.add(ep_url)
            eps.append((int(txt), ep_url))
        eps.sort(key=lambda x: x[0])
        play_url = '#'.join('第%d集$%s' % (n, u) for n, u in eps)
        vod = {
            'vod_id': path,
            'vod_name': name,
            'vod_pic': pic,
            'vod_content': content,
            'vod_remarks': remarks,
            'vod_play_from': '在线播放',
            'vod_play_url': play_url,
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg != 1:
            return {'list': []}
        url = BASE + '/search/' + urllib.parse.quote(key) + '/'
        try:
            src = self._get(url)
            return {'list': self._cards(src)}
        except Exception:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        ep = id or ''
        if not ep.startswith('http'):
            url = BASE + ep if ep.startswith('/') else BASE + '/' + ep
        else:
            url = ep
        header = {'User-Agent': UA, 'Referer': BASE + '/'}
        try:
            src = self._get(url)
        except Exception:
            return {'parse': 0, 'playUrl': '', 'url': '', 'header': header}
        m3u8 = ''
        jm = re.search(r'"src"\s*:\s*"([^"]*\.m3u8[^"]*)"', src)
        if jm:
            m3u8 = _fix_url(jm.group(1))
        if not m3u8:
            jm = re.search(r'"src"\s*:\s*"([^"]+)"', src)
            if jm:
                cand = _fix_url(jm.group(1))
                if '.m3u8' in cand:
                    m3u8 = cand
        if not m3u8:
            for m in re.finditer(r'https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*', src):
                cand = _fix_url(m.group(0))
                if 'hls' in cand or 'videos' in cand:
                    m3u8 = cand
                    break
        if not m3u8:
            for m in re.finditer(r'https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*', src):
                m3u8 = _fix_url(m.group(0))
                break
        return {
            'parse': 0,
            'playUrl': m3u8,
            'url': m3u8,
            'header': header,
        }

    def localProxy(self, param):
        return [200, 'video/mpeg', '', '']

    def isVideoFormat(self, url):
        url = (url or '').lower()
        return url.endswith('.m3u8') or url.endswith('.mp4') or '.m3u8?' in url or '.mp4?' in url

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return None
