"""
stego.py — Steganography library.

Implements:
  1. LSB (Least Significant Bit) steganography in PNG/BMP images
  2. Text-in-text steganography using Unicode zero-width characters
  3. Whitespace steganography (trailing spaces encoding binary)

Each technique has an embed() and extract() function.
No external dependencies beyond Pillow for image support.

Requirements:
    pip install Pillow
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Union

try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False


# ─────────────────────────────────────────────────────────────
# LSB image steganography
# ─────────────────────────────────────────────────────────────

_LSB_MAGIC   = b"STEG"          # 4-byte header marker
_LSB_HDR_LEN = 4 + 4            # magic (4) + payload length (4)


def lsb_embed(image_path: Union[str, Path],
              message: Union[str, bytes],
              output_path: Union[str, Path],
              bits: int = 1) -> int:
    """
    Embed *message* into *image_path* using LSB substitution.

    Each pixel channel's least significant *bits* bits are replaced
    with message bits. Writes the stego image to *output_path*.

    Args:
        image_path:  Cover image (PNG, BMP — lossless only).
        message:     Bytes or str to hide.
        output_path: Destination file path (must be PNG or BMP).
        bits:        Number of LSBs to use (1–4). More bits = higher
                     capacity but more visible distortion.

    Returns:
        Number of bytes embedded.

    Raises:
        ValueError if the image does not have enough capacity.
    """
    if not _PIL:
        raise RuntimeError("Pillow not installed (pip install Pillow)")

    payload = message.encode() if isinstance(message, str) else message
    header  = _LSB_MAGIC + struct.pack(">I", len(payload))
    data    = header + payload

    img  = Image.open(image_path).convert("RGB")
    w, h = img.size
    pixels = list(img.getdata())   # list of (R,G,B) tuples

    capacity = (w * h * 3 * bits) // 8
    if len(data) > capacity:
        raise ValueError(
            f"Message too large: {len(data)} bytes, capacity {capacity} bytes"
        )

    # Convert data bytes to a stream of bits
    bits_stream = []
    for byte in data:
        for b in range(7, -1, -1):
            bits_stream.append((byte >> b) & 1)

    mask    = (1 << bits) - 1
    bit_idx = 0
    new_pixels = []

    for pixel in pixels:
        channels = list(pixel)
        for i in range(3):
            if bit_idx >= len(bits_stream):
                new_pixels.append(tuple(channels))
                break
            chunk = 0
            for _ in range(bits):
                if bit_idx < len(bits_stream):
                    chunk = (chunk << 1) | bits_stream[bit_idx]
                    bit_idx += 1
                else:
                    chunk <<= 1
            channels[i] = (channels[i] & ~mask) | chunk
        else:
            new_pixels.append(tuple(channels))
            continue
        break
    else:
        # Fill remaining pixels unchanged
        new_pixels.extend(pixels[len(new_pixels):])

    out_img = Image.new("RGB", (w, h))
    out_img.putdata(new_pixels)
    out_img.save(str(output_path))
    return len(payload)


def lsb_extract(image_path: Union[str, Path], bits: int = 1) -> bytes:
    """
    Extract a message previously embedded with lsb_embed().

    Args:
        image_path: Stego image.
        bits:       Must match the value used during embedding.

    Returns:
        Extracted bytes payload.

    Raises:
        ValueError if magic header is not found.
    """
    if not _PIL:
        raise RuntimeError("Pillow not installed (pip install Pillow)")

    img    = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())

    mask = (1 << bits) - 1

    def _extract_bits(n_bytes: int) -> bytes:
        out_bits: list[int] = []
        for pixel in pixels:
            for ch in pixel:
                chunk = ch & mask
                for b in range(bits - 1, -1, -1):
                    out_bits.append((chunk >> b) & 1)
                if len(out_bits) >= n_bytes * 8:
                    break
            if len(out_bits) >= n_bytes * 8:
                break
        result = bytearray()
        for i in range(0, len(out_bits) - 7, 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | out_bits[i + j]
            result.append(byte)
        return bytes(result)

    # Read header
    header = _extract_bits(_LSB_HDR_LEN)
    if header[:4] != _LSB_MAGIC:
        raise ValueError("No LSB steganography header found in this image")

    payload_len = struct.unpack(">I", header[4:8])[0]
    full = _extract_bits(_LSB_HDR_LEN + payload_len)
    return full[_LSB_HDR_LEN:]


# ─────────────────────────────────────────────────────────────
# Unicode zero-width character steganography
# ─────────────────────────────────────────────────────────────
# Encodes binary data as sequences of:
#   U+200B ZERO WIDTH SPACE        → bit 0
#   U+200C ZERO WIDTH NON-JOINER   → bit 1
# The message is sandwiched between the first and second words
# of the carrier text.

_ZW_ZERO = "​"   # bit 0
_ZW_ONE  = "‌"   # bit 1
_ZW_SEP  = "‍"   # separator between header and payload

_ZW_MAGIC_BITS = "10101010"   # 1 byte = 0xAA as a recognisable sync marker


def zw_embed(carrier: str, message: Union[str, bytes]) -> str:
    """
    Embed *message* into *carrier* text using zero-width characters.

    The hidden data is inserted after the first space in the carrier.
    Returns the stego text (looks identical to carrier when rendered).
    """
    payload = message.encode() if isinstance(message, str) else message
    header  = struct.pack(">I", len(payload))
    data    = bytes([0xAA]) + header + payload   # 0xAA sync + 4-byte length

    zw_bits: list[str] = []
    for byte in data:
        for b in range(7, -1, -1):
            zw_bits.append(_ZW_ONE if (byte >> b) & 1 else _ZW_ZERO)

    hidden = "".join(zw_bits)

    # Insert after first whitespace in carrier
    insert_at = carrier.find(" ")
    if insert_at == -1:
        insert_at = len(carrier)
    else:
        insert_at += 1   # after the space

    return carrier[:insert_at] + hidden + carrier[insert_at:]


def zw_extract(stego_text: str) -> bytes:
    """
    Extract the message previously embedded with zw_embed().

    Returns the payload bytes.
    Raises ValueError if no hidden message is detected.
    """
    bits = []
    for ch in stego_text:
        if ch == _ZW_ZERO:
            bits.append(0)
        elif ch == _ZW_ONE:
            bits.append(1)

    if len(bits) < 8:
        raise ValueError("No zero-width characters found")

    # Reconstruct bytes
    def _bits_to_bytes(bit_list: list[int]) -> bytes:
        result = bytearray()
        for i in range(0, len(bit_list) - 7, 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bit_list[i + j]
            result.append(byte)
        return bytes(result)

    raw = _bits_to_bytes(bits)
    if not raw or raw[0] != 0xAA:
        raise ValueError("No hidden message detected (sync byte missing)")

    if len(raw) < 5:
        raise ValueError("Hidden data truncated")

    payload_len = struct.unpack(">I", raw[1:5])[0]
    if len(raw) < 5 + payload_len:
        raise ValueError("Hidden data truncated")

    return raw[5:5 + payload_len]


# ─────────────────────────────────────────────────────────────
# Whitespace steganography
# ─────────────────────────────────────────────────────────────
# Encodes bits as trailing whitespace at line ends:
#   one trailing space  → bit 1
#   no trailing space   → bit 0
# A line with just TAB  → end-of-message marker

_WS_MAGIC = b"WS"


def ws_embed(carrier: str, message: Union[str, bytes]) -> str:
    """
    Embed *message* in *carrier* text using trailing whitespace.

    Each line encodes one bit: trailing space = 1, no space = 0.
    The carrier must have enough lines to encode the message.
    """
    payload = message.encode() if isinstance(message, str) else message
    data    = _WS_MAGIC + struct.pack(">I", len(payload)) + payload

    bits: list[int] = []
    for byte in data:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)

    lines = carrier.splitlines()
    if len(lines) < len(bits) + 1:
        raise ValueError(
            f"Carrier too short: need {len(bits) + 1} lines, have {len(lines)}"
        )

    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if i < len(bits):
            new_lines.append(stripped + (" " if bits[i] else ""))
        else:
            new_lines.append(stripped)

    # End-of-message marker
    new_lines[len(bits)] = new_lines[len(bits)].rstrip() + "\t"
    return "\n".join(new_lines)


def ws_extract(stego_text: str) -> bytes:
    """
    Extract a message embedded with ws_embed().
    """
    lines = stego_text.splitlines()
    bits: list[int] = []

    for line in lines:
        if line.endswith("\t"):
            break
        # Check trailing space (before any tab)
        raw_line = line.rstrip("\t")
        bits.append(1 if raw_line.endswith(" ") else 0)

    if len(bits) < 8:
        raise ValueError("No whitespace-encoded message found")

    # Reconstruct
    raw_bytes = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        raw_bytes.append(byte)

    raw = bytes(raw_bytes)
    if raw[:2] != _WS_MAGIC:
        raise ValueError("Whitespace magic header not found")
    if len(raw) < 6:
        raise ValueError("Truncated message")

    payload_len = struct.unpack(">I", raw[2:6])[0]
    return raw[6:6 + payload_len]
