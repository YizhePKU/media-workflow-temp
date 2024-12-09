import cv2
import numpy as np
from temporalio import activity


def rgb2hex(rgb: list[int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def hex2rgb(hex: str) -> np.array:
    r = int(hex[1:3], base=16)
    g = int(hex[3:5], base=16)
    b = int(hex[5:7], base=16)
    return np.array([r, g, b], dtype=np.uint8)


def distance(arr1, arr2):
    return np.linalg.norm(arr1.astype(np.int64) - arr2.astype(np.int64))


@activity.defn
async def calibrate(colors: list[str]) -> dict[str, str]:
    # Load the fixed palette from file, which is in BGR, and convert it to LAB.
    palette = np.load("colors.npy").astype(np.uint8)
    palette = cv2.cvtColor(palette, cv2.COLOR_BGR2Lab)[0]

    # Convert the colors to LAB as well.
    # NOTE: `cv2.cvtColor` requires the input array to be 3-dimentional.
    colors_array = np.stack([hex2rgb(color) for color in colors])
    colors_lab = cv2.cvtColor(colors_array.reshape((1, -1, 3)), cv2.COLOR_RGB2Lab)[0]

    # For each color, find the closest approximation in the fixed palette.
    targets = np.array(
        [min(palette, key=lambda x: distance(x, color)) for color in colors_lab]
    )

    # Convert it back to RGB.
    targets = cv2.cvtColor(targets.reshape((1, -1, 3)), cv2.COLOR_Lab2RGB)[0]
    return {color: rgb2hex(target) for (color, target) in zip(colors, targets)}
