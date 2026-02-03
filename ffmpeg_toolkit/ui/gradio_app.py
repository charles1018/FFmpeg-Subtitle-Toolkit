"""
Gradio 網頁介面模組

提供基於 Gradio 的網頁 UI，用於字幕燒錄功能。
"""

import os
from pathlib import Path
from typing import Optional

import gradio as gr

from ..core.encoding import EncodingStrategy
from ..core.executor import FFmpegExecutor
from ..features.subtitle import SubtitleBurner, SubtitleConfig, SubtitleStyle


class GradioApp:
    """
    Gradio 網頁應用程式

    提供字幕燒錄的網頁介面，支援檔案上傳、樣式設定和即時日誌輸出。
    """

    def __init__(self):
        """初始化 Gradio 應用程式"""
        self.executor: Optional[FFmpegExecutor] = None
        self.encoding_strategy = EncodingStrategy()
        self.subtitle_burner: Optional[SubtitleBurner] = None
        self.log_buffer: list[str] = []
        self.processing = False
        self.should_exit = False

    @staticmethod
    def _get_common_fonts() -> list[str]:
        """
        取得常見字型列表

        Returns:
            list[str]: 常見字型名稱列表
        """
        # 跨平台常見字型列表
        common_fonts = [
            "Arial",
            "Arial Black",
            "Comic Sans MS",
            "Courier New",
            "Georgia",
            "Impact",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
            # 中文字型 (Windows)
            "Microsoft JhengHei",  # 微軟正黑體
            "Microsoft YaHei",  # 微軟雅黑體
            "SimSun",  # 宋體
            "SimHei",  # 黑體
            "KaiTi",  # 楷體
            "FangSong",  # 仿宋
            "PMingLiU",  # 新細明體
            "MingLiU",  # 細明體
            # 中文字型 (macOS)
            "PingFang TC",  # 蘋方-繁
            "PingFang SC",  # 蘋方-簡
            "Heiti TC",  # 黑體-繁
            "Songti TC",  # 宋體-繁
            "STHeiti",  # 華文黑體
            "STKaiti",  # 華文楷體
            "STSong",  # 華文宋體
            # 中文字型 (Linux)
            "Noto Sans CJK TC",  # 思源黑體-繁
            "Noto Sans CJK SC",  # 思源黑體-簡
            "Noto Serif CJK TC",  # 思源宋體-繁
            "WenQuanYi Zen Hei",  # 文泉驛正黑
            "WenQuanYi Micro Hei",  # 文泉驛微米黑
            # 其他常見字型
            "DejaVu Sans",
            "Liberation Sans",
            "Ubuntu",
        ]
        return sorted(common_fonts)

    def _shutdown_app(self) -> str:
        """
        關閉應用程式

        Returns:
            str: 關閉訊息
        """
        self.should_exit = True
        # 延遲退出,讓 Gradio 有時間返回響應
        import threading

        def delayed_exit():
            import time

            time.sleep(1)
            os._exit(0)

        threading.Thread(target=delayed_exit, daemon=True).start()
        return "⏹️ 程式正在關閉..."

    def create_ui(self) -> gr.Blocks:
        """
        建立 Gradio UI

        Returns:
            gr.Blocks: Gradio 介面物件
        """
        # JavaScript 代碼：監聽瀏覽器關閉事件（使用最佳實踐）
        browser_close_js = """
        function() {
            // 標記是否為手動關閉
            let isManualShutdown = false;
            let hasShutdownBeenSent = false;

            // 發送關閉信號的統一函數
            function sendShutdownSignal(source) {
                if (hasShutdownBeenSent || isManualShutdown) {
                    return;
                }
                hasShutdownBeenSent = true;

                // 優先使用 sendBeacon (最可靠的方法)
                const data = JSON.stringify({source: source});

                if (navigator.sendBeacon) {
                    try {
                        const success = navigator.sendBeacon('/api/shutdown', data);
                        if (success) {
                            console.log('關閉信號已發送 (sendBeacon)');
                            return;
                        }
                    } catch (e) {
                        console.log('sendBeacon 失敗，嘗試 fetch:', e);
                    }
                }

                // 後備方案：使用 fetch with keepalive
                try {
                    fetch('/api/shutdown', {
                        method: 'POST',
                        keepalive: true,
                        headers: {'Content-Type': 'application/json'},
                        body: data
                    }).then(() => {
                        console.log('關閉信號已發送 (fetch)');
                    }).catch((e) => {
                        console.log('fetch 失敗:', e);
                    });
                } catch (error) {
                    console.log('無法發送關閉信號:', error);
                }
            }

            // 主要方法：監聽頁面可見性變化（最可靠）
            document.addEventListener('visibilitychange', function() {
                if (document.visibilityState === 'hidden' && !isManualShutdown) {
                    sendShutdownSignal('visibility_hidden');
                }
            });

            // 後備方案 1：beforeunload 事件（桌面瀏覽器）
            window.addEventListener('beforeunload', function(e) {
                if (!isManualShutdown) {
                    sendShutdownSignal('beforeunload');
                }
            });

            // 後備方案 2：pagehide 事件（iOS Safari）
            window.addEventListener('pagehide', function(e) {
                if (!isManualShutdown) {
                    sendShutdownSignal('pagehide');
                }
            });

            // 監聽關閉按鈕點擊事件
            document.addEventListener('click', function(e) {
                const target = e.target;
                if (target && target.textContent && target.textContent.includes('關閉程式')) {
                    isManualShutdown = true;
                    hasShutdownBeenSent = false; // 允許按鈕觸發關閉
                }
            });

            console.log('✅ 自動關閉監聽已啟動 (visibilitychange + beforeunload + pagehide)');
        }
        """

        with gr.Blocks(title="FFmpeg 字幕工具箱", theme=gr.themes.Soft(), js=browser_close_js) as demo:
            gr.Markdown("# 🎬 FFmpeg 字幕工具箱")
            gr.Markdown("簡單易用的影片字幕燒錄工具")

            with gr.Tabs():
                with gr.Tab("📝 字幕燒錄"):
                    self._create_subtitle_tab()

                with gr.Tab("✂️ 影片剪輯 (即將推出)"):
                    gr.Markdown("### 影片剪輯功能")
                    gr.Markdown("此功能尚未實作，敬請期待！")

                with gr.Tab("🔊 音訊處理 (即將推出)"):
                    gr.Markdown("### 音訊處理功能")
                    gr.Markdown("此功能尚未實作，敬請期待！")

        return demo

    def _create_subtitle_tab(self):
        """建立字幕燒錄分頁"""
        with gr.Row():
            with gr.Column(scale=1):
                # 檔案上傳區
                gr.Markdown("### 📁 檔案選擇")
                video_input = gr.File(
                    label="影片檔案",
                    file_types=["video"],
                    file_count="single",
                )
                subtitle_input = gr.File(
                    label="字幕檔案",
                    file_types=[".srt", ".ass", ".ssa"],
                    file_count="single",
                )
                output_path = gr.Textbox(
                    label="輸出檔案名稱",
                    placeholder="output.mp4",
                    value="output.mp4",
                )

                # 編碼設定
                gr.Markdown("### ⚙️ 編碼設定")
                codec = gr.Dropdown(
                    label="編碼器",
                    choices=["H.264 (推薦)", "H.265 (高壓縮率)"],
                    value="H.264 (推薦)",
                )
                preset = gr.Dropdown(
                    label="編碼速度",
                    choices=[
                        "ultrafast",
                        "superfast",
                        "veryfast",
                        "faster",
                        "fast",
                        "medium",
                        "slow",
                        "slower",
                        "veryslow",
                    ],
                    value="medium",
                )

            with gr.Column(scale=1):
                # 字幕樣式設定
                gr.Markdown("### 🎨 字幕樣式")

                with gr.Accordion("字型設定", open=True):
                    font_name = gr.Dropdown(
                        label="字型名稱",
                        choices=self._get_common_fonts(),
                        value="Arial",
                        allow_custom_value=True,
                        info="選擇字型或輸入自訂字型名稱",
                    )
                    font_size = gr.Slider(
                        label="字型大小",
                        minimum=12,
                        maximum=72,
                        value=24,
                        step=1,
                    )

                with gr.Accordion("顏色設定", open=True):
                    primary_color = gr.ColorPicker(
                        label="字幕顏色",
                        value="#FFFFFF",
                    )
                    transparency = gr.Slider(
                        label="背景透明度 (%)",
                        minimum=0,
                        maximum=100,
                        value=50,
                        step=5,
                    )

                with gr.Accordion("邊框設定", open=False):
                    border_style = gr.Dropdown(
                        label="邊框樣式",
                        choices=[
                            ("外框", 1),
                            ("不透明背景", 3),
                            ("無邊框", 0),
                            ("陰影", 4),
                        ],
                        value=1,
                    )
                    outline_width = gr.Slider(
                        label="外框寬度",
                        minimum=0,
                        maximum=5,
                        value=1,
                        step=1,
                    )

                with gr.Accordion("位置設定", open=False):
                    margin_v = gr.Slider(
                        label="垂直邊距",
                        minimum=0,
                        maximum=100,
                        value=20,
                        step=5,
                    )
                    alignment = gr.Dropdown(
                        label="對齊方式",
                        choices=[
                            ("底部居中", 2),
                            ("底部左側", 1),
                            ("底部右側", 3),
                            ("中間居中", 5),
                            ("頂部居中", 8),
                        ],
                        value=2,
                    )

        # 動作按鈕和狀態區
        with gr.Row():
            process_btn = gr.Button("🚀 開始處理", variant="primary", size="lg")
            shutdown_btn = gr.Button("⏹️ 關閉程式", variant="secondary", size="lg")
            status_text = gr.Textbox(label="狀態", value="就緒", interactive=False)

        # 日誌輸出區
        log_output = gr.Textbox(
            label="📋 處理日誌",
            lines=15,
            max_lines=20,
            interactive=False,
            autoscroll=True,
        )

        # 綁定處理事件
        process_btn.click(
            fn=self._process_subtitle,
            inputs=[
                video_input,
                subtitle_input,
                output_path,
                codec,
                preset,
                font_name,
                font_size,
                primary_color,
                transparency,
                border_style,
                outline_width,
                margin_v,
                alignment,
            ],
            outputs=[status_text, log_output],
        )

        # 綁定關閉事件
        shutdown_btn.click(
            fn=self._shutdown_app,
            inputs=None,
            outputs=status_text,
        )

    def _process_subtitle(
        self,
        video_file,
        subtitle_file,
        output_name: str,
        codec_choice: str,
        preset: str,
        font_name: str,
        font_size: int,
        primary_color: str,
        transparency: int,
        border_style: int,
        outline_width: int,
        margin_v: int,
        alignment: int,
    ) -> tuple[str, str]:
        """
        處理字幕燒錄（Gradio 事件處理器）

        Args:
            video_file: Gradio File 對象（影片）
            subtitle_file: Gradio File 對象（字幕）
            output_name: 輸出檔案名稱
            codec_choice: 編碼器選擇
            preset: 編碼速度
            font_name: 字型名稱
            font_size: 字型大小
            primary_color: 字幕顏色（HEX）
            transparency: 背景透明度
            border_style: 邊框樣式
            outline_width: 外框寬度
            margin_v: 垂直邊距
            alignment: 對齊方式

        Returns:
            tuple[str, str]: (狀態訊息, 日誌內容)
        """
        # 清空日誌緩衝區
        self.log_buffer = []

        # 驗證輸入
        if video_file is None:
            return "❌ 錯誤：請選擇影片檔案", "\n".join(self.log_buffer)

        if subtitle_file is None:
            return "❌ 錯誤：請選擇字幕檔案", "\n".join(self.log_buffer)

        if self.processing:
            return "⚠️ 警告：已有處理任務執行中", "\n".join(self.log_buffer)

        try:
            self.processing = True

            # 初始化執行器和燒錄器
            self.executor = FFmpegExecutor(log_callback=self._log)
            self.subtitle_burner = SubtitleBurner(self.executor, self.encoding_strategy)

            # 取得檔案路徑
            video_path = Path(video_file)
            subtitle_path = Path(subtitle_file)

            # 決定輸出路徑（與影片同目錄）
            output_file = video_path.parent / output_name

            self._log(f"影片檔案: {video_path.name}")
            self._log(f"字幕檔案: {subtitle_path.name}")
            self._log(f"輸出檔案: {output_file}")

            # 轉換編碼器選擇
            encoding = "libx264" if codec_choice == "H.264 (推薦)" else "libx265"

            # 轉換顏色格式：HEX RGB → ASS BGR
            primary_color_ass = self._hex_to_ass_color(primary_color)

            # 建立字幕樣式
            style = SubtitleStyle(
                font_name=font_name,
                font_size=int(font_size),
                primary_color=primary_color_ass,
                border_style=int(border_style),
                transparency=int(transparency),
                margin_v=int(margin_v),
                outline_width=int(outline_width),
                alignment=int(alignment),
            )

            # 建立配置
            config = SubtitleConfig(
                video_file=video_path,
                subtitle_file=subtitle_path,
                output_file=output_file,
                style=style,
                encoding=encoding,
                preset=preset,
            )

            self._log("開始處理...")

            # 執行燒錄（在背景執行緒中執行）
            success, message = self.subtitle_burner.burn(config)

            if success:
                self._log("✅ 處理完成!")
                return f"✅ 成功：{message}", "\n".join(self.log_buffer)
            else:
                self._log(f"❌ 處理失敗: {message}")
                return f"❌ 失敗：{message}", "\n".join(self.log_buffer)

        except Exception as e:
            error_msg = f"處理時發生錯誤: {str(e)}"
            self._log(f"❌ {error_msg}")
            return f"❌ 錯誤：{error_msg}", "\n".join(self.log_buffer)

        finally:
            self.processing = False

    def _hex_to_ass_color(self, hex_color: str) -> str:
        """
        將 HEX 顏色轉換為 ASS BGR 格式

        Args:
            hex_color: HEX 顏色字串（例如 "#FFFFFF"）

        Returns:
            str: ASS 格式顏色字串（例如 "&H00FFFFFF"）
        """
        # 移除 # 符號
        hex_color = hex_color.lstrip("#")

        # 解析 RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # 轉換為 BGR 格式
        return f"&H00{b:02X}{g:02X}{r:02X}"

    def _log(self, message: str):
        """
        記錄訊息到日誌緩衝區

        Args:
            message: 要記錄的訊息
        """
        self.log_buffer.append(message)
