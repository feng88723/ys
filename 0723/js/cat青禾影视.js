let host = 'https://tv.qhdaohang.cn';
let headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.31 Mobile Safari/537.36',
};

function getList(html) {
    let videos = [];
    const list = pdfa(html, '.public-list-exp');
    list.forEach(it => {
        const id = pdfh(it, 'a&&href');
        const name = pdfh(it, 'a&&title') || pdfh(it, 'a&&alt') || pdfh(it, '.movie-title&&Text');
        const pic = pdfh(it, 'a&&data-original') || pdfh(it, 'img&&data-src') || pdfh(it, '.lazy&&data-src') || pdfh(it, '.lazyload&&data-original');
        const remark = pdfh(it, '.ft2&&Text');
        if (id && name) {
            let vod_pic = pic;
            if (pic && pic != '') {
                vod_pic = pic.startsWith('/') ? (host + pic) : pic;
            } else {
                vod_pic = 'data:image/gif;base64,R0lGODdhAQABAPAAAMPDwwAAACwAAAAAAQABAAACAkQBADs=';
            }
            videos.push({
                vod_id: id,
                vod_name: (name || "未知片名").trim(),
                vod_pic: vod_pic,
                vod_remarks: (remark || "").trim()
            });
        }
    });
    return videos;
}

async function init(cfg) {}

async function home(filter) {
    return JSON.stringify({
        class: [{
            "type_id": "20",
            "type_name": "电影"
        }, {
            "type_id": "37",
            "type_name": "连续剧"
        }, {
            "type_id": "47",
            "type_name": "B站"
        }, {
            "type_id": "45",
            "type_name": "综艺"
        },{
            "type_id": "56",
            "type_name": "下饭剧"
        }, {
            "type_id": "45",
            "type_name": "Netflix自制剧"
        }, {
            "type_id": "43",
            "type_name": "动画"
        }, {
            "type_id": "55",
            "type_name": "短剧"
        }],
        filters: {}
    });
}    

async function homeVod() {
    let resp = await req(host, {
        headers
    });
    return JSON.stringify({
        list: getList(resp.content)
    });
}

async function category(tid, pg, filter, extend) {
    const p = pg || 1;
    const cateId = extend.cateId || tid;
    const class_ = extend.class_ || '';
    const area = extend.area || '';
    const lang = extend.lang || '';
    const letter = extend.letter || '';
    const year = extend.year || '';
    const by = extend.by || '';
    const url = `${host}/vodshow/${cateId}-${area}-${by}-${class_}-${lang}-${letter}---${p}---${year}.html`;  
    const resp = await req(url, {
        headers
    });
    return JSON.stringify({
        list: getList(resp.content),
        page: parseInt(p),
        pagecount: parseInt(p) + 1
    });
}


async function detail(id) {
    const dUrl = host + id;
    const dResp = await req(dUrl, {headers});
    const dhtml = dResp.content;
    
    // 提取基本信息
    const playFrom = [], playList = [];
    const tabs = pdfa(dhtml, '.anthology-tab a');
    const playBoxes = pdfa(dhtml, '.anthology-list-box');
    
    for (let i = 0; i < Math.min(tabs.length, playBoxes.length); i++) {
        const name = pdfh(tabs[i], 'a&&Text') || '播放源' + (i+1);
        const episodes = pdfa(playBoxes[i], 'li a')
            .map(a => pdfh(a, 'span&&Text') + '$' + pdfh(a, 'a&&href'))
            .join('#');
        if (episodes) {
            playFrom.push(name);
            playList.push(episodes);
        }
    }
    
    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: pdfh(dhtml, '.title-h&&Text'),
            vod_pic: '',
            vod_year: pdfh(dhtml, '.this-text:contains(年份) a&&Text') || pdfh(dhtml, '.this-desc-info span:eq(1)&&Text'),
            vod_area: pdfh(dhtml, '.this-desc-info span:eq(2)&&Text') || '',
            vod_remarks: pdfh(dhtml, '.this-desc-info span:eq(3)&&Text') || '',
            type_name: pdfh(dhtml, '.this-desc-tags span&&Text') || '',
            vod_actor: pdfa(dhtml, '.this-text:contains(主演) a').map(a => pdfh(a, 'a&&Text')).join('/'),
            vod_director: '',
            vod_content: pdfh(dhtml, '.this-desc .text&&Text').replace('描述：', '') || '',
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playList.join('$$$')
        }]
    });
}

async function search(wd, quick, pg) {
    let p = pg || 1;
    let url = `${host}/vodsearch/${wd}----------${p}---.html`;
    let resp = await req(url, {
        headers
    });
    return JSON.stringify({
        list: getList(resp.content)
    });
}

async function play(flag, id, flags) {
    try {
        let playUrl = !/^http/.test(id) ? `${host}${id}` : id;
        let resHtml = (await req(playUrl, {
            headers
        })).content;
        let kcode = safeParseJSON(
            resHtml.match(/var\s+player_\w+\s*=\s*(\{[^]*?\})\s*</)?.[1] ?? ''
        );
        let kurl = kcode?.url ?? '';
        let kp = /m3u8|mp4|mkv/i.test(kurl) ? 0 : 1;
        if (kp) kurl = playUrl;
        return JSON.stringify({
            jx: 0,
            parse: kp,
            url: kurl,
            header: headers
        });
    } catch (e) {
        return JSON.stringify({
            jx: 0,
            parse: 0,
            url: '',
            header: {}
        });
    }
}

function safeParseJSON(str) {
    try {
        return JSON.parse(str.trim().replace(/;+$/, ''));
    } catch {
        return null;
    }
}

export default {
    init,
    home,
    homeVod,
    category,
    detail,
    search,
    play
};





