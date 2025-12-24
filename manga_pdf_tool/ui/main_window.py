"""
主窗口 - 支持拖拽排序修复版
"""

import os
import uuid
import shutil
import tempfile
import subprocess
import sys
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QSpinBox, QSlider, QLineEdit,
    QScrollArea, QFrame, QFileDialog, QProgressBar, QMessageBox,
    QSizePolicy, QGridLayout, QSpacerItem, QMenu, QButtonGroup,
    QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer, QMimeData
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent

from ui.drop_area import DropArea
from ui.image_card import ImageCard
from core.image_processor import ImageProcessor
from core.pdf_generator import PDFGenerator
from utils.helpers import is_image_file, natural_sort_key, sanitize_filename


class PDFWorker(QThread):
    """PDF生成工作线程"""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str, str)
    
    def __init__(self, generator: PDFGenerator, images: List[str], 
                 output_path: str, page_size: str, quality: int, margin: float):
        super().__init__()
        self.generator = generator
        self.images = images
        self.output_path = output_path
        self.page_size = page_size
        self.quality = quality
        self.margin = margin
    
    def run(self):
        self.generator.set_progress_callback(
            lambda c, t, m: self.progress.emit(c, t, m)
        )
        success = self.generator.generate_pdf(
            self.images, self.output_path,
            self.page_size, self.quality, self.margin
        )
        if success:
            self.finished.emit(True, f"已保存: {os.path.basename(self.output_path)}", self.output_path)
        else:
            self.finished.emit(False, "生成失败", "")


