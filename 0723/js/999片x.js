var rule = {
    author: 'Jack',
    title: '999片',
    类型: '影视',
    host: 'https://www.999xpian.com',
    //↑域名
    searchable: 2,
    quickSearch: 1,
    filterable: 1,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/141.0.7390.17 Mobile Safari/537.36'
    },
    
   url: 'https://www.999xpian.com/vodshow/fyclass--------fypage---.html',
     //url: '/vodshow/fyfilter.html',  
     
   // filter_url: '{{fl.cateId or "fyclass"}}-{{fl.area}}-{{fl.by}}--{{fl.lang}}--{{fl.letter}}--fypage---{{fl.year}}',

    searchUrl: 'https://www.999xpian.com/vodsearch/**----------fypage---.html',
    搜索: '*',
    
    推荐: '*',
    class_name: '电影&电视剧&综艺&动漫&短剧',
    //分类: '电影&电视剧&综艺&动漫',
    class_url: 'dianying&dianshiju&zongyi&dongman&duanju',
    //分类值: '1&2&3&4',
    filter_def: {
        dianying: {
            cateId: 'dianying'
        },
        dianshiju: {
            cateId: 'dianshiju'
        },
        zongyi: {
            cateId: 'zongyi'
        },
        dongman: {
            cateId: 'dongman'
        },
        duanju: {
            cateId: 'duanju'
        }
    },
    一级: '.hl-lazy;a&&title;a&&data-original;.hl-lc-1&&Text;a&&href',
    推荐: '*', 

      二级: {
        title: 'h2&&Text;li:contains(分类)&&Text',
        img: '.hl-lazy&&data-original',

        desc: 'li:contains(更新)&&Text;li:contains(年份)&&Text;li:contains(地区)&&Text;li:contains(演员)&&Text;li:contains(导演)&&Text',
        content: '.blurb&&Text',
        tabs: '.hl-tabs-btn',           
         tab_text: 'Text',              
          lists: '.hl-list-wrap:eq(#id) li',   
          list_text: 'a&&Text',           
           list_url: 'a&&href'            
    },

      搜索: '*',
      
    
    //是否启用辅助嗅探: 1,0
    sniffer: 0,
    // 辅助嗅探规则
    isVideo: 'http((?!http).){26,}\\.(m3u8|mp4|flv|avi|mkv|wmv|mpg|mpeg|mov|ts|3gp|rm|rmvb|asf|m4a|mp3|wma)',

    play_parse: true,
    //播放地址通用解析
    lazy: $js.toString(() => {
        let html = request(input);
        let kcode = JSON.parse(html.split('aaaa=')[1].split('<')[0]);
        let kurl = kcode.url;
        if (/\.(m3u8|mp4)/.test(kurl)) {
            input = { jx: 0, parse: 0, url: kurl, header: {'User-Agent': MOBILE_UA, 'Referer': getHome(kurl)} }
        } else {
            input = { jx: 0, parse: 1, url: input }
        }
    }),

}
