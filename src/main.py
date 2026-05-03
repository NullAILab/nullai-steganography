"""
main.py — Steganography Multi-Tool CLI

Techniques:
    lsb    — Least Significant Bit in PNG/BMP images
    zw     — Zero-width Unicode characters in text
    ws     — Trailing whitespace encoding in text files

Subcommands:
    embed  <technique> [options]    Hide a message
    extract <technique> [options]   Reveal a message

Examples:
    python main.py embed lsb --cover photo.png --msg "secret" --out stego.png
    python main.py extract lsb --file stego.png

    python main.py embed zw --carrier cover.txt --msg "hidden" --out stego.txt
    python main.py extract zw --file stego.txt

    python main.py embed ws --carrier poem.txt --msg "hello" --out stego.txt
    python main.py extract ws --file stego.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stego import (
    lsb_embed, lsb_extract,
    zw_embed,  zw_extract,
    ws_embed,  ws_extract,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_msg(args: argparse.Namespace) -> bytes:
    """Return message bytes from --msg or --msg-file."""
    if args.msg:
        return args.msg.encode()
    if hasattr(args, "msg_file") and args.msg_file:
        return Path(args.msg_file).read_bytes()
    sys.exit("[!] Provide --msg or --msg-file")


# ---------------------------------------------------------------------------
# Embed commands
# ---------------------------------------------------------------------------

def embed_lsb(args: argparse.Namespace) -> None:
    msg = _read_msg(args)
    n = lsb_embed(args.cover, msg, args.out, bits=args.bits)
    print(f"[+] Embedded {n} bytes into {args.out}  (bits={args.bits})")


def embed_zw(args: argparse.Namespace) -> None:
    msg     = _read_msg(args)
    carrier = Path(args.carrier).read_text(encoding="utf-8")
    result  = zw_embed(carrier, msg)
    Path(args.out).write_text(result, encoding="utf-8")
    print(f"[+] Embedded {len(msg)} bytes into {args.out} (zero-width)")


def embed_ws(args: argparse.Namespace) -> None:
    msg     = _read_msg(args)
    carrier = Path(args.carrier).read_text(encoding="utf-8")
    result  = ws_embed(carrier, msg)
    Path(args.out).write_text(result, encoding="utf-8")
    print(f"[+] Embedded {len(msg)} bytes into {args.out} (whitespace)")


# ---------------------------------------------------------------------------
# Extract commands
# ---------------------------------------------------------------------------

def extract_lsb(args: argparse.Namespace) -> None:
    data = lsb_extract(args.file, bits=args.bits)
    _output(data, args)


def extract_zw(args: argparse.Namespace) -> None:
    text = Path(args.file).read_text(encoding="utf-8")
    data = zw_extract(text)
    _output(data, args)


def extract_ws(args: argparse.Namespace) -> None:
    text = Path(args.file).read_text(encoding="utf-8")
    data = ws_extract(text)
    _output(data, args)


def _output(data: bytes, args: argparse.Namespace) -> None:
    if hasattr(args, "out") and args.out:
        Path(args.out).write_bytes(data)
        print(f"[+] Extracted {len(data)} bytes → {args.out}")
    else:
        try:
            print(f"[+] Extracted ({len(data)} bytes): {data.decode()}")
        except UnicodeDecodeError:
            print(f"[+] Extracted {len(data)} raw bytes (not UTF-8 text)")
            print(f"    Hex: {data.hex()}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stego",
        description="Steganography multi-tool: LSB / zero-width / whitespace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # ── embed ────────────────────────────────────────────────
    emb = sub.add_parser("embed", help="Hide a message")
    emb_sub = emb.add_subparsers(dest="technique", required=True)

    # embed lsb
    el = emb_sub.add_parser("lsb", help="LSB image steganography")
    el.add_argument("--cover", required=True, help="Cover image (PNG/BMP)")
    el.add_argument("--out",   required=True, help="Output stego image path")
    el.add_argument("--msg",   help="Message string to hide")
    el.add_argument("--msg-file", help="File whose contents to hide")
    el.add_argument("--bits",  type=int, default=1, choices=[1,2,3,4],
                    help="LSBs per channel (default: 1)")
    el.set_defaults(func=embed_lsb)

    # embed zw
    ez = emb_sub.add_parser("zw", help="Zero-width Unicode steganography")
    ez.add_argument("--carrier", required=True, help="Cover text file")
    ez.add_argument("--out",     required=True, help="Output stego text path")
    ez.add_argument("--msg",     help="Message string to hide")
    ez.add_argument("--msg-file", help="File whose contents to hide")
    ez.set_defaults(func=embed_zw)

    # embed ws
    ew = emb_sub.add_parser("ws", help="Trailing whitespace steganography")
    ew.add_argument("--carrier", required=True, help="Cover text file")
    ew.add_argument("--out",     required=True, help="Output stego text path")
    ew.add_argument("--msg",     help="Message string to hide")
    ew.add_argument("--msg-file", help="File whose contents to hide")
    ew.set_defaults(func=embed_ws)

    # ── extract ──────────────────────────────────────────────
    ext = sub.add_parser("extract", help="Reveal a hidden message")
    ext_sub = ext.add_subparsers(dest="technique", required=True)

    # extract lsb
    xl = ext_sub.add_parser("lsb")
    xl.add_argument("--file",  required=True, help="Stego image")
    xl.add_argument("--out",   help="Write extracted bytes to file")
    xl.add_argument("--bits",  type=int, default=1, choices=[1,2,3,4])
    xl.set_defaults(func=extract_lsb)

    # extract zw
    xz = ext_sub.add_parser("zw")
    xz.add_argument("--file", required=True, help="Stego text file")
    xz.add_argument("--out",  help="Write extracted bytes to file")
    xz.set_defaults(func=extract_zw)

    # extract ws
    xw = ext_sub.add_parser("ws")
    xw.add_argument("--file", required=True, help="Stego text file")
    xw.add_argument("--out",  help="Write extracted bytes to file")
    xw.set_defaults(func=extract_ws)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        sys.exit(f"[!] {exc}")


if __name__ == "__main__":
    main()
