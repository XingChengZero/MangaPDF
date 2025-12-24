"""
图片处理模块 - 智能裁剪版
"""

import io
from PIL import Image
from typing import Tuple, Optional


class ImageProcessor:
    """图片处理器"""
    
    @staticmethod
    def load_image(filepath: str) -> Optional[Image.Image]:
        """加载图片文件"""
        try:
            img = Image.open(filepath)
            if img.mode in ('RGBA', 'P', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            return img
        except Exception as e:
            print(f"加载图片失败: {filepath}, 错误: {e}")
            return None
    
    @staticmethod
    def get_image_dimensions(filepath: str) -> Tuple[int, int]:
        """获取图片尺寸"""
        try:
            with Image.open(filepath) as img:
                return img.size
        except:
            return (0, 0)
    
    @staticmethod
    def create_thumbnail(filepath: str, max_width: int = 300) -> Optional[bytes]:
        """
        创建缩略图
        - 宽度固定
        - 高度限制最大值（裁剪），避免长条漫过长
        - 保证内容清晰度（"放大"效果）
        """
        try:
            with Image.open(filepath) as img:
                orig_w, orig_h = img.size
                
                # 目标宽度
                target_w = max_width
                # 计算按宽度缩放后的高度
                scale = target_w / orig_w
                target_h = int(orig_h * scale)
                
                # 限制最大高度（例如宽度的2倍），超过则裁剪顶部
                # 这样长条漫会显示顶部内容，且宽度填满，看起来是"放大"的
                max_h = int(target_w * 1.6) 
                
                # 缩放
                if target_h > max_h:
                    # 如果太长，先按宽度缩放
                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    # 然后裁剪顶部区域
                    img = img.crop((0, 0, target_w, max_h))
                else:
                    # 正常缩放
                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                # 转换为RGB
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 保存
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=90, optimize=True)
                return buffer.getvalue()
        except Exception as e:
            print(f"创建缩略图失败: {filepath}, 错误: {e}")
            return None
    
    @staticmethod
    def compress_image(filepath: str, quality: int = 85) -> bytes:
        """压缩图片"""
        try:
            with Image.open(filepath) as img:
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                return buffer.getvalue()
        except Exception as e:
            print(f"压缩图片失败: {filepath}, 错误: {e}")
            return b''
