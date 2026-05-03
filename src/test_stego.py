"""
test_stego.py — Unit tests for the steganography library.

Run with:  python -m pytest src/test_stego.py -v
"""

import struct
import tempfile
from pathlib import Path

import pytest

from stego import (
    lsb_embed, lsb_extract,
    zw_embed,  zw_extract,
    ws_embed,  ws_extract,
)


# ─────────────────────────────────────────────────────────────
# LSB image tests
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def tiny_png(tmp_path: Path) -> Path:
    """Create a tiny 64×64 white PNG for testing."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", (64, 64), color=(255, 255, 255))
    p = tmp_path / "cover.png"
    img.save(str(p))
    return p


class TestLSB:
    def test_round_trip(self, tiny_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "stego.png"
        msg = b"Hello, steganography!"
        lsb_embed(tiny_png, msg, out)
        extracted = lsb_extract(out)
        assert extracted == msg

    def test_round_trip_multi_bit(self, tiny_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "stego2.png"
        msg = b"Multi-bit LSB test"
        lsb_embed(tiny_png, msg, out, bits=2)
        extracted = lsb_extract(out, bits=2)
        assert extracted == msg

    def test_string_message(self, tiny_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "stego3.png"
        lsb_embed(tiny_png, "string message", out)
        assert lsb_extract(out) == b"string message"

    def test_capacity_error(self, tiny_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "stego4.png"
        # 64×64 × 3 channels × 1 bit / 8 = 1536 bytes capacity
        too_big = b"X" * 2000
        with pytest.raises(ValueError, match="too large"):
            lsb_embed(tiny_png, too_big, out)

    def test_no_header_raises(self, tiny_png: Path) -> None:
        with pytest.raises(ValueError, match="No LSB"):
            lsb_extract(tiny_png)   # clean image has no header


# ─────────────────────────────────────────────────────────────
# Zero-width character tests
# ─────────────────────────────────────────────────────────────

class TestZeroWidth:
    def test_round_trip(self) -> None:
        carrier = "The quick brown fox jumps over the lazy dog."
        msg = b"secret"
        stego = zw_embed(carrier, msg)
        assert zw_extract(stego) == msg

    def test_looks_identical(self) -> None:
        carrier = "Visible text remains unchanged."
        stego = zw_embed(carrier, b"hidden")
        # Strip zero-width chars to compare visible content
        zw_chars = "​‌‍"
        stripped = "".join(c for c in stego if c not in zw_chars)
        assert stripped == carrier

    def test_empty_message(self) -> None:
        carrier = "Some text here."
        stego = zw_embed(carrier, b"")
        assert zw_extract(stego) == b""

    def test_no_hidden_raises(self) -> None:
        with pytest.raises(ValueError):
            zw_extract("No hidden data in this plain text.")

    def test_binary_payload(self) -> None:
        carrier = "Cover text with binary payload."
        msg = bytes(range(256))
        stego = zw_embed(carrier, msg)
        assert zw_extract(stego) == msg


# ─────────────────────────────────────────────────────────────
# Whitespace steganography tests
# ─────────────────────────────────────────────────────────────

_LONG_CARRIER = "\n".join(f"Line {i}: The quick brown fox." for i in range(300))


class TestWhitespace:
    def test_round_trip(self) -> None:
        msg = b"ws stego works"
        stego = ws_embed(_LONG_CARRIER, msg)
        assert ws_extract(stego) == msg

    def test_short_message(self) -> None:
        msg = b"hi"
        stego = ws_embed(_LONG_CARRIER, msg)
        assert ws_extract(stego) == msg

    def test_too_short_carrier(self) -> None:
        short = "only two lines\nhere"
        with pytest.raises(ValueError, match="Carrier too short"):
            ws_embed(short, b"a message that needs many lines")

    def test_no_hidden_raises(self) -> None:
        with pytest.raises(ValueError):
            ws_extract("plain text\nno hidden message here")
