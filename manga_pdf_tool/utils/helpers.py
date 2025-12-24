"""
工具函数模块
"""

import re
import os
from typing import List


def natural_sort_key(s: str):
    """自然排序键函数，使 '2' 排在 '10' 前面"""
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]


def get_supported_extensions() -> List[str]:
    """获取支持的图片格式"""
    return ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']


def is_image_file(filepath: str) -> bool:
    """检查文件是否为支持的图片格式"""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in get_supported_extensions()


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    illegal_chars = r'[<>:"/\\|?*]'
    return re.sub(illegal_chars, '_', filename)
