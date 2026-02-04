let host = 'https://6699xb.cfd/';
let headers = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 SE 2.X MetaSr 1.0"
};

async function init(cfg) {}

function getList(html) {
  let videos = [];
  let items = pdfa(html, ".img-list-data li");
  items.forEach(it => {
    let idMatch = it.match(/href="(.*?)"/);
    let nameMatch = it.match(/title="(.*?)"/) || it.match(/alt="(.*?)"/);
    let picMatch = it.match(/data-original="(.*?)"/) || it.match(/src="(.*?)"/);
    if (idMatch && nameMatch) {
      let pic = picMatch ? (picMatch[1] || picMatch[2]) : "";
      videos.push({
        vod_id: idMatch[1],
        vod_name: nameMatch[1].replace(/<.*?>/g, ""),
        vod_pic: pic.startsWith('/') ? host + pic : pic
      });
    }
  });
  return videos;
}
async function home(filter) {
  return JSON.stringify({
    "class": [{
      "type_id": "1",
      "type_name": "无码专区"
    }, {
      "type_id": "6",
      "type_name": "中文字幕"
    }, {
      "type_id": "2",
      "type_name": "麻豆传媒"
    }, {
      "type_id": "3",
      "type_name": "制服诱惑"
    }, {
      "type_id": "4",
      "type_name": "三级伦理"
    }, {
      "type_id": "7",
      "type_name": "卡通动漫"
    }, {
      "type_id": "5",
      "type_name": "明星换脸"
    }, {
      "type_id": "8",
      "type_name": "欧美系列"
    }, {
      "type_id": "13",
      "type_name": "女同性爱"
    }, {
      "type_id": "14",
      "type_name": "多人群交"
    }, {
      "type_id": "15",
      "type_name": "美乳巨乳"
    }, {
      "type_id": "9",
      "type_name": "美女主播"
    }, {
      "type_id": "16",
      "type_name": "强奸乱轮"
    }, {
      "type_id": "11",
      "type_name": "熟女人妻"
    }, {
      "type_id": "12",
      "type_name": "萝莉少女"
    }, {
      "type_id": "10",
      "type_name": "国产自拍"
    }, {
      "type_id": "17",
      "type_name": "抖音视频"
    }, {
      "type_id": "18",
      "type_name": "韩国主播"
    }, {
      "type_id": "20",
      "type_name": "网红头条"
    }, {
      "type_id": "23",
      "type_name": "网爆黑料"
    }, {
      "type_id": "24",
      "type_name": "欧美无码"
    }, {
      "type_id": "25",
      "type_name": "女忧明星"
    }, {
      "type_id": "26",
      "type_name": "捆绑调教"
    }, {
      "type_id": "27",
      "type_name": "电影解说"
    }]
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
  let p = pg || 1;
  let targetId = (extend && extend.class) ? extend.class : tid;
  let url = `${host}/index.php/vod/type/id/${tid}/page/${p}.html`;
  let resp = await req(url, {
    headers
  });
  return JSON.stringify({
    list: getList(resp.content),
    page: parseInt(p)
  });
}
async function detail(id) {
  //二级链接拼接
  let url = host + '/index.php/vod/detail/id/' + id + '.html';
  let resp = await req(url, {
    headers
  });
  let html = resp.content;
  //播放数组
  let playUrl = pdfa(html, ".play-btn-group").map(list => //播放列表(基本不用动)
    pdfa(list, "a").map(a => {
      //播放标题(基本不用动)
      let n = (a.match(/">(.*?)<\/a>/) || ["", "播放"])[1];
      //播放链接(基本不用动)
      let v = a.match(/href="(.*?)"/);
      return n + '$' + (v ? v[1] : "");
    }).join('#')
  ).join('$$$');
  return JSON.stringify({
    list: [{
      vod_id: id,
      'vod_name': (html.match(/<h2 class="c_pink text-ellipsis">(.*?)<\/h2>/) || ["", ""])[1],
      'vod_pic': (html.match(/background-image:url((.*?))/) || ["", ""])[1],
      vod_year: (html.match(/<a href="\/gqsc\/-------------.*?.html" target="_blank">(.*?)<\/a>/) || ["", ""])[1],
      vod_area: (html.match(/<a href="\/gqsc\/--.*?-----------.html" target="_blank">(.*?)<\/a>/) || ["", ""])[1],
      'vod_remarks': (html.match(/<p>更新：(.*?)<\/p>/) || ["", ""])[1],
      'type_name': (html.match(/<p>類型：(.*?)<\/p>/) || ["", ""])[1],
      vod_actor: Array.from(
        html.match(/<p class="data">\s*主演：([\s\S]*?)<\/p>/)?.[1]?.matchAll(/<a [^>]*>([^<]+)<\/a>/g) || []).map(m => m[1]).join(' / ') || '',
      vod_director: Array.from(
        html.match(/<p class="data">\s*导演：([\s\S]*?)<\/p>/)?.[1]?.matchAll(/<a [^>]*>([^<]+)<\/a>/g) || []).map(m => m[1]).join(' / ') || '',
      'vod_content': "菜佬湿📢:本资源来源于网络🚓侵权请联系删除👉" + (html.match(/<meta name="description" content="([\s\S]*?)"/) || ["", ""])[1].replace(/<.*?>/g, "").replace("特别提醒如果您对影片有自己的看法请留言弹幕评论。", ""),
      vod_play_from: "菜佬湿❤️深夜专线",
      vod_play_url: playUrl
    }]
  });
}
async function search(wd, quick, pg) {
  let p = pg || 1;
  let url = host + "/index.php/vod/search/" + (parseInt(p) > 1 ? "page/" + p + "/" : "") + "wd/" + encodeURIComponent(wd) + ".html";
  let resp = await req(url, {
    headers
  });
  return JSON.stringify({
    list: getList(resp.content)
  });
}
async function play(flag, id, flags) {
  try {
    // 拼接播放页完整URL（如果是相对路径则补全域名）
    const playUrl = /^http/.test(id) ? id : `${host}${id}`;
    // 请求播放页HTML
    const resHtml = (await req(playUrl, {
      headers
    })).content;

    // 匹配并解析播放器配置的JSON数据（提取播放URL）
    const kcode = safeParseJSON(
      resHtml.match(/var player_.*?=([^]*?)</)?.[1] ?? ''
    );
    let kurl = kcode?.url ?? ''; // 提取原始播放URL

    // 判断是否需要二次解析：如果是m3u8/mp4/mkv直接播放，否则标记为需要解析
    const kp = /m3u8|mp4|mkv/i.test(kurl) ? 0 : 1;
    if (kp) kurl = playUrl; // 需要解析则使用播放页URL

    // 返回播放配置
    return JSON.stringify({
      jx: 0, // 无需代理（固定值）
      parse: kp, // 是否需要解析（0=否，1=是）
      url: kurl, // 播放URL
      header: headers // 播放请求头
    });
  } catch (e) {
    // 异常时返回空配置
    return JSON.stringify({
      jx: 0,
      parse: 0,
      url: '',
      header: {}
    });
  }
}

/**
 * 安全解析JSON字符串（容错处理）
 * @param {string} str - 待解析的JSON字符串
 * @returns {Object|null} 解析后的对象，失败则返回null
 */
function safeParseJSON(str) {
  try {
    // 去除字符串首尾空格和末尾分号后解析
    return JSON.parse(str.trim().replace(/;+$/, ''));
  } catch {
    return null; // 解析失败返回null
  }
}

// 导出核心函数，供外部调用
export default {
  init, // 初始化
  home, // 获取首页分类
  homeVod, // 获取首页视频
  category, // 获取分类视频
  detail, // 获取视频详情
  search, // 搜索视频
  play // 获取播放链接
};