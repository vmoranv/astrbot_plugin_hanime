"""
Hanime1.me 视频类
"""
import re
import aiohttp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .consts import (
    VIDEO_URL_PREFIX, HEADERS,
    REGEX_VIDEO_TITLE, REGEX_VIDEO_TITLE_ALT,
    REGEX_VIDEO_VIEWS, REGEX_VIDEO_VIEWS_ALT,
    REGEX_VIDEO_UPLOAD_DATE, REGEX_VIDEO_DURATION,
    REGEX_VIDEO_SOURCE, REGEX_VIDEO_SOURCE_ALT, REGEX_VIDEO_MP4,
    REGEX_THUMBNAIL, REGEX_THUMBNAIL_ALT, REGEX_THUMBNAIL_ALT2,
    REGEX_TAGS, REGEX_UPLOADER, REGEX_UPLOADER_ALT
)
from .utils import parse_views, parse_duration, clean_html


@dataclass
class Video:
    """视频信息类"""
    video_id: str
    title: str = ""
    views: int = 0
    duration: int = 0  # 秒
    upload_date: str = ""
    thumbnail: str = ""
    uploader: str = ""
    tags: List[str] = field(default_factory=list)
    video_url: str = ""  # m3u8 或 mp4 链接
    
    # 内部使用
    _html_content: str = ""
    _fetched: bool = False
    
    @property
    def url(self) -> str:
        """获取视频页面URL"""
        return f"{VIDEO_URL_PREFIX}{self.video_id}"
    
    @property
    def views_formatted(self) -> str:
        """格式化的观看次数"""
        from .utils import format_views
        return format_views(self.views)
    
    @property
    def duration_formatted(self) -> str:
        """格式化的时长"""
        from .utils import format_duration
        return format_duration(self.duration)
    
    async def fetch(
        self, 
        session: Optional[aiohttp.ClientSession] = None,
        proxy: Optional[str] = None
    ) -> bool:
        """
        获取视频详情
        
        Args:
            session: aiohttp会话
            proxy: 代理地址
            
        Returns:
            是否获取成功
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            async with session.get(
                self.url, 
                headers=HEADERS,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    return False
                
                self._html_content = await response.text()
                self._fetched = True
                
                # 解析HTML
                self._parse_html()
                
                return True
        except Exception as e:
            print(f"Error fetching video {self.video_id}: {e}")
            return False
        finally:
            if close_session:
                await session.close()
    
    def _parse_html(self):
        """解析HTML内容"""
        if not self._html_content:
            return
        
        # 提取标题
        self.title = self._extract_title()
        
        # 提取观看次数
        self.views = self._extract_views()
        
        # 提取上传日期
        self.upload_date = self._extract_upload_date()
        
        # 提取时长
        self.duration = self._extract_duration()
        
        # 提取缩略图
        self.thumbnail = self._extract_thumbnail()
        
        # 提取上传者
        self.uploader = self._extract_uploader()
        
        # 提取标签
        self.tags = self._extract_tags()
        
        # 提取视频源
        self.video_url = self._extract_video_url()
    
    def _extract_title(self) -> str:
        """提取标题"""
        # 尝试主正则
        match = REGEX_VIDEO_TITLE.search(self._html_content)
        if match:
            return clean_html(match.group(1)).strip()
        
        # 尝试备用正则（从title标签）
        match = REGEX_VIDEO_TITLE_ALT.search(self._html_content)
        if match:
            title = clean_html(match.group(1)).strip()
            # 移除网站后缀
            title = re.sub(r'\s*[-|]\s*Hanime1.*$', '', title, flags=re.IGNORECASE)
            return title
        
        return ""
    
    def _extract_views(self) -> int:
        """提取观看次数"""
        # 尝试主正则 - 匹配 "觀看次數：9.7万次"
        match = REGEX_VIDEO_VIEWS.search(self._html_content)
        if match:
            return parse_views(match.group(0))
        
        # 尝试备用正则 - 匹配更宽松的格式
        match = REGEX_VIDEO_VIEWS_ALT.search(self._html_content)
        if match:
            return parse_views(match.group(0))
        
        # 尝试更宽松的匹配
        # 匹配类似 "9.7万次" 或 "97000次" 的格式
        patterns = [
            r'([\d,.]+)\s*(?:万|萬)\s*次',  # 9.7万次
            r'([\d,]+)\s*次(?:觀看|观看|瀏覽)?',  # 97000次觀看
            r'觀看[：:]\s*([\d,.]+)(?:万|萬)?',  # 觀看：9.7万
            r'views?[：:]\s*([\d,.]+)',  # views: 97000
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self._html_content, re.IGNORECASE)
            if match:
                return parse_views(match.group(0))
        
        return 0
    
    def _extract_upload_date(self) -> str:
        """提取上传日期"""
        match = REGEX_VIDEO_UPLOAD_DATE.search(self._html_content)
        if match:
            return match.group(1)
        
        return ""
    
    def _extract_duration(self) -> int:
        """提取时长"""
        # 首先尝试从meta或特定元素提取
        patterns = [
            r'duration["\']?\s*[=:]\s*["\']?(\d{1,2}:\d{2}(?::\d{2})?)',
            r'<span[^>]*class="[^"]*duration[^"]*"[^>]*>(\d{1,2}:\d{2}(?::\d{2})?)</span>',
            r'時長[：:]\s*(\d{1,2}:\d{2}(?::\d{2})?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self._html_content, re.IGNORECASE)
            if match:
                return parse_duration(match.group(1))
        
        # 使用通用正则
        match = REGEX_VIDEO_DURATION.search(self._html_content)
        if match:
            return parse_duration(match.group(1))
        
        return 0
    
    def _extract_thumbnail(self) -> str:
        """提取缩略图"""
        # 尝试从og:image提取
        match = REGEX_THUMBNAIL_ALT.search(self._html_content)
        if match:
            return match.group(1)
        
        match = REGEX_THUMBNAIL_ALT2.search(self._html_content)
        if match:
            return match.group(1)
        
        # 尝试从poster属性提取
        match = REGEX_THUMBNAIL.search(self._html_content)
        if match:
            return match.group(1)
        
        # 尝试其他常见模式
        patterns = [
            r'<img[^>]+id="player-cover"[^>]+src="([^"]+)"',
            r'<img[^>]+class="[^"]*cover[^"]*"[^>]+src="([^"]+)"',
            r'data-poster="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self._html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_uploader(self) -> str:
        """提取上传者 (针对 HTML 源码修正版)"""
        if not self._html_content:
            return "未知上传者"

        # 1. 策略一：精准匹配 ID (最稳)
        # 源码中: <a id="video-artist-name" ...> StarryMomoko </a>
        # 使用 DOTALL 模式因为名字可能在标签的下一行
        id_pattern = r'id="video-artist-name"[^>]*>(.*?)</a>'
        match = re.search(id_pattern, self._html_content, re.DOTALL | re.IGNORECASE)
        if match:
            name = clean_html(match.group(1)).strip()
            if name:
                return name

        # 2. 策略二：从标题中提取 (备选)
        # 源码中: <h3 id="shareBtn-title" ...>[StarryMomoko] Ellen oral...</h3>
        # 很多视频标题开头是 [作者名]
        title_pattern = r'<h3\s+id="shareBtn-title"[^>]*>\s*\[([^\]]+)\]'
        match = re.search(title_pattern, self._html_content, re.IGNORECASE)
        if match:
            name = clean_html(match.group(1)).strip()
            # 排除一些非作者的标记
            if name and "中文字幕" not in name and "無碼" not in name:
                return name

        # 3. 策略三：从 Meta Description 提取
        # 源码中: Title / タイトル: ... Brand / ブランド: StarryMomoko
        desc_pattern = r'(?:Brand|Circle|Artist)\s*/\s*(?:ブランド|サークル|作者)[^:]*:\s*([^\n<]+)'
        match = re.search(desc_pattern, self._html_content, re.IGNORECASE)
        if match:
            return clean_html(match.group(1)).strip()

        return "未知上传者"


    
    def _extract_tags(self) -> List[str]:
        """提取标签 (最终修正版：基于 single-video-tag 类提取)"""
        tags = set()
        
        if not self._html_content:
            return []

        # 1. 策略一：Meta 标签 (依旧保留，作为最稳的备选)
        meta_pattern = r'<meta\s+property="article:tag"\s+content="([^"]+)"'
        for match in re.finditer(meta_pattern, self._html_content, re.IGNORECASE):
            tag = clean_html(match.group(1)).strip()
            if tag:
                tags.add(tag)

        # 2. 策略二：基于 class="single-video-tag" 提取 (针对你提供的 HTML 结构)
        # 这种方法最准，因为它专门定位标签区域，绝对不会抓到导航栏
        
        # HTML 结构示例:
        # <div class="single-video-tag" ...><a ...><span>#</span>&nbsp;绝区零</a></div>
        # <div class="single-video-tag" ...><a ...>无码&nbsp;<span>(1)</span></a></div>
        
        # 正则逻辑：
        # 1. 找到 class="single-video-tag" 的 div
        # 2. 提取里面 <a> 标签包裹的所有内容 (group 1)
        tag_pattern = r'class="single-video-tag"[^>]*>.*?<a[^>]*>(.*?)</a>'
        
        for match in re.finditer(tag_pattern, self._html_content, re.DOTALL | re.IGNORECASE):
            raw_content = match.group(1)
            
            # 数据清洗步骤：
            
            # 第一步：移除所有 <span>...</span> 标签及其内容
            # 这会把 <span>#</span> 和 <span>(1)</span> 全部删掉
            cleaned_content = re.sub(r'<span[^>]*>.*?</span>', '', raw_content, flags=re.DOTALL | re.IGNORECASE)
            
            # 第二步：使用 clean_html 清理 &nbsp; 和其他 HTML 实体
            tag_text = clean_html(cleaned_content).strip()
            
            # 第三步：有效性检查
            if tag_text and len(tag_text) < 50:
                tags.add(tag_text)

        # 3. 清理黑名单
        blacklist = {'Hanime1', 'H動漫', '線上看', '免費', '1080p', 'HD', '登入', '註冊'}
        final_tags = [t for t in tags if t not in blacklist]

        # 排序并返回
        return sorted(list(final_tags))


    
    def _extract_video_url(self) -> str:
        """提取视频源URL (终极版：支持 m3u8/mp4，自动修复转义和 &amp;)"""
        # 引入 html 库用于解码 &amp;
        import html
        
        if not self._html_content:
            return ""

        # --- 阶段 1: 暴力提取 (针对 JS 变量中的链接) ---
        
        # 定义要查找的扩展名和对应的正则模式
        # 优先找 m3u8，其次找 mp4
        targets = [
            ('.m3u8', [
                r'"(https?://[^"]+\.m3u8[^"]*)"',      # 双引号
                r'\'(https?://[^\']+\.m3u8[^\']*)\'',  # 单引号
                r'url:\s*"(https?://[^"]+\.m3u8[^"]*)"' # JS属性
            ]),
            ('.mp4', [
                r'"(https?://[^"]+\.mp4[^"]*)"',
                r'\'(https?://[^\']+\.mp4[^\']*)\''
            ])
        ]

        for ext, patterns in targets:
            for pattern in patterns:
                for match in re.finditer(pattern, self._html_content):
                    url = match.group(1)
                    
                    # 步骤1：处理 Unicode 转义 (如 \u002F)
                    try:
                        url = url.encode('utf-8').decode('unicode_escape')
                    except:
                        pass
                    
                    # 步骤2：处理反斜杠转义 (如 \/ -> /)
                    url = url.replace(r'\/', '/')
                    
                    # 步骤3：处理 HTML 实体 (关键！把 &amp; 变回 &)
                    url = html.unescape(url)
                    
                    # 简单的有效性检查
                    if url.startswith('http'):
                        return url

        # --- 阶段 2: 使用 consts.py 中的正则 (保底逻辑) ---
        
        try:
            from .consts import (
                REGEX_VIDEO_SOURCE, 
                REGEX_VIDEO_SOURCE_ALT, 
                REGEX_VIDEO_MP4
            )
            
            # 辅助函数：统一清理 URL
            def clean_url(u):
                if not u: return ""
                u = u.replace(r'\/', '/')
                return html.unescape(u)

            # 尝试标准 m3u8 匹配
            match = REGEX_VIDEO_SOURCE.search(self._html_content)
            if match:
                return clean_url(match.group(1))
            
            match = REGEX_VIDEO_SOURCE_ALT.search(self._html_content)
            if match:
                return clean_url(match.group(0))
                
            # 尝试标准 mp4 匹配
            match = REGEX_VIDEO_MP4.search(self._html_content)
            if match:
                return clean_url(match.group(0))
                
        except ImportError:
            pass

        return ""


    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "views": self.views,
            "views_formatted": self.views_formatted,
            "duration": self.duration,
            "duration_formatted": self.duration_formatted,
            "upload_date": self.upload_date,
            "thumbnail": self.thumbnail,
            "uploader": self.uploader,
            "tags": self.tags,
            "video_url": self.video_url,
        }
    
    def __repr__(self) -> str:
        return f"Video(id={self.video_id}, title={self.title[:30]}...)"


class VideoPreview:
    """视频预览信息（列表页使用）"""
    
    def __init__(
        self,
        video_id: str,
        title: str = "",
        thumbnail: str = "",
        duration: str = "",
        views: str = ""
    ):
        self.video_id = video_id
        self.title = title
        self.thumbnail = thumbnail
        self.duration_str = duration
        self.views_str = views
    
    @property
    def url(self) -> str:
        return f"{VIDEO_URL_PREFIX}{self.video_id}"
    
    @property
    def duration(self) -> int:
        return parse_duration(self.duration_str)
    
    @property
    def views(self) -> int:
        return parse_views(self.views_str)
    
    async def to_video(
        self, 
        session: Optional[aiohttp.ClientSession] = None,
        proxy: Optional[str] = None
    ) -> Video:
        """转换为完整的Video对象（需要额外请求）"""
        video = Video(video_id=self.video_id)
        video.title = self.title
        video.thumbnail = self.thumbnail
        video.duration = self.duration
        video.views = self.views
        
        # 获取完整信息
        await video.fetch(session=session, proxy=proxy)
        
        return video
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "duration": self.duration_str,
            "views": self.views_str,
        }
    
    def __repr__(self) -> str:
        return f"VideoPreview(id={self.video_id}, title={self.title[:30] if self.title else 'N/A'})"
