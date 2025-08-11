import os, json
from PIL import Image, ImageDraw

def _clamp_bbox(bbox, w, h):
    l, t, r, b = bbox
    l = max(0, min(int(l), w))
    t = max(0, min(int(t), h))
    r = max(0, min(int(r), w))
    b = max(0, min(int(b), h))
    if r <= l: r = min(w, l + 1)
    if b <= t: b = min(h, t + 1)
    return (l, t, r, b)

def save_diagrams_from_line_data(image_path, result, base_outdir="diagrams"):
    """
    Quét result['line_data'] -> crop tất cả vùng type=='diagram' theo polygon `cnt`.
    Trả về: list[dict] gồm id, path, bbox, polygon.
    """
    line_data = (result or {}).get("line_data") or []
    diagrams = [ln for ln in line_data if ln.get("type") == "diagram" and ln.get("cnt")]

    if not diagrams:
        return []

    # Thư mục lưu theo tên ảnh gốc để đỡ lẫn
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    outdir = os.path.join(base_outdir, image_name)
    os.makedirs(outdir, exist_ok=True)

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    saved = []

    for idx, d in enumerate(diagrams):
        poly = d.get("cnt")  # [[x,y], ...]
        # Ép int & lọc điểm hợp lệ
        poly_tuples = []
        for p in poly:
            try:
                x, y = int(round(p[0])), int(round(p[1]))
                if 0 <= x <= w and 0 <= y <= h:
                    poly_tuples.append((x, y))
            except Exception:
                pass

        if len(poly_tuples) < 3:
            # Polygon không đủ điểm -> fallback bbox từ min/max
            xs = [p[0] for p in poly if isinstance(p, (list, tuple)) and len(p) == 2]
            ys = [p[1] for p in poly if isinstance(p, (list, tuple)) and len(p) == 2]
            if not xs or not ys:
                continue
            bbox = _clamp_bbox((min(xs), min(ys), max(xs), max(ys)), w, h)
            crop = img.crop(bbox).convert("RGB")
            out_path = os.path.join(outdir, f"diagram_{idx:02d}.png")
            crop.save(out_path)
            saved.append({
                "id": d.get("id"),
                "path": out_path,
                "bbox": bbox,
                "polygon": None
            })
            continue

        # Bbox gọn để cắt mask
        xs = [x for x, _ in poly_tuples]
        ys = [y for _, y in poly_tuples]
        bbox = _clamp_bbox((min(xs), min(ys), max(xs), max(ys)), w, h)

        # Tạo mask polygon & cắt chính xác
        mask_full = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask_full)
        draw.polygon(poly_tuples, fill=255, outline=255)

        # Cắt theo bbox để nhẹ
        mask_crop = mask_full.crop(bbox)
        region = img.crop(bbox)

        # Áp mask để nền ngoài polygon trong bbox trong suốt, rồi lưu RGB (nền trắng)
        out_rgba = Image.new("RGBA", region.size)
        out_rgba.paste(region, (0, 0), mask_crop)

        # Nếu muốn nền trắng:
        bg = Image.new("RGB", region.size, (255, 255, 255))
        bg.paste(out_rgba, mask=out_rgba.split()[-1])

        out_path = os.path.join(outdir, f"diagram_{idx:02d}.png")
        bg.save(out_path, optimize=True)

        saved.append({
            "id": d.get("id"),
            "path": out_path,
            "bbox": bbox,
            "polygon": poly_tuples
        })

    return saved
