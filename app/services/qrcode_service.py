from io import BytesIO
from textwrap import wrap

import qrcode
from PIL import Image, ImageDraw, ImageFont


def generate_qrcode_image(data: str) -> BytesIO:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(data)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    ).convert("RGB")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer


def load_font(size: int, bold: bool = False):
    try:
        font_path = (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )

        return ImageFont.truetype(font_path, size)
    except OSError:
        return ImageFont.load_default()


def draw_centered_text(draw, text: str, y: int, image_width: int, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    x = (image_width - text_width) // 2

    draw.text(
        (x, y),
        text,
        fill="black",
        font=font,
    )


def generate_product_label_image(
    data: str,
    product_name: str,
    product_category: str,
    product_id: int,
) -> BytesIO:
    qr_buffer = generate_qrcode_image(data)
    qr_image = Image.open(qr_buffer).convert("RGB")

    label_width = max(qr_image.width + 80, 500)
    padding = 30

    title_font = load_font(28, bold=True)
    subtitle_font = load_font(20)
    small_font = load_font(18)

    # Quebra o nome do produto em linhas menores
    product_name_lines = wrap(product_name, width=24)

    title_line_height = 34
    subtitle_height = 28
    footer_height = 28

    text_top_height = len(product_name_lines) * title_line_height
    total_height = (
        padding
        + text_top_height
        + subtitle_height
        + 20
        + qr_image.height
        + 20
        + footer_height
        + padding
    )

    label_image = Image.new(
        "RGB",
        (label_width, total_height),
        "white",
    )

    draw = ImageDraw.Draw(label_image)

    current_y = padding

    for line in product_name_lines:
        draw_centered_text(
            draw=draw,
            text=line,
            y=current_y,
            image_width=label_width,
            font=title_font,
        )
        current_y += title_line_height

    draw_centered_text(
        draw=draw,
        text=product_category,
        y=current_y,
        image_width=label_width,
        font=subtitle_font,
    )

    current_y += subtitle_height + 20

    qr_x = (label_width - qr_image.width) // 2

    label_image.paste(
        qr_image,
        (qr_x, current_y),
    )

    current_y += qr_image.height + 20

    draw_centered_text(
        draw=draw,
        text=f"Produto ID: {product_id}",
        y=current_y,
        image_width=label_width,
        font=small_font,
    )

    buffer = BytesIO()
    label_image.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer