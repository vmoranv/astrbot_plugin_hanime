"""
Hanime1.me 常量定义
"""
import re

# 基础URL
BASE_URL = "https://hanime1.me"
VIDEO_URL_PREFIX = f"{BASE_URL}/watch?v="

# API端点 - hanime1.me 使用的内部API
# 基于 Nuxt.js 的网站通常有 /_nuxt/ 或 /api/ 端点
API_BASE_URL = "https://hanime1.me/api"
API_SEARCH_HINT = f"{BASE_URL}/search"  # 搜索建议接口

# HTTP 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": BASE_URL,
}

# JSON API 请求头
JSON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
}

# 正则表达式 - 提取视频信息
REGEX_VIDEO_ID = re.compile(r'watch\?v=(\d+)')

# 视频详情页 - 标题
REGEX_VIDEO_TITLE = re.compile(r'<h3[^>]*class="[^"]*video-details-title[^"]*"[^>]*>([^<]+)</h3>', re.IGNORECASE)
REGEX_VIDEO_TITLE_ALT = re.compile(r'<title>([^<]+)</title>', re.IGNORECASE)

# 视频详情页 - 观看次数 (格式: 观看次数：9.7万次  2026-01-16)
# 支持多种格式: "9.7万次", "97000次", "9,700次"
REGEX_VIDEO_VIEWS = re.compile(r'觀看次數[：:]\s*([\d,.]+)(?:万|萬)?次', re.IGNORECASE)
REGEX_VIDEO_VIEWS_ALT = re.compile(r'([\d,.]+)\s*(?:万|萬)?\s*次(?:觀看|观看)?', re.IGNORECASE)

# 视频详情页 - 上传日期 (格式: 2026-01-16 或 2026/01/16)
REGEX_VIDEO_UPLOAD_DATE = re.compile(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})')

# 视频详情页 - 时长
REGEX_VIDEO_DURATION = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)')

# 提取视频源 - m3u8/mp4
REGEX_VIDEO_SOURCE = re.compile(r'["\']?(?:src|source)["\']?\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE)
REGEX_VIDEO_SOURCE_ALT = re.compile(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', re.IGNORECASE)
REGEX_VIDEO_MP4 = re.compile(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', re.IGNORECASE)

# 提取缩略图/封面
REGEX_THUMBNAIL = re.compile(r'poster["\']?\s*[=:]\s*["\']([^"\']+)["\']', re.IGNORECASE)
REGEX_THUMBNAIL_ALT = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"', re.IGNORECASE)
REGEX_THUMBNAIL_ALT2 = re.compile(r'content="([^"]+)"\s+property="og:image"', re.IGNORECASE)

# 提取标签 - 匹配 # 开头的标签链接
REGEX_TAGS = re.compile(r'<a[^>]+href="/search\?(?:genre|query)=([^"&]+)"[^>]*>\s*#?\s*([^<]+)</a>', re.IGNORECASE)
REGEX_TAGS_ALT = re.compile(r'#\s*(\S+)', re.IGNORECASE)

# 提取作者/上传者
REGEX_UPLOADER = re.compile(r'<a[^>]+class="[^"]*(?:creator|uploader|artist)[^"]*"[^>]*>([^<]+)</a>', re.IGNORECASE)
REGEX_UPLOADER_ALT = re.compile(r'class="[^"]*video-details-uploader[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>', re.IGNORECASE)

# 首页/列表页 - 视频卡片
# 格式: 时长在左上角(如02:59), 点赞率和观看次数在底部(如 100% 9.7万次)
REGEX_VIDEO_CARD = re.compile(
    r'<a[^>]+href="(/watch\?v=(\d+))"[^>]*>.*?'
    r'(?:<img[^>]+(?:src|data-src)="([^"]+)"[^>]*>)?.*?'
    r'(?:<[^>]*class="[^"]*(?:card-mobile-title|title)[^"]*"[^>]*>([^<]*)</[^>]*>)?',
    re.IGNORECASE | re.DOTALL
)

# 列表页视频卡片 - 简化版
REGEX_VIDEO_CARD_SIMPLE = re.compile(
    r'href="(/watch\?v=(\d+))"',
    re.IGNORECASE
)

# 列表页缩略图
REGEX_CARD_THUMBNAIL = re.compile(
    r'<a[^>]+href="/watch\?v=(\d+)"[^>]*>.*?<img[^>]+(?:src|data-src)="([^"]+)"',
    re.IGNORECASE | re.DOTALL
)

# 列表页标题
REGEX_CARD_TITLE = re.compile(
    r'/watch\?v=(\d+)"[^>]*>.*?class="[^"]*(?:card-mobile-title|home-rows-videos-title)[^"]*"[^>]*>([^<]+)<',
    re.IGNORECASE | re.DOTALL
)

# 搜索相关
SEARCH_URL = f"{BASE_URL}/search"

# 分类/类型
CATEGORIES = [
    "里番", "泡面番", "Motion Anime",
    "3DCG", "2.5D", "2D動画", "AI生成", "MMD", "Cosplay"
]
TAGS = [
    "NTR", "ビッチ", "ファンタジー", 
    "レイプ", "ロリ", "人妻", "催眠", "凌辱", 
    "女子校生", "女教師", "妹", "姉", "巨乳",
    "近親相姦", "母", "痴女", "純愛", "輪姦",
    "中文字幕", "無碼"
]
# 排序选项
SORT_OPTIONS = {
    "latest": "最新上傳",
    "views": "最多觀看", 
    "likes": "最多喜歡",
}

# 视频质量
QUALITY_OPTIONS = ["360p", "480p", "720p", "1080p"]
