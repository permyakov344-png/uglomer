from machine import Pin, ADC
import math
from lcd_driver import LCD_1inch28
from imu_qmi8658 import QMI8658
from writer import CWriter
import courier20

# ─── ЦВЕТА RGB565 ───────────────────────
BLACK  = 0x0000
WHITE  = 0xFFFF
GREEN  = 0x07E0
RED    = 0x00F8
YELLOW = 0x07FF
GRAY   = 0x2104

CX, CY = 120, 120

btn = Pin(0, Pin.IN, Pin.PULL_UP)

# ════════════════════════════════════════
#  СЕМИСЕГМЕНТНЫЕ ЦИФРЫ
#  Большие, по центру экрана
# ════════════════════════════════════════
SW = 42   # ширина цифры
SH = 90   # высота цифры
ST = 9    # толщина сегмента

SEGS = {
    0:'ABCDEF', 1:'BC',     2:'ABDEG', 3:'ABCDG', 4:'BCFG',
    5:'ACDFG',  6:'ACDEFG', 7:'ABC',   8:'ABCDEFG', 9:'ABCDFG'
}

def draw_digit(d, x, y, color):
    s  = SEGS.get(d, '')
    hh = SH // 2
    if 'A' in s: LCD.fill_rect(x+ST,    y,          SW-2*ST, ST,    color)
    if 'D' in s: LCD.fill_rect(x+ST,    y+SH-ST,    SW-2*ST, ST,    color)
    if 'G' in s: LCD.fill_rect(x+ST,    y+hh-ST//2, SW-2*ST, ST,    color)
    if 'F' in s: LCD.fill_rect(x,       y+ST,       ST,      hh-ST, color)
    if 'B' in s: LCD.fill_rect(x+SW-ST, y+ST,       ST,      hh-ST, color)
    if 'E' in s: LCD.fill_rect(x,       y+hh+ST//2, ST,      hh-ST, color)
    if 'C' in s: LCD.fill_rect(x+SW-ST, y+hh+ST//2, ST,      hh-ST, color)

def draw_number(angle, color):
    """±XX.X° — центрировано по экрану."""
    abs_a = abs(angle)
    int_p = int(abs_a)
    dec_p = int(round((abs_a - int_p) * 10))
    if dec_p > 9: dec_p = 9

    has_tens = int_p >= 10
    has_sign = angle < 0

    # Подсчёт ширины для центровки
    total_w = (ST+6 if has_sign else 0) + \
              ((SW+4) if has_tens else 0) + \
              (SW+4) + (ST+4) + (SW+4) + (ST+6)
    x = CX - total_w // 2
    y = CY - SH // 2

    # Знак −
    if has_sign:
        LCD.fill_rect(x, y + SH//2 - ST//2, ST+4, ST, color)
        x += ST + 6

    # Десятки
    if has_tens:
        draw_digit(int_p // 10, x, y, color)
        x += SW + 4

    # Единицы
    draw_digit(int_p % 10, x, y, color)
    x += SW + 4

    # Точка
    LCD.fill_rect(x, y + SH - ST - 1, ST, ST, color)
    x += ST + 4

    # Десятые
    draw_digit(dec_p, x, y, color)
    x += SW + 4

    # °
    LCD.fill_rect(x,   y + 2, 7, 7, color)
    LCD.fill_rect(x+2, y + 4, 3, 3, BLACK)


# ════════════════════════════════════════
#  ГЛАВНЫЙ ЦИКЛ
# ════════════════════════════════════════
if __name__ == '__main__':
    LCD  = LCD_1inch28()
    LCD.set_bl_pwm(65535)
    imu  = QMI8658()
    vbat = ADC(Pin(29))
    wri  = CWriter(LCD, courier20, verbose=False)

    ACC   = 10
    acc_i = 0
    bx    = [0.0] * ACC
    bz    = [0.0] * ACC

    ref   = 0.0
    flash = 0
    prev  = 1

    while True:
        # 1. IMU — только X и Z
        xyz = imu.Read_XYZ()
        bx[acc_i] = xyz[0]
        bz[acc_i] = xyz[2]
        ax = sum(bx) / ACC
        az = sum(bz) / ACC
        acc_i = (acc_i + 1) % ACC

        raw = math.atan2(ax, -az) * 180.0 / math.pi

        # 2. Кнопка GP0
        now = btn.value()
        if prev == 1 and now == 0:
            ref   = raw
            flash = 20
        prev = now

        angle = raw - ref
        if angle >  180: angle -= 360
        if angle < -180: angle += 360

        # 3. Цвет
        color = GREEN if abs(angle) < 2.0 else (WHITE if abs(angle) < 45.0 else RED)

        # 4. Рисуем — только чёрный фон + цифры
        LCD.fill(BLACK)
        draw_number(angle, color)

        # 5. Вольтаж
        v  = vbat.read_u16() * 3.3 / 65535 * 2
        vc = GREEN if v > 3.5 else (YELLOW if v > 3.2 else RED)
        CWriter.set_textpos(LCD, 10, 88)
        wri.setcolor(vc, BLACK)
        wri.printstring("{:.2f}V".format(v))

        # 6. Кнопка
        CWriter.set_textpos(LCD, 210, 76)
        if flash > 0:
            wri.setcolor(GREEN, BLACK)
            wri.printstring("ZERO SET!")
            flash -= 1
        else:
            wri.setcolor(GRAY, BLACK)
            wri.printstring("GP0=ZERO")

        LCD.show()
