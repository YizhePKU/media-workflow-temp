from typing import Tuple


def rgb2hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def hex2rgb(hex: str) -> Tuple[int, int, int]:
    return (int(hex[1:3], base=16), int(hex[3:5], base=16), int(hex[5:7], base=16))
