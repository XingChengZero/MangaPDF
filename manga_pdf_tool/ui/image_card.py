"""
图片卡片组件 - 最终修复版
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData, QPoint
from PyQt6.QtGui import QPixmap, QDrag, QMouseEvent, QPainter, QColor, QPen, QBrush

import os


class ImageCard(QFrame):
    """图片预览卡片"""
    
    delete_requested = pyqtSignal(str)
    drag_started = pyqtSignal(str)
    
    CARD_WIDTH = 160
    
    def __init__(self, image_id: str, filepath: str, thumbnail_data: bytes, 
                 width: int, height: int, parent=None):
        super().__init__(parent)
        self.image_id = image_id
        self.filepath = filepath
        self.img_width = width
        self.img_height = height
        self._drag_start_pos = None
        
        self.setAcceptDrops(True)
        self.setFixedWidth(self.CARD_WIDTH)
        # 允许卡片伸缩，但有最小高度
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setObjectName("imageCard")
        
        self._setup_ui(thumbnail_data)
    
    def _setup_ui(self, thumbnail_data: bytes):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 图片容器
        # 由于缩略图已经裁剪并限制了大小，我们可以直接使用缩略图的高度
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background: #1a1a1a; border-radius: 6px 6px 0 0;")
        
        if thumbnail_data:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail_data)
            # 确保宽度填满
            scaled = pixmap.scaledToWidth(self.CARD_WIDTH, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(scaled)
        else:
            self.img_label.setText("?")
            self.img_label.setStyleSheet("background: #1a1a1a; color: #666; font-size: 24px;")
            self.img_label.setFixedSize(self.CARD_WIDTH, 200)
            
        layout.addWidget(self.img_label)
        
        # 悬浮层容器 (用于定位尺寸标签和删除按钮)
        # 注意：Qt布局中叠加控件比较麻烦，这里使用父子关系定位
        
        # 尺寸标签 (左上角)
        self.size_label = QLabel(f"{self.img_width}x{self.img_height}")
        self.size_label.setStyleSheet("""
            background: rgba(0, 0, 0, 0.7);
            color: white;
            font-size: 9px;
            padding: 2px 4px;
            border-radius: 3px;
        """)
        self.size_label.setParent(self.img_label)
        self.size_label.move(5, 5)
        self.size_label.show()
        
        # 删除按钮 (右上角)
        self.delete_btn = DeleteButton(self.img_label)
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.move(self.CARD_WIDTH - 28, 5)
        self.delete_btn.hide() # 初始隐藏
        
        # 长条漫提示 (如果被裁剪)
        if self.img_height > self.img_width * 2:
            hint = QLabel("LONG")
            hint.setStyleSheet("""
                background: rgba(0, 80, 200, 0.8);
                color: white;
                font-size: 8px;
                font-weight: bold;
                padding: 1px 3px;
                border-radius: 2px;
            """)
            hint.setParent(self.img_label)
            hint.move(5, self.img_label.height() - 20)
            hint.show()

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #333;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 文件名显示区
        name_container = QFrame()
        name_container.setStyleSheet("""
            background: #252525;
            border-radius: 0 0 6px 6px;
        """)
        name_container.setFixedHeight(36)
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(6, 0, 6, 0)
        name_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        filename = os.path.basename(self.filepath)
        # 获取文件名后4位作为扩展名，保留主要部分
        name_display = filename
        if len(filename) > 15:
             name_display = filename[:8] + "..." + filename[-4:]
             
        name_label = QLabel(name_display)
        name_label.setStyleSheet("""
            color: #cccccc;
            font-size: 11px;
            background: transparent;
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_layout.addWidget(name_label)
        
        layout.addWidget(name_container)
    
    def enterEvent(self, event):
        self.delete_btn.show()
        self.img_label.setStyleSheet("background: #1a1a1a; border-radius: 6px 6px 0 0; border: 1px solid #666;")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.delete_btn.hide()
        self.img_label.setStyleSheet("background: #1a1a1a; border-radius: 6px 6px 0 0; border: none;")
        super().leaveEvent(event)
    
    def _on_delete(self):
        self.delete_requested.emit(self.image_id)
    
    # 拖拽支持
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._drag_start_pos:
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.image_id)
        drag.setMimeData(mime_data)
        
        pixmap = self.img_label.pixmap()
        if pixmap:
            scaled_pixmap = pixmap.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
            drag.setPixmap(scaled_pixmap)
            drag.setHotSpot(QPoint(50, 50))
        
        self.drag_started.emit(self.image_id)
        drag.exec(Qt.DropAction.MoveAction)
        
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start_pos = None
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class DeleteButton(QPushButton):
    """绘制的删除按钮"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 透明背景，靠绘制
        self.setStyleSheet("background: transparent; border: none;")
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景圆
        if self.underMouse():
            painter.setBrush(QBrush(QColor(232, 17, 35))) # 红色
        else:
            painter.setBrush(QBrush(QColor(0, 0, 0, 150))) # 半透明黑
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 24, 24)
        
        # 绘制X
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        
        m = 7 # 边距
        painter.drawLine(m, m, 24-m, 24-m)
        painter.drawLine(24-m, m, m, 24-m)
