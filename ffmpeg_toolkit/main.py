"""
FFmpeg 工具箱 - 主程式進入點

此模組提供應用程式的主要進入點，啟動 Gradio 網頁介面。
"""

import os
import shutil
import sys
import threading
import time

from .ui.gradio_app import GradioApp


def main():
    """主程式進入點"""
    # 設定 Windows 終端機編碼為 UTF-8
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            # Python < 3.7 的後備方案
            import io

            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    # 檢查 FFmpeg 是否可用
    if not shutil.which("ffmpeg"):
        print("❌ 錯誤：找不到 FFmpeg")
        print("請確保 FFmpeg 已安裝並在系統 PATH 中")
        print("\n安裝指南：")
        print("  Windows: 從 https://ffmpeg.org/download.html 下載並加入 PATH")
        print("  macOS:   brew install ffmpeg")
        print("  Linux:   sudo apt install ffmpeg (Ubuntu/Debian)")
        sys.exit(1)

    print("🎬 正在啟動 FFmpeg 工具箱...")

    # 建立並啟動 Gradio 應用程式
    app = GradioApp()
    interface = app.create_ui()

    # 添加自定義 API 路由來處理瀏覽器關閉事件
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import Response

        # 獲取 Gradio 的 FastAPI app
        fastapi_app: FastAPI = interface.app

        @fastapi_app.post("/api/shutdown")
        async def shutdown_endpoint(request: Request):
            """
            處理瀏覽器關閉時的關閉請求

            支持多種請求方式：
            - navigator.sendBeacon() (text/plain 或 application/json)
            - fetch() with keepalive (application/json)
            """
            # 嘗試解析請求體
            try:
                body = await request.body()
                if body:
                    try:
                        import json

                        data = json.loads(body)
                        source = data.get("source", "unknown")
                    except json.JSONDecodeError:
                        # sendBeacon 可能發送純文本
                        source = "beacon"
                else:
                    source = "unknown"
            except Exception:
                source = "unknown"

            def delayed_shutdown():
                print(f"\n🔔 偵測到瀏覽器關閉 (來源: {source})")
                print("   程式將在 2 秒後自動退出...")
                time.sleep(2)
                print("⏹️ 程式已關閉")
                os._exit(0)

            threading.Thread(target=delayed_shutdown, daemon=True).start()

            # 返回簡單的 200 響應（sendBeacon 不需要 JSON）
            return Response(status_code=200, content="OK")

        print("✅ 自動關閉功能已啟用")
        print("   支援方法: visibilitychange + beforeunload + pagehide")
        print("   傳輸方式: sendBeacon (優先) + fetch keepalive (後備)")

    except Exception as e:
        print(f"⚠️ 警告：無法啟用自動關閉功能: {e}")
        print("   您仍可使用介面上的「關閉程式」按鈕")

    print("✅ 應用程式已啟動!")
    print("🌐 正在開啟瀏覽器...")
    print("💡 提示：關閉瀏覽器視窗後，程式將自動退出")

    # 取得自訂設定 (Gradio 6.0 要求傳遞給 launch)
    custom_theme = getattr(interface, "_custom_theme", None)
    custom_css = getattr(interface, "_custom_css", None)
    custom_js = getattr(interface, "_custom_js", None)

    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,  # 自動開啟瀏覽器
        quiet=False,
        theme=custom_theme,
        css=custom_css,
        js=custom_js,
    )


if __name__ == "__main__":
    main()
