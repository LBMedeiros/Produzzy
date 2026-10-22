from functools import lru_cache
from io import BytesIO
from pathlib import Path

import barcode
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps


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


def get_product_barcode_value(product) -> str:
    product_id = getattr(product, "id", product)

    try:
        numeric_id = int(product_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("O produto precisa ter um ID numérico válido.") from exc

    if numeric_id <= 0:
        raise ValueError("O produto precisa ter um ID numérico válido.")

    return f"{numeric_id:09d}"


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


def resize_qrcode(qr_image: Image.Image, size: int) -> Image.Image:
    try:
        resampling = Image.Resampling.NEAREST
    except AttributeError:
        resampling = Image.NEAREST

    return qr_image.resize((size, size), resampling)


# --- Print sheet (docs/redesign Fase 5): selected products, QR or barcode,
# N copies, A4 pages in 3 columns. QR codes keep the brand icon in the
# centre (generate_qrcode_pil, error correction H).

PRINT_SHEET_DPI = 200
PRINT_SHEET_COLUMNS = 3
PRINT_SHEET_MAX_LABELS = 120
_A4_MM = (210, 297)
_SHEET_MARGIN_MM = 8
_SHEET_GAP_MM = 3
_CARD_HEIGHT_MM = 30
_CARD_QR_MM = 24


def ellipsize_to_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    text = str(text or "").strip()

    if text_size(draw, text, font)[0] <= max_width:
        return text

    while text and text_size(draw, f"{text}…", font)[0] > max_width:
        text = text[:-1]

    return f"{text.rstrip()}…"


def draw_barcode_bars(
    draw: ImageDraw.ImageDraw,
    barcode_value: str,
    left: int,
    top: int,
    max_width: int,
    height: int,
) -> int:
    """Code128 drawn with a whole number of pixels per module, so the bars stay
    sharp (no resampling). Returns the drawn width."""
    modules = barcode.get("code128", barcode_value).build()[0]
    module_px = max(1, max_width // len(modules))

    for index, module in enumerate(modules):
        if module == "1":
            x = left + index * module_px
            draw.rectangle((x, top, x + module_px - 1, top + height - 1), fill="black")

    return len(modules) * module_px


def fit_label_name(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    dpi: int,
):
    """Same bold size on every label (9 pt), up to two lines; only very long
    names shrink (down to 8 pt) and then get an ellipsis."""
    for size_pt in (9, 8.5, 8):
        font = load_font(pt_to_px(size_pt, dpi), bold=True)
        lines = wrap_text_without_truncation(draw, text, font, max_width)
        if len(lines) <= 2:
            return font, lines

    return font, [
        lines[0],
        ellipsize_to_width(draw, " ".join(lines[1:]), font, max_width),
    ]


def generate_print_label_card_pil(
    data: str,
    product_name: str,
    product_id: int,
    width: int,
    height: int,
    dpi: int = PRINT_SHEET_DPI,
) -> Image.Image:
    """Single label with both codes: QR Code (brand icon in the centre) on the
    left; the product name on top and the Code128 barcode at the bottom on the
    right, both lined up with the QR Code's edges."""
    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)
    border_width = max(2, width // 240)
    padding = mm_to_px(2.5, dpi)
    draw.rounded_rectangle(
        (border_width, border_width, width - border_width - 1, height - border_width - 1),
        radius=max(8, width // 28),
        fill="white",
        outline=BORDER_COLOR,
        width=border_width,
    )

    qr_size = min(mm_to_px(_CARD_QR_MM, dpi), height - padding * 2)
    qr_image = resize_qrcode(generate_qrcode_pil(data), qr_size)
    qr_left = padding
    qr_top = (height - qr_size) // 2
    card.paste(qr_image, (qr_left, qr_top))

    # The QR image has a white quiet zone: align to its dark modules instead.
    dark_box = ImageOps.invert(qr_image.convert("L")).getbbox() or (0, 0, qr_size, qr_size)
    content_top = qr_top + dark_box[1]
    content_bottom = qr_top + dark_box[3]
    right_left = qr_left + dark_box[2] + mm_to_px(2.8, dpi)
    right_width = width - right_left - padding

    name_font, name_lines = fit_label_name(draw, str(product_name).strip(), right_width, dpi)
    name_line_height = round(getattr(name_font, "size", 16) * 1.2)
    # textbbox top offset: put the cap line exactly on the QR's top edge.
    name_offset = draw.textbbox((0, 0), "A", font=name_font)[1]

    for index, line in enumerate(name_lines):
        draw.text(
            (right_left, content_top - name_offset + index * name_line_height),
            line,
            fill=TEXT_COLOR,
            font=name_font,
        )

    barcode_value = get_product_barcode_value(product_id)
    digits_font = load_font(pt_to_px(7, dpi), bold=True)
    digits_box = draw.textbbox((0, 0), barcode_value, font=digits_font)
    digits_top = content_bottom - digits_box[3]
    bars_bottom = digits_top + digits_box[1] - mm_to_px(1, dpi)
    name_bottom = content_top + len(name_lines) * name_line_height
    # Bars as tall as possible (up to 9 mm) while keeping air below the name.
    bars_height = max(mm_to_px(5, dpi), min(mm_to_px(9, dpi), bars_bottom - name_bottom - mm_to_px(2, dpi)))
    bars_top = bars_bottom - bars_height
    bars_width = draw_barcode_bars(
        draw, barcode_value, right_left, bars_top, right_width, bars_height
    )
    digits_width = digits_box[2] - digits_box[0]
    draw.text(
        (right_left + max(0, (bars_width - digits_width) // 2) - digits_box[0], digits_top),
        barcode_value,
        fill=MUTED_COLOR,
        font=digits_font,
    )
    return card


def generate_print_sheet_pages(
    items: list[dict],
    dpi: int = PRINT_SHEET_DPI,
    columns: int = PRINT_SHEET_COLUMNS,
) -> list[Image.Image]:
    """One A4 image per page. `items`: data, product_name, product_id
    (already repeated for copies)."""
    sheet_width = mm_to_px(_A4_MM[0], dpi)
    sheet_height = mm_to_px(_A4_MM[1], dpi)
    margin = mm_to_px(_SHEET_MARGIN_MM, dpi)
    gap = mm_to_px(_SHEET_GAP_MM, dpi)
    card_width = (sheet_width - margin * 2 - gap * (columns - 1)) // columns
    card_height = mm_to_px(_CARD_HEIGHT_MM, dpi)
    rows = max(1, (sheet_height - margin * 2 + gap) // (card_height + gap))
    per_page = columns * rows
    pages = []

    for index, item in enumerate(items):
        position = index % per_page
        if position == 0:
            pages.append(Image.new("RGB", (sheet_width, sheet_height), "white"))

        x = margin + (position % columns) * (card_width + gap)
        y = margin + (position // columns) * (card_height + gap)
        card = generate_print_label_card_pil(
            data=item["data"],
            product_name=item["product_name"],
            product_id=item["product_id"],
            width=card_width,
            height=card_height,
            dpi=dpi,
        )
        pages[-1].paste(card, (x, y))

    return pages


def pages_to_png_buffer(pages: list[Image.Image], dpi: int = PRINT_SHEET_DPI) -> BytesIO:
    # Pages stacked into one tall PNG, like the other sheet endpoints.
    width, height = pages[0].size
    sheet = Image.new("RGB", (width, height * len(pages)), "white")

    for index, page in enumerate(pages):
        sheet.paste(page, (0, index * height))

    return image_to_png_buffer(sheet, dpi=dpi)


def pages_to_pdf_buffer(pages: list[Image.Image], dpi: int = PRINT_SHEET_DPI) -> BytesIO:
    buffer = BytesIO()
    pages[0].save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=dpi,
    )
    buffer.seek(0)
    return buffer
