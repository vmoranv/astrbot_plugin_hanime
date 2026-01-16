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
        """提取上传者"""
        match = REGEX_UPLOADER.search(self._html_content)
        if match:
            return clean_html(match.group(1)).strip()
        
        match = REGEX_UPLOADER_ALT.search(self._html_content)
        if match:
            return clean_html(match.group(1)).strip()
        
        # 尝试其他模式
        patterns = [
            r'上傳者[：:]\s*<[^>]*>([^<]+)<',
            r'<a[^>]+href="/creator/[^"]*"[^>]*>([^<]+)</a>',
            r'class="[^"]*uploader[^"]*"[^>]*>([^<]+)<',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self._html_content, re.IGNORECASE)
            if match:
                return clean_html(match.group(1)).strip()
        
        return ""
    
    def _extract_tags(self) -> List[str]:
        """提取标签"""
        tags = set()
        
        # 使用主正则
        for match in REGEX_TAGS.finditer(self._html_content):
            tag = clean_html(match.group(2)).strip()
            if tag and len(tag) < 50:
                tags.add(tag)
        
        # 如果没找到，尝试其他模式
        if not tags:
            # 匹配 href="/search?genre=xxx" 模式
            genre_pattern = r'<a[^>]+href="/search\?genre=([^"&]+)"[^>]*>([^<]*)</a>'
            for match in re.finditer(genre_pattern, self._html_content, re.IGNORECASE):
                tag = clean_html(match.group(2)).strip()
                if tag and len(tag) < 50:
                    tags.add(tag)
            
            # 匹配 class="tag" 模式
            tag_pattern = r'<[^>]+class="[^"]*tag[^"]*"[^>]*>([^<]+)</[^>]+>'
            for match in re.finditer(tag_pattern, self._html_content, re.IGNORECASE):
                tag = clean_html(match.group(1)).strip()
                # 排除数字和过短的标签
                if tag and len(tag) > 1 and len(tag) < 50 and not tag.isdigit():
                    tags.add(tag)
        
        return list(tags)
    
    def _extract_video_url(self) -> str:
        """提取视频源URL"""
        # 尝试提取m3u8
        match = REGEX_VIDEO_SOURCE.search(self._html_content)
        if match:
            return match.group(1)
        
        match = REGEX_VIDEO_SOURCE_ALT.search(self._html_content)
        if match:
            return match.group(0)
        
        # 尝试提取mp4
        match = REGEX_VIDEO_MP4.search(self._html_content)
        if match:
            return match.group(0)
        
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