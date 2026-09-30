var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/index.config.js
var index_config_exports = {};
__export(index_config_exports, {
  default: () => index_config_default
});
module.exports = __toCommonJS(index_config_exports);

// src/util/network.js
var import_os = __toESM(require("os"), 1);
var findIPv4 = (IPInfos) => {
  return IPInfos?.find((item) => item.family === "IPv4")?.address;
};
var getIPAddress = function() {
  const interfaces = import_os.default.networkInterfaces();
  return findIPv4(interfaces["en0"]) || findIPv4(interfaces["en1"]) || findIPv4(interfaces["en2"]) || "127.0.0.1";
};

// src/index.config.js
var index_config_default = {
  ali: {
    token: "",
    token280: "token280"
  },
  quark: {
    cookie: "ctoken=DBTmd0OSYvlnAB5rWCBBTpvk;__pus=a3cceb9788aa0cd9920c346e48545793AAQoHAkyfYgyKWizJK9OIyK8ahzqo+4XoLgdD8WHhKeEy91AyHNmEsO9JS7y5cjgSBRqzf0G77zNKIitYgqUq37x;__kp=0fb98570-d218-11f0-bb65-5928ecc57741;__kps=AAQE6cOihN7VOU7zAKrTgWkJ;__ktd=tt6Yp5rXh8lQuCaG/k6t6w;__uid=AAQE6cOihN7VOU7zAKrTgWkJ;__puus=0e5ac3ed9d059388a97e0e95f1b6c65cAARgUz8kdvmRZsczLiQ/g3wmCX+n3/722RxiYMUobVtty7JLS4pmTswGoVvyuHIckfzZGgvKRlNaATxvUkcnL2PWH7FgTGygBna13lMuj34lLguYt/YFbxFvbApOWBkyPMDTMxLaNTYxm6HTiOKkPRHQWT6UWTjo4JjKxuLQhZuFDqKiZrRqmAVOShCRDdGFXqK4+XcoZ2r5+IEGRcpJFTJj"
  },
  uc: {
    cookie: "__pus=d281c7d72d32e5a8a1282d0377788070AAROklpLiz4iUTmJ0yUSsorTjSF8KrMH68rB3g5k1Xwjj8Jsgi0PJPuJSkbhptgLwANkV3tWDcTB5UnDWHcc0oQB;__uid=AARj40O7XcxSGllkUwD0e3R6;__puus=7da1f53c608b769272cfd7ef434896c6AAQltZBoSxTlvmDQF5qAbBsRBTx20rXfrcj3XADs67IqcwoPwc007Q8BWzA/Jy5D4NgwB0q49g/0473v9WNPY07+lJs1Qmxxtdph5TL/fHJLwAHAPRbsmV3T1cef4s4e8qYThqhlKHCruBdHNITxn51O7cKx9OPvMN810Y/amoYoMC3NE/bViJ5hsHOq7fi+Svs=",
    token: "token",
    ut: "eyJhbGciOiJIUzI1NiIsIlR5cGUiOiJKd3QiLCJ0eXAiOiJKV1QifQ.eyJvcGVuSWQiOiIwMDcxZGJkMDk0ODc0NWM3YTRmYmMzODZmZWNhODgyYyIsImV4cCI6MTc2ODc3NTkxNiwidG9rZW4iOiIzYzM4Y2EwY2RiMzI0ODc2ODQ1YjQ1MzY0MDIyZGQ4ZSJ9._GJ1-jeCbGAvFGofe4rH5xdhtzRwGTOzYDL_baNlAhw"
  },
  y115: {
    cookie: ""
  },
  baidu: {
    cookie: "PASSID=x8uWcB;UBI=fi_PncwhpxZ%7ETaJcw%7ExXnkz-55Q5YC0s-hk;STOKEN=22b1ef57a90a5bfa357d55f59e2206877ca398b243462a8bec2b2549a45e5151;BDUSS=GRjSzI3SGxveVI1OUQxTDhnZUF3N0RTMUVDcndzUUkwcnk5YkpSbjRvWndHYmRvSVFBQUFBJCQAAAAAAQAAAAEAAABvmM8RAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHCMj2hwjI9oO;PTOKEN=7a642b660d93d9121001fab49903aa9c;BAIDUID=6317C33DA950A67389AB941D9BDC1474:FG=1;BAIDUID_BFESS=6317C33DA950A67389AB941D9BDC1474:FG=1;PANPSC=;csrfToken=QT3RhWnEFGDjHJcogBx-LbKq"
  },
  bili: {
    cookie: "buvid3=40207FB4-AA59-8C0E-0188-61D75036A28082691infoc; b_nut=1774834182; _uuid=39A72924-A39A-39410-ED95-A210B66B7BAF112908infoc; home_feed_column=4; bmg_af_switch=1; bmg_src_def_domain=i0.hdslb.com; buvid4=672DFF1A-EBB5-3AD0-3E33-909FA695C1A016028-026033009-8aQhBClBvz6XYj3V5an8DSMdyW1ixxkP9AlHEEZPvsE+Kkyc2Leo+V9OB96nfrqy; buvid_fp=200bf38f8e7d6f6663ba448cc45aade1; bsource=search_baidu; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzgyOTA5MzksImlhdCI6MTc3ODAzMTY3OSwicGx0IjotMX0.OssZjBC5nznsJ_KiTR5bR_JDapYCAnrUYirypyHk0YE; bili_ticket_expires=1778290879; browser_resolution=1100-2070; csrf_state=d690d3c90230580ef47531a7de777ee6; DedeUserID=3706983848872500; DedeUserID__ckMd5=6303511631b9d995; theme-tip-show=SHOWED; SESSDATA=df7de7a4%2C1793584224%2C081e5%2A51CjCBAvGS91tzAtGB8y0BenBSn8VShom_Cc0sQxUH-BDtQ5efu6F-9TybpDxst8oXQM0SVlQ4d28wd2s1TDhBMWJvdThkcHM1bmQxVk91emJ0NnZDN0ZZeUQwMlEyMWpueC12blJtMC1VLUd1cTVwS25DUWtRcFZyZlRQY2ExbWxlM0VhdDBKaXd3IIEC; bili_jct=08321b2afb28760abbdcb738cfe9283b; sid=8b6u6ur6; b_lsid=70E91457_19DFAFAD7EA"
  },
  muou: {
    url: ""
  },
  wogg: {
    url: ""
  },
  woniu: {
    url: ""
  },
  leijing: {
    url: ""
  },
  tgsou: {
    tgPic: false,
    count: 0,
    url: "",
    channelUsername: ""
  },
  sites: {
    list: []
  },
  pans: {
    list: []
  },
  danmu: {
    urls: [{ address: `http://${getIPAddress()}:9321`, name: "内置" }],
    autoPush: true
  },
  t4: {
    list: []
  },
  cms: {
    list: []
  },
  alist: [
    {
      name: "🐉神族九帝",
      server: "https://alist.shenzjd.com"
    },
    {
      name: "💢repl",
      server: "https://ali.liucn.repl.co"
    }
  ],
  color: [
    {
      light: {
        bg: "https://i2.100024.xyz/2024/01/13/pptcej.webp",
        bgMask: "0x50ffffff",
        primary: "0xff446732",
        onPrimary: "0xffffffff",
        primaryContainer: "0xffc5efab",
        onPrimaryContainer: "0xff072100",
        secondary: "0xff55624c",
        onSecondary: "0xffffffff",
        secondaryContainer: "0xffd9e7cb",
        onSecondaryContainer: "0xff131f0d",
        tertiary: "0xff386666",
        onTertiary: "0xffffffff",
        tertiaryContainer: "0xffbbebec",
        onTertiaryContainer: "0xff002020",
        error: "0xffba1a1a",
        onError: "0xffffffff",
        errorContainer: "0xffffdad6",
        onErrorContainer: "0xff410002",
        background: "0xfff8faf0",
        onBackground: "0xff191d16",
        surface: "0xfff8faf0",
        onSurface: "0xff191d16",
        surfaceVariant: "0xffe0e4d6",
        onSurfaceVariant: "0xff191d16",
        inverseSurface: "0xff2e312b",
        inverseOnSurface: "0xfff0f2e7",
        outline: "0xff74796d",
        outlineVariant: "0xffc3c8bb",
        shadow: "0xff000000",
        scrim: "0xff000000",
        inversePrimary: "0xffaad291",
        surfaceTint: "0xff446732"
      },
      dark: {
        bg: "https://i2.100024.xyz/2024/01/13/pptg3z.webp",
        bgMask: "0x50000000",
        primary: "0xffaad291",
        onPrimary: "0xff173807",
        primaryContainer: "0xff2d4f1c",
        onPrimaryContainer: "0xffc5efab",
        secondary: "0xffbdcbb0",
        onSecondary: "0xff283420",
        secondaryContainer: "0xff3e4a35",
        onSecondaryContainer: "0xffd9e7cb",
        tertiary: "0xffa0cfcf",
        onTertiary: "0xff003738",
        tertiaryContainer: "0xff1e4e4e",
        onTertiaryContainer: "0xffbbebec",
        error: "0xffffb4ab",
        onError: "0xff690005",
        errorContainer: "0xff93000a",
        onErrorContainer: "0xffffdad6",
        background: "0xff11140e",
        onBackground: "0xffe1e4d9",
        surface: "0xff11140e",
        onSurface: "0xffe1e4d9",
        surfaceVariant: "0xff43483e",
        onSurfaceVariant: "0xffe1e4d9",
        inverseSurface: "0xffe1e4d9",
        inverseOnSurface: "0xff2e312b",
        outline: "0xff8d9286",
        outlineVariant: "0xff43483e",
        shadow: "0xff000000",
        scrim: "0xff000000",
        inversePrimary: "0xff446732",
        surfaceTint: "0xffaad291"
      }
    },
    {
      light: {
        bg: "https://i2.100024.xyz/2024/01/13/pi2rpw.webp",
        bgMask: "0x50ffffff",
        primary: "0xff666014",
        onPrimary: "0xffffffff",
        primaryContainer: "0xffeee58c",
        onPrimaryContainer: "0xff1f1c00",
        secondary: "0xff625f42",
        onSecondary: "0xffffffff",
        secondaryContainer: "0xffe9e4be",
        onSecondaryContainer: "0xff1e1c05",
        tertiary: "0xff3f6654",
        onTertiary: "0xffffffff",
        tertiaryContainer: "0xffc1ecd5",
        onTertiaryContainer: "0xff002114",
        error: "0xffba1a1a",
        onError: "0xffffffff",
        errorContainer: "0xffffdad6",
        onErrorContainer: "0xff410002",
        background: "0xfffef9eb",
        onBackground: "0xff1d1c14",
        surface: "0xfffef9eb",
        onSurface: "0xff1d1c14",
        surfaceVariant: "0xffe7e3d0",
        onSurfaceVariant: "0xff1d1c14",
        inverseSurface: "0xff323128",
        inverseOnSurface: "0xfff5f1e3",
        outline: "0xff7a7768",
        outlineVariant: "0xffcbc7b5",
        shadow: "0xff000000",
        scrim: "0xff000000",
        inversePrimary: "0xffd1c973",
        surfaceTint: "0xff666014"
      },
      dark: {
        bg: "https://i2.100024.xyz/2024/01/13/pi2reo.webp",
        bgMask: "0x50000000",
        primary: "0xffd1c973",
        onPrimary: "0xff353100",
        primaryContainer: "0xff4d4800",
        onPrimaryContainer: "0xffeee58c",
        secondary: "0xffcdc8a3",
        onSecondary: "0xff333117",
        secondaryContainer: "0xff4a482c",
        onSecondaryContainer: "0xffe9e4be",
        tertiary: "0xffa6d0b9",
        onTertiary: "0xff0e3727",
        tertiaryContainer: "0xff274e3d",
        onTertiaryContainer: "0xffc1ecd5",
        error: "0xffffb4ab",
        onError: "0xff690005",
        errorContainer: "0xff93000a",
        onErrorContainer: "0xffffdad6",
        background: "0xff14140c",
        onBackground: "0xffe7e2d5",
        surface: "0xff14140c",
        onSurface: "0xffe7e2d5",
        surfaceVariant: "0xff49473a",
        onSurfaceVariant: "0xffe7e2d5",
        inverseSurface: "0xffe7e2d5",
        inverseOnSurface: "0xff323128",
        outline: "0xff949181",
        outlineVariant: "0xff49473a",
        shadow: "0xff000000",
        scrim: "0xff000000",
        inversePrimary: "0xff666014",
        surfaceTint: "0xffd1c973"
      }
    },
    {
      light: {
        bg: "https://i2.100024.xyz/2024/01/13/qrnuwt.webp",
        bgMask: "0x50ffffff",
        primary: "0xFF2B6C00",
        onPrimary: "0xFFFFFFFF",
        primaryContainer: "0xFFA6F779",
        onPrimaryContainer: "0xFF082100",
        secondary: "0xFF55624C",
        onSecondary: "0xFFFFFFFF",
        secondaryContainer: "0xFFD9E7CA",
        onSecondaryContainer: "0xFF131F0D",
        tertiary: "0xFF386666",
        onTertiary: "0xFFFFFFFF",
        tertiaryContainer: "0xFFBBEBEB",
        onTertiaryContainer: "0xFF002020",
        error: "0xFFBA1A1A",
        onError: "0xFFFFFFFF",
        errorContainer: "0xFFFFDAD6",
        onErrorContainer: "0xFF410002",
        background: "0xFFFDFDF5",
        onBackground: "0xFF1A1C18",
        surface: "0xFFFDFDF5",
        onSurface: "0xFF1A1C18",
        surfaceVariant: "0xFFE0E4D6",
        onSurfaceVariant: "0xFF1A1C18",
        inverseSurface: "0xFF2F312C",
        onInverseSurface: "0xFFF1F1EA",
        outline: "0xFF74796D",
        outlineVariant: "0xFFC3C8BB",
        shadow: "0xFF000000",
        scrim: "0xFF000000",
        inversePrimary: "0xFF8CDA60",
        surfaceTint: "0xFF2B6C00"
      },
      dark: {
        bg: "https://i2.100024.xyz/2024/01/13/qrc37o.webp",
        bgMask: "0x50000000",
        primary: "0xFF8CDA60",
        onPrimary: "0xFF133800",
        primaryContainer: "0xFF1F5100",
        onPrimaryContainer: "0xFFA6F779",
        secondary: "0xFFBDCBAF",
        onSecondary: "0xFF283420",
        secondaryContainer: "0xFF3E4A35",
        onSecondaryContainer: "0xFFD9E7CA",
        tertiary: "0xFFA0CFCF",
        onTertiary: "0xFF003737",
        tertiaryContainer: "0xFF1E4E4E",
        onTertiaryContainer: "0xFFBBEBEB",
        error: "0xFFFFB4AB",
        errorContainer: "0xFF93000A",
        onError: "0xFF690005",
        onErrorContainer: "0xFFFFDAD6",
        background: "0xFF1A1C18",
        onBackground: "0xFFE3E3DC",
        outline: "0xFF8D9286",
        onInverseSurface: "0xFF1A1C18",
        inverseSurface: "0xFFE3E3DC",
        inversePrimary: "0xFF2B6C00",
        shadow: "0xFF000000",
        surfaceTint: "0xFF8CDA60",
        outlineVariant: "0xFF43483E",
        scrim: "0xFF000000",
        surface: "0xFF1A1C18",
        onSurface: "0xFFC7C7C0",
        surfaceVariant: "0xFF43483E",
        onSurfaceVariant: "0xFFC7C7C0"
      }
    }
  ]
};
