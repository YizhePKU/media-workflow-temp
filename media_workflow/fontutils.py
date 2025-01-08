from fontTools.ttLib import TTFont


def supports_chinese(font: TTFont) -> bool:
    """Check if the font supports Chinese characters."""
    cmap = font.getBestCmap()
    return all(ord(char) in cmap for char in "你好世界" if not char.isspace())
