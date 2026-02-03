"""
FFmpeg 字幕工具箱 - 主程式進入點

此模組提供應用程式的主要進入點，啟動 Gradio 網頁介面。
"""

import shutil
import sys

from .ui.gradio_app import GradioApp


def main():
    """主程式進入點"""
    # 檢查 FFmpeg 是否可用
    if not shutil.which("ffmpeg"):
        print("❌ 錯誤：找不到 FFmpeg")
        print("請確保 FFmpeg 已安裝並在系統 PATH 中")
        print("\n安裝指南：")
        print("  Windows: 從 https://ffmpeg.org/download.html 下載並加入 PATH")
        print("  macOS:   brew install ffmpeg")
        print("  Linux:   sudo apt install ffmpeg (Ubuntu/Debian)")
        sys.exit(1)

    print("🎬 正在啟動 FFmpeg 字幕工具箱...")

    # 建立並啟動 Gradio 應用程式
    app = GradioApp()
    interface = app.create_ui()

    print("✅ 應用程式已啟動!")
    print("🌐 正在開啟瀏覽器...")

    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,  # 自動開啟瀏覽器
        quiet=False,
    )


if __name__ == "__main__":
    main()
