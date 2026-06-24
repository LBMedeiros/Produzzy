from io import BytesIO
from textwrap import wrap

import qrcode
from PIL import Image, ImageDraw, ImageFont


def mm_to_px(mm: float, dpi: int = 300) -> int:
    return int((mm / 25.4) * dpi)


def pt_to_px(pt: float, dpi: int = 300) -> int:
    return int((pt / 72) * dpi)


def generate_qrcode_pil(data: str) -> Image.Image:
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

    return image


def generate_qrcode_image(data: str) -> BytesIO:
    image = generate_qrcode_pil(data)

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


def resize_qrcode(qr_image: Image.Image, size: int) -> Image.Image:
    try:
        resampling = Image.Resampling.NEAREST
    except AttributeError:
        resampling = Image.NEAREST

    return qr_image.resize((size, size), resampling)


def generate_product_label_pil(
    data: str,
    product_name: str,
    product_category: str,
    product_id: int,
    label_width_mm: int = 70,
    label_height_mm: int = 90,
    qr_size_mm: int = 45,
    dpi: int = 300,
) -> Image.Image:
    label_width_px = mm_to_px(label_width_mm, dpi)
    label_height_px = mm_to_px(label_height_mm, dpi)
    qr_size_px = mm_to_px(qr_size_mm, dpi)

    padding_top = mm_to_px(5, dpi)

    title_font = load_font(pt_to_px(12, dpi), bold=True)
    subtitle_font = load_font(pt_to_px(9, dpi))
    small_font = load_font(pt_to_px(8, dpi))

    label_image = Image.new(
        "RGB",
        (label_width_px, label_height_px),
        "white",
    )

    draw = ImageDraw.Draw(label_image)

    product_name_lines = wrap(product_name, width=22)

    if len(product_name_lines) > 2:
        product_name_lines = product_name_lines[:2]
        product_name_lines[-1] = product_name_lines[-1][:19] + "..."

    current_y = padding_top

    for line in product_name_lines:
        draw_centered_text(
            draw=draw,
            text=line,
            y=current_y,
            image_width=label_width_px,
            font=title_font,
        )
        current_y += mm_to_px(7, dpi)

    draw_centered_text(
        draw=draw,
        text=product_category,
        y=current_y,
        image_width=label_width_px,
        font=subtitle_font,
    )

    qr_image = generate_qrcode_pil(data)
    qr_image = resize_qrcode(qr_image, qr_size_px)

    qr_x = (label_width_px - qr_image.width) // 2
    qr_y = mm_to_px(25, dpi)

    label_image.paste(
        qr_image,
        (qr_x, qr_y),
    )

    footer_y = label_height_px - mm_to_px(10, dpi)

    draw_centered_text(
        draw=draw,
        text=f"Produto ID: {product_id}",
        y=footer_y,
        image_width=label_width_px,
        font=small_font,
    )

    return label_image


def generate_product_label_image(
    data: str,
    product_name: str,
    product_category: str,
    product_id: int,
) -> BytesIO:
    label_image = generate_product_label_pil(
        data=data,
        product_name=product_name,
        product_category=product_category,
        product_id=product_id,
    )

    buffer = BytesIO()
    label_image.save(buffer, format="PNG", dpi=(300, 300))
    buffer.seek(0)

    return buffer


def generate_products_labels_sheet_image(
    labels_data: list[dict],
    label_width_mm: int = 70,
    label_height_mm: int = 90,
    qr_size_mm: int = 45,
    dpi: int = 300,
) -> BytesIO:
    a4_width_mm = 210
    a4_height_mm = 297

    margin_mm = 8
    gap_mm = 3

    sheet_width_px = mm_to_px(a4_width_mm, dpi)
    sheet_height_px = mm_to_px(a4_height_mm, dpi)

    margin_px = mm_to_px(margin_mm, dpi)
    gap_px = mm_to_px(gap_mm, dpi)

    label_width_px = mm_to_px(label_width_mm, dpi)
    label_height_px = mm_to_px(label_height_mm, dpi)

    columns = max(
        1,
        (sheet_width_px - (margin_px * 2) + gap_px)
        // (label_width_px + gap_px),
    )

    rows = max(
        1,
        (sheet_height_px - (margin_px * 2) + gap_px)
        // (label_height_px + gap_px),
    )

    max_labels_per_page = columns * rows

    sheet_image = Image.new(
        "RGB",
        (sheet_width_px, sheet_height_px),
        "white",
    )

    draw = ImageDraw.Draw(sheet_image)

    for index, label_data in enumerate(labels_data[:max_labels_per_page]):
        row = index // columns
        column = index % columns

        x = margin_px + column * (label_width_px + gap_px)
        y = margin_px + row * (label_height_px + gap_px)

        label_image = generate_product_label_pil(
            data=label_data["data"],
            product_name=label_data["product_name"],
            product_category=label_data["product_category"],
            product_id=label_data["product_id"],
            label_width_mm=label_width_mm,
            label_height_mm=label_height_mm,
            qr_size_mm=qr_size_mm,
            dpi=dpi,
        )

        sheet_image.paste(label_image, (x, y))

        draw.rectangle(
            [
                x,
                y,
                x + label_width_px,
                y + label_height_px,
            ],
            outline="black",
            width=2,
        )

    buffer = BytesIO()
    sheet_image.save(buffer, format="PNG", dpi=(dpi, dpi))
    buffer.seek(0)

    return buffer