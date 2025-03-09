import tkinter as tk
from tkinter import ttk, Frame, Toplevel
try:
    import vlc
except ImportError:
    # 先不引發錯誤，讓模組能夠載入
    pass
import os
import tempfile
import shutil
import subprocess
import threading
import time
import logging
from datetime import datetime

class SubtitlePreviewModule:
    """字幕預覽模組：提供即時預覽字幕效果的功能"""
    
    def __init__(self, parent, video_path_var, subtitle_path_var, font_var, font_size_var, 
                font_color_var, border_style_var, pos_x_var, pos_y_var, 
                transparency_var, margin_var, log_callback=None):
        """
        初始化字幕預覽模組
        
        參數:
            parent: 父視窗
            video_path_var: 影片路徑變數
            subtitle_path_var: 字幕路徑變數
            font_var: 字型變數
            font_size_var: 字型大小變數
            font_color_var: 字型顏色變數
            border_style_var: 邊框樣式變數
            pos_x_var: X座標變數
            pos_y_var: Y座標變數
            transparency_var: 透明度變數
            margin_var: 邊距變數
            log_callback: 日誌回調函數
        """
        self.parent = parent
        self.video_path_var = video_path_var
        self.subtitle_path_var = subtitle_path_var
        self.font_var = font_var
        self.font_size_var = font_size_var
        self.font_color_var = font_color_var
        self.border_style_var = border_style_var
        self.pos_x_var = pos_x_var
        self.pos_y_var = pos_y_var
        self.transparency_var = transparency_var
        self.margin_var = margin_var
        self.log_callback = log_callback
        
        # VLC 實例和播放器
        self.instance = None
        self.player = None
        self.preview_window = None
        self.temp_dir = None
        self.temp_video_path = None
        self.is_previewing = False
        self.preview_thread = None
    
    def _check_vlc(self):
        """檢查系統是否已安裝 VLC"""
        try:
            import vlc
            if self.log_callback:
                self.log_callback("VLC Python 綁定可用", "INFO")
            return True
        except ImportError:
            if self.log_callback:
                self.log_callback("無法載入 VLC Python 綁定，請確認已安裝 python-vlc 套件", "ERROR")
            else:
                print("錯誤: 無法載入 VLC Python 綁定，請確認已安裝 python-vlc 套件")
            return False
    
    def create_preview_button(self, container):
        """
        創建預覽按鈕
        
        參數:
            container: 放置按鈕的容器
        """
        preview_button = ttk.Button(
            container, 
            text="預覽字幕效果", 
            command=self.show_preview
        )
        return preview_button
    
    def show_preview(self):
        """顯示預覽視窗"""
        # 確保已初始化VLC檢查
        if not hasattr(self, 'vlc_checked'):
            self.vlc_checked = self._check_vlc()
            if not self.vlc_checked:
                if self.log_callback:
                    self.log_callback("無法啟用預覽功能：需要安裝VLC和python-vlc", "ERROR")
                else:
                    print("無法啟用預覽功能：需要安裝VLC和python-vlc")
                messagebox = tk.messagebox
                messagebox.showerror("錯誤", "無法啟用預覽功能：需要安裝VLC和python-vlc")
                return
                
        if not self.video_path_var.get() or not self.subtitle_path_var.get():
            msg = "請先選擇影片和字幕檔案"
            if self.log_callback:
                self.log_callback(msg, "ERROR")
            messagebox = tk.messagebox
            messagebox.showerror("錯誤", msg)
            return
        
        if not os.path.exists(self.video_path_var.get()):
            msg = "影片檔案不存在"
            if self.log_callback:
                self.log_callback(msg, "ERROR")
            messagebox = tk.messagebox
            messagebox.showerror("錯誤", msg)
            return
            
        if not os.path.exists(self.subtitle_path_var.get()):
            msg = "字幕檔案不存在"
            if self.log_callback:
                self.log_callback(msg, "ERROR")
            messagebox = tk.messagebox
            messagebox.showerror("錯誤", msg)
            return
        
        if self.is_previewing:
            if self.log_callback:
                self.log_callback("預覽已在進行中", "WARNING")
            if self.preview_window:
                self.preview_window.lift()  # 將視窗提到前面
            return
        
        if self.log_callback:
            self.log_callback("開始準備預覽...", "INFO")
        self.is_previewing = True
        
        # 使用執行緒來處理預覽，避免凍結主介面
        self.preview_thread = threading.Thread(target=self._prepare_preview)
        self.preview_thread.daemon = True
        self.preview_thread.start()
    
    def _prepare_preview(self):
        """準備預覽所需的臨時影片"""
        try:
            if self.log_callback:
                self.log_callback("正在製作預覽影片...", "INFO")
            
            # 建立臨時目錄
            self.temp_dir = tempfile.mkdtemp(prefix="subtitle_preview_")
            if self.log_callback:
                self.log_callback(f"建立臨時目錄: {self.temp_dir}", "INFO")
            
            # 提取前 30 秒的影片以加快預覽速度
            self._create_preview_video()
            
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"預覽準備失敗: {str(e)}", "ERROR")
            self.cleanup()
    
    def _create_preview_video(self):
        """從原始影片創建預覽用的臨時影片（提取前30秒並添加字幕）"""
        try:
            # 複製字幕檔案到臨時目錄
            subtitle_ext = os.path.splitext(self.subtitle_path_var.get())[1]
            temp_subtitle_path = os.path.join(self.temp_dir, f"subtitle{subtitle_ext}")
            shutil.copy2(self.subtitle_path_var.get(), temp_subtitle_path)
            
            # 提取前 30 秒的影片
            video_ext = os.path.splitext(self.video_path_var.get())[1]
            temp_video_input = os.path.join(self.temp_dir, f"input{video_ext}")
            self.temp_video_path = os.path.join(self.temp_dir, "preview.mp4")
            
            # 將原始影片複製到臨時目錄
            shutil.copy2(self.video_path_var.get(), temp_video_input)
            
            # 提取影片時長
            duration_cmd = ["ffmpeg", "-i", temp_video_input, "-hide_banner"]
            duration_process = subprocess.Popen(
                duration_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace'
            )
            _, video_info = duration_process.communicate()
            
            import re
            # 從輸出中提取影片長度
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})', video_info)
            if duration_match:
                hours, minutes, seconds = map(int, duration_match.groups())
                total_seconds = hours * 3600 + minutes * 60 + seconds
                # 設定預覽長度為 30 秒或影片長度，取較小值
                preview_seconds = min(30, total_seconds)
            else:
                preview_seconds = 30
                
            if self.log_callback:
                self.log_callback(f"提取前 {preview_seconds} 秒影片用於預覽", "INFO")
            
            # 設定字幕樣式
            font = self.font_var.get()
            font_size = self.font_size_var.get()
            font_color = self.font_color_var.get()
            border_style_map = {"無邊框": 0, "普通邊框": 1, "陰影": 4, "半透明背景": 3}
            border_style = border_style_map[self.border_style_var.get()]
            pos_x = self.pos_x_var.get()
            pos_y = self.pos_y_var.get()
            margin_v = self.margin_var.get()
            transparency = int(self.transparency_var.get())
            
            # 計算透明度的十六進制值
            alpha = int((100 - transparency) * 255 / 100)
            alpha_hex = f"{alpha:02x}"
            back_color = f"&H{alpha_hex}000000"
            
            # 獲取影片尺寸
            size_match = re.search(r'(\d{2,4})x(\d{2,4})', video_info)
            video_size = size_match.group(0) if size_match else "1920x1080"
            
            # 設定字幕樣式
            subtitle_style = (
                f"Fontname={font},Fontsize={font_size},PrimaryColour={font_color},"
                f"BackColour={back_color},BorderStyle={border_style},Outline=1,"
                f"MarginV={margin_v + pos_y if pos_y >= 0 else margin_v},"
                f"MarginL={pos_x if pos_x > 0 else 0},MarginR={-pos_x if pos_x < 0 else 0},"
                f"Alignment=2"
            )
            
            # 使用 FFmpeg 提取影片並加入字幕
            subtitle_filename = os.path.basename(temp_subtitle_path)
            
            # 準備 FFmpeg 命令，用於創建預覽影片
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-ss", "0",
                "-t", str(preview_seconds),
                "-i", temp_video_input,
                "-c:v", "libx264",
                "-preset", "ultrafast",  # 使用最快速度的編碼，提高預覽生成速度
                "-c:a", "aac",
                "-vf", f"subtitles='{subtitle_filename}':force_style='{subtitle_style}':original_size={video_size}",
                self.temp_video_path
            ]
            
            cmd_str = " ".join(ffmpeg_cmd)
            if self.log_callback:
                self.log_callback(f"執行預覽命令: {cmd_str}", "INFO")
            
            # 保存當前工作目錄
            cwd = os.getcwd()
            # 切換到臨時目錄
            os.chdir(self.temp_dir)
            
            try:
                process = subprocess.Popen(
                    ffmpeg_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace'
                )
                
                # 等待處理完成
                while True:
                    output_line = process.stderr.readline()
                    if output_line == '' and process.poll() is not None:
                        break
                    if output_line and "time=" in output_line and self.log_callback:
                        self.log_callback(f"預覽製作中: {output_line.strip()}", "INFO")
                
                if process.returncode != 0:
                    stderr = process.stderr.read()
                    if self.log_callback:
                        self.log_callback(f"預覽影片製作失敗: {stderr}", "ERROR")
                    os.chdir(cwd)
                    self.cleanup()
                    self.is_previewing = False
                    return
                
                if self.log_callback:
                    self.log_callback("預覽影片製作完成", "SUCCESS")
                
                # 創建預覽窗口
                self.parent.after(0, self._create_preview_window)
                
            finally:
                os.chdir(cwd)  # 恢復工作目錄
                
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"預覽影片製作時發生錯誤: {str(e)}", "ERROR")
            self.cleanup()
            self.is_previewing = False
    
    def _create_preview_window(self):
        """創建預覽視窗並播放影片"""
        if not os.path.exists(self.temp_video_path):
            if self.log_callback:
                self.log_callback("預覽影片不存在", "ERROR")
            self.cleanup()
            self.is_previewing = False
            return
        
        try:
            # 創建預覽視窗
            self.preview_window = Toplevel(self.parent)
            self.preview_window.title("字幕效果預覽")
            self.preview_window.geometry("800x600")
            self.preview_window.protocol("WM_DELETE_WINDOW", self.close_preview)
            
            # 創建 VLC 實例和播放器容器
            frame = Frame(self.preview_window, bg="black")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # 获取播放窗口的 ID (Windows 跟 Linux 不同)
            if os.name == "nt":  # Windows
                frame.update()
                player_widget_id = str(int(frame.winfo_id()))
            else:  # Linux
                frame.update()
                player_widget_id = frame.winfo_id()
            
            # 初始化 VLC 實例和播放器
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()
            self.player.set_hwnd(player_widget_id)
            
            # 添加控制按鈕
            control_frame = Frame(self.preview_window)
            control_frame.pack(fill=tk.X, padx=10, pady=5)
            
            play_button = ttk.Button(control_frame, text="播放", command=self.play_preview)
            play_button.pack(side=tk.LEFT, padx=5)
            
            pause_button = ttk.Button(control_frame, text="暫停", command=self.pause_preview)
            pause_button.pack(side=tk.LEFT, padx=5)
            
            stop_button = ttk.Button(control_frame, text="停止", command=self.stop_preview)
            stop_button.pack(side=tk.LEFT, padx=5)
            
            restart_button = ttk.Button(control_frame, text="重新製作預覽", command=self.restart_preview)
            restart_button.pack(side=tk.RIGHT, padx=5)
            
            # 設置影片來源
            media = self.instance.media_new(self.temp_video_path)
            self.player.set_media(media)
            
            # 自動播放
            self.play_preview()
            
            if self.log_callback:
                self.log_callback("預覽視窗已開啟", "SUCCESS")
            
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"創建預覽視窗時發生錯誤: {str(e)}", "ERROR")
            self.cleanup()
    
    def play_preview(self):
        """播放預覽影片"""
        if self.player:
            self.player.play()
    
    def pause_preview(self):
        """暫停預覽"""
        if self.player:
            self.player.pause()
    
    def stop_preview(self):
        """停止預覽"""
        if self.player:
            self.player.stop()
    
    def restart_preview(self):
        """重新製作預覽"""
        self.close_preview()
        self.show_preview()
    
    def close_preview(self):
        """關閉預覽"""
        if self.player:
            self.player.stop()
        
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
        
        self.cleanup()
        self.is_previewing = False
        if self.log_callback:
            self.log_callback("預覽已關閉", "INFO")
    
    def cleanup(self):
        """清理臨時文件"""
        try:
            if self.player:
                self.player.stop()
                self.player.release()
                self.player = None
            
            if self.instance:
                self.instance.release()
                self.instance = None
            
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir = None
                if self.log_callback:
                    self.log_callback("臨時預覽檔案已清理", "INFO")
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"清理預覽時發生錯誤: {str(e)}", "WARNING")
