"""
PDF生成模块
"""

import io
import os
from typing import List, Callable, Optional
from PIL import Image
import img2pdf

from core.image_processor import ImageProcessor


class PDFGenerator:
    """PDF生成器"""
    
    # 页面尺寸常量 (mm)
    PAGE_SIZES = {
        'original': None,  # 保持原图尺寸
        'a4': (210, 297),
        'letter': (215.9, 279.4),
    }
    
    def __init__(self):
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调函数 (current, total, message)"""
        self.progress_callback = callback
    
    def _report_progress(self, current: int, total: int, message: str):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def generate_pdf(
        self,
        image_paths: List[str],
        output_path: str,
        page_size: str = 'original',
        quality: int = 90,
        margin_mm: float = 0
    ) -> bool:
        """
        生成PDF文件
        
        Args:
            image_paths: 图片文件路径列表
            output_path: 输出PDF路径
            page_size: 页面尺寸模式 ('original', 'a4', 'letter')
            quality: 压缩质量 (1-100)
            margin_mm: 边距 (毫米)
        
        Returns:
            bool: 是否成功
        """
        if not image_paths:
            return False
        
        try:
            total = len(image_paths)
            processed_images = []
            
            for i, img_path in enumerate(image_paths):
                self._report_progress(i + 1, total, f"处理第 {i + 1}/{total} 页...")
                
                # 压缩图片
                img_data = ImageProcessor.compress_image(img_path, quality)
                if img_data:
                    processed_images.append(img_data)
            
            if not processed_images:
                return False
            
            self._report_progress(total, total, "正在生成 PDF...")
            
            # 配置PDF选项
            if page_size == 'original':
                # 保持原图尺寸
                layout_fun = img2pdf.get_layout_fun(None)
            else:
                # 使用固定页面尺寸
                page_dim = self.PAGE_SIZES.get(page_size, (210, 297))
                # 转换为点 (1mm = 2.834645669 points)
                page_width_pt = page_dim[0] * 2.834645669
                page_height_pt = page_dim[1] * 2.834645669
                margin_pt = margin_mm * 2.834645669
                
                layout_fun = img2pdf.get_layout_fun(
                    pagesize=(
                        img2pdf.mm_to_pt(page_dim[0]),
                        img2pdf.mm_to_pt(page_dim[1])
                    ),
                    fit=img2pdf.FitMode.into,
                    border=(
                        img2pdf.mm_to_pt(margin_mm),
                        img2pdf.mm_to_pt(margin_mm),
                        img2pdf.mm_to_pt(margin_mm),
                        img2pdf.mm_to_pt(margin_mm)
                    )
                )
            
            # 生成PDF
            pdf_bytes = img2pdf.convert(processed_images, layout_fun=layout_fun)
            
            # 保存文件
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            
            self._report_progress(total, total, "完成！")
            return True
            
        except Exception as e:
            print(f"生成PDF失败: {e}")
            self._report_progress(0, 0, f"生成失败: {e}")
            return False
