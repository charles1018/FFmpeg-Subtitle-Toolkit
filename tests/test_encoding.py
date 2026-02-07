"""
測試 EncodingStrategy 編碼策略模組
"""

import pytest

from ffmpeg_toolkit.core.encoding import EncodingStrategy


class TestEncodingStrategy:
    """測試 EncodingStrategy 類別"""

    def test_h264_fallback_order(self):
        """測試 H.264 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx264"))

        assert codecs == ["h264_nvenc", "libx264"]

    def test_h265_fallback_order(self):
        """測試 H.265 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx265"))

        assert codecs == ["hevc_nvenc", "libx265"]

    def test_nvenc_h264_fallback_order(self):
        """測試 NVENC H.264 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("h264_nvenc"))

        assert codecs == ["h264_nvenc", "libx264"]

    def test_nvenc_h265_fallback_order(self):
        """測試 NVENC H.265 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("hevc_nvenc"))

        assert codecs == ["hevc_nvenc", "libx265"]

    def test_unknown_codec_no_fallback(self):
        """測試未知編碼器（無回退）"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("unknown_codec"))

        assert codecs == ["unknown_codec"]

    @pytest.mark.parametrize(
        "error_msg,should_fallback",
        [
            ("Cannot load nvEncodeAPI", True),
            ("No NVENC capable devices found", True),
            ("Invalid encoder", True),
            ("Unknown encoder 'h264_nvenc'", True),
            ("Impossible to convert between the formats", True),
            ("Error initializing", True),
            ("nvenc not available", True),
            ("Disk full", False),
            ("Invalid file format", False),
            ("Permission denied", False),
            ("No such file or directory", False),
        ],
    )
    def test_should_fallback(self, error_msg, should_fallback):
        """測試 NVENC 錯誤檢測"""
        strategy = EncodingStrategy()
        assert strategy.should_fallback(error_msg) == should_fallback

    def test_should_fallback_case_insensitive(self):
        """測試 NVENC 錯誤檢測（不分大小寫）"""
        strategy = EncodingStrategy()

        assert strategy.should_fallback("CANNOT LOAD NVENCODEAPI")
        assert strategy.should_fallback("no nvenc capable devices found")
        assert strategy.should_fallback("NvEnc Not Available")


from unittest.mock import patch, MagicMock


class TestDetectAvailableEncoders:
    """測試可用編碼器偵測"""

    SAMPLE_ENCODERS_OUTPUT = """\
Encoders:
 V..... = Video
 A..... = Audio
 S..... = Subtitle
 V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V....D libx265              libx265 H.265 / HEVC (codec hevc)
 V....D h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V....D hevc_nvenc           NVIDIA NVENC hevc encoder (codec hevc)
 V....D h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
 V....D hevc_qsv             HEVC (Intel Quick Sync Video acceleration) (codec hevc)
"""

    SAMPLE_NO_GPU_OUTPUT = """\
Encoders:
 V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V....D libx265              libx265 H.265 / HEVC (codec hevc)
"""

    @patch("subprocess.run")
    def test_detect_all_encoders(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_ENCODERS_OUTPUT)
        strategy = EncodingStrategy()
        available = strategy.detect_available_encoders()
        assert "h264_nvenc" in available
        assert "hevc_nvenc" in available
        assert "h264_qsv" in available
        assert "hevc_qsv" in available

    @patch("subprocess.run")
    def test_detect_no_gpu(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_NO_GPU_OUTPUT)
        strategy = EncodingStrategy()
        available = strategy.detect_available_encoders()
        assert "h264_nvenc" not in available
        assert "h264_qsv" not in available

    @patch("subprocess.run")
    def test_detect_caches_result(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_ENCODERS_OUTPUT)
        strategy = EncodingStrategy()
        result1 = strategy.detect_available_encoders()
        result2 = strategy.detect_available_encoders()
        assert result1 is result2
        assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_detect_ffmpeg_failure(self, mock_run):
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        strategy = EncodingStrategy()
        available = strategy.detect_available_encoders()
        assert available == set()

    def test_get_available_hw_accelerators(self):
        strategy = EncodingStrategy()
        strategy._available_encoders = {"h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv"}
        accels = strategy.get_available_hw_accelerators()
        assert ("NVIDIA NVENC", "nvenc") in accels
        assert ("Intel QSV", "qsv") in accels

    def test_get_available_hw_accelerators_no_gpu(self):
        strategy = EncodingStrategy()
        strategy._available_encoders = set()
        accels = strategy.get_available_hw_accelerators()
        assert accels == []


class TestGetCodecsWithHwAccel:
    """測試帶硬體加速選擇的 get_codecs"""

    def test_auto_mode_nvenc_first(self):
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx264", hw_accel="auto"))
        assert codecs == ["h264_nvenc", "libx264"]

    def test_nvenc_mode(self):
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx264", hw_accel="nvenc"))
        assert codecs == ["h264_nvenc", "libx264"]

    def test_qsv_mode_h264(self):
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx264", hw_accel="qsv"))
        assert codecs == ["h264_qsv", "libx264"]

    def test_qsv_mode_h265(self):
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx265", hw_accel="qsv"))
        assert codecs == ["hevc_qsv", "libx265"]

    def test_cpu_mode(self):
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx264", hw_accel="cpu"))
        assert codecs == ["libx264"]

    def test_cpu_mode_h265(self):
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx265", hw_accel="cpu"))
        assert codecs == ["libx265"]

    def test_default_is_auto(self):
        strategy = EncodingStrategy()
        codecs_default = list(strategy.get_codecs("libx264"))
        codecs_auto = list(strategy.get_codecs("libx264", hw_accel="auto"))
        assert codecs_default == codecs_auto
