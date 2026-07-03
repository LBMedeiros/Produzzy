from functools import lru_cache
from io import BytesIO
from pathlib import Path

import barcode
import qrcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
BRAND_ICON_PATH = ASSETS_DIR / "produzzy-icon.png"
BRAND_BLUE = "#0865f5"
TEXT_COLOR = "#111827"
MUTED_COLOR = "#475569"
BORDER_COLOR = "#d8e0eb"


def mm_to_px(mm: float, dpi: int = 300) -> int:
    return int(round((mm / 25.4) * dpi))


def pt_to_px(pt: float, dpi: int = 300) -> int:
    return int(round((pt / 72) * dpi))


@lru_cache(maxsize=1)
def load_brand_icon() -> Image.Image | None:
    if not BRAND_ICON_PATH.is_file():
        return None

    try:
        with Image.open(BRAND_ICON_PATH) as image:
            return image.convert("RGBA").copy()
    except (OSError, ValueError):
        return None


def resize_contained(image: Image.Image, width: int, height: int) -> Image.Image:
    resized = image.copy()

    try:
        resampling = Image.Resampling.LANCZOS
    except AttributeError:
        resampling = Image.LANCZOS

    resized.thumbnail((width, height), resampling)
    return resized


def paste_centered(
    target: Image.Image,
    image: Image.Image,
    center_x: int,
    center_y: int,
) -> None:
    x = center_x - (image.width // 2)
    y = center_y - (image.height // 2)
    mask = image if image.mode == "RGBA" else None
    target.paste(image, (x, y), mask)


def generate_qrcode_pil(data: str, include_brand_icon: bool = True) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    ).convert("RGB")

    brand_icon = load_brand_icon() if include_brand_icon else None

    if brand_icon is not None:
        plate_size = max(16, int(image.width * 0.2))
        icon_size = max(12, int(image.width * 0.16))
        plate = Image.new("RGB", (plate_size, plate_size), "white")
        plate_draw = ImageDraw.Draw(plate)
        plate_draw.rounded_rectangle(
            (0, 0, plate_size - 1, plate_size - 1),
            radius=max(3, plate_size // 8),
            fill="white",
        )
        paste_centered(
            image,
            plate,
            image.width // 2,
            image.height // 2,
        )
        resized_icon = resize_contained(brand_icon, icon_size, icon_size)
        paste_centered(
            image,
            resized_icon,
            image.width // 2,
            image.height // 2,
        )

    return image


def image_to_png_buffer(image: Image.Image, dpi: int | None = None) -> BytesIO:
    buffer = BytesIO()
    save_options = {"format": "PNG"}

    if dpi:
        save_options["dpi"] = (dpi, dpi)

    image.save(buffer, **save_options)
    buffer.seek(0)
    return buffer


def generate_qrcode_image(data: str) -> BytesIO:
    return image_to_png_buffer(generate_qrcode_pil(data))


def wrap_text_without_truncation(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
) -> list[str]:
    words = str(text).strip().split()

    if not words:
        return [""]

    lines: list[str] = []
    current_line = ""

    for word in words:
        candidate = f"{current_line} {word}".strip()

        if text_size(draw, candidate, font)[0] <= max_width:
            current_line = candidate
            continue

        if current_line:
            lines.append(current_line)
            current_line = ""

        if text_size(draw, word, font)[0] <= max_width:
            current_line = word
            continue

        word_part = ""

        for character in word:
            candidate_part = f"{word_part}{character}"

            if word_part and text_size(draw, candidate_part, font)[0] > max_width:
                lines.append(word_part)
                word_part = character
            else:
                word_part = candidate_part

        current_line = word_part

    if current_line:
        lines.append(current_line)

    return lines or [""]


def fit_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    initial_size: int,
    min_size: int,
    max_lines: int,
):
    font_size = initial_size

    while True:
        font = load_font(font_size, bold=True)
        lines = wrap_text_without_truncation(draw, text, font, max_width)

        if len(lines) <= max_lines or font_size <= min_size:
            return font, lines

        font_size -= 2


def generate_product_qrcode_pil(
    data: str,
    product_name: str,
) -> Image.Image:
    qr_image = generate_qrcode_pil(data)
    horizontal_padding = max(40, qr_image.width // 12)
    top_padding = max(30, qr_image.width // 16)
    bottom_padding = horizontal_padding
    text_gap = max(20, qr_image.width // 24)
    canvas_width = qr_image.width + (horizontal_padding * 2)
    measurement_image = Image.new("RGB", (canvas_width, 1), "white")
    measurement_draw = ImageDraw.Draw(measurement_image)
    name_font, name_lines = fit_wrapped_text(
        measurement_draw,
        product_name,
        max_width=canvas_width - (horizontal_padding * 2),
        initial_size=max(28, qr_image.width // 14),
        min_size=18,
        max_lines=3,
    )
    name_line_height = max(
        text_size(measurement_draw, "Ag", name_font)[1],
        getattr(name_font, "size", 18),
    )
    text_height = len(name_lines) * name_line_height
    qr_top = top_padding + text_height + text_gap
    canvas_height = qr_top + qr_image.height + bottom_padding
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)

    for index, line in enumerate(name_lines):
        draw_centered_text(
            draw,
            line,
            top_padding + (index * name_line_height),
            canvas_width,
            name_font,
        )

    canvas.paste(qr_image, (horizontal_padding, qr_top))
    return canvas


def generate_product_qrcode_image(
    data: str,
    product_name: str,
) -> BytesIO:
    return image_to_png_buffer(
        generate_product_qrcode_pil(
            data=data,
            product_name=product_name,
        )
    )


def get_product_barcode_value(product) -> str:
    product_id = getattr(product, "id", product)

    try:
        numeric_id = int(product_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("O produto precisa ter um ID numérico válido.") from exc

    if numeric_id <= 0:
        raise ValueError("O produto precisa ter um ID numérico válido.")

    return f"{numeric_id:09d}"


def generate_product_barcode(product) -> Image.Image:
    barcode_value = get_product_barcode_value(product)
    code128 = barcode.get("code128", barcode_value, writer=ImageWriter())
    return code128.render(
        writer_options={
            "background": "white",
            "foreground": "black",
            "module_height": 13,
            "module_width": 0.32,
            "quiet_zone": 1.5,
            "write_text": False,
            "dpi": 300,
        }
    ).convert("RGB")


def generate_product_barcode_image(product) -> BytesIO:
    return image_to_png_buffer(generate_product_barcode(product), dpi=300)


def load_font(size: int, bold: bool = False):
    font_names = (
        ("DejaVuSans-Bold.ttf", "Arial Bold.ttf")
        if bold
        else ("DejaVuSans.ttf", "Arial.ttf")
    )

    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, max(8, size))
        except OSError:
            continue

    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    image_width: int,
    font,
    fill: str = TEXT_COLOR,
) -> int:
    width, height = text_size(draw, text, font)
    draw.text(((image_width - width) // 2, y), text, fill=fill, font=font)
    return height


def wrap_text_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
    max_lines: int = 2,
) -> list[str]:
    words = str(text).strip().split()

    if not words:
        return [""]

    lines: list[str] = []
    current_line = ""

    for word in words:
        candidate = f"{current_line} {word}".strip()

        if text_size(draw, candidate, font)[0] <= max_width:
            current_line = candidate
            continue

        if current_line:
            lines.append(current_line)
            current_line = word
        else:
            lines.append(word)
            current_line = ""

        if len(lines) == max_lines:
            break

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    consumed_text = " ".join(lines)

    if consumed_text != " ".join(words) and lines:
        last_line = lines[-1]

        while last_line and text_size(draw, f"{last_line}…", font)[0] > max_width:
            last_line = last_line[:-1].rstrip()

        lines[-1] = f"{last_line}…"

    for index, line in enumerate(lines):
        if text_size(draw, line, font)[0] <= max_width:
            continue

        truncated_line = line

        while (
            truncated_line
            and text_size(draw, f"{truncated_line}…", font)[0] > max_width
        ):
            truncated_line = truncated_line[:-1].rstrip()

        lines[index] = f"{truncated_line}…"

    return lines


def draw_fallback_brand_icon(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(
        box,
        radius=max(2, (right - left) // 6),
        fill=BRAND_BLUE,
    )
    line_width = max(2, (right - left) // 12)
    draw.line(
        ((left + right) // 2, top + line_width, (left + right) // 2, bottom),
        fill="white",
        width=line_width,
    )
    draw.line(
        (
            left + line_width,
            (top + bottom) // 2,
            right - line_width,
            (top + bottom) // 2,
        ),
        fill="white",
        width=line_width,
    )


def generate_product_label_pil(
    data: str,
    product_name: str,
    product_category: str,
    product_id: int,
    label_width_mm: float = 70,
    label_height_mm: float = 42,
    qr_size_mm: float | None = None,
    dpi: int = 300,
) -> Image.Image:
    label_width_px = mm_to_px(label_width_mm, dpi)
    label_height_px = mm_to_px(label_height_mm, dpi)
    scale = min(label_width_px / 600, label_height_px / 360)
    border_width = max(1, round(2 * scale))
    padding = max(10, round(22 * scale))

    label_image = Image.new("RGB", (label_width_px, label_height_px), "white")
    draw = ImageDraw.Draw(label_image)
    draw.rounded_rectangle(
        (
            border_width,
            border_width,
            label_width_px - border_width - 1,
            label_height_px - border_width - 1,
        ),
        radius=max(6, round(14 * scale)),
        fill="white",
        outline=BORDER_COLOR,
        width=border_width,
    )

    brand_font = load_font(round(31 * scale), bold=True)
    name_font_size = round(27 * scale)
    code_font = load_font(round(17 * scale), bold=True)
    category_font = load_font(round(13 * scale))
    brand_icon = load_brand_icon()

    brand_text_width, brand_text_height = text_size(draw, "Produzzy", brand_font)
    brand_icon_size = max(22, round(48 * scale))
    brand_gap = max(6, round(10 * scale))
    brand_width = brand_icon_size + brand_gap + brand_text_width
    brand_left = (label_width_px - brand_width) // 2
    brand_top = max(padding // 2, round(22 * scale))

    if brand_icon is not None:
        resized_brand_icon = resize_contained(
            brand_icon,
            brand_icon_size,
            brand_icon_size,
        )
        paste_centered(
            label_image,
            resized_brand_icon,
            brand_left + (brand_icon_size // 2),
            brand_top + (brand_icon_size // 2),
        )
    else:
        draw_fallback_brand_icon(
            draw,
            (
                brand_left,
                brand_top,
                brand_left + brand_icon_size,
                brand_top + brand_icon_size,
            ),
        )

    draw.text(
        (
            brand_left + brand_icon_size + brand_gap,
            brand_top + ((brand_icon_size - brand_text_height) // 2) - round(2 * scale),
        ),
        "Produzzy",
        fill=TEXT_COLOR,
        font=brand_font,
    )

    max_name_width = label_width_px - (padding * 2)

    while True:
        name_font = load_font(name_font_size, bold=True)
        name_lines = wrap_text_to_width(
            draw,
            product_name,
            name_font,
            max_name_width,
            max_lines=2,
        )

        if len(name_lines) <= 1 or name_font_size <= round(19 * scale):
            break

        name_font_size -= max(1, round(2 * scale))

    name_line_height = max(text_size(draw, "Ag", name_font)[1], round(20 * scale))
    name_top = round(91 * scale)

    for index, line in enumerate(name_lines):
        draw_centered_text(
            draw,
            line,
            name_top + (index * round(name_line_height * 1.14)),
            label_width_px,
            name_font,
        )

    lower_top = max(
        round(171 * scale),
        name_top + round(len(name_lines) * name_line_height * 1.2) + round(8 * scale),
    )
    lower_bottom = label_height_px - padding
    lower_height = max(80, lower_bottom - lower_top)

    requested_qr_size = mm_to_px(qr_size_mm, dpi) if qr_size_mm else lower_height
    qr_size = min(requested_qr_size, lower_height, round(label_width_px * 0.3))
    qr_image = resize_qrcode(generate_qrcode_pil(data), qr_size)
    qr_x = padding + max(0, (round(label_width_px * 0.33) - padding - qr_size) // 2)
    qr_y = lower_top + max(0, (lower_height - qr_size) // 2)
    label_image.paste(qr_image, (qr_x, qr_y))

    barcode_left = round(label_width_px * 0.39)
    barcode_right = label_width_px - padding
    barcode_width = max(40, barcode_right - barcode_left)
    barcode_height = max(34, round(lower_height * 0.54))
    barcode_image = resize_contained(
        generate_product_barcode(product_id),
        barcode_width,
        barcode_height,
    )
    barcode_x = barcode_left + ((barcode_width - barcode_image.width) // 2)
    barcode_y = lower_top + max(0, round(lower_height * 0.04))
    label_image.paste(barcode_image, (barcode_x, barcode_y))

    barcode_value = get_product_barcode_value(product_id)
    code_y = min(
        lower_bottom - text_size(draw, barcode_value, code_font)[1],
        barcode_y + barcode_image.height + round(7 * scale),
    )
    code_width, _ = text_size(draw, barcode_value, code_font)
    draw.text(
        (barcode_left + ((barcode_width - code_width) // 2), code_y),
        barcode_value,
        fill=TEXT_COLOR,
        font=code_font,
    )

    category_text = str(product_category or "").strip()

    if category_text and label_height_px >= round(390 * scale):
        category_width, category_height = text_size(draw, category_text, category_font)
        draw.text(
            (
                label_width_px - padding - category_width,
                label_height_px - padding - category_height,
            ),
            category_text,
            fill=MUTED_COLOR,
            font=category_font,
        )

    return label_image


def resize_qrcode(qr_image: Image.Image, size: int) -> Image.Image:
    try:
        resampling = Image.Resampling.NEAREST
    except AttributeError:
        resampling = Image.NEAREST

    return qr_image.resize((size, size), resampling)


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
        label_width_mm=70,
        label_height_mm=42,
        dpi=216,
    )
    return image_to_png_buffer(label_image, dpi=216)


def generate_products_labels_sheet_image(
    labels_data: list[dict],
    label_width_mm: float = 70,
    label_height_mm: float = 42,
    qr_size_mm: float | None = None,
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

    return image_to_png_buffer(sheet_image, dpi=dpi)


def generate_print_qrcode_card_pil(
    data: str,
    product_name: str,
    product_id: int,
    width: int,
    height: int,
) -> Image.Image:
    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)
    border_width = max(2, width // 240)
    padding = max(18, width // 22)
    draw.rounded_rectangle(
        (
            border_width,
            border_width,
            width - border_width - 1,
            height - border_width - 1,
        ),
        radius=max(8, width // 28),
        fill="white",
        outline=BORDER_COLOR,
        width=border_width,
    )

    name_font, name_lines = fit_wrapped_text(
        draw,
        product_name,
        max_width=width - (padding * 2),
        initial_size=max(24, width // 18),
        min_size=max(14, width // 34),
        max_lines=3,
    )
    name_line_height = max(
        text_size(draw, "Ag", name_font)[1],
        getattr(name_font, "size", 16),
    )
    name_top = padding

    for index, line in enumerate(name_lines):
        draw_centered_text(
            draw,
            line,
            name_top + (index * name_line_height),
            width,
            name_font,
        )

    code_font = load_font(max(14, width // 34), bold=True)
    barcode_value = get_product_barcode_value(product_id)
    code_height = text_size(draw, barcode_value, code_font)[1]
    code_bottom = height - padding
    code_top = code_bottom - code_height
    qr_top = name_top + (len(name_lines) * name_line_height) + max(12, padding // 2)
    qr_bottom = code_top - max(12, padding // 2)
    qr_size = min(
        width - (padding * 2),
        max(1, qr_bottom - qr_top),
    )
    qr_image = resize_qrcode(generate_qrcode_pil(data), qr_size)
    paste_centered(
        card,
        qr_image,
        width // 2,
        qr_top + (qr_size // 2),
    )
    draw_centered_text(
        draw,
        barcode_value,
        code_top,
        width,
        code_font,
        fill=MUTED_COLOR,
    )
    return card


def generate_products_qrcodes_sheet_image(
    qrcodes_data: list[dict],
    dpi: int = 300,
) -> BytesIO:
    sheet_width_px = mm_to_px(210, dpi)
    sheet_height_px = mm_to_px(297, dpi)
    margin_px = mm_to_px(8, dpi)
    gap_px = mm_to_px(3, dpi)
    card_width_px = mm_to_px(46, dpi)
    card_height_px = mm_to_px(64, dpi)
    columns = max(
        1,
        (sheet_width_px - (margin_px * 2) + gap_px)
        // (card_width_px + gap_px),
    )
    rows = max(
        1,
        (sheet_height_px - (margin_px * 2) + gap_px)
        // (card_height_px + gap_px),
    )
    max_qrcodes_per_page = columns * rows
    sheet_image = Image.new(
        "RGB",
        (sheet_width_px, sheet_height_px),
        "white",
    )

    for index, qrcode_data in enumerate(qrcodes_data[:max_qrcodes_per_page]):
        row = index // columns
        column = index % columns
        x = margin_px + column * (card_width_px + gap_px)
        y = margin_px + row * (card_height_px + gap_px)
        card = generate_print_qrcode_card_pil(
            data=qrcode_data["data"],
            product_name=qrcode_data["product_name"],
            product_id=qrcode_data["product_id"],
            width=card_width_px,
            height=card_height_px,
        )
        sheet_image.paste(card, (x, y))

    return image_to_png_buffer(sheet_image, dpi=dpi)
