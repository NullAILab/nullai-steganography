# Architecture Notes — Steganography Multi-Tool

## LSB — why re-build the pixel array?

Pillow's `getdata()` returns a flat list of pixel tuples. We rebuild it from
scratch (list comprehension → new Image.putdata) rather than mutating an image
in-place because Pillow does not expose a per-pixel mutable view that handles
all modes uniformly. Re-building is O(n) in pixel count — fast enough for any
reasonable image.

## LSB header design

Embedding without a header means extraction has to guess the payload length,
which is fragile. The 8-byte header (4 magic + 4 length) costs 8 × 8 = 64
pixel channels — negligible. The magic bytes "STEG" let the extractor fail
cleanly if the image was not processed by this tool.

## Zero-width characters

U+200B (ZERO WIDTH SPACE) and U+200C (ZERO WIDTH NON-JOINER) are invisible
in all rendering environments (browsers, editors, terminals). The choice of
these two specific code points over others (U+FEFF, U+2060) is because they
are the most commonly supported and the least likely to be stripped by text
processing pipelines.

The 0xAA sync byte at the start of the payload (bit pattern 10101010) gives
the extractor a recognisable marker. U+200D (ZERO WIDTH JOINER) is reserved
as a field separator for future extensions.

## Whitespace encoding

Trailing spaces are invisible in most text editors and renderers. This is one
of the oldest steganography techniques — used in Morse code (STEGANO by
Peter Wayner, 2002). One bit per line limits capacity to roughly lines/8
bytes, so it works best for short messages in longer texts.

The TAB character at the end-of-message line acts as a line-level sentinel.
Tabs are distinct from spaces and indicate "stop reading here".

## Format independence

Each technique is fully self-contained: embed/extract are stateless functions
with no shared state. The CLI is a thin dispatcher; the same library functions
can be imported by any other script. Tests use tmp_path fixtures so no test
artefacts are left on disk.
