"""
Hanime1.me API 解析模块
"""

from .consts import BASE_URL, VIDEO_URL_PREFIX, CATEGORIES
from .utils import (
    parse_views, format_views, parse_duration, format_duration,
    download_image, blur_image, save_image,
    clean_html, extract_video_id
)
from .video import Video, VideoPreview
from .client import HanimeClient

# 为兼容性提供别名
Client = HanimeClient

__all__ = [
    'Video', 'VideoPreview',
    'Client', 'HanimeClient',
    'BASE_URL', 'VIDEO_URL_PREFIX', 'CATEGORIES',
    'parse_views', 'format_views', 'parse_duration', 'format_duration',
    'download_image', 'blur_image', 'save_image', 'clean_html', 'extract_video_id'
]