import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext, colorchooser
import subprocess
import os
import threading
import re
import logging
import tempfile
import shutil
from datetime import datetime

# 導入字幕預覽模組
from subtitle_preview import SubtitlePreviewModule

class FFmpegSubtitleGUI:
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
        
        # 初始化字幕預覽模組
        self.preview_module = SubtitlePreviewModule(
            self.root,
            self.video_path,
            self.subtitle_path,
            self.font_var,
            self.font_size_var,
            self.font_color_var,
            self.border_style_var,
            self.pos_x_var,
            self.pos_y_var,
            self.transparency_var,
            self.margin_var,
            self.log_to_gui
        )
        
        # 添加預覽按鈕
        if hasattr(self, 'subtitle_frame'):
            try:
                preview_button = self.preview_module.create_preview_button(self.subtitle_frame)
                preview_button.grid(row=7, column=1, sticky=tk.W, pady=10)
            except Exception as e:
                self.log_to_gui(f"無法創建預覽按鈕: {str(e)}", "WARNING")
        
    def setup_logging(self):
        """初始化日誌系統"""
        log_dir = os.path.join(os.path.expanduser("~"), "FFmpegGUI_Logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"ffmpeg_gui_{current_time}.log")
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='w'
        )
        
        self.log_file = log_file
        logging.info("日誌系統初始化完成")
    
    def check_ffmpeg(self):
        """檢查系統中是否已安裝並可用 ffmpeg"""
        try:
            logging.info("檢查 ffmpeg 是否已安裝")
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True,
                shell=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                error_msg = "無法找到系統中的 ffmpeg，請確認已安裝並設定環境變數"
                logging.error(error_msg)
                messagebox.showerror("錯誤", error_msg)
                return False
            
            ffmpeg_version = result.stdout.split('\n')[0]
            logging.info(f"檢測到 ffmpeg: {ffmpeg_version}")
            return True
            
        except Exception as e:
            error_msg = f"檢查 ffmpeg 時發生錯誤: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("錯誤", error_msg)
            return False
    
    def create_widgets(self):
        """建立 GUI 的元件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        file_frame = ttk.LabelFrame(main_frame, text="檔案選擇", padding="10")
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
        
        video_frame = ttk.LabelFrame(main_frame, text="影片參數", padding="10")
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
        
        subtitle_frame = ttk.LabelFrame(main_frame, text="字幕設定", padding="10")
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
                                 values=["&HFFFFFF", "&H000000", "&HFF0000", "&H00FF00", "&H0000FF"],  # 白、黑、紅、綠、藍
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
        
        # 儲存字幕框架供後續使用
        self.subtitle_frame = subtitle_frame
        
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        status_frame = ttk.LabelFrame(main_frame, text="處理狀態", padding="10")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(status_frame, textvariable=self.progress_var).pack(fill=tk.X)
        
        log_frame = ttk.LabelFrame(main_frame, text="詳細日誌", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_display.pack(fill=tk.BOTH, expand=True)
        self.log_display.config(state=tk.DISABLED)
        
        ttk.Button(log_frame, text="開啟日誌檔案", command=self.open_log_file).pack(pady=5)
        
        ttk.Button(action_frame, text="開始處理", command=self.start_processing, style="Accent.TButton").pack(pady=10)
        
        self.configure_styles()
    
    def configure_styles(self):
        """設定自訂的樣式"""
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 12, "bold"))
    
    def open_log_file(self):
        """開啟日誌檔案"""
        if hasattr(self, 'log_file') and os.path.exists(self.log_file):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.log_file)
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.run(['open', self.log_file], check=False)
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
                dirname = os.path.dirname(filepath)
                basename = os.path.basename(filepath)
                name, ext = os.path.splitext(basename)
                output_name = os.path.join(dirname, f"{name}_output.mp4")
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
            shutil.copy2(self.video_path.get(), temp_video_path)
            self.log_to_gui(f"複製影片到臨時目錄: {temp_video_path}")
            
            # 複製字幕檔案到臨時目錄
            subtitle_ext = os.path.splitext(self.subtitle_path.get())[1]
            temp_subtitle_path = os.path.join(self.temp_dir, f"subtitle{subtitle_ext}")
            shutil.copy2(self.subtitle_path.get(), temp_subtitle_path)
            self.log_to_gui(f"複製字幕到臨時目錄: {temp_subtitle_path}")
            
            # 設定臨時輸出路徑
            temp_output_path = os.path.join(self.temp_dir, "output.mp4")
            
            return temp_video_path, temp_subtitle_path, temp_output_path
            
        except Exception as e:
            self.log_to_gui(f"建立臨時檔案時發生錯誤: {str(e)}", "ERROR")
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            raise
    
    def cleanup_temp_files(self):
        """清理臨時檔案和目錄"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.log_to_gui("臨時檔案已清理")
            except Exception as e:
                self.log_to_gui(f"清理臨時檔案時發生錯誤: {str(e)}", "WARNING")
    
    def custom_color(self):
        """開啟自定義字體顏色的選擇器"""
        color = colorchooser.askcolor(title="選擇字體顏色")
        if color[1]:  # 如果有選擇顏色
            r, g, b = map(int, color[0])
            ass_color = f"&H{b:02x}{g:02x}{r:02x}"
            self.font_color_var.set(ass_color)
            self.log_to_gui(f"自定義字體顏色: {ass_color}")
    
    def process_video(self):
        """處理影片及燒錄字幕"""
        try:
            self.progress_var.set("處理中...")
            self.log_to_gui("開始處理影片", "INFO")
            self.root.update_idletasks()
            
            # 建立臨時檔案以避免路徑中的特殊字元問題
            temp_video_path, temp_subtitle_path, temp_output_path = self.create_temp_files()
            
            codec = "h264_nvenc" if self.codec_var.get() == "H.264" else "hevc_nvenc"
            preset = self.preset_var.get()
            font = self.font_var.get()
            font_size = self.font_size_var.get()
            font_color = self.font_color_var.get()
            border_style_map = {"無邊框": 0, "普通邊框": 1, "陰影": 4, "半透明背景": 3}
            border_style = border_style_map[self.border_style_var.get()]
            pos_x = self.pos_x_var.get()
            pos_y = self.pos_y_var.get()
            margin_v = self.margin_var.get()
            transparency = int(self.transparency_var.get())  # 透明度百分比
            
            self.log_to_gui(f"編碼: {codec}, 品質: {preset}")
            self.log_to_gui(f"字型: {font}, 大小: {font_size}, 顏色: {font_color}")
            self.log_to_gui(f"邊框樣式: {self.border_style_var.get()}, 位置: ({pos_x}, {pos_y}), 邊距: {margin_v}, 透明度: {transparency}%")
            
            alpha = int((100 - transparency) * 255 / 100)
            alpha_hex = f"{alpha:02x}"
            back_color = f"&H{alpha_hex}000000"
            
            video_info_cmd = ["ffmpeg", "-i", temp_video_path, "-hide_banner"]
            video_info_process = subprocess.Popen(
                video_info_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace'
            )
            _, video_info = video_info_process.communicate()
            
            # 從資訊中提取影片尺寸
            size_match = re.search(r'(\d{2,4})x(\d{2,4})', video_info)
            video_size = size_match.group(0) if size_match else "1920x1080"
            self.log_to_gui(f"檢測到影片尺寸: {video_size}")
            
            subtitle_style = (
                f"Fontname={font},Fontsize={font_size},PrimaryColour={font_color},"
                f"BackColour={back_color},BorderStyle={border_style},Outline=1,"
                f"MarginV={margin_v + pos_y if pos_y >= 0 else margin_v},"
                f"MarginL={pos_x if pos_x > 0 else 0},MarginR={-pos_x if pos_x < 0 else 0},"
                f"Alignment=2"
            )
            
            # 建構 FFmpeg 命令，使用列表避免引號和轉義問題
            subtitle_filename = os.path.basename(temp_subtitle_path)
            
            # 使用絕對路徑，避免使用 cd 切換目錄
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-hwaccel", "cuda",
                "-i", temp_video_path,
                "-c:v", codec,
                "-preset", preset,
                "-c:a", "copy",
                "-vf", f"subtitles='{subtitle_filename}':force_style='{subtitle_style}':original_size={video_size}",
                temp_output_path
            ]
            
            cmd_str = " ".join(ffmpeg_cmd)
            self.log_to_gui(f"執行命令: {cmd_str}")
            logging.info(f"FFmpeg 命令: {cmd_str}")
            
            # 修改當前工作目錄為臨時目錄
            cwd = os.getcwd()  # 儲存當前工作目錄
            os.chdir(self.temp_dir)  # 切換到臨時目錄
            
            try:
                process = subprocess.Popen(
                    ffmpeg_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace'
                )
                
                # 即時顯示 FFmpeg 的處理進度
                while True:
                    output_line = process.stderr.readline()
                    if output_line == '' and process.poll() is not None:
                        break
                    if output_line:
                        logging.info(output_line.strip())
                        if "frame=" in output_line or "speed=" in output_line:
                            self.progress_var.set("處理中: " + output_line.strip())
                            self.root.update_idletasks()
                
                return_code = process.poll()
                
                if return_code != 0:
                    stderr = process.stderr.read() if process.stderr else ""
                    error_detected = False
                    
                    # 檢查是否有 NVENC 錯誤，若有則嘗試使用 CPU 編碼
                    if "No NVENC capable devices found" in stderr or "Error initializing" in stderr:
                        self.log_to_gui("NVENC 不可用，切換至 CPU 編碼...", "WARNING")
                        self.progress_var.set("NVENC 不可用，切換至 CPU 編碼...")
                        self.root.update_idletasks()
                        
                        cpu_codec = "libx264" if self.codec_var.get() == "H.264" else "libx265"
                        cpu_cmd = [
                            "ffmpeg", "-y",
                            "-i", temp_video_path,
                            "-c:v", cpu_codec,
                            "-preset", preset,
                            "-c:a", "copy",
                            "-vf", f"subtitles='{subtitle_filename}':force_style='{subtitle_style}':original_size={video_size}",
                            temp_output_path
                        ]
                        
                        cpu_cmd_str = " ".join(cpu_cmd)
                        self.log_to_gui(f"使用 CPU 編碼，命令: {cpu_cmd_str}")
                        logging.info(f"使用 CPU 編碼，FFmpeg 命令: {cpu_cmd_str}")
                        
                        process = subprocess.Popen(
                            cpu_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True, encoding='utf-8', errors='replace'
                        )
                        
                        while True:
                            output_line = process.stderr.readline()
                            if output_line == '' and process.poll() is not None:
                                break
                            if output_line:
                                logging.info(output_line.strip())
                                if "frame=" in output_line or "speed=" in output_line:
                                    self.progress_var.set("CPU 處理中: " + output_line.strip())
                                    self.root.update_idletasks()
                        
                        cpu_return_code = process.poll()
                        
                        if cpu_return_code != 0:
                            cpu_stderr = process.stderr.read() if process.stderr else ""
                            error_message = f"CPU 處理失敗: {cpu_stderr}"
                            self.log_to_gui(error_message, "ERROR")
                            logging.error(error_message)
                            error_detected = True
                    else:
                        error_message = f"處理失敗: {stderr}"
                        self.log_to_gui(error_message, "ERROR")
                        logging.error(error_message)
                        error_detected = True
                    
                    if error_detected:
                        os.chdir(cwd)  # 恢復原始工作目錄
                        self.cleanup_temp_files()
                        raise Exception("處理過程中發生錯誤，請查看日誌以了解詳情")
            
            finally:
                os.chdir(cwd)  # 確保恢復原始工作目錄
            
            # 將最終輸出檔案複製到使用者指定的位置
            if os.path.exists(temp_output_path):
                shutil.copy2(temp_output_path, self.output_path.get())
                self.log_to_gui(f"已將處理後的影片複製到: {self.output_path.get()}")
                
                success_message = "影片處理成功完成！"
                self.progress_var.set("處理完成！")
                self.log_to_gui(success_message, "SUCCESS")
                logging.info(success_message)
                messagebox.showinfo("成功", success_message)
            else:
                error_message = "處理完成但找不到輸出檔案"
                self.progress_var.set(error_message)
                self.log_to_gui(error_message, "ERROR")
                logging.error(error_message)
                messagebox.showerror("錯誤", error_message)
            
            # 清理臨時檔案
            self.cleanup_temp_files()
            
        except Exception as e:
            error_message = f"處理失敗: {str(e)}"
            self.progress_var.set(f"錯誤: {str(e)}")
            self.log_to_gui(error_message, "ERROR")
            logging.error(error_message)
            logging.exception("詳細錯誤堆疊資訊")
            
            # 清理臨時檔案
            self.cleanup_temp_files()
            
            result = messagebox.askquestion("錯誤", f"{error_message}\n\n是否要開啟詳細日誌檔案？")
            if result == 'yes':
                self.open_log_file()

if __name__ == "__main__":
    root = tk.Tk()
    app = FFmpegSubtitleGUI(root)
    root.mainloop()