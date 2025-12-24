# MangaPDF 漫画拼接工具

## 📖 项目简介

**MangaPDF** 是一款专为漫画爱好者设计的轻量级 PDF 拼接工具。它可以帮助你轻松将散乱的漫画图片（JPG/PNG/WEBP）按照自定义顺序合并成高质量的 PDF 文件。

本项目采用 Python + PyQt6 开发，界面现代简洁，支持浅色/深色主题切换，并针对漫画阅读体验进行了优化（如自动尾页添加）。
<p align="center">
  <img src="https://github.com/XingChengZero/MangaPDF/blob/main/img/1.png?raw=true" alt="MangaPDF Preview" width="800">
</p>

## ✨ 主要功能

*   **多序列管理**：支持同时创建和管理最多 5 个独立的图片序列，方便批量处理不同章节。
*   **拖拽支持**：支持直接拖拽图片文件到应用中添加。
*   **现代 UI 设计**：
    *   **双主题支持**：内置精心调优的「浅色模式」和「深色模式」，随心切换。
    *   **响应式布局**：界面元素自适应调整，操作流畅。
*   **智能处理**：
    *   **图片缩略图**：直观预览已添加的图片。
    *   **自动排序**：支持手动调整图片顺序。
    *   **尾页设置**：一键添加自定义尾页（如汉化组声明等）。
*   **高性能打包**：内置多线程打包逻辑，快速生成 PDF。

## 🛠️ 环境要求

*   Python 3.9+
*   依赖库：
    *   `PyQt6`
    *   `Pillow`
    *   `img2pdf`

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行源码

```bash
python main.py
```

## 📦 打包流程

本项目内置了自动化打包脚本，使用 `PyInstaller` 将程序打包为独立的 `.exe` 可执行文件。

### 打包步骤：

1.  **确保已安装打包依赖**：
    ```bash
    pip install pyinstaller
    ```

2.  **运行打包脚本**：
    在项目根目录下运行：
    ```bash
    python build.py
    ```

3.  **获取程序**：
    打完成后，可执行文件将生成在 `dist/` 目录下：
    *   `dist/MangaPDF.exe`

### 自定义打包参数：

如果你需要修改打包配置（如修改图标、添加隐藏导入等），请编辑 `build.py` 或 `MangaPDF.spec` 文件。

---

## 📂 项目结构

```
manga_pdf_tool/
├── core/               # 核心逻辑 (PDF生成、序列管理)
├── ui/                 # 界面组件 (主窗口、拖拽区、图片卡片)
├── resources/          # 资源文件 (样式表、图标)
├── utils/              # 工具函数
├── main.py             # 程序入口
├── build.py            # 自动化打包脚本
├── requirements.txt    # 项目依赖
└── README.md           # 项目文档
```

## 📝 许可证

MIT License


