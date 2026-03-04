const MOBILE_UA = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36';
var HOST;
var KParams = {
    headers: { 'User-Agent': MOBILE_UA },
    timeout: 5000
};

async function init(cfg) {
    try {
        HOST = (cfg.ext?.host?.trim() || 'https://www.4f7lw7.cn').replace(/\/$/, '');
        KParams.headers['Referer'] = HOST;
        KParams.headers['Cookie'] = '';
        let parseTimeout = parseInt(cfg.ext?.timeout?.trim(), 10);
        if (parseTimeout > 0) { KParams.timeout = parseTimeout; }
        KParams.resHtml = await request(HOST);
    } catch (e) {
        console.error('初始化失败：', e.message);
    }
}

async function home(filter) {
    try {
        let resHtml = KParams.resHtml;
        if (!resHtml) throw new Error('首页源码为空');
        const navHtml = cutStr(resHtml, '<div id="sj-nav-1"', '</ul>', '', false);
        const typeArr = cutStr(navHtml, '<li', '</li>', '', false, 0, true)
            .filter(item => item.includes('/4f7lw7tp/'));      
        let classes = typeArr.map((it, idx) => {
            let cName = cutStr(it, '>', '</a', `分类${idx+1}`);
            let cId = cutStr(it, '/4f7lw7tp/', '.html', `值${idx+1}`);
            return { type_name: cName, type_id: cId };
        }).filter(c => c.type_id && !isNaN(c.type_id));       
        if (KParams.catesSet) classes = ctSet(classes, KParams.catesSet);

      const dynamicFilters = [
            { key: 'class', name: '分类', reg: /\d+----/ },
            { key: 'area',  name: '地区', reg: /\/\d+-([^-]+)-/ },
            { key: 'lang',  name: '语言', reg: /\d+----([^-]+)-/ },
            { key: 'year',  name: '年份', reg: /-([^-]+)\./ },
            { key: 'letter',name: '字母', reg: /\d+-----([^-]+)-/ }
        ];

        const resHtmlList = await Promise.all(classes.map(cls => request(`${HOST}/4f7lw7sw/${cls.type_id}-----------.html`).catch(() => '')));
        let filters = {};
        classes.forEach((cls, idx) => {
            const pageHtml = resHtmlList[idx];
            const filterList = [];
            if (pageHtml) {
                const screenBlocks = cutStr(pageHtml, 'dl', '</dl>', '', false, 0, true);
                for (let { key, name, reg } of dynamicFilters) {
                    const targetBlock = screenBlocks.find(block => reg.test(block));
                    if (!targetBlock) continue;
                    let items = cutStr(targetBlock, '<a', '/a>', '', false, 0, true).map(el => {
                        let n = cutStr(el, '>', '<', '', true).trim();
                        return n ? { n, v: n } : null;
                    }).filter(Boolean);
                    if (items.length === 0) continue;
                    const allIndex = items.findIndex(item => item.n === '全部');
                    if (allIndex === -1) items.unshift({ n: '全部', v: '' });
                    else if (allIndex > 0) {
                        const [allItem] = items.splice(allIndex, 1);
                        items.unshift(allItem);
                    }
                    filterList.push({ key, name, value: items });
                }
            }
            filterList.push({ key: 'by', name: '排序', value: [
            { n: '时间', v: 'time' },
            { n: '人气', v: 'hits' },
            { n: '评分', v: 'score' }]});
            filters[cls.type_id] = filterList;
        });
        return JSON.stringify({ class: classes, filters });
    } catch (e) {
        console.error('获取分类失败：', e.message);
        return JSON.stringify({ class: [], filters: {} });
    }
}

async function homeVod() {
    try {
        let resHtml = KParams.resHtml;
        let VODS = getVodList(resHtml);
        return JSON.stringify({ list: VODS });
    } catch (e) {
        console.error('推荐获取失败：', e.message);
        return JSON.stringify({ list: [] });
    }
}