class DraggableGridWidget(QWidget):
    """支持拖拽排序的网格容器"""
    
    order_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(12)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.cards: List[ImageCard] = []
        self.drag_target_index = -1
    
    def add_card(self, card: ImageCard, row: int, col: int):
        self.layout.addWidget(card, row, col)
        self.cards.append(card)
    
    def clear(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
    
    def get_card_index(self, image_id: str) -> int:
        for i, card in enumerate(self.cards):
            if card.image_id == image_id:
                return i
        return -1
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasText():
            return
        
        source_id = event.mimeData().text()
        source_idx = self.get_card_index(source_id)
        
        if source_idx < 0:
            return
        
        # 找到目标位置
        drop_pos = event.position().toPoint()
        target_idx = self._get_drop_index(drop_pos)
        
        if target_idx < 0 or target_idx == source_idx:
            return
        
        # 移动卡片
        card = self.cards.pop(source_idx)
        self.cards.insert(target_idx if target_idx < source_idx else target_idx, card)
        
        event.acceptProposedAction()
        self.order_changed.emit()
    
    def _get_drop_index(self, pos) -> int:
        """根据鼠标位置计算放置索引"""
        for i, card in enumerate(self.cards):
            card_rect = card.geometry()
            if card_rect.contains(pos):
                # 判断是放在前面还是后面
                center_x = card_rect.center().x()
                if pos.x() < center_x:
                    return i
                else:
                    return i + 1
        
        # 如果没有命中任何卡片，放在最后
        return len(self.cards)
    
    def get_order(self) -> List[str]:
        """获取当前卡片顺序"""
        return [card.image_id for card in self.cards]


class MainWindow(QMainWindow):
    """主窗口"""
    
    MAX_SEQUENCES = 5
    
    def __init__(self):
        super().__init__()
        
        self.settings = QSettings("MangaPDF", "MangaHePDF")
        
        self.sequences: List[Dict[str, Any]] = [
            {'id': '1', 'name': '漫画合集1', 'images': []}
        ]
        self.current_sequence_id = '1'
        self.sequence_counter = 1
        self.is_processing = False
        self.pdf_generator = PDFGenerator()
        self.worker = None
        self.current_theme = self.settings.value("theme", "light")
        
        # 尾页设置
        self.tail_page_path = self.settings.value("tail_page_path", "")
        self.tail_page_enabled = self.settings.value("tail_page_enabled", False, type=bool)
        
        self._setup_window()
        self._setup_ui()
        self._apply_theme(self.current_theme)
        self._update_ui()
    
    def _setup_window(self):
        self.setWindowTitle("MangaPDF - 漫画拼接专用工具")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)
    
    def _get_current_sequence(self) -> Dict[str, Any]:
        for seq in self.sequences:
            if seq['id'] == self.current_sequence_id:
                return seq
        return self.sequences[0]
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setFixedWidth(300)
        left_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        left_panel = self._create_settings_panel()
        left_scroll.setWidget(left_panel)
        content_layout.addWidget(left_scroll)
        
        right_panel = self._create_work_area()
        content_layout.addWidget(right_panel, 1)
        
        main_layout.addWidget(content, 1)
    
    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(52)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)
        
        # 左侧：标题区域
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)
        
        title = QLabel("MangaPDF")
        title.setObjectName("appTitle")
        title_layout.addWidget(title)
        
        subtitle = QLabel("漫画拼接工具")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(subtitle)
        
        layout.addWidget(title_container)
        layout.addStretch()
        
        # 右侧：功能区域
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        # 1. 主题选择
        theme_group = QWidget()
        theme_layout = QHBoxLayout(theme_group)
        theme_layout.setContentsMargins(0, 0, 0, 0)
        theme_layout.setSpacing(6)
        
        theme_label = QLabel("主题:")
        theme_label.setObjectName("toolbarLabel")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("toolbarCombo")
        self.theme_combo.addItems(["浅色", "深色"])
        theme_map = {"light": 0, "dark": 1}
        self.theme_combo.setCurrentIndex(theme_map.get(self.current_theme, 0))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        right_layout.addWidget(theme_group)
        
        # 2. 尾页设置组
        tail_group = QWidget()
        tail_layout = QHBoxLayout(tail_group)
        tail_layout.setContentsMargins(0, 0, 0, 0)
        tail_layout.setSpacing(6)
        
        self.tail_checkbox = QCheckBox("尾页")
        self.tail_checkbox.setObjectName("toolbarCheckbox")
        self.tail_checkbox.setChecked(self.tail_page_enabled)
        self.tail_checkbox.toggled.connect(self._on_tail_enabled_changed)
        tail_layout.addWidget(self.tail_checkbox)
        
        self.tail_btn = QPushButton("选择")
        self.tail_btn.setObjectName("toolbarBtn")
        self.tail_btn.clicked.connect(self._select_tail_page)
        self._update_tail_btn_style()
        tail_layout.addWidget(self.tail_btn)
        
        right_layout.addWidget(tail_group)
        
        # 3. 清除缓存
        clear_cache_btn = QPushButton("清除缓存")
        clear_cache_btn.setObjectName("toolbarBtn")
        clear_cache_btn.clicked.connect(self._clear_cache)
        right_layout.addWidget(clear_cache_btn)
        
        # 4. 关于按钮
        about_btn = QPushButton("关于")
        about_btn.setObjectName("toolbarBtn")
        about_btn.clicked.connect(self._show_about)
        right_layout.addWidget(about_btn)
        
        layout.addWidget(right_container)
        
        return toolbar
    
    def _on_theme_changed(self, index: int):
        theme_map = {0: "light", 1: "dark", 2: "system"}
        theme = theme_map.get(index, "light")
        
        if theme == "system":
            theme = "light"
        
        self.current_theme = theme
        self.settings.setValue("theme", theme)
        self._apply_theme(theme)
    
    def _apply_theme(self, theme: str):
        self.centralWidget().setProperty("theme", theme)
        self._update_widget_theme(self.centralWidget(), theme)
    
    def _update_widget_theme(self, widget: QWidget, theme: str):
        widget.setProperty("theme", theme)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        
        for child in widget.findChildren(QWidget):
            child.setProperty("theme", theme)
            child.style().unpolish(child)
            child.style().polish(child)
    
    def _clear_cache(self):
        temp_dir = tempfile.gettempdir()
        cleared = 0
        
        for item in os.listdir(temp_dir):
            if item.startswith("_MEI"):
                try:
                    shutil.rmtree(os.path.join(temp_dir, item))
                    cleared += 1
                except:
                    pass
        
        if cleared > 0:
            QMessageBox.information(self, "清除缓存", f"已清除 {cleared} 个缓存目录")
        else:
            QMessageBox.information(self, "清除缓存", "没有找到需要清除的缓存")
    
    def _show_about(self):
        """显示关于对话框"""
        about_text = """
<h2 style="margin-bottom: 10px;">MangaPDF v2.0</h2>
<p style="color: #666; margin-bottom: 15px;">漫画拼接专用工具</p>

<h3 style="margin-bottom: 8px;">功能特性</h3>
<ul style="margin-left: 20px; line-height: 1.6;">
<li>拖拽上传图片，自动排序</li>
<li>多序列管理（最多5个）</li>
<li>拖拽调整图片顺序</li>
<li>长条漫智能预览</li>
<li>尾页批量添加</li>
<li>PDF 质量压缩控制</li>
<li>页面尺寸设置</li>
<li>深色/浅色主题切换</li>
</ul>

<h3 style="margin-top: 15px; margin-bottom: 8px;">使用说明</h3>
<ol style="margin-left: 20px; line-height: 1.6;">
<li>拖拽或点击上传区域添加图片</li>
<li>拖拽卡片调整顺序</li>
<li>设置输出参数（尺寸、质量等）</li>
<li>点击"合成当前序列"生成PDF</li>
</ol>

<p style="margin-top: 15px; color: #888; font-size: 12px;">
技术栈：Python + PyQt6 + img2pdf
</p>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("关于 MangaPDF")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
    def _on_tail_enabled_changed(self, enabled: bool):
        """尾页开关切换"""
        self.tail_page_enabled = enabled
        self.settings.setValue("tail_page_enabled", enabled)
        self._update_tail_btn_style()
    
    def _select_tail_page(self):
        """选择尾页图片"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择尾页图片",
            self.tail_page_path or "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if filepath:
            self.tail_page_path = filepath
            self.settings.setValue("tail_page_path", filepath)
            self._update_tail_btn_style()
            QMessageBox.information(self, "尾页设置", f"已设置尾页:\n{os.path.basename(filepath)}")
    
    def _update_tail_btn_style(self):
        """更新尾页按钮样式"""
        if self.tail_page_path and os.path.exists(self.tail_page_path):
            self.tail_btn.setText("已设置")
            self.tail_btn.setStyleSheet("color: #4CAF50;")
            self.tail_btn.setToolTip(f"尾页: {self.tail_page_path}")
        else:
            self.tail_btn.setText("选择尾页")
            self.tail_btn.setStyleSheet("")
            self.tail_btn.setToolTip("点击选择尾页图片")
    
    def _get_images_with_tail(self, images: List[str]) -> List[str]:
        """获取带尾页的图片列表"""
        if self.tail_page_enabled and self.tail_page_path and os.path.exists(self.tail_page_path):
            return images + [self.tail_page_path]
        return images
    
    def _create_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(270)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        self.counter_label = QLabel("0 页")
        self.counter_label.setObjectName("counter")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(self.counter_label)
        
        add_btn = QPushButton("添加图片")
        add_btn.clicked.connect(self._open_file_dialog)
        layout.addWidget(add_btn)
        
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep1)
        
        settings_title = QLabel("输出设置")
        settings_title.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        layout.addWidget(settings_title)
        
        size_label = QLabel("页面尺寸模式")
        size_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent;")
        layout.addWidget(size_label)
        
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems([
            "保持原图尺寸 (推荐)",
            "强制 A4 纸张",
            "强制 Letter 纸张"
        ])
        layout.addWidget(self.page_size_combo)
        
        margin_label = QLabel("边距 (毫米)")
        margin_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent;")
        layout.addWidget(margin_label)
        
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 50)
        self.margin_spin.setValue(0)
        layout.addWidget(self.margin_spin)
        
        quality_layout = QHBoxLayout()
        quality_label = QLabel("压缩质量")
        quality_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent;")
        quality_layout.addWidget(quality_label)
        self.quality_value_label = QLabel("90")
        self.quality_value_label.setStyleSheet("color: #555555; font-size: 12px; font-family: monospace; background: transparent;")
        quality_layout.addWidget(self.quality_value_label)
        layout.addLayout(quality_layout)
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_value_label.setText(str(v))
        )
        layout.addWidget(self.quality_slider)
        
        name_label = QLabel("输出文件名")
        name_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent;")
        layout.addWidget(name_label)
        
        self.filename_input = QLineEdit("漫画合集1")
        self.filename_input.textChanged.connect(self._on_filename_changed)
        layout.addWidget(self.filename_input)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep2)
        
        self.generate_btn = QPushButton("合成当前序列")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.clicked.connect(self._generate_current_pdf)
        self.generate_btn.setEnabled(False)
        layout.addWidget(self.generate_btn)
        
        self.generate_all_btn = QPushButton("生成全部 PDF (0 个)")
        self.generate_all_btn.setObjectName("generateAllBtn")
        self.generate_all_btn.clicked.connect(self._generate_all_pdfs)
        self.generate_all_btn.setEnabled(False)
        layout.addWidget(self.generate_all_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        return panel
    
    def _create_work_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        seq_panel = QFrame()
        seq_panel.setObjectName("panel")
        seq_layout = QVBoxLayout(seq_panel)
        seq_layout.setContentsMargins(12, 12, 12, 12)
        
        seq_header = QHBoxLayout()
        seq_title = QLabel("PDF 序列 (最多 5 个) - 右键删除 | 拖拽卡片可排序")
        seq_title.setStyleSheet("font-size: 12px; color: #888888; background: transparent;")
        seq_header.addWidget(seq_title)
        self.seq_counter_label = QLabel("1 个序列")
        self.seq_counter_label.setStyleSheet("font-size: 11px; color: #999999; background: transparent;")
        seq_header.addWidget(self.seq_counter_label)
        seq_header.addStretch()
        seq_layout.addLayout(seq_header)
        
        self.seq_tabs_layout = QHBoxLayout()
        self.seq_tabs_layout.setSpacing(8)
        seq_layout.addLayout(self.seq_tabs_layout)
        
        self.add_seq_btn = QPushButton("新建序列")
        self.add_seq_btn.setObjectName("addSequenceBtn")
        self.add_seq_btn.clicked.connect(self._add_sequence)
        self.add_seq_btn.setFixedWidth(80)
        seq_layout.addWidget(self.add_seq_btn)
        
        layout.addWidget(seq_panel)
        
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_area)
        
        preview_header = QHBoxLayout()
        preview_title = QLabel("预览与排序 (拖拽图片可调整顺序)")
        preview_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        
        clear_btn = QPushButton("清空全部")
        clear_btn.setObjectName("clearBtn")
        clear_btn.clicked.connect(self._clear_all)
        preview_header.addWidget(clear_btn)
        layout.addLayout(preview_header)
        
        # 使用支持拖拽的网格容器
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_widget = DraggableGridWidget()
        self.grid_widget.setObjectName("gridWidget")
        self.grid_widget.order_changed.connect(self._on_order_changed)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll, 1)
        
        self.empty_label = QLabel("暂无图片，请上传漫画文件")
        self.empty_label.setStyleSheet("color: #999999; font-size: 14px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(200)
        layout.addWidget(self.empty_label)
        
        self._render_sequence_tabs()
        
        return container
    
    def _on_order_changed(self):
        """卡片顺序改变后更新数据"""
        seq = self._get_current_sequence()
        new_order = self.grid_widget.get_order()
        
        # 根据新顺序重排图片数据
        old_images = {img['id']: img for img in seq['images']}
        seq['images'] = [old_images[img_id] for img_id in new_order if img_id in old_images]
        
        # 重新渲染
        self._render_image_grid()
    
    def _render_sequence_tabs(self):
        while self.seq_tabs_layout.count():
            item = self.seq_tabs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for seq in self.sequences:
            btn = QPushButton(f"{seq['name']} ({len(seq['images'])})")
            btn.setObjectName("sequenceTab")
            btn.setCheckable(True)
            btn.setChecked(seq['id'] == self.current_sequence_id)
            btn.setProperty("seq_id", seq['id'])
            btn.clicked.connect(lambda checked, sid=seq['id']: self._switch_sequence(sid))
            
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, sid=seq['id']: self._show_sequence_menu(b, sid)
            )
            
            self.seq_tabs_layout.addWidget(btn)
        
        self.seq_tabs_layout.addStretch()
        
        self.add_seq_btn.setEnabled(len(self.sequences) < self.MAX_SEQUENCES)
        self.seq_counter_label.setText(f"{len(self.sequences)} 个序列")
    
    def _show_sequence_menu(self, button: QPushButton, seq_id: str):
        if len(self.sequences) <= 1:
            QMessageBox.information(self, "提示", "至少保留一个序列")
            return
        
        menu = QMenu(self)
        delete_action = QAction("删除此序列", self)
        delete_action.triggered.connect(lambda: self._delete_sequence(seq_id))
        menu.addAction(delete_action)
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
    
    def _switch_sequence(self, seq_id: str):
        if self.current_sequence_id == seq_id:
            return
        
        self.current_sequence_id = seq_id
        seq = self._get_current_sequence()
        self.filename_input.setText(seq['name'])
        self._render_sequence_tabs()
        self._render_image_grid()
        self._update_ui()
    
    def _add_sequence(self):
        if len(self.sequences) >= self.MAX_SEQUENCES:
            QMessageBox.warning(self, "提示", f"最多只能创建 {self.MAX_SEQUENCES} 个序列")
            return
        
        self.sequence_counter += 1
        new_seq = {
            'id': str(uuid.uuid4()),
            'name': f'漫画合集{self.sequence_counter}',
            'images': []
        }
        self.sequences.append(new_seq)
        self.current_sequence_id = new_seq['id']
        self.filename_input.setText(new_seq['name'])
        self._render_sequence_tabs()
        self._render_image_grid()
        self._update_ui()
    
    def _delete_sequence(self, seq_id: str):
        if len(self.sequences) <= 1:
            return
        
        seq = next((s for s in self.sequences if s['id'] == seq_id), None)
        if not seq:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除序列「{seq['name']}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.sequences = [s for s in self.sequences if s['id'] != seq_id]
            if self.current_sequence_id == seq_id:
                self.current_sequence_id = self.sequences[0]['id']
                self.filename_input.setText(self.sequences[0]['name'])
            self._render_sequence_tabs()
            self._render_image_grid()
            self._update_ui()
    
    def _on_filename_changed(self, text: str):
        seq = self._get_current_sequence()
        seq['name'] = text or f"漫画合集{self.sequence_counter}"
        self._render_sequence_tabs()
    
    def _open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif)"
        )
        if files:
            self._add_images(files)
    
    def _on_files_dropped(self, files: List[str]):
        if not files:
            self._open_file_dialog()
        else:
            self._add_images(files)
    
    def _add_images(self, filepaths: List[str]):
        filepaths = sorted(filepaths, key=lambda x: natural_sort_key(os.path.basename(x)))
        
        seq = self._get_current_sequence()
        
        for filepath in filepaths:
            if not is_image_file(filepath):
                continue
            
            # 为长条漫生成更大的缩略图（宽度160，高度自动按比例并裁剪）
            thumbnail = ImageProcessor.create_thumbnail(filepath, 160)
            width, height = ImageProcessor.get_image_dimensions(filepath)
            
            img_data = {
                'id': str(uuid.uuid4()),
                'filepath': filepath,
                'thumbnail': thumbnail,
                'width': width,
                'height': height
            }
            seq['images'].append(img_data)
        
        self._render_sequence_tabs()
        self._render_image_grid()
        self._update_ui()
    
    def _render_image_grid(self):
        self.grid_widget.clear()
        
        seq = self._get_current_sequence()
        
        # 动态计算列数
        cols = max(1, (self.width() - 380) // 180)
        
        for i, img in enumerate(seq['images']):
            card = ImageCard(
                img['id'], img['filepath'], img['thumbnail'],
                img['width'], img['height']
            )
            card.delete_requested.connect(self._remove_image)
            
            row = i // cols
            col = i % cols
            self.grid_widget.add_card(card, row, col)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        else:
            self._resize_timer = QTimer()
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._render_image_grid)
        self._resize_timer.start(100)
    
    def _remove_image(self, image_id: str):
        seq = self._get_current_sequence()
        seq['images'] = [img for img in seq['images'] if img['id'] != image_id]
        self._render_sequence_tabs()
        self._render_image_grid()
        self._update_ui()
    
    def _clear_all(self):
        seq = self._get_current_sequence()
        if not seq['images']:
            return
        
        reply = QMessageBox.question(
            self, "确认清空",
            f"确定要清空「{seq['name']}」的所有图片吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            seq['images'] = []
            self._render_sequence_tabs()
            self._render_image_grid()
            self._update_ui()
    
    def _update_ui(self):
        seq = self._get_current_sequence()
        count = len(seq['images'])
        
        self.counter_label.setText(f"{count} 页")
        self.generate_btn.setEnabled(count > 0 and not self.is_processing)
        
        self.empty_label.setVisible(count == 0)
        self.grid_widget.setVisible(count > 0)
        
        non_empty = [s for s in self.sequences if len(s['images']) > 0]
        self.generate_all_btn.setText(f"生成全部 PDF ({len(non_empty)} 个)")
        self.generate_all_btn.setEnabled(len(non_empty) > 0 and not self.is_processing)
    
    def _get_page_size_value(self) -> str:
        index = self.page_size_combo.currentIndex()
        return ['original', 'a4', 'letter'][index]
    
    def _generate_current_pdf(self):
        seq = self._get_current_sequence()
        if not seq['images'] or self.is_processing:
            return
        
        default_name = sanitize_filename(seq['name']) + ".pdf"
        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF",
            default_name,
            "PDF 文件 (*.pdf)"
        )
        
        if not output_path:
            return
        
        self._start_generation(
            self._get_images_with_tail([img['filepath'] for img in seq['images']]),
            output_path
        )
    
    def _generate_all_pdfs(self):
        non_empty = [s for s in self.sequences if len(s['images']) > 0]
        if not non_empty or self.is_processing:
            return
        
        output_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not output_dir:
            return
        
        self.is_processing = True
        self._update_ui()
        self.progress_bar.setVisible(True)
        
        total = len(non_empty)
        for i, seq in enumerate(non_empty):
            self.status_label.setText(f"生成 {i + 1}/{total}: {seq['name']}")
            self.progress_bar.setValue(int((i / total) * 100))
            QApplication.processEvents()
            
            output_path = os.path.join(output_dir, sanitize_filename(seq['name']) + ".pdf")
            images = self._get_images_with_tail([img['filepath'] for img in seq['images']])
            
            success = self.pdf_generator.generate_pdf(
                images, output_path,
                self._get_page_size_value(),
                self.quality_slider.value(),
                self.margin_spin.value()
            )
            
            if not success:
                QMessageBox.warning(self, "错误", f"生成「{seq['name']}」失败")
        
        self.progress_bar.setValue(100)
        self.status_label.setText(f"已生成 {total} 个 PDF 文件！")
        self.is_processing = False
        self._update_ui()
        
        QTimer.singleShot(2000, self._hide_progress)
        self._ask_open_folder(output_dir)
    
    def _start_generation(self, images: List[str], output_path: str):
        self.is_processing = True
        self._update_ui()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = PDFWorker(
            self.pdf_generator,
            images,
            output_path,
            self._get_page_size_value(),
            self.quality_slider.value(),
            self.margin_spin.value()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, current: int, total: int, message: str):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.status_label.setText(message)
    
    def _on_finished(self, success: bool, message: str, output_path: str):
        self.is_processing = False
        self.status_label.setText(message)
        
        if success:
            self.progress_bar.setValue(100)
            QTimer.singleShot(2000, self._hide_progress)
            if output_path:
                output_dir = os.path.dirname(output_path)
                self._ask_open_folder(output_dir)
        
        self._update_ui()
    
    def _hide_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("")
    
    def _ask_open_folder(self, folder_path: str):
        reply = QMessageBox.question(
            self, "生成完成",
            "PDF 生成完成！是否打开所在文件夹？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
