"""
打包脚本 - 使用 PyInstaller 生成 EXE
"""

import os
import subprocess
import sys


def build():
    """打包应用程序"""
    
    # 获取当前目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, "main.py")
    resources_dir = os.path.join(base_dir, "resources")
    
    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MangaPDF",
        "--onefile",                    # 单文件模式
        "--windowed",                   # 无控制台窗口
        "--noconfirm",                  # 覆盖输出目录
        f"--add-data={resources_dir};resources",  # 添加资源文件
        "--hidden-import=PIL._tkinter_finder",
        main_py
    ]
    
    # 如果有图标文件
    icon_path = os.path.join(resources_dir, "icon.ico")
    if os.path.exists(icon_path):
        cmd.insert(-1, f"--icon={icon_path}")
    
    print("=" * 50)
    print("开始打包 MangaPDF...")
    print("=" * 50)
    print(f"命令: {' '.join(cmd)}")
    print()
    
    # 执行打包
    result = subprocess.run(cmd, cwd=base_dir)
    
    if result.returncode == 0:
        print()
        print("=" * 50)
        print("✅ 打包完成！")
        print(f"📁 输出目录: {os.path.join(base_dir, 'dist')}")
        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print("❌ 打包失败，请检查错误信息")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    build()