async function category(tid, pg, filter, extend) {
    pg = pg > 0 ? pg : 1;
    let fl = extend || {};
    let cateUrl = `${HOST}/4f7lw7sw/${fl.cateId || tid}-${fl.area ?? ''}-${fl.by ?? ''}-${fl.class ?? ''}-${fl.lang ?? ''}-${fl.letter ?? ''}---${pg}---${fl.year ?? ''}.html`;
    let html = await request(cateUrl);
    return JSON.stringify({
        list: getVodList(html),
        page: pg,
        pagecount: 999,
        limit: 30,
        total: 30 * 999
    });
}

async function search(wd, quick, pg) {
    try {
        pg = Math.max(parseInt(pg, 10) || 1, 1);
        let searchUrl = `${HOST}/4f7lw7sc/${wd}----------${pg}---.html`;
        let resHtml = await request(searchUrl);
        let VODS = getVodList(resHtml, true);
        return JSON.stringify({ list: VODS, page: pg, pagecount: 10, limit: 30, total: 300 });
    } catch (e) {
        console.error('搜索失败：', e.message);
        return JSON.stringify({ list: [], page: 1, pagecount: 0, limit: 30, total: 0 });
    }
}

function getVodList(html, isSearch = false) {
    try {
        if (!html) return [];
        let items = cutStr(html, '<a class="link-hover"', '</li>', '', false, 0, true);   
        return items.map(it => {
            let href = cutStr(it, 'href="', '"');
            if (!href) return null;          
            let name = cutStr(it, 'title="', '"') || cutStr(it, '<p class="name">', '</p>', '', true);
            let pic = cutStr(it, 'data-original="', '"') || cutStr(it, 'src="', '"');
            let remarks = cutStr(it, 'class="other"><i>', '<', '', true);
            
            pic = pic?.startsWith('http') ? pic : (HOST || '') + pic;           
            return {
                vod_name: name,
                vod_pic: pic,
                vod_remarks: remarks,
                vod_id: `${href}@${name}@${pic}@${remarks}`
            };
        }).filter(Boolean);
    } catch (e) {
        console.error('列表解析失败：', e.message);
        return [];
    }
}

async function detail(ids) {
    try {
        let [id, kname, kpic, kremarks] = ids.split('@');
        let detailUrl = !/^http/.test(id) ? `${HOST}${id}` : id;
        let resHtml = await request(detailUrl);
        if (!resHtml) throw new Error('源码为空');
        
        let intros = cutStr(resHtml, '<div class="ct-c">', '</div>', '', false);
        
        let tabsHtml = cutStr(resHtml, 'tab-down', '</ul>', '', false);
        let ktabs = cutStr(tabsHtml, '<li', '/li>', '', false, 0, true)
            .map(li => cutStr(li, '"></i>', '<', '', true).trim())
            .filter(name => name && name !== '简介');
        
        let items = cutStr(resHtml, 'videourl clearfix', '</ul>', '', false, 0, true);
        let kurls = items.map(item => {
            return cutStr(item, '<a', '/a>', '', false, 0, true)
                .map(it => {
                    let n = cutStr(it, '>', '<', '', true).trim();
                    let u = cutStr(it, 'href="', '"', '', true);
                    if (!u) return null;
                    return n + '$' + u;
                }).filter(ep => ep && !ep.includes('APP秒播')).join('#');
        }).filter(ul => ul);

        let VOD = {
            vod_id: detailUrl,
            vod_name: kname,
            vod_pic: kpic,
            vod_remarks: kremarks,
            type_name: cutStr(intros, '类型：</span>', '<', '', true),
            vod_area: cutStr(intros, '地区：</span>', '<', '', true),
            vod_year: cutStr(intros, '年份：</span>', '<', '', true),
            vod_lang: cutStr(intros, '语言：</span>', '<', '', true),
            vod_director: cutStr(intros, '导演：</span>', '<', '', true),
            vod_actor: cutStr(intros, '主演：</span>', '<', '', true),
            vod_content: cutStr(resHtml, '<div class="tab-jq">', '</div>', '', true).trim(),
            vod_play_from: ktabs.join('$$$'),
            vod_play_url: kurls.join('$$$')
        };

        return JSON.stringify({ list: [VOD] });
    } catch (e) {
        console.error('详情页获取失败：', e.message);
        return JSON.stringify({ list: [] });
    }
}

