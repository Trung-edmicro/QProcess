import os, json, re
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

def save_diagrams_from_line_data(image_path, result, base_outdir=r"data\diagrams"):
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

def insert_diagrams_into_text(raw_text, result, diagram_files, min_gap_px=8):
    """
    Chèn ảnh diagram (đã crop) vào chuỗi text theo thứ tự đọc.
    - raw_text: chuỗi MMD/markdown hiện có (từ Mathpix "text" hoặc "mmd")
    - result: JSON trả về từ Mathpix (chứa line_data)
    - diagram_files: list dict [{id, path, bbox, polygon}] từ hàm crop
    - min_gap_px: ngưỡng khoảng cách dọc để coi là "ngay dưới/ ngay trên"
    Trả về: markdown đã được chèn ![](path)
    """
    line_data = (result or {}).get("line_data") or []
    if not line_data or not diagram_files:
        return raw_text

    # Map id -> path ảnh crop
    id2path = {d["id"]: d["path"] for d in diagram_files if d.get("id") and d.get("path")}

    # Chuẩn hoá items (lấy top/left cho sort)
    def bbox_from_cnt(cnt):
        xs = [p[0] for p in cnt]
        ys = [p[1] for p in cnt]
        return (min(xs), min(ys), max(xs), max(ys))

    items = []
    for ln in line_data:
        cnt = ln.get("cnt")
        if not cnt:
            continue
        l, t, r, b = bbox_from_cnt(cnt)
        typ = ln.get("type")
        items.append({
            "type": typ,
            "id": ln.get("id"),
            "top": t,
            "left": l,
            "bbox": (l, t, r, b),
            "text": ln.get("text", "")
        })

    # Sort: từ trên xuống, trái sang phải
    items.sort(key=lambda x: (x["top"], x["left"]))

    # Lấy list các node văn bản (để chèn ảnh trước node text kế tiếp)
    text_nodes = [it for it in items if it["type"] == "text"]
    diagram_nodes = [it for it in items if it["type"] == "diagram" and it.get("id") in id2path]

    if not text_nodes or not diagram_nodes:
        return raw_text

    # Chia text hiện có thành các dòng (đơn giản) để tìm vị trí chèn.
    # Mẹo: ta sẽ chèn theo nhóm đoạn (đệm 1 dòng trống trước/sau ảnh).
    lines = raw_text.splitlines()

    # Một index chỉ báo chúng ta đang ở đoạn nào theo chiều dọc.
    # Tạo mốc theo thứ tự text_nodes.
    text_order = [{"top": n["top"], "left": n["left"], "text": n["text"]} for n in text_nodes]

    # Map: top của text_node -> (chỉ số dòng “gần nhất” trong raw_text)
    # Cách đơn giản: khớp đoạn text ngắn (tối đa ~40 ký tự) để tìm vị trí xuất hiện đầu tiên.
    def find_line_index_for_text(snippet):
        if not snippet:
            return None
        snip = snippet.strip()
        if not snip:
            return None
        # Lấy 30–50 ký tự đầu để tránh trùng quá nhiều
        probe = snip[:50]
        # escape regex special
        pat = re.escape(probe)
        joined = "\n".join(lines)
        m = re.search(pat, joined)
        if not m:
            return None
        # Quy đổi offset -> chỉ số dòng
        upto = joined[:m.start()]
        line_idx = upto.count("\n")
        return line_idx

    text_line_map = []
    for n in text_order:
        line_idx = find_line_index_for_text(n["text"])
        if line_idx is not None:
            text_line_map.append({"top": n["top"], "line_idx": line_idx})

    # Nếu không khớp được gì, trả nguyên văn
    if not text_line_map:
        return raw_text

    # Sắp xếp theo top tăng dần
    text_line_map.sort(key=lambda x: x["top"])

    # Hàm: tìm vị trí dòng để chèn ảnh dựa trên top của ảnh
    def find_insert_line_for_diagram(di_top):
        # tìm text node đầu tiên có top > di_top - min_gap_px
        for i, m in enumerate(text_line_map):
            if di_top <= m["top"] + min_gap_px:
                return m["line_idx"]
        # nếu ảnh nằm cuối trang: chèn cuối file
        return len(lines)

    # Chèn lần lượt (đi từ dưới lên để không xô lệch chỉ số dòng)
    inserts = []
    for d in diagram_nodes:
        insert_at = find_insert_line_for_diagram(d["top"])
        md_img = f"![]({id2path[d['id']]})"
        # chèn 1 block trống trước/sau cho sạch
        block = ["", md_img, ""]
        inserts.append((insert_at, block))

    # Thực hiện chèn từ insert cuối cùng
    inserts.sort(key=lambda x: x[0], reverse=True)
    for pos, block in inserts:
        lines[pos:pos] = block

    return "\n".join(lines)