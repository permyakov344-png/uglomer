"""Макет интерфейса угломера.

Рисует экран 240x240 тем же алгоритмом, что и main.py (семисегментные цифры),
и тем же шрифтом courier20, что и на плате. Результат — PNG для документации.

Запуск:  python tools/make_screen_mockup.py
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import courier20  # noqa: E402  — настоящий шрифт с платы

W = H = 240
CX, CY = 120, 120

SW, SH, ST = 42, 90, 9

SEGS = {
    0: "ABCDEF", 1: "BC", 2: "ABDEG", 3: "ABCDG", 4: "BCFG",
    5: "ACDFG", 6: "ACDEFG", 7: "ABC", 8: "ABCDEFG", 9: "ABCDFG",
}

BLACK, WHITE, GREEN, RED, YELLOW, GRAY = 0x0000, 0xFFFF, 0x07E0, 0x00F8, 0x07FF, 0x2104


def rgb565(v):
    """RGB565 -> RGB888 с учётом BGR-панели (MADCTL 0x98): R и B меняются местами."""
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return (b * 255 // 31, g * 255 // 63, r * 255 // 31)


class Screen:
    """Минимальная замена framebuf.FrameBuffer: только fill и fill_rect."""

    def __init__(self):
        self.img = Image.new("RGB", (W, H), (0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def fill(self, color):
        self.d.rectangle((0, 0, W - 1, H - 1), fill=rgb565(color))

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        self.d.rectangle((x, y, x + w - 1, y + h - 1), fill=rgb565(color))

    def text(self, x, y, s, color):
        """CWriter/Courier20: моноширинный, 20 px высотой, 14 px на символ."""
        fg = rgb565(color)
        px = self.img.load()
        for ch in s:
            buf, ch_h, ch_w = courier20.get_ch(ch)
            for row in range(ch_h):
                base = row * 2
                for col in range(ch_w):
                    byte = buf[base + (col >> 3)]
                    if byte & (1 << (col & 7)):
                        xx, yy = x + col, y + row
                        if 0 <= xx < W and 0 <= yy < H:
                            px[xx, yy] = fg
            x += courier20.max_width()


def draw_digit(scr, d, x, y, color):
    s = SEGS.get(d, "")
    hh = SH // 2
    if "A" in s: scr.fill_rect(x + ST, y, SW - 2 * ST, ST, color)
    if "D" in s: scr.fill_rect(x + ST, y + SH - ST, SW - 2 * ST, ST, color)
    if "G" in s: scr.fill_rect(x + ST, y + hh - ST // 2, SW - 2 * ST, ST, color)
    if "F" in s: scr.fill_rect(x, y + ST, ST, hh - ST, color)
    if "B" in s: scr.fill_rect(x + SW - ST, y + ST, ST, hh - ST, color)
    if "E" in s: scr.fill_rect(x, y + hh + ST // 2, ST, hh - ST, color)
    if "C" in s: scr.fill_rect(x + SW - ST, y + hh + ST // 2, ST, hh - ST, color)


def draw_number(scr, angle, color):
    abs_a = abs(angle)
    int_p = int(abs_a)
    dec_p = int(round((abs_a - int_p) * 10))
    if dec_p > 9:
        dec_p = 9

    has_tens = int_p >= 10
    has_sign = angle < 0

    total_w = (ST + 6 if has_sign else 0) + \
              ((SW + 4) if has_tens else 0) + \
              (SW + 4) + (ST + 4) + (SW + 4) + (ST + 6)
    x = CX - total_w // 2
    y = CY - SH // 2

    if has_sign:
        scr.fill_rect(x, y + SH // 2 - ST // 2, ST + 4, ST, color)
        x += ST + 6
    if has_tens:
        draw_digit(scr, int_p // 10, x, y, color)
        x += SW + 4
    draw_digit(scr, int_p % 10, x, y, color)
    x += SW + 4
    scr.fill_rect(x, y + SH - ST - 1, ST, ST, color)
    x += ST + 4
    draw_digit(scr, dec_p, x, y, color)
    x += SW + 4
    scr.fill_rect(x, y + 2, 7, 7, color)
    scr.fill_rect(x + 2, y + 4, 3, 3, BLACK)


def render(angle, volt, status, status_color):
    scr = Screen()
    scr.fill(BLACK)

    a = abs(angle)
    color = GREEN if a < 2.0 else (WHITE if a < 45.0 else RED)
    draw_number(scr, angle, color)

    vc = GREEN if volt > 3.5 else (YELLOW if volt > 3.2 else RED)
    scr.text(88, 10, "{:.2f}V".format(volt), vc)
    scr.text(76, 210, status, status_color)

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, W - 1, H - 1), fill=255)
    out = Image.new("RGB", (W, H), (0, 0, 0))
    out.paste(scr.img, (0, 0), mask)
    return out


def scale(img, k):
    return img.resize((W * k, H * k), Image.NEAREST)


def bezel(img, k):
    """Тёмный корпус вокруг круглого экрана."""
    size = W * k
    pad = 14 * k // 3
    frame = Image.new("RGB", (size + 2 * pad, size + 2 * pad), (14, 14, 16))
    d = ImageDraw.Draw(frame)
    d.ellipse((0, 0, frame.width - 1, frame.height - 1), fill=(28, 28, 32))
    frame.paste(img, (pad, pad))
    return frame


def caption(img, text, font):
    canvas = Image.new("RGB", (img.width, img.height + 44), (14, 14, 16))
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas)
    tw = d.textlength(text, font=font)
    d.text(((img.width - tw) / 2, img.height + 8), text, font=font, fill=(170, 170, 178))
    return canvas


def main():
    root = os.path.join(os.path.dirname(__file__), "..")
    out_dir = os.path.join(root, "docs", "screens")
    os.makedirs(out_dir, exist_ok=True)

    font_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")
    font = ImageFont.truetype(font_path, 26)

    scenes = [
        ("01-nol", 0.0, 4.05, "ZERO SET!", GREEN, "0.0° — зелёный, ноль выставлен кнопкой"),
        ("02-ugol", 12.3, 4.05, "GP0=ZERO", GRAY, "12.3° — белый, рабочий диапазон"),
        ("03-naklon", 47.8, 3.10, "GP0=ZERO", GRAY, "47.8° — красный, большой наклон"),
    ]

    tiles = []
    for name, angle, volt, status, scolor, text in scenes:
        img = bezel(scale(render(angle, volt, status, scolor), 3), 3)
        img.save(os.path.join(out_dir, name + ".png"))
        tiles.append(caption(img, text, font))

    gap = 24
    total_w = sum(t.width for t in tiles) + gap * (len(tiles) - 1)
    total_h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (total_w, total_h), (14, 14, 16))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + gap
    sheet.save(os.path.join(root, "docs", "interfeys.png"))

    for name, *_ in scenes:
        print("OK docs/screens/%s.png" % name)
    print("OK docs/interfeys.png  %dx%d" % sheet.size)


if __name__ == "__main__":
    main()
