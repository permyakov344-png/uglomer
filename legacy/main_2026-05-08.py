from machine import Pin, I2C, SPI, PWM, ADC
import framebuf
import time
import math

from lcd_driver import LCD_1inch28
from imu_qmi8658 import QMI8658
from writer import CWriter
import courier20

# --- ЦВЕТА (BGR Экран) ---
BLACK     = 0x0000
RED       = 0x07E0  # Красный
YELLOW    = 0x07FF  # Желтый
GREEN     = 0x001f  # Зеленый
PURPLE    = 0xFFE0  # Пурпурный

# ==============================================================
# ОГРОМНЫЕ ЦИФРЫ ВО ВЕСЬ ЭКРАН (Молниеносная отрисовка)
# ==============================================================
def draw_giant_digit(digit, x, y, color):
    w = 50; h = 110; t = 12
    segs = {
        0: 'ABCDEF', 1: 'BC', 2: 'ABDEG', 3: 'ABCDG', 4: 'BCFG',
        5: 'ACDFG', 6: 'ACDEFG', 7: 'ABC', 8: 'ABCDEFG', 9: 'ABCDFG'
    }
    active = segs.get(digit, '')
    half_h = h // 2
    
    # Горизонтальные сегменты
    if 'A' in active: LCD.fill_rect(x + t, y, w - 2*t, t, color)
    if 'D' in active: LCD.fill_rect(x + t, y + h - t, w - 2*t, t, color)
    if 'G' in active: LCD.fill_rect(x + t, y + half_h - t//2, w - 2*t, t, color)
    
    # Вертикальные сегменты
    if 'F' in active: LCD.fill_rect(x, y + t, t, half_h - t, color)
    if 'B' in active: LCD.fill_rect(x + w - t, y + t, t, half_h - t, color)
    if 'E' in active: LCD.fill_rect(x, y + half_h + t//2, t, half_h - t, color)
    if 'C' in active: LCD.fill_rect(x + w - t, y + half_h + t//2, t, half_h - t, color)

def draw_giant_value(val):
    is_neg = val < 0
    abs_val = abs(val)
    int_part = int(abs_val)
    dec_part = int(round((abs_val - int_part) * 10))
    if dec_part > 9: dec_part = 9
    
    d_tens = int_part // 10
    d_units = int_part % 10
    d_dec = dec_part
    
    color = YELLOW
    y_start = 55
    
    # ЖЕСТКИЕ КООРДИНАТЫ X (Запятая и цифры никогда не сдвигаются)
    x_sign = 15
    x_tens = 40
    x_units = 100
    x_dot = 153   # ТОЧКА ЗДЕСЬ НАВСЕГДА
    x_dec = 170
    
    # 1. Знак минуса (если есть)
    if is_neg:
        LCD.fill_rect(x_sign + 2, y_start + 55 - 6, 20, 12, color)
        
    # 2. Десятки (рисуем только если они есть или если число > 9)
    if d_tens != 0 or int_part >= 10:
        draw_giant_digit(d_tens, x_tens, y_start, color)
        
    # 3. Единицы (Всегда рисуем)
    draw_giant_digit(d_units, x_units, y_start, color)
    
    # 4. Толстая точка
    LCD.fill_rect(x_dot, y_start + 95, 12, 12, color)
    
    # 5. Десятые доли
    draw_giant_digit(d_dec, x_dec, y_start, color)

# --- ГЛАВНЫЙ ЦИКЛ ---
if __name__=='__main__':
    LCD = LCD_1inch28()
    LCD.set_bl_pwm(65535)
    qmi8658 = QMI8658()
    Vbat = ADC(Pin(29))
    
    wri = CWriter(LCD, courier20)
    
    acc_len = 8
    acc_i = 0
    acc_xa = [0]*acc_len
    acc_za = [0]*acc_len
    
    while True:
        xyz = qmi8658.Read_XYZ()
        acc_xa[acc_i] = xyz[0]
        acc_za[acc_i] = xyz[2]
        acc_x = sum(acc_xa) / acc_len
        acc_z = sum(acc_za) / acc_len
        
        angle_deg = math.atan2(acc_x, -acc_z) * 180 / math.pi
        reading = Vbat.read_u16() * 3.3 / 65535 * 2

        # 1. ОЧИСТКА ЭКРАНА (Полная, чтобы не было мусора)
        LCD.fill(BLACK)

        # 2. ОГРОМНЫЕ ЖЕЛТЫЕ ЦИФРЫ
        draw_giant_value(angle_deg)
        
        # 3. Надпись ANGLE (Зеленая, внизу)
        CWriter.set_textpos(LCD, 185, 85)
        wri.setcolor(GREEN, BLACK)
        wri.printstring("ANGLE")
        
        # 4. Вольтаж (Пурпурный, в самом низу)
        CWriter.set_textpos(LCD, 210, 78)
        wri.setcolor(PURPLE, BLACK)
        wri.printstring("{:.2f}V".format(reading))

        # 5. ВЫВОДИМ НА ЭКРАН
        LCD.show()
        
        acc_i = (acc_i + 1) % acc_len
        time.sleep(0.05)