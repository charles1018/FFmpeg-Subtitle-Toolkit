"""
路徑驗證模組

此模組提供路徑驗證和安全檢查功能，
防止路徑遍歷攻擊和無效路徑操作。
"""

import os
from pathlib import Path
from typing import Optional


class PathValidator:
    """
    路徑驗證器

    提供路徑驗證和安全檢查功能，確保路徑操作的安全性。
    """

    @staticmethod
    def validate_file_exists(file_path: str | Path, file_type: str = "檔案") -> bool:
        """
        驗證檔案是否存在

        Args:
            file_path: 檔案路徑
            file_type: 檔案類型描述（用於錯誤訊息）

        Returns:
            bool: 檔案存在返回 True，否則返回 False

        Examples:
            >>> validator = PathValidator()
            >>> validator.validate_file_exists("/path/to/video.mp4", "影片")
            True
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path
        return path.exists() and path.is_file()

    @staticmethod
    def validate_path_safe(file_path: str | Path, base_dir: Optional[Path] = None) -> bool:
        """
        驗證路徑是否安全（防止路徑遍歷攻擊）

        檢查路徑是否包含可能的路徑遍歷模式（如 ../）

        Args:
            file_path: 要驗證的路徑
            base_dir: 可選的基礎目錄（路徑必須在此目錄內）

        Returns:
            bool: 路徑安全返回 True，否則返回 False

        Examples:
            >>> validator = PathValidator()
            >>> validator.validate_path_safe("/tmp/safe.txt")
            True
            >>> validator.validate_path_safe("../../etc/passwd")
            False
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path

        try:
            # 解析為絕對路徑
            resolved_path = path.resolve()

            # 檢查是否包含路徑遍歷模式
            if ".." in str(file_path):
                return False

            # 如果指定了基礎目錄，檢查路徑是否在基礎目錄內
            if base_dir is not None:
                base_resolved = base_dir.resolve()
                if not str(resolved_path).startswith(str(base_resolved)):
                    return False

            return True

        except (ValueError, OSError):
            return False

    @staticmethod
    def validate_output_writable(output_path: str | Path) -> bool:
        """
        驗證輸出路徑是否可寫入

        Args:
            output_path: 輸出檔案路徑

        Returns:
            bool: 路徑可寫入返回 True，否則返回 False

        Examples:
            >>> validator = PathValidator()
            >>> validator.validate_output_writable("/tmp/output.mp4")
            True
        """
        path = Path(output_path) if isinstance(output_path, str) else output_path

        # 檢查父目錄是否存在且可寫入
        parent_dir = path.parent
        if not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                return False

        # 檢查目錄是否可寫入
        return os.access(parent_dir, os.W_OK)

    @staticmethod
    def normalize_path(file_path: str | Path) -> Path:
        """
        標準化路徑（解析為絕對路徑）

        Args:
            file_path: 要標準化的路徑

        Returns:
            Path: 標準化後的路徑物件

        Examples:
            >>> validator = PathValidator()
            >>> validator.normalize_path("./video.mp4")
            PosixPath('/current/dir/video.mp4')
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path
        return path.resolve()
