import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext, colorchooser
import subprocess
import os
import sys
import threading
import re
import logging
import tempfile
from shutil import which, copy2, rmtree
from datetime import datetime

__version__ = "0.1.0"

class FFmpegSubtitleGUI:
    """FFmpeg 字幕燒錄工具的主要 GUI 類別"""

    # 類級別常數
    BORDER_STYLE_MAP = {"無邊框": 0, "普通邊框": 1, "陰影": 4, "半透明背景": 3}

    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg 字幕燒錄工具")
        self.root.geometry("600x750")
        self.root.resizable(True, True)
        
        # 初始化變數
        self.video_path = tk.StringVar()
        self.subtitle_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.codec_var = tk.StringVar(value="H.264")
        self.preset_var = tk.StringVar(value="medium")
        self.font_var = tk.StringVar(value="Arial")
        self.transparency_var = tk.StringVar(value="80")  # 透明度百分比
        self.margin_var = tk.IntVar(value=30)
        
        # 新增其他變數
        self.font_size_var = tk.IntVar(value=24)  # 字體大小預設為24
        self.font_color_var = tk.StringVar(value="&HFFFFFF")  # 預設為白色 (ASS格式)
        self.border_style_var = tk.StringVar(value="半透明背景")  # 邊框樣式
        self.pos_x_var = tk.IntVar(value=0)  # X座標微調
        self.pos_y_var = tk.IntVar(value=0)  # Y座標微調
        
        self.progress_var = tk.StringVar(value="準備就緒")
        self.temp_dir = None  # 用於儲存臨時檔案的目錄
        
        # 初始化日誌系統
        self.setup_logging()
        
        # 檢查系統是否安裝 ffmpeg
        self.check_ffmpeg()
        
        # 建立使用者介面
        self.create_widgets()
        
    def setup_logging(self):
        """初始化日誌系統"""
        log_dir = os.path.join(os.path.expanduser("~"), "FFmpegGUI_Logs")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"ffmpeg_gui_{timestamp}.log")

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=self.log_file,
            filemode='w'
        )

        logging.info("日誌系統初始化完成")
    
    def check_ffmpeg(self):
        """檢查系統中是否已安裝並可用 ffmpeg（不依賴系統 shell）"""
        try:
            logging.info("檢查 ffmpeg 是否已安裝")
            if which("ffmpeg") is None:
                error_msg = "無法找到系統中的 ffmpeg，請確認已安裝並設定環境變數"
                logging.error(error_msg)
                messagebox.showerror("錯誤", error_msg)
                return False

            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode != 0:
                error_msg = "ffmpeg 執行異常，請確認安裝是否正確"
                logging.error(error_msg)
                messagebox.showerror("錯誤", error_msg)
                return False

            ffmpeg_version = (result.stdout or result.stderr).split('\n')[0]
            logging.info(f"檢測到 ffmpeg: {ffmpeg_version}")
            return True

        except Exception as e:
            error_msg = f"檢查 ffmpeg 時發生錯誤: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("錯誤", error_msg)
            return False
    
    def _create_file_selection_frame(self, parent):
        """創建檔案選擇區域"""
        file_frame = ttk.LabelFrame(parent, text="檔案選擇", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(file_frame, text="選擇影片:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.video_path, width=50).grid(row=0, column=1, pady=2, padx=5)
        ttk.Button(file_frame, text="瀏覽...", command=self.select_video).grid(row=0, column=2, pady=2)

        ttk.Label(file_frame, text="選擇字幕:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.subtitle_path, width=50).grid(row=1, column=1, pady=2, padx=5)
        ttk.Button(file_frame, text="瀏覽...", command=self.select_subtitle).grid(row=1, column=2, pady=2)

        ttk.Label(file_frame, text="輸出檔案:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.output_path, width=50).grid(row=2, column=1, pady=2, padx=5)
        ttk.Button(file_frame, text="瀏覽...", command=self.select_output).grid(row=2, column=2, pady=2)

    def _create_video_settings_frame(self, parent):
        """創建影片設定區域"""
        video_frame = ttk.LabelFrame(parent, text="影片參數", padding="10")
        video_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(video_frame, text="編碼格式:").grid(row=0, column=0, sticky=tk.W, pady=2)
        codec_menu = ttk.Combobox(video_frame, textvariable=self.codec_var, values=["H.264", "H.265"], state="readonly")
        codec_menu.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(video_frame, text="編碼品質:").grid(row=1, column=0, sticky=tk.W, pady=2)
        preset_menu = ttk.Combobox(video_frame, textvariable=self.preset_var,
                                  values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                                  state="readonly")
        preset_menu.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Label(video_frame, text="(越慢品質越好，但處理時間更長)").grid(row=1, column=2, sticky=tk.W, pady=2)

    def _create_subtitle_settings_frame(self, parent):
        """創建字幕設定區域"""
        subtitle_frame = ttk.LabelFrame(parent, text="字幕設定", padding="10")
        subtitle_frame.pack(fill=tk.X, padx=5, pady=5)

        # 字幕字型設定
        ttk.Label(subtitle_frame, text="字幕字型:").grid(row=0, column=0, sticky=tk.W, pady=2)
        font_menu = ttk.Combobox(subtitle_frame, textvariable=self.font_var,
                                values=["Arial", "微軟正黑體", "Noto Sans TC", "思源黑體", "Times New Roman"],
                                state="readonly")
        font_menu.grid(row=0, column=1, sticky=tk.W, pady=2)

        # 字體大小調整滑桿
        ttk.Label(subtitle_frame, text="字體大小:").grid(row=1, column=0, sticky=tk.W, pady=2)
        size_frame = ttk.Frame(subtitle_frame)
        size_frame.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Scale(size_frame, from_=10, to=72, orient=tk.HORIZONTAL,
                 variable=self.font_size_var, length=200).pack(side=tk.LEFT)
        ttk.Label(size_frame, textvariable=self.font_size_var).pack(side=tk.LEFT, padx=5)

        # 字體顏色選擇器
        ttk.Label(subtitle_frame, text="字體顏色:").grid(row=2, column=0, sticky=tk.W, pady=2)
        color_frame = ttk.Frame(subtitle_frame)
        color_frame.grid(row=2, column=1, sticky=tk.W, pady=2)
        color_menu = ttk.Combobox(color_frame, textvariable=self.font_color_var,
                                 values=["&HFFFFFF", "&H000000", "&HFF0000", "&H00FF00", "&H0000FF"],
                                 state="readonly")
        color_menu.pack(side=tk.LEFT)
        ttk.Button(color_frame, text="自定義", command=self.custom_color).pack(side=tk.LEFT, padx=5)

        # 邊框樣式設定
        ttk.Label(subtitle_frame, text="邊框樣式:").grid(row=3, column=0, sticky=tk.W, pady=2)
        border_menu = ttk.Combobox(subtitle_frame, textvariable=self.border_style_var,
                                  values=["無邊框", "普通邊框", "陰影", "半透明背景"],
                                  state="readonly")
        border_menu.grid(row=3, column=1, sticky=tk.W, pady=2)

        # 精確調整字幕位置
        ttk.Label(subtitle_frame, text="字幕位置:").grid(row=4, column=0, sticky=tk.W, pady=2)
        position_frame = ttk.Frame(subtitle_frame)
        position_frame.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Label(position_frame, text="X座標:").pack(side=tk.LEFT)
        ttk.Scale(position_frame, from_=-200, to=200, orient=tk.HORIZONTAL,
                 variable=self.pos_x_var, length=100).pack(side=tk.LEFT, padx=5)
        ttk.Label(position_frame, textvariable=self.pos_x_var).pack(side=tk.LEFT, padx=5)

        ttk.Label(position_frame, text="Y座標:").pack(side=tk.LEFT)
        ttk.Scale(position_frame, from_=-200, to=200, orient=tk.HORIZONTAL,
                 variable=self.pos_y_var, length=100).pack(side=tk.LEFT, padx=5)
        ttk.Label(position_frame, textvariable=self.pos_y_var).pack(side=tk.LEFT, padx=5)

        # 背景透明度設定
        ttk.Label(subtitle_frame, text="背景透明度:").grid(row=5, column=0, sticky=tk.W, pady=2)
        transparency_menu = ttk.Combobox(subtitle_frame, textvariable=self.transparency_var,
                                        values=["0", "50", "80", "100"], state="readonly")
        transparency_menu.grid(row=5, column=1, sticky=tk.W, pady=2)
        ttk.Label(subtitle_frame, text="0=完全透明, 100=不透明").grid(row=5, column=2, sticky=tk.W, pady=2)

        # 字幕邊距設定
        ttk.Label(subtitle_frame, text="字幕邊距:").grid(row=6, column=0, sticky=tk.W, pady=2)
        margin_frame = ttk.Frame(subtitle_frame)
        margin_frame.grid(row=6, column=1, sticky=tk.W, pady=2)
        ttk.Scale(margin_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                 variable=self.margin_var, length=200).pack(side=tk.LEFT)
        ttk.Label(margin_frame, textvariable=self.margin_var).pack(side=tk.LEFT, padx=5)

    def _create_action_and_status_frames(self, parent):
        """創建動作按鈕和狀態顯示區域"""
        action_frame = ttk.Frame(parent, padding="10")
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        ttk.Button(action_frame, text="開始處理", command=self.start_processing, style="Accent.TButton").pack(pady=10)

        status_frame = ttk.LabelFrame(parent, text="處理狀態", padding="10")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(status_frame, textvariable=self.progress_var).pack(fill=tk.X)

    def _create_log_frame(self, parent):
        """創建日誌顯示區域"""
        log_frame = ttk.LabelFrame(parent, text="詳細日誌", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_display = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_display.pack(fill=tk.BOTH, expand=True)
        self.log_display.config(state=tk.DISABLED)

        ttk.Button(log_frame, text="開啟日誌檔案", command=self.open_log_file).pack(pady=5)

    def create_widgets(self):
        """建立 GUI 的所有元件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 依序創建各個功能區域
        self._create_file_selection_frame(main_frame)
        self._create_video_settings_frame(main_frame)
        self._create_subtitle_settings_frame(main_frame)
        self._create_action_and_status_frames(main_frame)
        self._create_log_frame(main_frame)

        # 設定自訂樣式
        self.configure_styles()
    
    def configure_styles(self):
        """
        設定 GUI 的自訂視覺樣式

        目前配置:
            - Accent.TButton: 強調按鈕樣式（粗體 Arial 12pt）
        """
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 12, "bold"))
    
    def open_log_file(self):
        """開啟日誌檔案"""
        if hasattr(self, 'log_file') and os.path.exists(self.log_file):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.log_file)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', self.log_file], check=False)
                else:  # Linux/其他 POSIX
                    subprocess.run(['xdg-open', self.log_file], check=False)
            except Exception as e:
                messagebox.showerror("錯誤", f"無法開啟日誌檔案: {str(e)}")
        else:
            messagebox.showinfo("提示", "日誌檔案尚未建立")
    
    def log_to_gui(self, message, level="INFO"):
        """將訊息記錄到 GUI 和日誌檔案"""
        if level == "ERROR":
            logging.error(message)
        elif level == "WARNING":
            logging.warning(message)
        else:
            logging.info(message)
        
        self.log_display.config(state=tk.NORMAL)
        
        tag = None
        if level == "ERROR":
            tag = "error"
            self.log_display.tag_config("error", foreground="red")
        elif level == "WARNING":
            tag = "warning"
            self.log_display.tag_config("warning", foreground="orange")
        elif level == "SUCCESS":
            tag = "success"
            self.log_display.tag_config("success", foreground="green")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_display.insert(tk.END, log_entry, tag)
        self.log_display.see(tk.END)
        self.log_display.config(state=tk.DISABLED)
        
        self.root.update_idletasks()
    
    def select_video(self):
        """選擇影片檔案"""
        filepath = filedialog.askopenfilename(
            title="選擇影片檔案",
            filetypes=[("影片檔案", "*.mp4 *.avi *.mkv *.mov *.wmv"), ("所有檔案", "*.*")]
        )
        if filepath:
            self.video_path.set(filepath)
            self.log_to_gui(f"已選擇影片: {filepath}")

            if not self.output_path.get():
                base_path = os.path.splitext(filepath)[0]
                output_name = f"{base_path}_output.mp4"
                self.output_path.set(output_name)
                self.log_to_gui(f"自動設定輸出路徑: {output_name}")
    
    def select_subtitle(self):
        """選擇字幕檔案"""
        filepath = filedialog.askopenfilename(
            title="選擇字幕檔案",
            filetypes=[("字幕檔案", "*.srt *.ass *.ssa"), ("所有檔案", "*.*")]
        )
        if filepath:
            self.subtitle_path.set(filepath)
            self.log_to_gui(f"已選擇字幕: {filepath}")
    
    def select_output(self):
        """選擇輸出檔案的儲存位置"""
        filepath = filedialog.asksaveasfilename(
            title="設定輸出檔案",
            defaultextension=".mp4",
            filetypes=[("MP4 檔案", "*.mp4"), ("所有檔案", "*.*")]
        )
        if filepath:
            self.output_path.set(filepath)
            self.log_to_gui(f"已設定輸出路徑: {filepath}")
    
    def validate_inputs(self):
        """驗證輸入的資料是否有效"""
        if not self.video_path.get():
            self.log_to_gui("請選擇影片檔案", "ERROR")
            messagebox.showerror("錯誤", "請選擇影片檔案")
            return False
        
        if not self.subtitle_path.get():
            self.log_to_gui("請選擇字幕檔案", "ERROR")
            messagebox.showerror("錯誤", "請選擇字幕檔案")
            return False
        
        if not self.output_path.get():
            self.log_to_gui("請設定輸出檔案位置", "ERROR")
            messagebox.showerror("錯誤", "請設定輸出檔案位置")
            return False
        
        if not os.path.exists(self.video_path.get()):
            self.log_to_gui("影片檔案不存在", "ERROR")
            messagebox.showerror("錯誤", "影片檔案不存在")
            return False
        
        if not os.path.exists(self.subtitle_path.get()):
            self.log_to_gui("字幕檔案不存在", "ERROR")
            messagebox.showerror("錯誤", "字幕檔案不存在")
            return False
        
        self.log_to_gui("輸入驗證通過")
        return True
    
    def start_processing(self):
        """開始處理影片檔案"""
        if not self.validate_inputs():
            return
        
        threading.Thread(target=self.process_video, daemon=True).start()
    
    def create_temp_files(self):
        """建立臨時檔案和目錄，避免路徑中的特殊字元問題"""
        try:
            # 建立臨時目錄
            self.temp_dir = tempfile.mkdtemp(prefix="ffmpeg_gui_")
            self.log_to_gui(f"建立臨時目錄: {self.temp_dir}")
            
            # 複製影片檔案到臨時目錄，使用簡化後的檔案名稱
            video_ext = os.path.splitext(self.video_path.get())[1]
            temp_video_path = os.path.join(self.temp_dir, f"input{video_ext}")
            copy2(self.video_path.get(), temp_video_path)
            self.log_to_gui(f"複製影片到臨時目錄: {temp_video_path}")
            
            # 複製字幕檔案到臨時目錄
            subtitle_ext = os.path.splitext(self.subtitle_path.get())[1]
            temp_subtitle_path = os.path.join(self.temp_dir, f"subtitle{subtitle_ext}")
            copy2(self.subtitle_path.get(), temp_subtitle_path)
            self.log_to_gui(f"複製字幕到臨時目錄: {temp_subtitle_path}")
            
            # 設定臨時輸出路徑
            temp_output_path = os.path.join(self.temp_dir, "output.mp4")
            
            return temp_video_path, temp_subtitle_path, temp_output_path
            
        except Exception as e:
            self.log_to_gui(f"建立臨時檔案時發生錯誤: {str(e)}", "ERROR")
            if self.temp_dir and os.path.exists(self.temp_dir):
                rmtree(self.temp_dir, ignore_errors=True)
            raise
    
    def cleanup_temp_files(self):
        """清理臨時檔案和目錄"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                rmtree(self.temp_dir)
                self.log_to_gui("臨時檔案已清理")
            except OSError as e:
                self.log_to_gui(f"清理臨時檔案時發生錯誤: {e}", "WARNING")
    
    def custom_color(self):
        """
        開啟顏色選擇器讓使用者自定義字幕顏色

        將選擇的 RGB 顏色轉換為 ASS 格式（&HBBGGRR）並更新 font_color_var
        """
        color = colorchooser.askcolor(title="選擇字體顏色")
        if color[1]:  # 如果有選擇顏色
            r, g, b = map(int, color[0])
            ass_color = f"&H{b:02x}{g:02x}{r:02x}"
            self.font_color_var.set(ass_color)
            self.log_to_gui(f"自定義字體顏色: {ass_color}")

    def _build_subtitle_style(self, font, font_size, font_color, back_color,
                              border_style, pos_x, pos_y, margin_v):
        """
        構建 ASS/SSA 格式的字幕樣式字串

        參數:
            font: 字型名稱
            font_size: 字體大小
            font_color: 字體顏色（ASS 格式）
            back_color: 背景顏色（ASS 格式，包含透明度）
            border_style: 邊框樣式（0=無邊框, 1=普通邊框, 3=半透明背景, 4=陰影）
            pos_x: X 座標偏移
            pos_y: Y 座標偏移
            margin_v: 垂直邊距

        返回:
            str: 組合後的樣式字串
        """
        # 當 Y 座標向下偏移（pos_y >= 0）時，增加底部邊距以保持視覺位置
        # 向上偏移時不調整邊距，保持原有的 margin_v 值
        margin_v_adjusted = margin_v + pos_y if pos_y >= 0 else margin_v
        margin_l = max(0, pos_x)
        margin_r = max(0, -pos_x)

        # 使用字典組織樣式參數，提高可讀性
        style_params = {
            "Fontname": font,
            "Fontsize": font_size,
            "PrimaryColour": font_color,
            "BackColour": back_color,
            "BorderStyle": border_style,
            "Outline": 1,
            "MarginV": margin_v_adjusted,
            "MarginL": margin_l,
            "MarginR": margin_r,
            "Alignment": 2
        }

        return ",".join(f"{k}={v}" for k, v in style_params.items())

    def _detect_video_size(self, video_path):
        """
        檢測影片的解析度尺寸

        參數:
            video_path: 影片檔案路徑

        返回:
            str: 影片尺寸字串（例如 "1920x1080"），如果檢測失敗則返回預設值
        """
        video_info_cmd = ["ffmpeg", "-i", video_path, "-hide_banner"]
        video_info_process = subprocess.Popen(
            video_info_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace'
        )
        _, video_info = video_info_process.communicate()

        size_match = re.search(r'(\d{2,4})x(\d{2,4})', video_info)
        video_size = size_match.group(0) if size_match else "1920x1080"
        self.log_to_gui(f"檢測到影片尺寸: {video_size}")
        return video_size

    def _build_ffmpeg_command(self, video_path, subtitle_filename, output_path,
                              codec, preset, subtitle_style, video_size, extra_args):
        """
        構建 FFmpeg 命令列表

        參數:
            video_path: 輸入影片路徑
            subtitle_filename: 字幕檔案名稱（相對路徑）
            output_path: 輸出影片路徑
            codec: 影片編碼器
            preset: 編碼品質預設
            subtitle_style: 字幕樣式字串
            video_size: 影片尺寸
            extra_args: 額外的 FFmpeg 參數列表

        返回:
            list: FFmpeg 命令列表
        """
        ffmpeg_cmd = ["ffmpeg", "-y"] + extra_args + [
            "-i", video_path,
            "-c:v", codec,
            "-preset", preset,
            "-c:a", "copy",
            "-vf", f"subtitles='{subtitle_filename}':force_style='{subtitle_style}':original_size={video_size}",
            output_path
        ]
        return ffmpeg_cmd

    def _execute_ffmpeg(self, ffmpeg_cmd, label, cwd):
        """
        執行 FFmpeg 命令並監控進度

        參數:
            ffmpeg_cmd: FFmpeg 命令列表
            label: 處理標籤（用於顯示進度）
            cwd: 工作目錄

        返回:
            tuple: (return_code, stderr) - 返回碼和錯誤輸出
        """
        cmd_str = " ".join(ffmpeg_cmd)
        self.log_to_gui(f"執行命令: {cmd_str}")
        logging.info(f"FFmpeg 命令: {cmd_str}")

        process = subprocess.Popen(
            ffmpeg_cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=cwd
        )

        # 即時顯示 FFmpeg 的處理進度
        stderr_output = []
        while True:
            output_line = process.stderr.readline()
            if output_line == '' and process.poll() is not None:
                break
            if output_line:
                stderr_output.append(output_line)
                logging.info(output_line.strip())
                if "frame=" in output_line or "speed=" in output_line:
                    self.progress_var.set(f"{label}: " + output_line.strip())
                    self.root.update_idletasks()

        return_code = process.poll()
        stderr = ''.join(stderr_output)
        return return_code, stderr

    def _copy_output_file(self, temp_output_path, final_output_path):
        """
        將臨時輸出檔案複製到最終位置

        參數:
            temp_output_path: 臨時輸出檔案路徑
            final_output_path: 最終輸出檔案路徑

        返回:
            bool: 複製是否成功
        """
        if os.path.exists(temp_output_path):
            copy2(temp_output_path, final_output_path)
            self.log_to_gui(f"已將處理後的影片複製到: {final_output_path}")
            return True
        else:
            self.log_to_gui("處理完成但找不到輸出檔案", "ERROR")
            return False

    def process_video(self):
        """處理影片及燒錄字幕（使用編碼策略模式，支援 GPU/CPU 自動回退）"""
        try:
            self.progress_var.set("處理中...")
            self.log_to_gui("開始處理影片", "INFO")
            self.root.update_idletasks()

            # 準備臨時檔案和配置參數
            temp_video_path, temp_subtitle_path, temp_output_path = self.create_temp_files()

            # 收集編碼參數
            gpu_codec = "h264_nvenc" if self.codec_var.get() == "H.264" else "hevc_nvenc"
            cpu_codec = "libx264" if self.codec_var.get() == "H.264" else "libx265"
            preset = self.preset_var.get()

            # 收集字幕樣式參數
            font = self.font_var.get()
            font_size = self.font_size_var.get()
            font_color = self.font_color_var.get()
            border_style = self.BORDER_STYLE_MAP[self.border_style_var.get()]
            pos_x = self.pos_x_var.get()
            pos_y = self.pos_y_var.get()
            margin_v = self.margin_var.get()
            transparency = int(self.transparency_var.get())

            self.log_to_gui(f"編碼器: {self.codec_var.get()}, 品質: {preset}")
            self.log_to_gui(f"字型: {font}, 大小: {font_size}, 顏色: {font_color}")
            self.log_to_gui(f"邊框: {self.border_style_var.get()}, 位置: ({pos_x}, {pos_y}), 邊距: {margin_v}, 透明度: {transparency}%")

            # 計算背景顏色（包含透明度）
            alpha = int((100 - transparency) * 255 / 100)
            back_color = f"&H{alpha:02x}000000"

            # 檢測影片尺寸
            video_size = self._detect_video_size(temp_video_path)

            # 構建字幕樣式
            subtitle_style = self._build_subtitle_style(
                font, font_size, font_color, back_color,
                border_style, pos_x, pos_y, margin_v
            )

            subtitle_filename = os.path.basename(temp_subtitle_path)

            # 定義編碼策略：GPU 優先，CPU 作為回退
            encoding_strategies = [
                {"name": "GPU", "codec": gpu_codec, "extra_args": ["-hwaccel", "cuda"]},
                {"name": "CPU", "codec": cpu_codec, "extra_args": []}
            ]

            # 嘗試各種編碼策略，直到成功
            processing_success = False
            for strategy in encoding_strategies:
                self.log_to_gui(f"嘗試使用 {strategy['name']} 編碼...")

                # 構建 FFmpeg 命令
                ffmpeg_cmd = self._build_ffmpeg_command(
                    temp_video_path, subtitle_filename, temp_output_path,
                    strategy['codec'], preset, subtitle_style, video_size,
                    strategy['extra_args']
                )

                # 執行 FFmpeg（使用 cwd 參數指定工作目錄，避免 os.chdir()）
                return_code, stderr = self._execute_ffmpeg(
                    ffmpeg_cmd,
                    f"{strategy['name']} 處理中",
                    self.temp_dir
                )

                # 檢查執行結果
                if return_code == 0:
                    processing_success = True
                    self.log_to_gui(f"{strategy['name']} 編碼成功", "SUCCESS")
                    break
                else:
                    # 檢查是否為 NVENC 錯誤（僅在 GPU 策略時）
                    if strategy['name'] == "GPU" and ("No NVENC capable devices found" in stderr or "Error initializing" in stderr):
                        self.log_to_gui("NVENC 不可用，切換至 CPU 編碼...", "WARNING")
                        continue
                    else:
                        # 其他錯誤，記錄並繼續嘗試下一個策略
                        self.log_to_gui(f"{strategy['name']} 編碼失敗: {stderr[:200]}", "ERROR")
                        logging.error(f"{strategy['name']} 編碼失敗: {stderr}")

            # 如果所有策略都失敗，拋出異常
            if not processing_success:
                self.cleanup_temp_files()
                raise Exception("所有編碼策略均失敗，請查看日誌以了解詳情")

            # 複製輸出檔案到最終位置
            if self._copy_output_file(temp_output_path, self.output_path.get()):
                success_message = "影片處理成功完成！"
                self.progress_var.set("處理完成！")
                self.log_to_gui(success_message, "SUCCESS")
                logging.info(success_message)
                messagebox.showinfo("成功", success_message)
            else:
                self.cleanup_temp_files()
                raise Exception("處理完成但無法複製輸出檔案")

            # 清理臨時檔案
            self.cleanup_temp_files()

        except Exception as e:
            error_message = f"處理失敗: {str(e)}"
            self.progress_var.set(f"錯誤: {str(e)}")
            self.log_to_gui(error_message, "ERROR")
            logging.error(error_message)
            logging.exception("詳細錯誤堆疊資訊")

            # 確保清理臨時檔案
            self.cleanup_temp_files()

            result = messagebox.askquestion("錯誤", f"{error_message}\n\n是否要開啟詳細日誌檔案？")
            if result == 'yes':
                self.open_log_file()

def main() -> int:
    """啟動 GUI 應用程式。"""
    root = tk.Tk()
    FFmpegSubtitleGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
