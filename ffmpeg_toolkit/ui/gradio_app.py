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

        # 自訂 CSS - Cinema-grade aesthetic
        custom_css = """
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&display=swap');

        :root {
            --cinema-bg: #0a0e1a;
            --cinema-surface: #151b2e;
            --cinema-card: rgba(25, 35, 55, 0.6);
            --cinema-accent: #00d9ff;
            --cinema-accent-glow: rgba(0, 217, 255, 0.15);
            --cinema-secondary: #6366f1;
            --cinema-text: #e2e8f0;
            --cinema-text-dim: #94a3b8;
            --cinema-border: rgba(100, 116, 139, 0.2);
            --cinema-success: #10b981;
            --cinema-glass: rgba(255, 255, 255, 0.05);
        }

        /* 全域背景與動畫漸層 */
        .gradio-container {
            font-family: 'Noto Sans TC', 'JetBrains Mono', monospace !important;
            background: var(--cinema-bg) !important;
            background-image:
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(0, 217, 255, 0.1) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(139, 92, 246, 0.05) 0px, transparent 50%);
            animation: gradientShift 15s ease infinite;
            color: var(--cinema-text) !important;
        }

        @keyframes gradientShift {
            0%, 100% {
                background-position: 0% 50%, 100% 50%, 50% 50%;
            }
            50% {
                background-position: 100% 50%, 0% 50%, 25% 75%;
            }
        }

        /* 標題區域 - Cinematic header */
        .gradio-container h1 {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 3rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, var(--cinema-accent) 0%, var(--cinema-secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem !important;
            letter-spacing: -0.02em;
            animation: titleFadeIn 1s ease-out;
        }

        @keyframes titleFadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .gradio-container h1 + p, .gradio-container h1 ~ p {
            font-size: 1.125rem !important;
            color: var(--cinema-text-dim) !important;
            font-weight: 400 !important;
            margin-top: 0 !important;
        }

        /* Tabs - 電影時間軸風格 */
        .tabs {
            border: none !important;
            background: transparent !important;
        }

        .tab-nav {
            background: var(--cinema-card) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid var(--cinema-border) !important;
            border-radius: 16px !important;
            padding: 8px !important;
            margin-bottom: 2rem !important;
        }

        .tab-nav button {
            font-family: 'Noto Sans TC', sans-serif !important;
            font-weight: 500 !important;
            color: var(--cinema-text-dim) !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px 24px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            background: transparent !important;
        }

        .tab-nav button:hover {
            background: var(--cinema-glass) !important;
            color: var(--cinema-text) !important;
            transform: translateY(-2px);
        }

        .tab-nav button.selected {
            background: linear-gradient(135deg, var(--cinema-accent), var(--cinema-secondary)) !important;
            color: white !important;
            box-shadow: 0 8px 32px var(--cinema-accent-glow) !important;
        }

        /* 玻璃擬態卡片 */
        .form, .block {
            background: var(--cinema-card) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid var(--cinema-border) !important;
            border-radius: 20px !important;
            padding: 24px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }

        .form:hover, .block:hover {
            border-color: rgba(0, 217, 255, 0.3) !important;
            box-shadow: 0 12px 48px rgba(0, 217, 255, 0.1) !important;
            transform: translateY(-4px);
        }

        /* 區塊標題 */
        h2, h3 {
            font-family: 'JetBrains Mono', monospace !important;
            color: var(--cinema-text) !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            margin-bottom: 1rem !important;
        }

        /* 輸入框與下拉選單 */
        input, select, textarea, .dropdown {
            font-family: 'JetBrains Mono', monospace !important;
            background: var(--cinema-surface) !important;
            border: 1px solid var(--cinema-border) !important;
            border-radius: 12px !important;
            color: var(--cinema-text) !important;
            padding: 12px 16px !important;
            transition: all 0.3s ease !important;
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--cinema-accent) !important;
            box-shadow: 0 0 0 3px var(--cinema-accent-glow) !important;
            outline: none !important;
        }

        /* 按鈕 - Cinematic style */
        button {
            font-family: 'Noto Sans TC', sans-serif !important;
            font-weight: 600 !important;
            border-radius: 14px !important;
            padding: 14px 32px !important;
            border: none !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            position: relative !important;
            overflow: hidden !important;
        }

        button:before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }

        button:active:before {
            width: 300px;
            height: 300px;
        }

        button.primary {
            background: linear-gradient(135deg, var(--cinema-accent), var(--cinema-secondary)) !important;
            color: white !important;
            box-shadow: 0 8px 24px var(--cinema-accent-glow) !important;
        }

        button.primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 36px rgba(0, 217, 255, 0.3) !important;
        }

        button.secondary {
            background: var(--cinema-surface) !important;
            color: var(--cinema-text) !important;
            border: 1px solid var(--cinema-border) !important;
        }

        button.secondary:hover {
            background: var(--cinema-card) !important;
            transform: translateY(-2px);
        }

        /* 日誌輸出 - Terminal style */
        #log-output {
            font-family: 'JetBrains Mono', monospace !important;
            background: #0d1117 !important;
            border: 1px solid rgba(0, 217, 255, 0.3) !important;
            border-radius: 16px !important;
            color: #58a6ff !important;
            padding: 20px !important;
            line-height: 1.6 !important;
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 20px rgba(0, 217, 255, 0.1) !important;
            font-size: 0.875rem !important;
        }

        /* 狀態文字 */
        #status-text {
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 500 !important;
            font-size: 1rem !important;
        }

        /* Accordion */
        .accordion {
            background: var(--cinema-glass) !important;
            border: 1px solid var(--cinema-border) !important;
            border-radius: 14px !important;
            margin-bottom: 12px !important;
            overflow: hidden !important;
            transition: all 0.3s ease !important;
        }

        .accordion:hover {
            border-color: rgba(0, 217, 255, 0.3) !important;
        }

        /* ColorPicker */
        .color-picker {
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        /* Slider */
        input[type="range"] {
            background: var(--cinema-surface) !important;
            height: 8px !important;
            border-radius: 4px !important;
        }

        input[type="range"]::-webkit-slider-thumb {
            background: linear-gradient(135deg, var(--cinema-accent), var(--cinema-secondary)) !important;
            border: 2px solid white !important;
            box-shadow: 0 4px 12px var(--cinema-accent-glow) !important;
        }

        /* 檔案上傳區域 */
        .file-upload {
            background: var(--cinema-surface) !important;
            border: 2px dashed var(--cinema-border) !important;
            border-radius: 16px !important;
            padding: 32px !important;
            transition: all 0.3s ease !important;
        }

        .file-upload:hover {
            border-color: var(--cinema-accent) !important;
            background: var(--cinema-card) !important;
        }

        /* 微動畫 - Stagger entrance */
        .block {
            animation: blockFadeIn 0.6s ease-out backwards;
        }

        .block:nth-child(1) { animation-delay: 0.1s; }
        .block:nth-child(2) { animation-delay: 0.2s; }
        .block:nth-child(3) { animation-delay: 0.3s; }
        .block:nth-child(4) { animation-delay: 0.4s; }

        @keyframes blockFadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* 滾動條 */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--cinema-surface);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, var(--cinema-accent), var(--cinema-secondary));
            border-radius: 5px;
            transition: all 0.3s ease;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--cinema-accent);
        }
        """

        # 創建自訂主題
        custom_theme = gr.themes.Base(
            primary_hue="blue",
            secondary_hue="cyan",
            neutral_hue="slate",
            font=("Noto Sans TC", "JetBrains Mono", "sans-serif"),
            font_mono=("JetBrains Mono", "monospace"),
        ).set(
            body_background_fill="#0a0e1a",
            body_background_fill_dark="#0a0e1a",
            button_primary_background_fill="linear-gradient(135deg, #00d9ff, #6366f1)",
            button_primary_background_fill_hover="linear-gradient(135deg, #00b8d9, #5558e3)",
        )

        with gr.Blocks(title="FFmpeg 字幕工具箱") as demo:
            gr.Markdown("# 🎬 FFmpeg 字幕工具箱")
            gr.Markdown("專業級影片字幕燒錄工具 — 簡單、快速、高品質")

            with gr.Tabs():
                with gr.Tab("📝 字幕燒錄"):
                    self._create_subtitle_tab()

                with gr.Tab("✂️ 影片剪輯"):
                    gr.Markdown("### 影片剪輯功能")
                    gr.Markdown("此功能開發中，即將推出")

                with gr.Tab("🔊 音訊處理"):
                    gr.Markdown("### 音訊處理功能")
                    gr.Markdown("此功能開發中,即將推出")

        # 儲存自訂設定供 launch 使用
        demo._custom_theme = custom_theme
        demo._custom_css = custom_css
        demo._custom_js = browser_close_js

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
            process_btn = gr.Button("🚀 開始處理", variant="primary", size="lg", elem_classes="primary")
            shutdown_btn = gr.Button("⏹️ 關閉程式", variant="secondary", size="lg", elem_classes="secondary")
            status_text = gr.Textbox(label="狀態", value="就緒", interactive=False, elem_id="status-text")

        # 日誌輸出區
        log_output = gr.Textbox(
            label="📋 處理日誌",
            lines=15,
            max_lines=20,
            interactive=False,
            autoscroll=True,
            elem_id="log-output",
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
