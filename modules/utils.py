"""
Hanime1.me 工具函数
"""
import re
import os
import aiohttp
import aiofiles
from typing import Optional
from PIL import Image, ImageFilter
import io


def parse_views(views_str: str) -> int:
    """
    解析观看次数字符串，支持万/萬单位
    
    支持格式:
    - "9.7万次" -> 97000
    - "9.7萬次" -> 97000
    - "97000次" -> 97000
    - "9,700次" -> 9700
    - "9.7万" -> 97000
    """
    if not views_str:
        return 0
    
    # 清理字符串
    views_str = views_str.strip()
    
    # 检查是否包含万/萬
    has_wan = '万' in views_str or '萬' in views_str
    
    # 提取数字部分
    if not (match := re.search(r'([\d,.]+)', views_str)):
        return 0
    
    num_str = match[1].replace(',', '')
    
    try:
        num = float(num_str)
        if has_wan:
            num *= 10000
        return int(num)
    except (ValueError, TypeError):
        return 0


def format_views(views: int) -> str:
    """
    格式化观看次数为易读格式
    
    Args:
        views: 观看次数
        
    Returns:
        格式化后的字符串
    """
    if views >= 10000:
        return f"{views / 10000:.1f}万"
    elif views >= 1000:
        return f"{views / 1000:.1f}k"
    else:
        return str(views)


def format_duration(seconds: int) -> str:
    """
    格式化时长（秒）为 MM:SS 或 HH:MM:SS 格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时长字符串
    """
    if seconds <= 0:
        return "00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def parse_duration(duration_str: str) -> int:
    """
    解析时长字符串为秒数
    
    支持格式:
    - "02:59" -> 179
    - "1:02:59" -> 3779
    - "02:59:00" -> 10740
    
    Args:
        duration_str: 时长字符串
        
    Returns:
        秒数
    """
    if not duration_str:
        return 0
    
    parts = duration_str.strip().split(':')
    
    try:
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0
    except (ValueError, TypeError):
        return 0


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除或替换非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    filename = re.sub(illegal_chars, '_', filename)
    
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()


async def download_image(
    url: str, 
    session: Optional[aiohttp.ClientSession] = None,
    proxy: Optional[str] = None,
    timeout: int = 30
) -> Optional[bytes]:
    """
    下载图片
    
    Args:
        url: 图片URL
        session: aiohttp会话（可选）
        proxy: 代理地址（可选）
        timeout: 超时时间（秒）
        
    Returns:
        图片二进制数据，失败返回None
    """
    if not url:
        return None
    
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
    
    try:
        async with session.get(
            url,
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            return await response.read() if response.status == 200 else None
    except Exception:
        return None
    finally:
        if close_session:
            await session.close()


async def blur_image(
    image_data: bytes, 
    blur_radius: int = 20
) -> bytes:
    """
    对图片进行高斯模糊处理
    
    Args:
        image_data: 原始图片二进制数据
        blur_radius: 模糊半径，值越大越模糊
        
    Returns:
        模糊处理后的图片二进制数据
    """
    if blur_radius <= 0:
        return image_data
    
    try:
        # 读取图片
        img = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB（处理RGBA等格式）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 应用高斯模糊
        blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # 转换回bytes
        output = io.BytesIO()
        blurred.save(output, format='JPEG', quality=85)
        return output.getvalue()
    except Exception:
        return image_data


async def save_image(
    image_data: bytes, 
    filepath: str
) -> bool:
    """
    保存图片到文件
    
    Args:
        image_data: 图片二进制数据
        filepath: 保存路径
        
    Returns:
        是否保存成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(image_data)
        return True
    except Exception:
        return False


def clean_html(html: str) -> str:
    """
    清理HTML标签
    
    Args:
        html: 原始HTML字符串
        
    Returns:
        清理后的纯文本
    """
    if not html:
        return ""
    
    # 移除script和style标签及内容
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    # 移除HTML标签
    html = re.sub(r'<[^>]+>', '', html)
    
    # 解码HTML实体
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&amp;', '&')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    
    # 清理多余空白
    html = re.sub(r'\s+', ' ', html)
    
    return html.strip()


def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    从URL或ID字符串中提取视频ID
    
    Args:
        url_or_id: URL或视频ID
        
    Returns:
        视频ID，无效则返回None
    """
    if not url_or_id:
        return None
    
    url_or_id = url_or_id.strip()
    
    # 如果是纯数字，直接返回
    if url_or_id.isdigit():
        return url_or_id
    
    # 尝试从URL中提取
    if match := re.search(r'watch\?v=(\d+)', url_or_id):
        return match[1]
    
    # 尝试其他格式
    if match := re.search(r'/video/(\d+)', url_or_id):
        return match[1]
    
    # 尝试提取任意数字序列（至少4位）
    if match := re.search(r'(\d{4,})', url_or_id):
        return match[1]
    
    return None


def build_search_url(
    query: str = "",
    genre: str = "",
    sort: str = "latest",
    page: int = 1
) -> str:
    """
    构建搜索URL
    
    Args:
        query: 搜索关键词
        genre: 分类/类型
        sort: 排序方式
        page: 页码
        
    Returns:
        搜索URL
    """
    from .consts import BASE_URL
    
    params = []
    
    if query:
        params.append(f"query={query}")
    if genre:
        params.append(f"genre={genre}")
    if sort and sort != "latest":
        params.append(f"sort={sort}")
    if page > 1:
        params.append(f"page={page}")
    
    return f"{BASE_URL}/search?{'&'.join(params)}" if params else BASE_URL