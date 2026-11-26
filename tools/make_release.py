"""Собирает архив с файлами для платы: dist/uglomer-board-files.zip.

В архиве ровно 6 файлов, в корне, с теми именами, которые нужны на плате.
Запуск:  python tools/make_release.py
"""

import os
import zipfile

BOARD_FILES = [
    "main.py",
    "lcd_driver.py",
    "imu_qmi8658.py",
    "writer.py",
    "courier20.py",
    "boolpalette.py",
]


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist = os.path.join(root, "dist")
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, "uglomer-board-files.zip")

    missing = [f for f in BOARD_FILES if not os.path.isfile(os.path.join(root, f))]
    if missing:
        raise SystemExit("Нет файлов: " + ", ".join(missing))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in BOARD_FILES:
            z.write(os.path.join(root, name), arcname=name)

    print("OK", os.path.relpath(out, root))
    with zipfile.ZipFile(out) as z:
        for info in z.infolist():
            print("   %-18s %6d байт" % (info.filename, info.file_size))


if __name__ == "__main__":
    main()
