"""
拖拽上传区域组件
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from utils.helpers import is_image_file


class DropArea(QFrame):
    """拖拽上传区域"""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        
        # 主提示文字
        self.main_label = QLabel("点击或拖拽图片到这里")
        self.main_label.setObjectName("dropMainLabel")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.main_label)
        
        # 副提示文字
        self.sub_label = QLabel("支持 JPG, PNG, WebP 格式，可批量上传")
        self.sub_label.setObjectName("dropSubLabel")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sub_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            has_images = any(is_image_file(url.toLocalFile()) for url in urls)
            if has_images:
                event.acceptProposedAction()
                self.setProperty("dragging", True)
                self.style().unpolish(self)
                self.style().polish(self)
    
    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        
        urls = event.mimeData().urls()
        files = []
        for url in urls:
            filepath = url.toLocalFile()
            if is_image_file(filepath):
                files.append(filepath)
        
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.files_dropped.emit([])
