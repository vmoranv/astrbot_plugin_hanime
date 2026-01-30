"""
Hanime1.me AstrBot 插件
提供 hanime1.me 视频信息查询功能
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, Image
from astrbot.api import logger

from .modules.client import HanimeClient
from .modules.video import Video
from .modules.utils import download_image, blur_image, save_image
from .modules.consts import CATEGORIES, TAGS


def get_cache_dir() -> Path:
    """获取缓存目录"""
    cache_dir = Path(tempfile.gettempdir()) / "hanime_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def clean_cache(cache_dir: Path, max_age_hours: int = 24) -> int:
    """清理缓存文件"""
    import time
    cleaned = 0
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    try:
        for file_path in cache_dir.glob("*"):
            if file_path.is_file() and (max_age_hours == 0 or (now - file_path.stat().st_mtime) > max_age_seconds):
                file_path.unlink()
                cleaned += 1
    except Exception as e:
        logger.warning(f"[Hanime] 清理缓存时出错: {e}")
    
    return cleaned


@register("hanime", "Hanime Plugin", "Hanime1.me 视频信息查询插件", "1.0.0")
class HanimePlugin(Star):
    """Hanime1.me 视频查询插件"""
    
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.client: Optional[HanimeClient] = None
        self.cache_dir = get_cache_dir()
    
    async def initialize(self):
        """插件初始化"""
        # 获取配置
        proxy = self.config.get("proxy", "")
        self.blur_level = self.config.get("blur_level", 0)
        self.max_search_results = self.config.get("max_search_results", 10)
        
        # 初始化客户端
        self.client = HanimeClient(proxy=proxy or None)
        
        # 清理旧缓存
        cleaned = clean_cache(self.cache_dir, max_age_hours=24)
        if cleaned > 0:
            logger.info(f"[Hanime] 清理了 {cleaned} 个缓存文件")
        
        logger.info("[Hanime] 插件初始化完成")
    
    async def terminate(self):
        """插件销毁"""
        # 关闭客户端
        if self.client:
            await self.client.close()
        
        # 清理缓存
        clean_cache(self.cache_dir, max_age_hours=0)
        logger.info("[Hanime] 插件已停止")
    
    def _clean_previous_cache(self):
        """清理之前的缓存文件"""
        try:
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
        except Exception as e:
            logger.warning(f"[Hanime] 清理缓存失败: {e}")
    
    async def _get_thumbnail_with_blur(self, thumbnail_url: str, video_id: str) -> Optional[str]:
        """
        获取并处理缩略图
        
        Args:
            thumbnail_url: 缩略图URL
            video_id: 视频ID
        
        Returns:
            处理后的本地图片路径，失败返回None
        """
        if not thumbnail_url:
            return None
        
        try:
            # 清理之前的缓存
            self._clean_previous_cache()
            
            # 下载图片
            proxy = self.config.get("proxy", "")
            image_data = await download_image(thumbnail_url, proxy=proxy or None)
            
            if not image_data:
                return None
            
            # 应用模糊效果
            if self.blur_level > 0:
                image_data = await blur_image(image_data, blur_radius=self.blur_level)
            
            # 保存到本地
            save_path = str(self.cache_dir / f"{video_id}_thumb.jpg")
            success = await save_image(image_data, save_path)
            
            return save_path if success else None
        except Exception as e:
            logger.warning(f"[Hanime] 获取缩略图失败: {e}")
            return None
    
    def _format_video_info(self, video: Video) -> str:
        """格式化视频信息"""
        lines = [
            f"🎬 {video.title}",
            "",
            f"📊 ID: {video.video_id}",
            f"👁️ 观看: {video.views_formatted}",
            f"⏱️ 时长: {video.duration_formatted}",
        ]
        
        if video.upload_date:
            lines.append(f"📅 上传: {video.upload_date}")
        
        if video.uploader:
            lines.append(f"👤 上传者: {video.uploader}")
        
        if video.tags:
            lines.append(f"🏷️ 标签: {', '.join(video.tags[:5])}")
        
        lines.extend(["", f"🔗 链接: {video.url}"])
        if video.video_url:
            lines.append(f"▶️ 直链: {video.video_url}")
        
        return "\n\u200E".join(lines)
    
    @filter.command("hv")
    async def cmd_video_info(self, event: AstrMessageEvent, video_id: str = ""):
        """
        获取视频信息
        用法: /hv <视频ID>
        """
        if not video_id:
            yield event.plain_result("❌ 请提供视频ID\u200E")
            return
        
        try:
            # 获取视频信息
            video = await self.client.get_video(video_id)
            
            if not video:
                yield event.plain_result(f"❌ 未找到视频: {video_id}\u200E")
                return
            
            # 获取并处理缩略图
            thumb_path = await self._get_thumbnail_with_blur(video.thumbnail, video_id)
            
            # 格式化信息
            info_text = self._format_video_info(video)
            
            # 发送结果
            if thumb_path and os.path.exists(thumb_path):
                yield event.chain_result([
                    Image.fromFileSystem(thumb_path),
                    Plain(f"\n{info_text}")
                ])
            else:
                yield event.plain_result(info_text)
                
        except Exception as e:
            logger.error(f"[Hanime] 获取视频信息失败: {e}")
            yield event.plain_result(f"❌ 获取视频信息失败: {str(e)}\u200E")
    
    @filter.command("hs")
    async def cmd_search(self, event: AstrMessageEvent, args: str = ""):
        """
        搜索视频
        用法: /hs <关键词> [页码]
        """
        if not args:
            yield event.plain_result("❌ 请提供搜索关键词\u200E")
            return
        
        # 解析参数
        page = 1
        query = ""
        
        # 逻辑：只有当参数超过1个，且最后一个参数是纯数字时，才把最后一个当页码
        if len(args) > 1 and args[-1].isdigit():
            page = int(args[-1])
            # 关键词是除了最后一个之外的所有内容
            query = " ".join(args[:-1])
        else:
            # 其他情况（只有一个参数，或者最后一个不是数字），全部当作关键词
            query = " ".join(args)
        
        if not query:
            yield event.plain_result("❌ 请提供搜索关键词\u200E")
            return
        
        try:
            # 清理之前的缓存
            self._clean_previous_cache()
            
            # 搜索
            results = await self.client.search(query=query, page=page, limit=self.max_search_results)
            
            if not results:
                yield event.plain_result(f"📭 未找到 \"{query}\" 的搜索结果\u200E")
                return
            
            # 格式化结果
            lines = [
                f"🔍 搜索: {query}",
                f"📄 第 {page} 页",
                ""
            ]
            
            for i, item in enumerate(results[:self.max_search_results], 1):
                title = item.title or f"视频 {item.video_id}"
                lines.append(f"{i}. 【{item.video_id}】{title}")
            
            lines.extend(["", "💡 使用 /hv <ID> 查看详情"])
            
            output = "\u200E\n".join(lines) + "\u200E"
            yield event.plain_result(output)
            
        except Exception as e:
            logger.error(f"[Hanime] 搜索失败: {e}")
            yield event.plain_result(f"❌ 搜索失败: {str(e)}\u200E")
    
    @filter.command("htag")
    async def cmd_by_tag(self, event: AstrMessageEvent, tag: str = "", page: str = "1"):
        """
        按标签查询
        用法: /htag <标签1>, <标签2> [页码]
        """
        if not tag:
            # 显示可用标签
            tags_text = "📂 可用标签:\n" + "\n".join(f"  • {cat}" for cat in TAGS[:15])
            if len(TAGS) > 15:
                tags_text += f"\n  ..."
            yield event.plain_result(tags_text + "\u200E")
            return
        
        try:
            page_num = int(page) if page.isdigit() else 1
        except ValueError:
            page_num = 1
        
        raw_tag_input = tag.replace("，", ",")
        tag_list = [t.strip() for t in raw_tag_input.split(",") if t.strip()]
        try:
            # 清理之前的缓存
            self._clean_previous_cache()
            
            # 按标签查询
            results = await self.client.get_by_tags(tag_list, page=page_num, limit=self.max_search_results)
            
            if not results:
                yield event.plain_result(f"📭 未找到标签 \"{tag}\" 的视频\u200E")
                return
            
            # 格式化结果
            lines = [
                f"🏷️ 标签: {tag}",
                f"📄 第 {page_num} 页",
                ""
            ]
            
            for i, item in enumerate(results[:self.max_search_results], 1):
                title = item.title or f"视频 {item.video_id}"
                lines.append(f"{i}. 【{item.video_id}】{title}")
            
            lines.extend(["", "💡 使用 /hv <ID> 查看详情"])
            
            output = "\u200E\n".join(lines) + "\u200E"
            yield event.plain_result(output)
            
        except Exception as e:
            logger.error(f"[Hanime] 标签查询失败: {e}")
            yield event.plain_result(f"❌ 标签查询失败: {str(e)}\u200E")

    @filter.command("hgenre")
    async def cmd_by_hgenre(self, event: AstrMessageEvent, genre: str = "", page: str = "1"):
        """
        按分类查询
        用法: /hgenre <分类名> [页码]
        """
        if not genre:
            # 显示可用分类
            tags_text = "📂 可用分类 (Genre):\n" + "\n".join(f"  • {cat}" for cat in CATEGORIES[:15])
            if len(CATEGORIES) > 15:
                tags_text += f"\n  ... 还有 {len(CATEGORIES) - 15} 个分类"
            yield event.plain_result(tags_text + "\n\n用法: /hgenre <分类名>\u200E")
            return
        
        try:
            page_num = int(page) if page.isdigit() else 1
        except ValueError:
            page_num = 1
        
        try:
            # 清理之前的缓存
            self._clean_previous_cache()
            
            # 按标签查询
            results = await self.client.get_by_genre(genre, page=page_num, limit=self.max_search_results)
            
            if not results:
                yield event.plain_result(f"📭 未找到分类 \"{genre}\" 的视频\u200E")
                return
            
            lines = [
                f"📂 分类搜索: {genre}",
                f"📄 第 {page} 页",
                ""
            ]
            
            for i, item in enumerate(results[:self.max_search_results], 1):
                title = item.title or f"视频 {item.video_id}"
                lines.append(f"{i}. 【{item.video_id}】{title}")
            
            lines.extend(["", "💡 使用 /hv <ID> 查看详情"])
            yield event.plain_result("\u200E\n".join(lines) + "\u200E")
            
        except Exception as e:
            logger.error(f"[Hanime] 分类查询失败: {e}")
            yield event.plain_result(f"❌ 分类查询失败: {str(e)}\u200E")

    @filter.command("hlatest")
    async def cmd_latest(self, event: AstrMessageEvent):
        """
        获取最新视频
        用法: /hlatest
        """
        try:
            # 清理之前的缓存
            self._clean_previous_cache()
            
            # 获取最新
            results = await self.client.get_latest(limit=self.max_search_results)
            
            if not results:
                yield event.plain_result("📭 未获取到最新视频\u200E")
                return
            
            # 格式化结果
            lines = [
                "🆕 最新视频",
                ""
            ]
            
            for i, item in enumerate(results[:self.max_search_results], 1):
                title = item.title or f"视频 {item.video_id}"
                lines.append(f"{i}. 【{item.video_id}】{title}")
            
            lines.extend(["", "💡 使用 /hv <ID> 查看详情"])
            
            output = "\u200E\n".join(lines) + "\u200E"
            yield event.plain_result(output)
            
        except Exception as e:
            logger.error(f"[Hanime] 获取最新视频失败: {e}")
            yield event.plain_result(f"❌ 获取最新视频失败: {str(e)}\u200E")
    
    @filter.command("hrandom")
    async def cmd_random(self, event: AstrMessageEvent):
        """
        获取随机视频
        用法: /hrandom
        """
        try:
            # 清理之前的缓存
            self._clean_previous_cache()
            
            # 获取随机视频
            video = await self.client.get_random()
            
            if not video:
                yield event.plain_result("❌ 获取随机视频失败\u200E")
                return
            
            # 获取并处理缩略图
            thumb_path = await self._get_thumbnail_with_blur(video.thumbnail, video.video_id)
            
            # 格式化信息
            info_text = "🎲 随机视频\n\n" + self._format_video_info(video)
            
            # 发送结果
            if thumb_path and os.path.exists(thumb_path):
                yield event.chain_result([
                    Image.fromFileSystem(thumb_path),
                    Plain(f"\n{info_text}")
                ])
            else:
                yield event.plain_result(info_text)
                
        except Exception as e:
            logger.error(f"[Hanime] 获取随机视频失败: {e}")
            yield event.plain_result(f"❌ 获取随机视频失败: {str(e)}\u200E")
    
    @filter.command("htags")
    async def cmd_video_tags(self, event: AstrMessageEvent, video_id: str = ""):
        """
        获取视频标签
        用法: /htags <视频ID>
        """
        if not video_id:
            yield event.plain_result("❌ 请提供视频ID\u200E")
            return
        
        try:
            # 获取视频信息
            video = await self.client.get_video(video_id)
            
            if not video:
                yield event.plain_result(f"❌ 未找到视频: {video_id}\u200E")
                return
            
            tags = video.tags
            
            if not tags:
                yield event.plain_result(f"📭 视频 【{video_id}】 没有标签\u200E")
                return
            
            lines = [
                f"🏷️ 视频 【{video_id}】 的标签",
                "",
                "  " + " | ".join(tags)
            ]
            
            output = "\u200E\n".join(lines) + "\u200E"
            yield event.plain_result(output)
            
        except Exception as e:
            logger.error(f"[Hanime] 获取视频标签失败: {e}")
            yield event.plain_result(f"❌ 获取视频标签失败: {str(e)}\u200E")
    
    @filter.command("hcategories")
    async def cmd_categories(self, event: AstrMessageEvent):
        """
        显示所有分类
        用法: /hcategories
        """
        lines = [
            "📂 所有分类",
            ""
        ]
        
        # 每行显示3个分类
        row = []
        for cat in CATEGORIES:
            row.append(cat)
            if len(row) >= 3:
                lines.append("  " + " | ".join(row))
                row = []
        
        if row:
            lines.append("  " + " | ".join(row))
        
        lines.extend(["", "💡 使用 /htag <标签名> 查询指定标签的视频"])
        
        output = "\u200E\n".join(lines) + "\u200E"
        yield event.plain_result(output)
