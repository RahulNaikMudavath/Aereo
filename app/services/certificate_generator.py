import os
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont


def get_font(size: int, bold: bool = False, serif: bool = False) -> ImageFont.ImageFont:
    """Load a system font if available, with robust fallback to default."""
    candidate_font_names = []
    
    if os.name == "nt":  # Windows
        fonts_dir = Path("C:/Windows/Fonts")
        if serif:
            candidate_font_names = [
                fonts_dir / ("georgiab.ttf" if bold else "georgia.ttf"),
                fonts_dir / ("timesbd.ttf" if bold else "times.ttf"),
                fonts_dir / ("arialbd.ttf" if bold else "arial.ttf")
            ]
        else:
            candidate_font_names = [
                fonts_dir / ("arialbd.ttf" if bold else "arial.ttf"),
                fonts_dir / ("calibrib.ttf" if bold else "calibri.ttf"),
                fonts_dir / ("segoeui.ttf" if not bold else "segoeuib.ttf")
            ]
    else:  # Linux / MacOS
        if serif:
            candidate_font_names = [
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")
            ]
        else:
            candidate_font_names = [
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
            ]

    for font_path in candidate_font_names:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except Exception:
                continue

    # Fallback to Pillow's built-in font
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def generate_certificate_file(
    recipient_name: str,
    event_name: str,
    issuer_name: str,
    issue_date: str,
    certificate_id: str,
    output_path: Path,
    file_format: str = "pdf"
) -> Path:
    """
    Renders an elegant, high-resolution certificate and saves it as PDF or PNG.
    Canvas: 1754 x 1240 px (A4 Landscape @ 150 DPI).
    """
    width = 1754
    height = 1240

    # Base canvas: Rich Ivory / Off-White
    image = Image.new("RGB", (width, height), color=(253, 252, 248))
    draw = ImageDraw.Draw(image)

    # Color Palette
    navy = (15, 41, 66)
    gold = (184, 134, 11)
    light_gold = (218, 165, 32)
    dark_gray = (55, 65, 81)
    charcoal = (24, 24, 27)

    # 1. Outer Double Decorative Borders
    margin = 50
    draw.rectangle(
        [(margin, margin), (width - margin, height - margin)],
        outline=navy,
        width=8
    )

    inner_margin = margin + 14
    draw.rectangle(
        [(inner_margin, inner_margin), (width - inner_margin, height - inner_margin)],
        outline=gold,
        width=3
    )

    # Corner Decorative Corner Boxes
    corner_size = 28
    for cx, cy in [
        (inner_margin, inner_margin),
        (width - inner_margin - corner_size, inner_margin),
        (inner_margin, height - inner_margin - corner_size),
        (width - inner_margin - corner_size, height - inner_margin - corner_size)
    ]:
        draw.rectangle([(cx, cy), (cx + corner_size, cy + corner_size)], fill=navy, outline=gold, width=2)

    # 2. Top Header Elements
    font_top_badge = get_font(size=22, bold=True)
    badge_text = "✦   OFFICIAL RECOGNITION   ✦"
    draw.text((width / 2, 140), badge_text, fill=gold, font=font_top_badge, anchor="mm")

    font_title = get_font(size=56, bold=True, serif=True)
    draw.text((width / 2, 220), "CERTIFICATE OF ACHIEVEMENT", fill=navy, font=font_title, anchor="mm")

    font_subtitle = get_font(size=20, bold=False)
    draw.text((width / 2, 290), "THIS CERTIFICATE IS PROUDLY PRESENTED TO", fill=dark_gray, font=font_subtitle, anchor="mm")

    # 3. Recipient Name
    font_name = get_font(size=64, bold=True, serif=True)
    draw.text((width / 2, 410), recipient_name, fill=charcoal, font=font_name, anchor="mm")

    # Elegant gold underline below recipient name
    name_line_w = 600
    draw.line(
        [(width / 2 - name_line_w / 2, 470), (width / 2 + name_line_w / 2, 470)],
        fill=gold,
        width=3
    )

    # 4. Event / Course Information
    font_body = get_font(size=22, bold=False)
    draw.text(
        (width / 2, 540),
        "for successfully completing all prescribed requirements and demonstrating excellence in",
        fill=dark_gray,
        font=font_body,
        anchor="mm"
    )

    font_event = get_font(size=40, bold=True, serif=True)
    draw.text((width / 2, 620), event_name, fill=navy, font=font_event, anchor="mm")

    # 5. Footer Details: Date, Official Medallion Seal, and Issuer Signature
    y_footer = 980

    # Left: Date & Certificate ID
    font_meta_label = get_font(size=18, bold=True)
    font_meta_val = get_font(size=20, bold=False)

    draw.text((220, y_footer - 35), "DATE OF ISSUANCE", fill=gold, font=font_meta_label, anchor="mm")
    draw.text((220, y_footer), issue_date, fill=navy, font=font_meta_val, anchor="mm")
    draw.line([(120, y_footer + 20), (320, y_footer + 20)], fill=dark_gray, width=1)
    
    font_id = get_font(size=15, bold=False)
    draw.text((220, y_footer + 45), f"Cert ID: {certificate_id}", fill=dark_gray, font=font_id, anchor="mm")

    # Center: Official Seal / Rosette Medallion
    seal_radius = 65
    seal_cx, seal_cy = width / 2, y_footer - 10
    draw.ellipse(
        [(seal_cx - seal_radius, seal_cy - seal_radius), (seal_cx + seal_radius, seal_cy + seal_radius)],
        fill=(250, 245, 230),
        outline=gold,
        width=4
    )
    draw.ellipse(
        [(seal_cx - seal_radius + 8, seal_cy - seal_radius + 8), (seal_cx + seal_radius - 8, seal_cy + seal_radius - 8)],
        outline=light_gold,
        width=2
    )
    font_seal = get_font(size=14, bold=True)
    draw.text((seal_cx, seal_cy - 12), "OFFICIAL", fill=navy, font=font_seal, anchor="mm")
    draw.text((seal_cx, seal_cy + 12), "VERIFIED", fill=gold, font=font_seal, anchor="mm")

    # Right: Authorized Issuer & Signature Line
    draw.text((width - 220, y_footer - 35), "AUTHORIZED SIGNATURE", fill=gold, font=font_meta_label, anchor="mm")
    draw.line([(width - 320, y_footer + 20), (width - 120, y_footer + 20)], fill=dark_gray, width=1)
    draw.text((width - 220, y_footer), issuer_name, fill=navy, font=font_meta_val, anchor="mm")
    draw.text((width - 220, y_footer + 45), "Authorized Representative", fill=dark_gray, font=font_id, anchor="mm")

    # 6. Save the certificate file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_format_lower = file_format.lower().strip()

    if file_format_lower == "pdf":
        target_file = output_path.with_suffix(".pdf")
        image.convert("RGB").save(str(target_file), "PDF", resolution=150.0)
        return target_file
    else:
        target_file = output_path.with_suffix(".png")
        image.convert("RGB").save(str(target_file), "PNG", optimize=True)
        return target_file
