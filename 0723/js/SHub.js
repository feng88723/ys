var rule = {
author: '小可乐/v5.10.2',
title: 'SeedHub',
类型: '影视',
host: 'https://www.seedhub.cc',
hostJs: '',
headers: {'User-Agent': MOBILE_UA},
编码: 'utf-8',
timeout: 5000,

homeUrl: '/',
url: '/categories/fyclassfyfilter/movies/?page=fypage',
filter_url: '{{fl.tags}}',
searchUrl: '/s/**/?page=fypage',
detailUrl: '',

limit: 9,
double: false,
class_name: '电影&剧集&动漫',
class_url: '1&3&2',
filter_def: {},
图片来源: `@Referer=${HOST}@User-Agent=${MOBILE_UA}`,

推荐: '*',
一级: $js.toString(() => {
    let klists = pdfa(fetch(input), '.cover');
    VODS = [];
    klists.forEach((it) => {
        VODS.push({
            vod_name: pdfh(it, 'img&&alt'),
            vod_pic: pdfh(it, 'img&&src'),
            vod_remarks: pdfh(it, 'li:eq(-1)&&a&&Text') + '_' + pdfh(it, 'li:eq(-2)&&Text').replace('类型: ',''),
            vod_year: pdfh(it, 'li:eq(1)&&Text').split('/')[0],
            vod_id: pdfh(it, 'a&&href')
        })
    })
}),
搜索: '*',
二级: $js.toString(() => {
    let khtml = fetch(input);
    let kdetail = pdfh(khtml, '.cover-container');
    let ktabs = [], kflags = [], kurls = [];
    let ptabs = pdfa(khtml, '.nav-links:eq(-1)&&a');
    for (let ptab of ptabs) {
        ktabs.push(pdfh(ptab, 'body&&Text').replace(/[\d()]*/g,''));
        kflags.push(pdfh(ptab, 'a&&href').split("'")[1]);
    }
    for (let kflag of kflags) {
        if (kflag === 'seed') {
            let kurl = pdfa(khtml, '.seeds&&a').map((it) => { return pdfh(it, 'a&&title') + '$' + encodeURI(pd(it, 'a&&href', HOST)) });
            kurls.push(kurl.join('#'));
        } else {
            let kurl = pdfa(khtml, '.pan-links&&a').filter( it => pdfh(it, 'a&&data-link').includes(`.${kflag}`) );
            kurl = kurl.map((it) => { return pdfh(it, 'a&&title') + '$' + encodeURI(pd(it, 'a&&href', HOST)) });
            kurls.push(kurl.join('#'));
        }
    }
    VOD = {
        vod_id: input,
        vod_name: pdfh(kdetail, 'img&&alt'),
        vod_pic: pdfh(kdetail, 'img&&src'),
        type_name: pdfh(kdetail, 'li:contains(类型:)&&Text').replace('类型:','') || '未提供',
        vod_remarks: pdfh(kdetail, 'li&&Text') || '未提供',
        vod_year: pdfh(kdetail, 'li:eq(-1)&&a:eq(-1)&&Text') || '3000',
        vod_area: pdfh(kdetail, 'li:contains(地区:)&&a&&Text') || '未提供',
        vod_lang: pdfh(kdetail, 'li:contains(语言:)&&a&&Text') || '未提供',
        vod_director: pdfh(kdetail, 'li:contains(导演:)&&Text').replace('导演:','') || '未提供',
        vod_actor: pdfh(kdetail, 'li:contains(主演:)&&Text').replace('主演:','') || '未提供',
        vod_content: khtml.split('的简介')[1].split('<h2')[0].replace(/<[^>]*>/g,''),
        vod_play_from: ktabs.join('$$$'),
        vod_play_url: kurls.join('$$$')
    }
}),

play_parse: true,
lazy: $js.toString(() => {
    let kurl = input;
    let dcUrl = decodeURI(kurl);
    if (dcUrl.includes('磁力')) {
        kurl = fetch(kurl).split('const data = "')[1].split('"')[0];
        input = atob(kurl);
    } else {
        kurl = pdfh(fetch(kurl), '.direct-pan&&href');
        input = 'push://' + kurl;
    }
}),

filter: 'H4sIAAAAAAAAA7WYy04cRxSG9/MYvUai69JV1X4VywsWKIskViQ7kSyEhA02l1hhiGISEAlEgYCdAMaWEnkShpeZnp55i9RIxPWf04daJcvuv09d/rp85/RSr1DFvfu9peLTxSfFveLxwiePirni4cLni/FpfLTeng/j81cLn30ZX9xfKh7G183zs+nq2ex1fCiW527fbp6OV5/fvp1//OSLxUfzPqm7B/EDqoaP6nh1a/xsn6o2xW6dja4PqKo+qu3GVadfVSZ567K9fsNknXp+2h+v7FLZJPXZ7+3uDgtOcvPi2+neayq71PPpTvPhL6qmjpuT9Y5apdjBm+b6Vbu5zjxJfY/+PppcvGVDA88u/mgG51Su07w2fhgNNllwGnnzzYtm+x2T0+Cmh+9HH/pMTo1Pbvpxxdi8wbT+y/EK2wkqLef4/OVk4ycWnXbK5OQm7b1/5TTt9vC8Y5pJI2+2jye/sL2i05q0T4fT/SEbmoeh/ToaHrHoNPLJ11eTy2R5PEnzdW0g/Goz6uO9i+nK/uTyR/Khs8bCl+9f8ZaCgdPy/QmXlTIVMandjkbs8c+Mhtk2wz+5rj268e64E6/q5PV4bbs5Pm02XvOvrKpNCbul84FSwSffRjdrndnWMF1d6oqZVcOaRtky2WqPsulYbVHWVDYeNmuUFZ2bVyWJLpmBJQ48ngqiWhyXClQ0GkXP1xdFR1clkGapWUqXKFKraCD1SdeoMZMUaopNEjVqj8MpltQch2MpqTc1zqGk1pAwxywlccyYyqFIjfE4wZIZQxqlxljSJjOGaHzfRGceLPcezPUK8z8C2cA9LBDZpDWXsApXjIRVA3eDAE6T5z3clBLwDeBJQKeFhEDgbpVnQICJyeR1eerbfEZR5dnq0o6S6Ohh8ALWq2Rce3A4Ggza0xXWfupeIj+cZimrsGl0EtpDHpB12lJS3uAg5xHY7dKWksjvYWJC3uAhKenCOfgAmV4eznBxCfTVrgKkCMCL2IUr7E4829pl8Rsh7zBLeNtpoFIBLOmmEbqyFezkbgagAt6LdyI+MtYRDHYJTQDOCW0sYSwntFUIH05oqyvCd0ZoFzTpm960Xnm8hxmhjQ4EexRDpqyISkFkDLGEQTo2TKDJYOToqCxXCf4NVwniNVMp5KlZRgWSdZRcxTyLAdsoQ4gWWL81usGg7UrasmNLmAO3sQHdYOTWNY2lXhmnCNk7XpFYtrGMJ7lGydQZwG4Rrv8rhG+dtd/xEhJoICAc0jaJk5CEiPkBkEjAnM4zuoKyW4JwWjYpu7Dp1EqYM1AjCtlFlS8CK4gWko8qX77CtSxBDNJ6KS9yUHgLyQFc6VJuAseoWbtpfzthtgCZBLbD1SDR2ecLbwubScpbYMWEvAWQJ1bWZdrJUt4BZ1FirrVwZQp4n5WBqYM83y3kxRI1tQ5Q59+F79gO2p1hp88yuCqth4S0mwdoZyEnFOrnqMPaTHZ+nvTX7hhwnuKUw906m0R3KK6RLR2KW1JkcYoH7zMUV7oOBKes0HYEER2Mk54Zxm1QBIkM446W6dQxbzPFtrKUtayqdDpDce1I6cxLbpY9UK8qVxJeMqu8Qp9L/lNCEcZ7fi6ISq1Sqib98v8S5GcIp7jLUVwp8oOHUdyXNfnNQL1yxmfq8CrMboIZxXvL/wDwgLjDHBcAAA=='
}