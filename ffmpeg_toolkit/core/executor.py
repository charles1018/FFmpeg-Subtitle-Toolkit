"""
FFmpeg 命令執行器模組

此模組提供 FFmpeg 命令的執行、錯誤處理和日誌記錄功能。
完全 UI 獨立，可用於任何需要執行 FFmpeg 的應用程式。
"""

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class FFmpegCommand:
    """FFmpeg 命令封裝"""

    input_files: list[Path]
    output_file: Path
    codec_args: list[str]
    filter_args: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)
    timeout: int = 3600  # 1 小時超時保護


class FFmpegExecutor:
    """
    執行 FFmpeg 命令，提供錯誤處理、日誌記錄和超時保護

    此類別封裝了所有 subprocess 操作，提供乾淨的介面和安全保護機制。
    """

    # 敏感資訊模式（用於錯誤訊息清理）
    SENSITIVE_PATTERNS = [
        re.compile(r"([A-Z]:\\|/)[^\s:]*", re.IGNORECASE),  # 完整路徑
        re.compile(r"\\\\[^\s]*", re.IGNORECASE),  # UNC 路徑
    ]

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化 FFmpeg 執行器

        Args:
            log_callback: 可選的日誌回呼函式，用於記錄執行過程
        """
        self.log_callback = log_callback
        self._current_process: Optional[subprocess.Popen] = None

    def execute(self, command: FFmpegCommand, cwd: Optional[Path] = None) -> tuple[bool, str]:
        """
        執行 FFmpeg 命令

        Args:
            command: FFmpegCommand 物件，包含所有命令參數
            cwd: 可選的工作目錄

        Returns:
            tuple[bool, str]: (成功與否, 訊息或錯誤描述)
        """
        # 建立命令列
        cmd = self._build_command(command)

        # 記錄命令
        cmd_str = " ".join(str(c) for c in cmd)
        self._log(f"執行 FFmpeg 命令: {cmd_str}")

        try:
            # 執行命令並監控進度
            return_code, stderr = self._run_ffmpeg_process(cmd, command.timeout, cwd)

            if return_code == 0:
                return True, "處理完成"
            else:
                # 清理錯誤訊息（移除敏感資訊）
                sanitized_error = self._sanitize_error(stderr)
                return False, sanitized_error

        except TimeoutError as e:
            return False, str(e)
        except Exception as e:
            return False, f"執行錯誤: {str(e)}"

    def _build_command(self, command: FFmpegCommand) -> list[str]:
        """
        建立 FFmpeg 命令列參數

        Args:
            command: FFmpegCommand 物件

        Returns:
            list[str]: 完整的命令列參數列表
        """
        cmd = ["ffmpeg"]

        # 新增輸入檔案
        for input_file in command.input_files:
            cmd.extend(["-i", str(input_file)])

        # 新增額外參數（如 -hwaccel cuda）
        if command.extra_args:
            cmd.extend(command.extra_args)

        # 新增編碼器參數
        cmd.extend(command.codec_args)

        # 新增濾鏡參數
        if command.filter_args:
            cmd.extend(["-vf", ",".join(command.filter_args)])

        # 音訊複製（不重新編碼）
        cmd.extend(["-c:a", "copy"])

        # 輸出檔案
        cmd.extend(["-y", str(command.output_file)])  # -y 覆寫現有檔案

        return cmd

    def _run_ffmpeg_process(
        self, cmd: list[str], timeout: int, cwd: Optional[Path]
    ) -> tuple[int, str]:
        """
        執行 FFmpeg 程序並監控進度

        Args:
            cmd: 命令列參數
            timeout: 超時時間（秒）
            cwd: 工作目錄

        Returns:
            tuple[int, str]: (返回碼, stderr 輸出)

        Raises:
            TimeoutError: 當執行超過指定時間
        """
        self._current_process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd) if cwd else None,
        )

        start_time = time.time()
        stderr_output = []

        try:
            while True:
                # 檢查是否超時
                if time.time() - start_time > timeout:
                    self._log(f"FFmpeg 處理超時（{timeout}秒），已終止")
                    raise TimeoutError(f"FFmpeg 處理超過 {timeout} 秒，已自動終止")

                # 讀取 stderr 輸出（FFmpeg 的進度資訊在 stderr）
                output_line = self._current_process.stderr.readline()
                if output_line == "" and self._current_process.poll() is not None:
                    break

                if output_line:
                    stderr_output.append(output_line)
                    # 記錄包含 frame= 或 speed= 的進度行
                    if "frame=" in output_line or "speed=" in output_line:
                        self._log(output_line.strip())

        except Exception:
            # 發生錯誤時終止程序
            if self._current_process:
                self._current_process.kill()
                self._current_process.wait()
            raise

        # 儲存返回碼（在重置 _current_process 之前）
        return_code = self._current_process.poll()
        stderr = "".join(stderr_output)

        # 清理
        self._current_process = None

        return return_code, stderr

    def _sanitize_error(self, error_message: str) -> str:
        """
        清理錯誤訊息，移除敏感資訊（如完整路徑）

        Args:
            error_message: 原始錯誤訊息

        Returns:
            str: 清理後的錯誤訊息
        """
        sanitized = error_message

        # 移除完整路徑，只保留檔案名稱
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = pattern.sub("[PATH]", sanitized)

        # 限制錯誤訊息長度（取前 500 個字元）
        if len(sanitized) > 500:
            sanitized = sanitized[:500] + "... (詳細資訊請查看日誌檔案)"

        return sanitized

    def _log(self, message: str):
        """
        透過回呼函式記錄訊息

        Args:
            message: 要記錄的訊息
        """
        if self.log_callback:
            self.log_callback(message)
