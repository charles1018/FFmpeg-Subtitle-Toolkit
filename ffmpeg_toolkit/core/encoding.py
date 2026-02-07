"""
編碼策略模組

此模組管理 GPU/CPU 編碼策略和自動回退邏輯。
支援 NVENC GPU 編碼，並在不可用時自動回退至 CPU 編碼。
"""

import re
import subprocess
from typing import Iterator


class EncodingStrategy:
    """
    管理 GPU/CPU 編碼策略和回退邏輯

    此類別提供編碼器選擇策略（GPU 優先，CPU 回退）
    並檢測 NVENC 相關錯誤以觸發自動回退。
    """

    # NVENC 錯誤檢測模式（正則表達式）
    NVENC_ERROR_PATTERNS = [
        r"Cannot load.*nvEncodeAPI",
        r"No NVENC capable devices found",
        r"Invalid encoder",
        r"Unknown encoder.*nvenc",
        r"Impossible to convert between the formats",
        r"Error initializing",
        r"nvenc.*not available",
    ]

    # QSV 錯誤檢測模式（正則表達式）
    QSV_ERROR_PATTERNS = [
        r"Error initializing an MFX session",
        r"Error during initialization.*qsv",
        r"Selected driver.*not available",
        r"Unknown encoder.*qsv",
        r"qsv.*not available",
    ]

    # 支援的硬體加速器定義
    HW_ACCELERATORS = {
        "nvenc": {"label": "NVIDIA NVENC", "h264": "h264_nvenc", "hevc": "hevc_nvenc"},
        "qsv": {"label": "Intel QSV", "h264": "h264_qsv", "hevc": "hevc_qsv"},
    }

    def __init__(self):
        """初始化編碼策略"""
        # 編譯錯誤模式正則表達式（結合 NVENC 和 QSV 模式）
        all_patterns = self.NVENC_ERROR_PATTERNS + self.QSV_ERROR_PATTERNS
        self._error_regex = re.compile("|".join(all_patterns), re.IGNORECASE)
        # 可用編碼器快取
        self._available_encoders: set[str] | None = None

    def get_codecs(self, preferred: str, hw_accel: str = "auto") -> Iterator[str]:
        """
        返回編碼器列表（含回退策略）

        Args:
            preferred: 偏好的 CPU 編碼器 ("libx264" 或 "libx265")
            hw_accel: 硬體加速模式 ("auto"/"nvenc"/"qsv"/"cpu")

        Yields:
            str: 編碼器名稱
        """
        is_h265 = preferred in ("libx265", "hevc_nvenc", "hevc_qsv")
        cpu_codec = "libx265" if is_h265 else "libx264"
        codec_key = "hevc" if is_h265 else "h264"

        # 未知編碼器（非 h264/h265 系列），直接返回
        known_codecs = {"libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv"}
        if preferred not in known_codecs:
            yield preferred
            return

        if hw_accel == "cpu":
            yield cpu_codec
        elif hw_accel in self.HW_ACCELERATORS:
            yield self.HW_ACCELERATORS[hw_accel][codec_key]
            yield cpu_codec
        else:
            # auto: 預設用 NVENC（向後相容）
            nvenc_info = self.HW_ACCELERATORS["nvenc"]
            yield nvenc_info[codec_key]
            yield cpu_codec

    def should_fallback(self, error_message: str) -> bool:
        """
        檢查錯誤訊息是否為 GPU 編碼失敗（需要回退至 CPU）

        Args:
            error_message: FFmpeg 錯誤訊息

        Returns:
            bool: 如果是 GPU 編碼錯誤則返回 True，否則返回 False

        Examples:
            >>> strategy = EncodingStrategy()
            >>> strategy.should_fallback("Cannot load nvEncodeAPI")
            True
            >>> strategy.should_fallback("No NVENC capable devices found")
            True
            >>> strategy.should_fallback("Disk full")
            False
        """
        return bool(self._error_regex.search(error_message))

    def detect_available_encoders(self) -> set[str]:
        """
        偵測系統可用的硬體編碼器

        執行 ffmpeg -encoders 並解析輸出，找出可用的 GPU 編碼器。
        結果會被快取，避免重複執行。

        Returns:
            set[str]: 可用的硬體編碼器名稱集合
        """
        if self._available_encoders is not None:
            return self._available_encoders

        hw_encoder_names = set()
        for accel_info in self.HW_ACCELERATORS.values():
            hw_encoder_names.add(accel_info["h264"])
            hw_encoder_names.add(accel_info["hevc"])

        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders", "-hide_banner"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            found = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                for encoder_name in hw_encoder_names:
                    if encoder_name in line.split():
                        found.add(encoder_name)
            self._available_encoders = found
        except Exception:
            self._available_encoders = set()

        return self._available_encoders

    def get_available_hw_accelerators(self) -> list[tuple[str, str]]:
        """
        取得系統可用的硬體加速器列表

        Returns:
            list[tuple[str, str]]: (標籤, 加速器 ID) 的列表
        """
        available = self.detect_available_encoders()
        result = []
        for accel_id, accel_info in self.HW_ACCELERATORS.items():
            if accel_info["h264"] in available or accel_info["hevc"] in available:
                result.append((accel_info["label"], accel_id))
        return result
