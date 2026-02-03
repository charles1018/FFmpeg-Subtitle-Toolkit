"""
編碼策略模組

此模組管理 GPU/CPU 編碼策略和自動回退邏輯。
支援 NVENC GPU 編碼，並在不可用時自動回退至 CPU 編碼。
"""

import re
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

    def __init__(self):
        """初始化編碼策略"""
        # 編譯錯誤模式正則表達式（提升效能）
        self._error_regex = re.compile("|".join(self.NVENC_ERROR_PATTERNS), re.IGNORECASE)

    def get_codecs(self, preferred: str) -> Iterator[str]:
        """
        返回編碼器列表（含回退策略）

        根據偏好的編碼器，返回 GPU 優先、CPU 回退的編碼器列表。

        Args:
            preferred: 偏好的編碼器名稱
                      - "libx264": H.264 CPU 編碼器
                      - "libx265": H.265 CPU 編碼器
                      - "h264_nvenc": H.264 NVENC GPU 編碼器
                      - "hevc_nvenc": H.265 NVENC GPU 編碼器

        Yields:
            str: 編碼器名稱（GPU 優先，CPU 回退）

        Examples:
            >>> strategy = EncodingStrategy()
            >>> list(strategy.get_codecs("libx264"))
            ['h264_nvenc', 'libx264']
            >>> list(strategy.get_codecs("libx265"))
            ['hevc_nvenc', 'libx265']
        """
        if preferred == "libx264":
            yield "h264_nvenc"  # 先嘗試 GPU
            yield "libx264"  # 回退至 CPU
        elif preferred == "libx265":
            yield "hevc_nvenc"
            yield "libx265"
        elif preferred == "h264_nvenc":
            yield "h264_nvenc"
            yield "libx264"  # 回退選項
        elif preferred == "hevc_nvenc":
            yield "hevc_nvenc"
            yield "libx265"
        else:
            # 未知編碼器，直接返回（不提供回退）
            yield preferred

    def should_fallback(self, error_message: str) -> bool:
        """
        檢查錯誤訊息是否為 NVENC 失敗（需要回退至 CPU）

        Args:
            error_message: FFmpeg 錯誤訊息

        Returns:
            bool: 如果是 NVENC 錯誤則返回 True，否則返回 False

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
