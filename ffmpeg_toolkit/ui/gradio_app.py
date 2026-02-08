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
from ..features.audio_extractor import AUDIO_FORMATS, AudioExtractConfig, AudioExtractor
from ..features.converter import ConvertConfig, VideoConverter
from ..features.media_info import MediaInfoReader
from ..features.screenshot import BatchScreenshotConfig, ScreenshotConfig, VideoScreenshot
from ..features.subtitle import SubtitleBurner, SubtitleConfig, SubtitleStyle
from ..features.trimmer import TrimConfig, VideoTrimmer
from ..features.video_adjust import AdjustConfig, VideoAdjuster


class GradioApp:
    """
    Gradio 網頁應用程式

    提供字幕燒錄的網頁介面，支援檔案上傳、樣式設定和即時日誌輸出。
    """

    def __init__(self):
        """初始化 Gradio 應用程式"""
        self.executor: Optional[FFmpegExecutor] = None
        self.encoding_strategy = EncodingStrategy()
        self._hw_accelerators = self.encoding_strategy.get_available_hw_accelerators()
        self.subtitle_burner: Optional[SubtitleBurner] = None
        self.media_info_reader = MediaInfoReader()
        self.log_buffer: list[str] = []
        self.processing = False
        self.should_exit = False

    @staticmethod
    def _resolve_output_dir(output_dir: str) -> Path:
        """解析輸出目錄路徑，空值時 fallback 到 Documents"""
        if output_dir and output_dir.strip():
            path = Path(output_dir.strip())
        else:
            path = Path.home() / "Documents"
        path.mkdir(parents=True, exist_ok=True)
        return path

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

    @staticmethod
    def _browse_directory(current_dir: str) -> str:
        """開啟原生資料夾選擇對話框"""
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        initial_dir = current_dir if current_dir and Path(current_dir).is_dir() else str(Path.home() / "Documents")

        selected = filedialog.askdirectory(
            title="選擇輸出目錄",
            initialdir=initial_dir,
        )

        root.destroy()

        return selected if selected else current_dir

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

        /* 確保下拉選單選項容器正常顯示 */
        .dropdown-menu, .dropdown-content, [role="listbox"], .svelte-select-list {
            position: absolute !important;
            z-index: 9999 !important;
            background: var(--cinema-surface) !important;
            border: 1px solid var(--cinema-accent) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
            max-height: 300px !important;
            overflow-y: auto !important;
        }

        /* 下拉選項樣式 */
        .dropdown-menu li, .dropdown-content li, [role="option"] {
            padding: 10px 16px !important;
            color: var(--cinema-text) !important;
            cursor: pointer !important;
            transition: background 0.2s ease !important;
        }

        .dropdown-menu li:hover, .dropdown-content li:hover, [role="option"]:hover {
            background: var(--cinema-card) !important;
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

        /* 關閉程式按鈕 - 醒目的紅色風格 */
        button.stop {
            background: linear-gradient(135deg, #dc2626, #991b1b) !important;
            color: white !important;
            border: 1px solid rgba(220, 38, 38, 0.5) !important;
            box-shadow: 0 4px 16px rgba(220, 38, 38, 0.2) !important;
            align-self: flex-end !important;
        }

        button.stop:hover {
            background: linear-gradient(135deg, #ef4444, #b91c1c) !important;
            box-shadow: 0 8px 24px rgba(220, 38, 38, 0.4) !important;
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

        with gr.Blocks(title="FFmpeg 工具箱") as demo:
            gr.Markdown("# 🎬 FFmpeg 工具箱")
            gr.Markdown("專業級影片處理工具 — 轉換、剪輯、字幕、音訊提取")

            with gr.Row():
                self.output_dir = gr.Textbox(
                    label="📁 輸出目錄",
                    value=str(Path.home() / "Documents"),
                    info="所有處理後的檔案將儲存到此目錄（可手動輸入或點擊「瀏覽」選擇）",
                    interactive=True,
                    scale=4,
                )
                browse_btn = gr.Button(
                    "📂 選擇資料夾",
                    variant="secondary",
                    size="lg",
                    scale=1,
                    min_width=100,
                )
                shutdown_btn = gr.Button(
                    "⏹️ 關閉程式",
                    variant="stop",
                    size="lg",
                    scale=1,
                    min_width=120,
                )

            with gr.Tabs():
                with gr.Tab("ℹ️ 影片資訊"):
                    self._create_media_info_tab()

                with gr.Tab("🔄 影片轉換"):
                    self._create_converter_tab()

                with gr.Tab("📝 字幕燒錄"):
                    self._create_subtitle_tab()

                with gr.Tab("✂️ 影片剪輯"):
                    self._create_trimmer_tab()

                with gr.Tab("📸 影片截圖"):
                    self._create_screenshot_tab()

                with gr.Tab("📐 解析度/旋轉"):
                    self._create_video_adjust_tab()

                with gr.Tab("🔊 音訊提取"):
                    self._create_audio_extractor_tab()

            # 綁定瀏覽目錄按鈕
            browse_btn.click(
                fn=self._browse_directory,
                inputs=[self.output_dir],
                outputs=[self.output_dir],
            )

            # 綁定全域關閉事件
            shutdown_status = gr.Textbox(visible=False)
            shutdown_btn.click(
                fn=self._shutdown_app,
                inputs=None,
                outputs=shutdown_status,
            )

        # 儲存自訂設定供 launch 使用
        demo._custom_theme = custom_theme
        demo._custom_css = custom_css
        demo._custom_js = browser_close_js

        return demo

    def _create_media_info_tab(self):
        """建立影片資訊分頁"""
        gr.Markdown("### 📊 影片資訊查看")
        gr.Markdown("上傳影片檔案，查看詳細的媒體資訊")

        media_file = gr.File(
            label="選擇媒體檔案",
            file_types=["video", "audio"],
            file_count="single",
        )
        analyze_btn = gr.Button("🔍 分析檔案", variant="primary", elem_classes="primary")
        info_output = gr.Textbox(
            label="媒體資訊",
            lines=12,
            max_lines=20,
            interactive=False,
        )

        analyze_btn.click(
            fn=self._analyze_media,
            inputs=[media_file],
            outputs=[info_output],
        )

    def _analyze_media(self, media_file) -> str:
        """
        分析媒體檔案資訊

        Args:
            media_file: Gradio File 對象

        Returns:
            str: 媒體資訊文字
        """
        if media_file is None:
            return "請先選擇媒體檔案"

        file_path = Path(media_file)
        success, info, error = self.media_info_reader.read(file_path)

        if not success:
            return f"分析失敗: {error}"

        return self.media_info_reader.format_info(info)

    def _create_converter_tab(self):
        """建立影片轉換分頁"""
        gr.Markdown("### 🔄 影片格式/編碼轉換")
        gr.Markdown("支援格式轉換（MP4/MKV/AVI/MOV/WebM）和編碼轉換（H.264/H.265）")

        with gr.Row():
            with gr.Column(scale=1):
                conv_video = gr.File(label="選擇影片檔案", file_types=["video"], file_count="single")
                conv_output = gr.Textbox(
                    label="輸出檔案名稱",
                    placeholder="上傳影片後自動產生",
                    value="",
                    info="上傳影片後自動填入，也可手動修改",
                )

            with gr.Column(scale=1):
                conv_format = gr.Radio(
                    label="輸出格式",
                    choices=[
                        ("MP4 (最通用)", "MP4"),
                        ("MKV (高相容性)", "MKV"),
                        ("AVI", "AVI"),
                        ("MOV (Apple)", "MOV"),
                        ("WebM (網頁)", "WebM"),
                    ],
                    value="MP4",
                )
                conv_codec = gr.Radio(
                    label="編碼器",
                    choices=[("H.264 (推薦)", "H.264"), ("H.265 (高壓縮率)", "H.265")],
                    value="H.264",
                )
                # 動態建構硬體加速選項
                hw_choices = [("自動（優先 GPU）", "auto"), ("CPU（軟體編碼）", "cpu")]
                for label, accel_id in self._hw_accelerators:
                    hw_choices.append((label, accel_id))

                conv_hw_accel = gr.Radio(
                    label="硬體加速",
                    choices=hw_choices,
                    value="auto",
                    info="自動模式會嘗試 GPU 加速，失敗自動回退 CPU",
                )
                conv_quality = gr.Radio(
                    label="畫質",
                    choices=[
                        ("省空間", 28),
                        ("標準 (推薦)", 23),
                        ("高品質", 18),
                        ("最高品質", 15),
                    ],
                    value=23,
                )
                conv_preset = gr.Dropdown(
                    label="編碼速度",
                    choices=[
                        ("快速（省時間）", "fast"),
                        ("平衡 (推薦)", "medium"),
                        ("高品質（較慢）", "slow"),
                    ],
                    value="medium",
                )

        # 格式 → 副檔名對應表
        format_ext_map = {"MP4": ".mp4", "MKV": ".mkv", "AVI": ".avi", "MOV": ".mov", "WebM": ".webm"}

        def on_video_upload(video_file, current_format):
            """上傳影片後自動產生輸出檔名"""
            if video_file is None:
                return ""
            stem = Path(video_file).stem
            ext = format_ext_map.get(current_format, ".mp4")
            return f"{stem}_converted{ext}"

        def on_format_change(new_format, current_output):
            """切換格式時自動更新副檔名"""
            if not current_output:
                return ""
            stem = Path(current_output).stem
            ext = format_ext_map.get(new_format, ".mp4")
            return f"{stem}{ext}"

        conv_video.change(fn=on_video_upload, inputs=[conv_video, conv_format], outputs=[conv_output])
        conv_format.change(fn=on_format_change, inputs=[conv_format, conv_output], outputs=[conv_output])

        conv_btn = gr.Button("🚀 開始轉換", variant="primary", elem_classes="primary")
        conv_status = gr.Textbox(label="狀態", value="就緒", interactive=False)
        conv_log = gr.Textbox(label="📋 處理日誌", lines=10, max_lines=15, interactive=False, autoscroll=True)

        conv_btn.click(
            fn=self._process_convert,
            inputs=[
                conv_video,
                conv_output,
                conv_format,
                conv_codec,
                conv_preset,
                conv_quality,
                conv_hw_accel,
                self.output_dir,
            ],
            outputs=[conv_status, conv_log],
        )

    def _process_convert(
        self, video_file, output_name, output_format, codec_choice, preset, quality, hw_accel, output_dir
    ) -> tuple[str, str]:
        """處理影片轉換"""
        self.log_buffer = []

        if video_file is None:
            return "請選擇影片檔案", ""

        if self.processing:
            return "已有處理任務執行中", ""

        try:
            self.processing = True

            video_path = Path(video_file)

            # 根據格式調整副檔名
            format_ext = {"MP4": ".mp4", "MKV": ".mkv", "AVI": ".avi", "MOV": ".mov", "WebM": ".webm"}
            ext = format_ext.get(output_format, ".mp4")

            # 自動產生輸出檔名（若使用者未填寫）
            if not output_name or not output_name.strip():
                output_name = f"{video_path.stem}_converted{ext}"

            # 確保輸出副檔名正確
            output_base = Path(output_name).stem
            output_path = self._resolve_output_dir(output_dir)
            output_file = output_path / f"{output_base}{ext}"

            encoding = "libx264" if codec_choice == "H.264" else "libx265"

            executor = FFmpegExecutor(log_callback=self._log)
            converter = VideoConverter(executor, self.encoding_strategy)

            self._log(f"輸入: {video_path.name}")
            self._log(f"輸出: {output_file}")
            crf = int(quality) if quality else 23
            hw_label = {"auto": "自動", "cpu": "CPU", "nvenc": "NVIDIA NVENC", "qsv": "Intel QSV"}.get(
                hw_accel, hw_accel
            )
            self._log(f"編碼: {encoding} | 加速: {hw_label} | 速度: {preset} | 品質: {crf}")

            config = ConvertConfig(
                input_file=video_path,
                output_file=output_file,
                encoding=encoding,
                preset=preset,
                crf=crf,
                hw_accel=hw_accel or "auto",
            )

            success, message = converter.convert(config)

            if success:
                self._log("轉換完成!")
                return f"成功: {message}", "\n".join(self.log_buffer)
            else:
                self._log(f"轉換失敗: {message}")
                return f"失敗: {message}", "\n".join(self.log_buffer)

        except Exception as e:
            self._log(f"錯誤: {e}")
            return f"錯誤: {e}", "\n".join(self.log_buffer)
        finally:
            self.processing = False

    def _create_trimmer_tab(self):
        """建立影片剪輯分頁"""
        gr.Markdown("### ✂️ 影片剪輯")
        gr.Markdown("指定起止時間裁切影片片段")

        with gr.Row():
            with gr.Column(scale=1):
                trim_video = gr.File(label="選擇影片檔案", file_types=["video"], file_count="single")
                trim_output = gr.Textbox(label="輸出檔案名稱", placeholder="trimmed.mp4", value="trimmed.mp4")

            with gr.Column(scale=1):
                trim_start = gr.Textbox(
                    label="開始時間", placeholder="00:00:00", value="00:00:00", info="格式: HH:MM:SS 或秒數"
                )
                trim_end = gr.Textbox(label="結束時間", placeholder="00:01:00", value="", info="留空表示到影片結尾")
                trim_copy = gr.Checkbox(
                    label="快速模式（不重編碼）",
                    value=True,
                    info="勾選速度極快但剪輯點可能不精確，取消勾選則精確但較慢",
                )

        trim_btn = gr.Button("✂️ 開始剪輯", variant="primary", elem_classes="primary")
        trim_status = gr.Textbox(label="狀態", value="就緒", interactive=False)
        trim_log = gr.Textbox(label="📋 處理日誌", lines=10, max_lines=15, interactive=False, autoscroll=True)

        trim_btn.click(
            fn=self._process_trim,
            inputs=[trim_video, trim_output, trim_start, trim_end, trim_copy, self.output_dir],
            outputs=[trim_status, trim_log],
        )

    def _process_trim(self, video_file, output_name, start_time, end_time, copy_mode, output_dir) -> tuple[str, str]:
        """處理影片剪輯"""
        self.log_buffer = []

        if video_file is None:
            return "請選擇影片檔案", ""

        if self.processing:
            return "已有處理任務執行中", ""

        if not VideoTrimmer.validate_time_format(start_time):
            return f"開始時間格式錯誤: {start_time}", ""

        if not VideoTrimmer.validate_time_format(end_time):
            return f"結束時間格式錯誤: {end_time}", ""

        try:
            self.processing = True

            video_path = Path(video_file)
            output_path = self._resolve_output_dir(output_dir)
            output_file = output_path / output_name

            executor = FFmpegExecutor(log_callback=self._log)
            trimmer = VideoTrimmer(executor)

            mode_text = "快速模式 (copy)" if copy_mode else "精確模式 (重編碼)"
            self._log(f"輸入: {video_path.name}")
            self._log(f"輸出: {output_file}")
            self._log(f"時間: {start_time} → {end_time or '結尾'}")
            self._log(f"模式: {mode_text}")

            config = TrimConfig(
                input_file=video_path,
                output_file=output_file,
                start_time=start_time,
                end_time=end_time,
                copy_mode=copy_mode,
            )

            success, message = trimmer.trim(config)

            if success:
                self._log("剪輯完成!")
                return f"成功: {message}", "\n".join(self.log_buffer)
            else:
                self._log(f"剪輯失敗: {message}")
                return f"失敗: {message}", "\n".join(self.log_buffer)

        except Exception as e:
            self._log(f"錯誤: {e}")
            return f"錯誤: {e}", "\n".join(self.log_buffer)
        finally:
            self.processing = False

    def _create_screenshot_tab(self):
        """建立影片截圖分頁"""
        gr.Markdown("### 📸 影片截圖")
        gr.Markdown("從影片中擷取單張或批次截圖")

        with gr.Row():
            with gr.Column(scale=1):
                ss_video = gr.File(label="選擇影片檔案", file_types=["video"], file_count="single")
                ss_mode = gr.Radio(
                    label="截圖模式",
                    choices=[("單張截圖", "single"), ("批次截圖", "batch")],
                    value="single",
                )

            with gr.Column(scale=1):
                ss_timestamp = gr.Textbox(
                    label="時間點",
                    placeholder="00:01:30",
                    value="00:00:00",
                    info="格式: HH:MM:SS 或秒數（單張模式使用）",
                )
                ss_interval = gr.Slider(
                    label="截圖間隔（秒）",
                    minimum=1,
                    maximum=60,
                    value=10,
                    step=1,
                    info="每隔 N 秒截取一張（批次模式使用）",
                    visible=False,
                )
                ss_format = gr.Radio(
                    label="圖片格式",
                    choices=["PNG", "JPG"],
                    value="PNG",
                )
                ss_output = gr.Textbox(label="輸出檔案名稱", placeholder="screenshot.png", value="screenshot.png")

        # 模式切換控制元件顯示
        def toggle_screenshot_mode(mode):
            if mode == "single":
                return gr.Textbox(visible=True), gr.Slider(visible=False)
            else:
                return gr.Textbox(visible=False), gr.Slider(visible=True)

        ss_mode.change(fn=toggle_screenshot_mode, inputs=[ss_mode], outputs=[ss_timestamp, ss_interval])

        ss_btn = gr.Button("📸 開始截圖", variant="primary", elem_classes="primary")
        ss_status = gr.Textbox(label="狀態", value="就緒", interactive=False)
        ss_log = gr.Textbox(label="📋 處理日誌", lines=10, max_lines=15, interactive=False, autoscroll=True)

        ss_btn.click(
            fn=self._process_screenshot,
            inputs=[ss_video, ss_mode, ss_timestamp, ss_interval, ss_format, ss_output, self.output_dir],
            outputs=[ss_status, ss_log],
        )

    def _process_screenshot(
        self, video_file, mode, timestamp, interval, image_format, output_name, output_dir
    ) -> tuple[str, str]:
        """處理影片截圖"""
        self.log_buffer = []

        if video_file is None:
            return "請選擇影片檔案", ""

        if self.processing:
            return "已有處理任務執行中", ""

        try:
            self.processing = True

            video_path = Path(video_file)
            executor = FFmpegExecutor(log_callback=self._log)
            screenshotter = VideoScreenshot(executor)

            output_path = self._resolve_output_dir(output_dir)

            if mode == "single":
                # 確保副檔名正確
                ext = ".jpg" if image_format.upper() == "JPG" else ".png"
                output_base = Path(output_name).stem
                output_file = output_path / f"{output_base}{ext}"

                self._log(f"輸入: {video_path.name}")
                self._log(f"時間點: {timestamp}")
                self._log(f"輸出: {output_file}")

                config = ScreenshotConfig(
                    input_file=video_path,
                    output_file=output_file,
                    timestamp=timestamp,
                    image_format=image_format,
                )
                success, message = screenshotter.capture(config)
            else:
                # 批次模式 — 輸出到資料夾
                batch_output_dir = output_path / f"{video_path.stem}_screenshots"

                self._log(f"輸入: {video_path.name}")
                self._log(f"間隔: 每 {int(interval)} 秒")
                self._log(f"輸出目錄: {batch_output_dir}")

                config_batch = BatchScreenshotConfig(
                    input_file=video_path,
                    output_dir=batch_output_dir,
                    interval=int(interval),
                    image_format=image_format,
                )
                success, message = screenshotter.capture_batch(config_batch)

            if success:
                self._log("截圖完成!")
                return f"成功: {message}", "\n".join(self.log_buffer)
            else:
                self._log(f"截圖失敗: {message}")
                return f"失敗: {message}", "\n".join(self.log_buffer)

        except Exception as e:
            self._log(f"錯誤: {e}")
            return f"錯誤: {e}", "\n".join(self.log_buffer)
        finally:
            self.processing = False

    def _create_video_adjust_tab(self):
        """建立解析度/旋轉調整分頁"""
        gr.Markdown("### 📐 解析度與旋轉調整")
        gr.Markdown("縮放影片解析度或旋轉影片方向")

        with gr.Row():
            with gr.Column(scale=1):
                adj_video = gr.File(label="選擇影片檔案", file_types=["video"], file_count="single")
                adj_output = gr.Textbox(label="輸出檔案名稱", placeholder="adjusted.mp4", value="adjusted.mp4")

            with gr.Column(scale=1):
                adj_resolution = gr.Radio(
                    label="解析度",
                    choices=[
                        ("原始（不縮放）", "original"),
                        ("1080p (1920x1080)", "1080p"),
                        ("720p (1280x720)", "720p"),
                        ("480p (854x480)", "480p"),
                        ("自訂", "custom"),
                    ],
                    value="original",
                )

                with gr.Row():
                    adj_width = gr.Number(label="寬度", value=1280, visible=False, precision=0)
                    adj_height = gr.Number(label="高度（-1 自動等比例）", value=-1, visible=False, precision=0)

                adj_rotation = gr.Radio(
                    label="旋轉",
                    choices=[
                        ("不旋轉", "0"),
                        ("順時針 90°", "90"),
                        ("180°", "180"),
                        ("逆時針 90°", "270"),
                    ],
                    value="0",
                )

                adj_codec = gr.Dropdown(
                    label="編碼器",
                    choices=["H.264 (推薦)", "H.265 (高壓縮率)"],
                    value="H.264 (推薦)",
                )
                adj_preset = gr.Dropdown(
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

        # 解析度切換顯示自訂欄位
        def toggle_custom_resolution(choice):
            visible = choice == "custom"
            return gr.Number(visible=visible), gr.Number(visible=visible)

        adj_resolution.change(fn=toggle_custom_resolution, inputs=[adj_resolution], outputs=[adj_width, adj_height])

        adj_btn = gr.Button("📐 開始調整", variant="primary", elem_classes="primary")
        adj_status = gr.Textbox(label="狀態", value="就緒", interactive=False)
        adj_log = gr.Textbox(label="📋 處理日誌", lines=10, max_lines=15, interactive=False, autoscroll=True)

        adj_btn.click(
            fn=self._process_video_adjust,
            inputs=[
                adj_video,
                adj_output,
                adj_resolution,
                adj_width,
                adj_height,
                adj_rotation,
                adj_codec,
                adj_preset,
                self.output_dir,
            ],
            outputs=[adj_status, adj_log],
        )

    def _process_video_adjust(
        self,
        video_file,
        output_name,
        resolution,
        custom_width,
        custom_height,
        rotation,
        codec_choice,
        preset,
        output_dir,
    ) -> tuple[str, str]:
        """處理解析度/旋轉調整"""
        self.log_buffer = []

        if video_file is None:
            return "請選擇影片檔案", ""

        if self.processing:
            return "已有處理任務執行中", ""

        # 解析解析度
        resolution_map = {
            "1080p": (1920, 1080),
            "720p": (1280, 720),
            "480p": (854, 480),
        }

        width = None
        height = None
        if resolution == "custom":
            width = int(custom_width) if custom_width else None
            height = int(custom_height) if custom_height else -1
        elif resolution in resolution_map:
            width, height = resolution_map[resolution]

        rotation_deg = int(rotation)

        if width is None and rotation_deg == 0:
            return "請選擇解析度或旋轉角度", ""

        try:
            self.processing = True

            video_path = Path(video_file)
            output_path = self._resolve_output_dir(output_dir)
            output_file = output_path / output_name
            encoding = "libx264" if codec_choice == "H.264 (推薦)" else "libx265"

            executor = FFmpegExecutor(log_callback=self._log)
            adjuster = VideoAdjuster(executor, self.encoding_strategy)

            self._log(f"輸入: {video_path.name}")
            self._log(f"輸出: {output_file}")
            if width is not None:
                self._log(f"解析度: {width}x{height}")
            if rotation_deg != 0:
                self._log(f"旋轉: {rotation_deg}°")

            config = AdjustConfig(
                input_file=video_path,
                output_file=output_file,
                width=width,
                height=height,
                rotation=rotation_deg,
                encoding=encoding,
                preset=preset,
            )

            success, message = adjuster.adjust(config)

            if success:
                self._log("調整完成!")
                return f"成功: {message}", "\n".join(self.log_buffer)
            else:
                self._log(f"調整失敗: {message}")
                return f"失敗: {message}", "\n".join(self.log_buffer)

        except Exception as e:
            self._log(f"錯誤: {e}")
            return f"錯誤: {e}", "\n".join(self.log_buffer)
        finally:
            self.processing = False

    def _create_audio_extractor_tab(self):
        """建立音訊提取分頁"""
        gr.Markdown("### 🔊 音訊提取")
        gr.Markdown("從影片中提取音訊，支援 MP3、AAC、FLAC、WAV 格式")

        with gr.Row():
            with gr.Column(scale=1):
                audio_video = gr.File(label="選擇影片檔案", file_types=["video"], file_count="single")
                audio_output = gr.Textbox(label="輸出檔案名稱", placeholder="audio.mp3", value="audio.mp3")

            with gr.Column(scale=1):
                audio_format = gr.Radio(
                    label="輸出格式",
                    choices=[
                        ("MP3 (通用)", "MP3"),
                        ("AAC (高品質)", "AAC"),
                        ("FLAC (無損)", "FLAC"),
                        ("WAV (無壓縮)", "WAV"),
                    ],
                    value="MP3",
                )

        audio_btn = gr.Button("🔊 開始提取", variant="primary", elem_classes="primary")
        audio_status = gr.Textbox(label="狀態", value="就緒", interactive=False)
        audio_log = gr.Textbox(label="📋 處理日誌", lines=10, max_lines=15, interactive=False, autoscroll=True)

        audio_btn.click(
            fn=self._process_audio_extract,
            inputs=[audio_video, audio_output, audio_format, self.output_dir],
            outputs=[audio_status, audio_log],
        )

    def _process_audio_extract(self, video_file, output_name, audio_format, output_dir) -> tuple[str, str]:
        """處理音訊提取"""
        self.log_buffer = []

        if video_file is None:
            return "請選擇影片檔案", ""

        if self.processing:
            return "已有處理任務執行中", ""

        try:
            self.processing = True

            video_path = Path(video_file)
            output_path = self._resolve_output_dir(output_dir)

            # 根據格式調整副檔名
            fmt = AUDIO_FORMATS.get(audio_format)
            if fmt:
                output_base = Path(output_name).stem
                output_file = output_path / f"{output_base}{fmt['ext']}"
            else:
                output_file = output_path / output_name

            executor = FFmpegExecutor(log_callback=self._log)
            extractor = AudioExtractor(executor)

            self._log(f"輸入: {video_path.name}")
            self._log(f"輸出: {output_file}")
            self._log(f"格式: {audio_format}")

            config = AudioExtractConfig(
                input_file=video_path,
                output_file=output_file,
                audio_format=audio_format,
            )

            success, message = extractor.extract(config)

            if success:
                self._log("音訊提取完成!")
                return f"成功: {message}", "\n".join(self.log_buffer)
            else:
                self._log(f"提取失敗: {message}")
                return f"失敗: {message}", "\n".join(self.log_buffer)

        except Exception as e:
            self._log(f"錯誤: {e}")
            return f"錯誤: {e}", "\n".join(self.log_buffer)
        finally:
            self.processing = False

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
                    # 常見字型選項
                    font_preset = gr.Radio(
                        label="字型預設",
                        choices=[
                            ("微軟正黑體 (推薦)", "Microsoft JhengHei"),
                            ("微軟雅黑體", "Microsoft YaHei"),
                            ("蘋方-繁體", "PingFang TC"),
                            ("思源黑體-繁", "Noto Sans CJK TC"),
                            ("黑體", "SimHei"),
                            ("Arial", "Arial"),
                            ("Times New Roman", "Times New Roman"),
                            ("自訂字型", "custom"),
                        ],
                        value="Microsoft JhengHei",
                        info="選擇常用字型或使用自訂",
                    )

                    # 自訂字型輸入框（只在選擇「自訂字型」時顯示）
                    custom_font_input = gr.Textbox(
                        label="自訂字型名稱",
                        placeholder="例如: PMingLiU, SimSun, Courier New",
                        visible=False,
                        info="輸入系統已安裝的字型名稱",
                    )

                    # 當選擇「自訂字型」時顯示輸入框
                    def toggle_custom_font(choice):
                        return gr.Textbox(visible=(choice == "custom"))

                    font_preset.change(
                        fn=toggle_custom_font,
                        inputs=font_preset,
                        outputs=custom_font_input,
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
                font_preset,
                custom_font_input,
                font_size,
                primary_color,
                transparency,
                border_style,
                outline_width,
                margin_v,
                alignment,
                self.output_dir,
            ],
            outputs=[status_text, log_output],
        )

    def _process_subtitle(
        self,
        video_file,
        subtitle_file,
        output_name: str,
        codec_choice: str,
        preset: str,
        font_preset: str,
        custom_font_input: str,
        font_size: int,
        primary_color: str,
        transparency: int,
        border_style: int,
        outline_width: int,
        margin_v: int,
        alignment: int,
        output_dir: str = "",
    ) -> tuple[str, str]:
        """
        處理字幕燒錄（Gradio 事件處理器）

        Args:
            video_file: Gradio File 對象（影片）
            subtitle_file: Gradio File 對象（字幕）
            output_name: 輸出檔案名稱
            codec_choice: 編碼器選擇
            preset: 編碼速度
            font_preset: 字型預設選擇
            custom_font_input: 自訂字型名稱
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

            # 決定輸出路徑
            output_path = self._resolve_output_dir(output_dir)
            output_file = output_path / output_name

            self._log(f"影片檔案: {video_path.name}")
            self._log(f"字幕檔案: {subtitle_path.name}")
            self._log(f"輸出檔案: {output_file}")

            # 決定使用的字型名稱
            if font_preset == "custom":
                # 使用自訂字型
                font_name = custom_font_input.strip() if custom_font_input else "Arial"
                if not font_name:
                    font_name = "Arial"
                self._log(f"使用自訂字型: {font_name}")
            else:
                # 使用預設字型
                font_name = font_preset
                self._log(f"使用預設字型: {font_name}")

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
