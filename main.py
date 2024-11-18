from cairosvg import svg2png

from media_workflow.image_loader import load_image

with open("tests/images/image_svg.svg", "rb") as file:
    png = load_image(file)
    print(png)
