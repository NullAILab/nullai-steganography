# Steganography Multi-Tool

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

> **Difficulty:** Beginner | **Language:** Python | **Requires:** Pillow (images only)

Three steganography techniques in one toolkit: LSB image encoding, zero-width Unicode character embedding, and trailing-whitespace text encoding. Each technique has a matching extractor. Comes with a pytest suite that round-trips all three and verifies error handling. Useful for learning how data can be concealed in plain sight and how forensic tools detect it.

---

## Techniques

| Technique | Carrier | Capacity | Visibility |
|-----------|---------|---------|-----------|
| LSB (1-bit) | PNG / BMP image | `W × H × 3 / 8` bytes | Imperceptible to the naked eye |
| Zero-width Unicode | Plain text | Unlimited (bounded by carrier length) | Invisible in all renderers |
| Trailing whitespace | Multi-line text | `lines / 8` bytes | Invisible in most editors |

---

## Project Structure

```
09-steganography-multi-tool/
├── README.md
├── .gitignore
├── src/
│   ├── stego.py          ← Library: LSB / zero-width / whitespace
│   ├── main.py           ← CLI: embed + extract subcommands
│   ├── test_stego.py     ← pytest suite
│   └── requirements.txt
└── docs/
    └── NOTES.md
```

---

## Installation

```bash
cd src
pip install -r requirements.txt
```

Only Pillow is required for image steganography. The zero-width and whitespace techniques use the Python standard library only.

---

## Usage

### LSB Image Steganography

```bash
# Embed
python main.py embed lsb --cover photo.png --msg "classified" --out stego.png

# Embed from file
python main.py embed lsb --cover photo.png --msg-file secret.txt --out stego.png

# Extract
python main.py extract lsb --file stego.png

# Use 2 LSBs (higher capacity, slightly more distortion)
python main.py embed lsb --cover photo.png --msg "more text" --out stego.png --bits 2
python main.py extract lsb --file stego.png --bits 2
```

### Zero-Width Unicode

```bash
# Embed into a text file
python main.py embed zw --carrier cover.txt --msg "hidden message" --out stego.txt

# Extract (output looks identical to the original)
python main.py extract zw --file stego.txt
```

### Trailing Whitespace

```bash
# Embed (carrier needs at least payload_bits lines)
python main.py embed ws --carrier poem.txt --msg "secret" --out stego.txt

# Extract
python main.py extract ws --file stego.txt
```

---

## Run Tests

```bash
cd src
python -m pytest test_stego.py -v
```

---

## How It Works

### LSB
Each pixel channel (R, G, B) has its least significant bit replaced with one bit of the message. The visual change per pixel is at most 1 grey level — indistinguishable to the human eye. A 4-byte magic header + 4-byte length prefix is prepended so extraction is deterministic.

### Zero-Width Unicode
U+200B (ZERO WIDTH SPACE) and U+200C (ZERO WIDTH NON-JOINER) are inserted invisibly into carrier text to encode binary data. A 0xAA sync byte followed by a 4-byte length makes the hidden stream self-framing.

### Whitespace
Each line of the carrier ends with a trailing space (bit 1) or no space (bit 0). A TAB-terminated line marks end-of-message. One byte requires 8 lines of carrier text.

---

## Detection (Steganalysis)

| Technique | How to Detect |
|-----------|-------------|
| LSB | Chi-squared steganalysis, visual attack (amplify LSB plane), `stegdetect` |
| Zero-width | Hex/binary editor — look for U+200B/200C sequences |
| Whitespace | `cat -A` (Linux) shows `$` at line ends — trailing spaces appear before `$` |

---

---

## Challenges & Extensions

- Add **DCT-domain steganography** in JPEG (F5 algorithm)
- Add **audio LSB steganography** in WAV files
- Add **PNG alpha channel encoding** (use the alpha byte as a carrier)
- Implement **chi-squared steganalysis** to detect LSB-modified images
- Add **AES encryption** of the payload before embedding

---

## References

- [Steganography — Wikipedia](https://en.wikipedia.org/wiki/Steganography)
- [LSB steganography primer](https://incoherency.co.uk/image-steganography/)
- [Unicode zero-width characters](https://www.unicode.org/charts/PDF/U2000.pdf)
- [StegCracker / stegdetect](https://github.com/Paradoxis/StegCracker)

---

