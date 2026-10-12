"""Draw the program icon (Win95 style: permit sheet with a hard hat) into icons/.

    pip install pillow
    python tools/make_icon.py

Writes icons/ptw.ico (16-256 px, for the exe and the window) and PNG files
(icons/ptw_16.png ... ptw_256.png) used by the window and the splash screen.
Every size is drawn separately on a 32-unit grid, so small icons stay sharp.
"""
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
SIZES = (16, 24, 32, 48, 64, 128, 256)

BLACK, WHITE, GREY, DARK = (0, 0, 0, 255), (255, 255, 255, 255), (192, 192, 192, 255), (128, 128, 128, 255)
NAVY, RED, YELLOW, OCHRE = (0, 0, 128, 255), (200, 0, 0, 255), (255, 204, 0, 255), (179, 143, 0, 255)


def draw(size):
    k = size / 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(1, round(k))  # outline width

    def P(*pts):
        return [(round(x * k), round(y * k)) for x, y in pts]

    # sheet shadow, sheet, folded corner
    d.polygon(P((6, 3), (21, 3), (27, 9), (27, 30), (6, 30)), fill=DARK)
    d.polygon(P((4, 1), (19, 1), (25, 7), (25, 28), (4, 28)), fill=WHITE, outline=BLACK, width=w)
    d.polygon(P((19, 1), (19, 7), (25, 7)), fill=GREY, outline=BLACK, width=w)
    # text lines
    if size >= 24:
        for y, x1 in ((10, 21), (13, 18), (16, 21)):
            d.line(P((7, y), (x1, y)), fill=NAVY, width=w)
    else:
        d.line(P((7, 10), (20, 10)), fill=NAVY, width=1)
        d.line(P((7, 14), (17, 14)), fill=NAVY, width=1)
    # red stamp
    if size >= 48:
        d.rectangle(P((7, 20), (15, 25)), outline=RED, width=w)
        d.line(P((8, 22.5), (14, 22.5)), fill=RED, width=w)
    else:
        d.rectangle(P((7, 20), (13, 24)), outline=RED, width=1)
    # hard hat: dome, ridge, brim
    d.chord(P((15, 15), (31, 31)), 180, 360, fill=YELLOW, outline=BLACK, width=w)
    d.line(P((23, 16), (23, 22)), fill=OCHRE, width=max(1, w))
    d.rectangle(P((13, 22.5), (31, 25)), fill=YELLOW, outline=BLACK, width=w)
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    images = {s: draw(s) for s in SIZES}
    for s, img in images.items():
        img.save(os.path.join(OUT, f"ptw_{s}.png"))
    big = images[256]
    big.save(os.path.join(OUT, "ptw.ico"), sizes=[(s, s) for s in SIZES],
             append_images=[images[s] for s in SIZES if s != 256])
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
