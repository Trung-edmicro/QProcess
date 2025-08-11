import os
import cv2
import numpy as np
from pathlib import Path

def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)

def equalize(gray):
    """Tăng tương phản nhẹ để nét đậm hơn."""
    return cv2.equalizeHist(gray)

def binarize(gray):
    """
    Nhị phân hoá để biến nét đen -> trắng (255) bằng adaptive threshold.
    Nếu ảnh rất đều sáng, bạn có thể thử Otsu thay cho adaptive.
    """
    # ADAPTIVE_THRESH_GAUSSIAN + THRESH_BINARY_INV: nền sáng -> 0, nét -> 255
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 10
    )

def post_process(mask):
    """
    Nối các nét đứt nhỏ bằng đóng (close). Có thể tăng iterations nếu nét quá mảnh.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    return closed

def auto_trim(bgr):
    """
    Cắt sát viền bên trong một crop bằng Otsu + bounding box non-zero.
    """
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    t = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    nz = cv2.findNonZero(255 - t)
    if nz is None:
        return bgr
    x, y, w, h = cv2.boundingRect(nz)
    return bgr[y:y+h, x:x+w]

def detect_diagrams(
    image_path: str,
    out_dir: str = "out_diagrams",
    target_width: int = 1600,
    min_wh: int = 80,             # bỏ nhiễu nhỏ: min chiều rộng/cao
    max_area_ratio: float = 0.2,  # bỏ vùng quá lớn (văn bản lớn)
    aspect_range=(0.3, 2.8),      # tỉ lệ w/h hợp lý cho hình vẽ
    solidity_range=(0.25, 0.85),  # độ “đặc” vùng; line drawings thường trung bình
    pad: int = 8,                  # đệm khi crop bbox
):
    ensure_dir(out_dir)

    # Đọc & resize để chuẩn hoá kích thước xử lý
    img0 = cv2.imread(image_path)
    if img0 is None:
        raise FileNotFoundError(image_path)
    h0, w0 = img0.shape[:2]
    scale = target_width / float(w0)
    img = cv2.resize(img0, (target_width, int(h0 * scale)), interpolation=cv2.INTER_AREA)

    # Tiền xử lý
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = equalize(gray)
    mask = binarize(gray)
    mask = post_process(mask)

    # Tìm contour ngoài
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    H, W = mask.shape
    boxes, crops = [], []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        ca = cv2.contourArea(c)

        if w < min_wh or h < min_wh:
            continue
        if area > max_area_ratio * H * W:
            continue

        aspect = w / float(h)
        if not (aspect_range[0] < aspect < aspect_range[1]):
            continue

        solidity = ca / float(area + 1e-6)
        if not (solidity_range[0] < solidity < solidity_range[1]):
            continue

        # Crop + trim sát bên trong bbox
        xx = max(0, x - pad)
        yy = max(0, y - pad)
        ww = min(W, x + w + pad) - xx
        hh = min(H, y + h + pad) - yy
        crop = img[yy:yy + hh, xx:xx + ww]
        crop = auto_trim(crop)

        # Loại bỏ nếu quá nhỏ sau khi trim
        if crop.shape[0] < min_wh or crop.shape[1] < min_wh:
            continue

        boxes.append((yy, xx, ww, hh))
        crops.append(crop)

    # Sắp xếp từ trên xuống dưới
    order = np.argsort([b[0] for b in boxes])

    # Lưu preview + từng crop
    overlay = img.copy()
    out_paths = []
    for i in order:
        y, x, w, h = boxes[i]
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
    preview_path = os.path.join(out_dir, "preview_boxes.png")
    cv2.imwrite(preview_path, overlay)

    for idx, i in enumerate(order, start=1):
        out_path = os.path.join(out_dir, f"diagram_{idx:02d}.png")
        cv2.imwrite(out_path, crops[i])
        out_paths.append(out_path)

    return preview_path, out_paths

if __name__ == "__main__":
    # ======= CÁCH DÙNG =======
    # 1) Đặt đường dẫn ảnh gốc vào image_path
    image_path = "testOCR1.png"   # -> thay bằng ảnh của bạn
    preview, crops = detect_diagrams(
        image_path,
        out_dir="diagrams_out",
        target_width=1600,
        min_wh=80,
        max_area_ratio=0.2,
        aspect_range=(0.3, 2.8),
        solidity_range=(0.25, 0.85),
        pad=8,
    )
    print("Preview:", preview)
    print("Crops:")
    for p in crops:
        print("  -", p)