async function play(flag, ids, flags) {
   try {
       let playUrl = !/^http/.test(ids) ? `${HOST}${ids}` : ids;
       let kp = 0, kurl = '', pheaders = {'User-Agent': MOBILE_UA};
       let resHtml = await request(playUrl);
       let kcode = safeParseJSON(cutStr(resHtml, 'var player_£=', '<', '', false));
       kurl = kcode?.url ?? '';
       if (!/m3u8|mp4|mkv/.test(kurl)) {
           kp = 1;
           kurl = playUrl;
       }
       return JSON.stringify({jx: 0, parse: kp, url: kurl, header: pheaders});
   } catch (e) {
       console.error('播放失败：', e.message);
       return JSON.stringify({jx: 0, parse: 0, url: '', header: {}});
   }
}

function safeParseJSON(jStr){
   try {return JSON.parse(jStr);} catch(e) {return null;}
}

function cutStr(str, prefix = '', suffix = '', defVal = '', clean = true, i = 0, all = false) {
    try {
        if (typeof str !== 'string') throw new Error('截取对象非字符串');

        const pre = prefix.replace(/£/g, '[\\s\\S]*?');
        const suf = suffix.replace(/£/g, '[\\s\\S]*?');

        const escapeReg = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        let preEsc = escapeReg(pre).replace(/\\\[\\s\\\\S\\\]\\\*\\\?/g, '[\\s\\S]*?');
        let sufEsc = escapeReg(suf).replace(/\\\[\\s\\\\S\\\]\\\*\\\?/g, '[\\s\\S]*?');

        const regex = new RegExp(`${preEsc}([\\s\\S]*?)${sufEsc}`, 'g');
        const matches = [...str.matchAll(regex)];

        if (all) {
            return matches.length ? matches.map(m => {
                let val = m[1] !== undefined ? m[1] : defVal;
                return clean ? cleanHtml(val) : val;
            }) : [defVal];
        }

        let idx = parseInt(i, 10);
        if (isNaN(idx)) throw new Error('索引必须为整数');

        let target;
        if (idx >= 0) {
            target = matches[idx]?.[1];
        } else {
            target = matches[matches.length + idx]?.[1];
        }

        if (target === undefined) return defVal;
        return clean ? cleanHtml(target) : target;
    } catch (e) {
        console.error('截取错误：', e.message);
        return all ? [defVal] : defVal;
    }
}

function cleanHtml(str) {
    return String(str)
        .replace(/<[^>]*>/g, ' ')
        .replace(/&nbsp;|[\u00A0\s]+/g, ' ')
        .trim()
        .replace(/\s+/g, ' ');
}

async function request(reqUrl, options = {}) {
   try {
       if (typeof reqUrl !== 'string' || !reqUrl.trim()) { throw new Error('reqUrl需为字符串且非空'); }
       if (typeof options !== 'object' || Array.isArray(options) || options === null) { throw new Error('options类型需为非null对象'); }
       options.method = options.method?.toUpperCase() || 'GET';
       if (['GET', 'HEAD'].includes(options.method)) {
           delete options.body;
           delete options.data;
           delete options.postType;
       }
       let {headers, timeout, ...restOpts} = options;
       const optObj = {
           headers: (typeof headers === 'object' && !Array.isArray(headers) && headers) ? headers : KParams.headers,
           timeout: parseInt(timeout, 10) > 0 ? parseInt(timeout, 10) : KParams.timeout,
           ...restOpts
       };
       const res = await req(reqUrl, optObj);
       if (options.withHeaders) {
           const resHeaders = typeof res.headers === 'object' && !Array.isArray(res.headers) && res.headers ? res.headers : {};
           const resWithHeaders = { ...resHeaders, body: res?.content ?? '' };
           return JSON.stringify(resWithHeaders);
       }
       return res?.content ?? '';
   } catch (e) {
       console.error(`${reqUrl}→请求失败：', e.message`);
       return options?.withHeaders ? JSON.stringify({ body: '' }) : '';
   }
}

export function __jsEvalReturn() {
   return {
       init,
       home,
       homeVod,
       category,
       search,
       detail,
       play,
       proxy: null
   };
}




