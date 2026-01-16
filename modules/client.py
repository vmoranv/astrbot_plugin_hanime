"""
Hanime1.me 客户端类

注意: hanime1.me 是一个使用 Nuxt.js 构建的 SPA（单页应用）。
视频列表是通过 JavaScript 动态渲染的，直接 HTTP 请求只能获取 HTML 骨架。
视频数据可能通过以下方式提供:
1. window.__NUXT__ 变量（Nuxt.js 服务端渲染的数据）
2. 内联脚本中的 JSON 数据
3. 通过 XHR/fetch 请求动态加载

因此，获取视频列表可能失败，但获取单个视频详情页通常是可行的。
"""
import re
import json
import random
import aiohttp
from typing import Optional, List, AsyncGenerator

from .consts import (
    BASE_URL, HEADERS, SEARCH_URL, JSON_HEADERS,
    REGEX_VIDEO_CARD_SIMPLE
)
from .video import Video, VideoPreview
from .utils import clean_html

# 使用 AstrBot 的 logger
try:
    from astrbot.api import logger
except ImportError:
    import logging
    logger = logging.getLogger("hanime.client")


class HanimeClient:
    """Hanime1.me 异步客户端"""
    
    def __init__(
        self,
        proxy: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化客户端
        
        Args:
            proxy: 代理地址（如 http://127.0.0.1:7890）
            timeout: 请求超时时间（秒）
        """
        self.proxy = proxy
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=HEADERS
            )
        return self._session
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _fetch(self, url: str) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 页面URL
            
        Returns:
            HTML内容，失败返回None
        """
        session = await self._get_session()
        try:
            logger.debug(f"[Hanime] Fetching: {url}")
            async with session.get(url, proxy=self.proxy) as response:
                logger.debug(f"[Hanime] Response status: {response.status}")
                if response.status == 200:
                    text = await response.text()
                    logger.debug(f"[Hanime] Got {len(text)} bytes")
                    return text
                else:
                    logger.warning(f"[Hanime] Non-200 status: {response.status}")
                return None
        except Exception as e:
            logger.error(f"[Hanime] Error fetching {url}: {e}")
            return None
    
    async def get_video(self, video_id: str) -> Optional[Video]:
        """
        获取视频详情
        
        Args:
            video_id: 视频ID
            
        Returns:
            Video对象，失败返回None
        """
        video = Video(video_id=video_id)
        session = await self._get_session()
        
        success = await video.fetch(session=session, proxy=self.proxy)
        if success:
            return video
        return None
    
    async def get_latest(self, limit: int = 10) -> List[VideoPreview]:
        """
        获取最新视频列表
        
        Args:
            limit: 最大返回数量
            
        Returns:
            VideoPreview列表
        """
        html = await self._fetch(BASE_URL)
        if not html:
            logger.warning("[Hanime] Failed to fetch homepage")
            return []
        
        # 调试：输出 HTML 片段
        self._debug_html(html, "homepage")
        
        # 首先尝试从嵌入的 JSON 数据中提取
        results = self._parse_embedded_json(html, limit)
        if results:
            logger.info(f"[Hanime] Found {len(results)} videos from embedded JSON")
            return results
        
        # 尝试从 Nuxt payload 提取
        results = self._parse_nuxt_payload(html, limit)
        if results:
            logger.info(f"[Hanime] Found {len(results)} videos from Nuxt payload")
            return results
        
        # 回退到 HTML 解析
        results = self._parse_video_list(html, limit)
        logger.info(f"[Hanime] Found {len(results)} videos from HTML parsing")
        return results
    
    def _debug_html(self, html: str, page_name: str = "page"):
        """调试：输出HTML关键信息"""
        # 检查页面特征
        has_nuxt = 'window.__NUXT__' in html or '__NUXT__' in html
        has_video_link = '/watch?v=' in html
        has_data_src = 'data-src=' in html
        script_count = html.count('<script')
        
        logger.info(f"[Hanime] {page_name} analysis:")
        logger.info(f"  - HTML length: {len(html)} bytes")
        logger.info(f"  - Has __NUXT__: {has_nuxt}")
        logger.info(f"  - Has /watch?v=: {has_video_link}")
        logger.info(f"  - Has data-src: {has_data_src}")
        logger.info(f"  - Script tags: {script_count}")
        
        # 输出找到的视频链接数量
        video_ids = re.findall(r'/watch\?v=(\d+)', html)
        unique_ids = list(set(video_ids))
        logger.info(f"  - Video IDs found: {len(unique_ids)} unique ({video_ids[:5]}...)")
    
    def _parse_nuxt_payload(self, html: str, limit: int) -> List[VideoPreview]:
        """
        解析 Nuxt.js 的 payload 数据
        
        Nuxt.js 会在页面中嵌入 __NUXT_DATA__ 或 __NUXT__ 变量
        """
        results = []
        
        # Nuxt 3.x 格式: <script id="__NUXT_DATA__" type="application/json">
        nuxt_data_pattern = r'<script[^>]+id=["\']__NUXT_DATA__["\'][^>]*>(.+?)</script>'
        matches = re.findall(nuxt_data_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                data = json.loads(match)
                logger.debug(f"[Hanime] Found NUXT_DATA with {len(str(data))} chars")
                videos = self._extract_videos_from_json(data)
                if videos:
                    results.extend(videos)
            except json.JSONDecodeError as e:
                logger.debug(f"[Hanime] NUXT_DATA parse error: {e}")
        
        # Nuxt 2.x 格式: window.__NUXT__=...
        nuxt_patterns = [
            r'window\.__NUXT__\s*=\s*(\{.+?\})(?:;|\s*</script>)',
            r'__NUXT__\s*=\s*(\{.+?\})(?:;|\s*</script>)',
            r'window\.__NUXT__\.state\s*=\s*(\{.+?\})(?:;|\s*</script>)',
        ]
        
        for pattern in nuxt_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    # Nuxt data 可能是 JavaScript 对象而不是严格的 JSON
                    # 尝试修复常见的问题
                    fixed_json = self._fix_js_object(match)
                    data = json.loads(fixed_json)
                    logger.debug(f"[Hanime] Found __NUXT__ with {len(str(data))} chars")
                    videos = self._extract_videos_from_json(data)
                    if videos:
                        results.extend(videos)
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"[Hanime] __NUXT__ parse error: {e}")
        
        return results[:limit] if results else []
    
    def _fix_js_object(self, js_obj: str) -> str:
        """
        尝试将 JavaScript 对象转换为有效的 JSON
        """
        # 替换 undefined -> null
        result = re.sub(r'\bundefined\b', 'null', js_obj)
        # 替换单引号 -> 双引号 (简单情况)
        # 注意：这不是完美的转换，但对于简单情况有效
        return result
    
    async def search(
        self, 
        query: str = "",
        genre: str = "",
        sort: str = "latest",
        page: int = 1,
        limit: int = 20
    ) -> List[VideoPreview]:
        """
        搜索视频
        
        Args:
            query: 搜索关键词
            genre: 分类/类型
            sort: 排序方式 (latest/views/likes)
            page: 页码
            limit: 最大返回数量
            
        Returns:
            VideoPreview列表
        """
        params = []
        if query:
            params.append(f"query={query}")
        if genre:
            params.append(f"genre={genre}")
        if sort and sort != "latest":
            params.append(f"sort={sort}")
        if page > 1:
            params.append(f"page={page}")
        
        url = f"{SEARCH_URL}?{'&'.join(params)}" if params else BASE_URL
        
        html = await self._fetch(url)
        if not html:
            return []
        
        return self._parse_video_list(html, limit)
    
    async def get_by_genre(
        self,
        genre: str,
        page: int = 1,
        limit: int = 20
    ) -> List[VideoPreview]:
        """
        按分类获取视频
        
        Args:
            genre: 分类名称
            page: 页码
            limit: 最大返回数量
            
        Returns:
            VideoPreview列表
        """
        return await self.search(genre=genre, page=page, limit=limit)
    
    def _parse_embedded_json(self, html: str, limit: int) -> List[VideoPreview]:
        """
        从页面嵌入的 JSON 数据中提取视频信息
        
        hanime1.me 在页面中嵌入了 __NUXT__ 或类似的 JSON 数据
        """
        results = []
        
        # 尝试多种 JSON 嵌入模式
        json_patterns = [
            # Nuxt.js 模式
            r'window\.__NUXT__\s*=\s*(\{.+?\});?\s*</script>',
            # 通用 JSON 数据模式
            r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*</script>',
            # 内联数据模式
            r'<script[^>]*>\s*var\s+(?:videos?|data)\s*=\s*(\[.+?\]);\s*</script>',
            # JSON-LD 模式
            r'<script[^>]+type="application/ld\+json"[^>]*>(\{.+?\})</script>',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    data = json.loads(match)
                    videos = self._extract_videos_from_json(data)
                    if videos:
                        results.extend(videos)
                        if len(results) >= limit:
                            return results[:limit]
                except json.JSONDecodeError:
                    continue
        
        return results[:limit] if results else []
    
    def _extract_videos_from_json(self, data, max_depth: int = 5) -> List[VideoPreview]:
        """
        递归从 JSON 数据中提取视频信息
        """
        results = []
        
        if max_depth <= 0:
            return results
        
        if isinstance(data, dict):
            # 检查是否是视频对象
            vid = None
            if 'id' in data and isinstance(data['id'], (int, str)):
                vid = str(data['id'])
            elif 'video_id' in data:
                vid = str(data['video_id'])
            elif 'slug' in data and str(data.get('slug', '')).isdigit():
                vid = str(data['slug'])
            
            if vid and vid.isdigit():
                preview = VideoPreview(video_id=vid)
                preview.title = data.get('name') or data.get('title') or ""
                preview.thumbnail = (
                    data.get('cover_url') or
                    data.get('thumbnail') or
                    data.get('poster_url') or
                    data.get('cover') or
                    ""
                )
                if preview.title or preview.thumbnail:
                    results.append(preview)
            
            # 递归搜索
            for key, value in data.items():
                if key in ('videos', 'items', 'results', 'data', 'hentai_videos', 'state'):
                    sub_results = self._extract_videos_from_json(value, max_depth - 1)
                    results.extend(sub_results)
        
        elif isinstance(data, list):
            for item in data:
                sub_results = self._extract_videos_from_json(item, max_depth - 1)
                results.extend(sub_results)
        
        return results
    
    def _parse_video_list(self, html: str, limit: int) -> List[VideoPreview]:
        """
        解析视频列表HTML
        
        Args:
            html: HTML内容
            limit: 最大返回数量
            
        Returns:
            VideoPreview列表
        """
        results = []
        seen_ids = set()
        
        # 输出调试信息
        logger.debug(f"[Hanime] HTML length: {len(html)}")
        
        # 方法1: 使用简单正则提取所有视频ID
        video_ids = []
        for match in REGEX_VIDEO_CARD_SIMPLE.finditer(html):
            vid = match.group(2)
            if vid and vid not in seen_ids:
                seen_ids.add(vid)
                video_ids.append(vid)
        
        logger.debug(f"[Hanime] Found {len(video_ids)} video IDs with simple regex")
        
        # 方法1.5: 尝试更多的正则模式
        if not video_ids:
            # 尝试匹配 data-video-id 属性
            for match in re.finditer(r'data-video-id="(\d+)"', html):
                vid = match.group(1)
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    video_ids.append(vid)
            
            # 尝试匹配 /watch?v= 的各种变体
            for match in re.finditer(r'/watch\?v=(\d+)', html):
                vid = match.group(1)
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    video_ids.append(vid)
            
            logger.debug(f"[Hanime] Found {len(video_ids)} video IDs with extended regex")
        
        # 为每个ID创建预览对象
        for vid in video_ids[:limit]:
            preview = VideoPreview(video_id=vid)
            
            # 尝试提取额外信息
            preview.thumbnail = self._extract_thumbnail_for_id(html, vid)
            preview.title = self._extract_title_for_id(html, vid)
            
            results.append(preview)
        
        # 如果方法1没有结果，尝试方法2
        if not results:
            logger.debug("[Hanime] Trying advanced parsing...")
            results = self._parse_video_cards_advanced(html, limit)
        
        return results[:limit]
    
    def _extract_thumbnail_for_id(self, html: str, video_id: str) -> str:
        """提取指定视频ID的缩略图"""
        # 在视频链接附近寻找图片
        # 匹配模式: 包含 /watch?v=ID 的链接附近的 img src
        patterns = [
            # 链接内的图片
            rf'<a[^>]+href="/watch\?v={video_id}"[^>]*>.*?<img[^>]+(?:src|data-src)="([^"]+)"',
            # 图片后跟链接
            rf'<img[^>]+(?:src|data-src)="([^"]+)"[^>]*>.*?<a[^>]+href="/watch\?v={video_id}"',
            # 更宽松的匹配
            rf'href="/watch\?v={video_id}".*?<img[^>]+(?:src|data-src)="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_title_for_id(self, html: str, video_id: str) -> str:
        """提取指定视频ID的标题"""
        patterns = [
            # 链接后的标题元素
            rf'href="/watch\?v={video_id}"[^>]*>.*?<[^>]*class="[^"]*(?:title|card-mobile-title|home-rows-videos-title)[^"]*"[^>]*>([^<]+)<',
            # 链接文本作为标题
            rf'<a[^>]+href="/watch\?v={video_id}"[^>]*title="([^"]+)"',
            # alt属性
            rf'href="/watch\?v={video_id}".*?alt="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                title = clean_html(match.group(1)).strip()
                if title and len(title) > 1:
                    return title
        
        return ""
    
    def _parse_video_cards_advanced(self, html: str, limit: int) -> List[VideoPreview]:
        """
        高级视频卡片解析（备用方法）
        
        尝试匹配更复杂的HTML结构
        """
        results = []
        seen_ids = set()
        
        # 尝试匹配包含视频信息的完整卡片块
        # 基于常见的 hanime 页面结构
        card_patterns = [
            # 模式1: div.card 结构
            r'<div[^>]*class="[^"]*(?:card|video-card|video-item)[^"]*"[^>]*>.*?'
            r'href="/watch\?v=(\d+)".*?'
            r'(?:<img[^>]+(?:src|data-src)="([^"]+)")?.*?'
            r'(?:class="[^"]*title[^"]*"[^>]*>([^<]*)<)?',
            
            # 模式2: a标签直接包含信息
            r'<a[^>]+href="/watch\?v=(\d+)"[^>]*>.*?'
            r'<img[^>]+(?:src|data-src)="([^"]+)"[^>]*>.*?'
            r'</a>.*?<[^>]*>([^<]{5,})<',
            
            # 模式3: 简化匹配
            r'<a[^>]+href="/watch\?v=(\d+)"[^>]*(?:title="([^"]+)")?[^>]*>',
        ]
        
        for pattern in card_patterns:
            for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
                vid = match.group(1)
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    
                    preview = VideoPreview(video_id=vid)
                    
                    # 尝试提取其他字段（不同模式有不同的分组）
                    groups = match.groups()
                    if len(groups) >= 2 and groups[1]:
                        # 可能是缩略图或标题
                        val = groups[1]
                        if val.startswith(('http', '//', 'data:')):
                            preview.thumbnail = val
                        else:
                            preview.title = clean_html(val).strip()
                    
                    if len(groups) >= 3 and groups[2]:
                        preview.title = clean_html(groups[2]).strip()
                    
                    results.append(preview)
                    
                    if len(results) >= limit:
                        break
            
            if results:
                break
        
        return results
    
    async def iter_latest(
        self, 
        max_pages: int = 5,
        per_page: int = 20
    ) -> AsyncGenerator[VideoPreview, None]:
        """
        迭代获取最新视频
        
        Args:
            max_pages: 最大页数
            per_page: 每页数量
            
        Yields:
            VideoPreview对象
        """
        for page in range(1, max_pages + 1):
            videos = await self.search(page=page, limit=per_page)
            if not videos:
                break
            
            for video in videos:
                yield video
    
    async def get_random(self) -> Optional[Video]:
        """
        获取随机视频
        
        由于 hanime1.me 使用 SPA 架构，获取视频列表可能失败。
        因此我们使用以下策略:
        1. 尝试从首页获取视频列表
        2. 如果失败，直接使用随机视频 ID
        
        Returns:
            Video对象，失败返回None
        """
        # 先尝试从首页获取
        videos = await self.get_latest(limit=20)
        
        if videos:
            preview = random.choice(videos)
            return await self.get_video(preview.video_id)
        
        # 如果首页没有，直接尝试随机视频ID
        # hanime1.me 的视频 ID 范围大约在 1-200000 之间
        # 使用多次尝试来提高成功率
        for attempt in range(5):
            # 使用不同的 ID 范围策略
            if attempt < 2:
                # 尝试较新的视频 (ID 较大)
                random_id = str(random.randint(100000, 200000))
            elif attempt < 4:
                # 尝试中间范围
                random_id = str(random.randint(50000, 100000))
            else:
                # 尝试较老的视频
                random_id = str(random.randint(10000, 50000))
            
            logger.info(f"[Hanime] Trying random video ID: {random_id} (attempt {attempt + 1})")
            video = await self.get_video(random_id)
            
            if video and video.title:
                return video
        
        logger.warning("[Hanime] Failed to get random video after 5 attempts")
        return None