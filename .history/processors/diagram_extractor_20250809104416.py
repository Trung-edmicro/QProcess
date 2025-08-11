"""
Diagram Extractor - Module nhận diện và cắt hình vẽ, bảng biểu từ ảnh
"""
import os
import cv2
import numpy as np
from pathlib import Path

class DiagramExtractor:
    """Class xử lý nhận diện và cắt hình vẽ từ ảnh"""
    
    def __init__(self, output_dir="data/images"):
        """
        Khởi tạo DiagramExtractor
        Args:
            output_dir: thư mục lưu ảnh kết quả
        """
        self.output_dir = output_dir
        self.ensure_dir(output_dir)
    
    @staticmethod
    def ensure_dir(path):
        """Tạo thư mục nếu chưa tồn tại"""
        Path(path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def equalize_histogram(gray_image):
        """Tăng tương phản để nét đậm hơn"""
        return cv2.equalizeHist(gray_image)
    
    @staticmethod
    def binarize_image(gray_image):
        """
        Nhị phân hóa ảnh để phát hiện các nét vẽ
        Args:
            gray_image: ảnh xám
        Returns:
            ảnh nhị phân với nét vẽ = 255, nền = 0
        """
        # Adaptive threshold để xử lý tốt với điều kiện ánh sáng khác nhau
        return cv2.adaptiveThreshold(
            gray_image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31, 10
        )
    
    @staticmethod
    def post_process_mask(mask):
        """
        Làm mịn mask bằng morphological operations
        Args:
            mask: ảnh nhị phân
        Returns:
            mask đã được làm mịn
        """
        # Nối các nét đứt bằng close operation
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Loại bỏ noise nhỏ bằng open operation
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open, iterations=1)
        
        return opened
    
    @staticmethod
    def auto_trim_image(bgr_image):
        """
        Tự động cắt sát viền nội dung trong ảnh
        Args:
            bgr_image: ảnh BGR
        Returns:
            ảnh đã được cắt sát viền
        """
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Tìm vùng không phải nền trắng
        non_zero = cv2.findNonZero(255 - thresh)
        if non_zero is None:
            return bgr_image
            
        x, y, w, h = cv2.boundingRect(non_zero)
        return bgr_image[y:y+h, x:x+w]
    
    def extract_diagrams(
        self,
        image_path,
        target_width=1600,
        min_size=80,
        max_area_ratio=0.3,
        aspect_range=(0.2, 4.0),
        solidity_range=(0.2, 0.9),
        padding=10
    ):
        """
        Nhận diện và cắt các hình vẽ, bảng biểu từ ảnh
        
        Args:
            image_path: đường dẫn ảnh input
            target_width: chiều rộng chuẩn hóa để xử lý
            min_size: kích thước tối thiểu (pixel)
            max_area_ratio: tỷ lệ diện tích tối đa so với ảnh gốc
            aspect_range: khoảng tỷ lệ khung hình hợp lệ (width/height)
            solidity_range: khoảng độ đặc của contour
            padding: đệm khi cắt
            
        Returns:
            tuple (preview_path, diagram_paths, stats)
        """
        print(f"🔍 Đang xử lý ảnh: {image_path}")
        
        # Đọc và resize ảnh
        original_image = cv2.imread(image_path)
        if original_image is None:
            raise FileNotFoundError(f"Không thể đọc ảnh: {image_path}")
        
        h0, w0 = original_image.shape[:2]
        scale = target_width / float(w0)
        resized_image = cv2.resize(
            original_image, 
            (target_width, int(h0 * scale)), 
            interpolation=cv2.INTER_AREA
        )
        
        print(f"📏 Kích thước gốc: {w0}x{h0}, đã resize: {target_width}x{int(h0 * scale)}")
        
        # Tiền xử lý ảnh
        gray = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
        gray = self.equalize_histogram(gray)
        mask = self.binarize_image(gray)
        mask = self.post_process_mask(mask)
        
        # Tìm contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"🔎 Tìm thấy {len(contours)} contours")
        
        # Phân tích và lọc contours
        H, W = mask.shape
        valid_boxes = []
        valid_crops = []
        stats = {
            'total_contours': len(contours),
            'filtered_by_size': 0,
            'filtered_by_area': 0, 
            'filtered_by_aspect': 0,
            'filtered_by_solidity': 0,
            'valid_diagrams': 0
        }
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            contour_area = cv2.contourArea(contour)
            
            # Lọc theo kích thước tối thiểu
            if w < min_size or h < min_size:
                stats['filtered_by_size'] += 1
                continue
            
            # Lọc theo diện tích tối đa (loại bỏ vùng text lớn)
            if area > max_area_ratio * H * W:
                stats['filtered_by_area'] += 1
                continue
            
            # Lọc theo tỷ lệ khung hình
            aspect_ratio = w / float(h)
            if not (aspect_range[0] <= aspect_ratio <= aspect_range[1]):
                stats['filtered_by_aspect'] += 1
                continue
            
            # Lọc theo độ đặc (solidity)
            solidity = contour_area / float(area + 1e-6)
            if not (solidity_range[0] <= solidity <= solidity_range[1]):
                stats['filtered_by_solidity'] += 1
                continue
            
            # Cắt vùng với padding
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(W, x + w + padding)
            y_end = min(H, y + h + padding)
            
            crop = resized_image[y_start:y_end, x_start:x_end]
            crop = self.auto_trim_image(crop)
            
            # Kiểm tra kích thước sau khi trim
            if crop.shape[0] < min_size or crop.shape[1] < min_size:
                continue
            
            valid_boxes.append({
                'x': x_start, 'y': y_start, 
                'width': x_end - x_start, 'height': y_end - y_start,
                'area': area, 'aspect_ratio': aspect_ratio, 'solidity': solidity
            })
            valid_crops.append(crop)
            stats['valid_diagrams'] += 1
        
        print(f"✅ Tìm thấy {stats['valid_diagrams']} hình vẽ hợp lệ")
        
        # Sắp xếp theo vị trí từ trên xuống dưới, trái sang phải
        if valid_boxes:
            # Sắp xếp theo y trước, sau đó theo x
            sorted_indices = sorted(
                range(len(valid_boxes)), 
                key=lambda i: (valid_boxes[i]['y'], valid_boxes[i]['x'])
            )
        else:
            sorted_indices = []
        
        # Tạo preview với các bounding boxes
        preview_image = resized_image.copy()
        for i, idx in enumerate(sorted_indices):
            box = valid_boxes[idx]
            # Vẽ rectangle với màu khác nhau
            color = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)][i % 5]
            cv2.rectangle(
                preview_image,
                (box['x'], box['y']),
                (box['x'] + box['width'], box['y'] + box['height']),
                color, 2
            )
            # Thêm số thứ tự
            cv2.putText(
                preview_image, str(i + 1),
                (box['x'] + 5, box['y'] + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
            )
        
        # Lưu preview
        base_name = Path(image_path).stem
        preview_path = os.path.join(self.output_dir, f"{base_name}_preview.png")
        cv2.imwrite(preview_path, preview_image)
        print(f"💾 Đã lưu preview: {preview_path}")
        
        # Lưu các diagram đã cắt
        diagram_paths = []
        for i, idx in enumerate(sorted_indices, 1):
            diagram_path = os.path.join(self.output_dir, f"{base_name}_diagram_{i:02d}.png")
            cv2.imwrite(diagram_path, valid_crops[idx])
            diagram_paths.append(diagram_path)
            print(f"💾 Đã lưu diagram {i}: {diagram_path}")
        
        return preview_path, diagram_paths, stats
    
    def extract_diagrams_from_folder(self, input_folder, file_extensions=None):
        """
        Xử lý tất cả ảnh trong thư mục
        
        Args:
            input_folder: thư mục chứa ảnh input
            file_extensions: danh sách extension được hỗ trợ
            
        Returns:
            dict chứa kết quả xử lý cho từng file
        """
        if file_extensions is None:
            file_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        
        input_path = Path(input_folder)
        if not input_path.exists():
            raise FileNotFoundError(f"Thư mục không tồn tại: {input_folder}")
        
        results = {}
        image_files = []
        
        # Tìm tất cả file ảnh
        for ext in file_extensions:
            image_files.extend(input_path.glob(f"*{ext}"))
            image_files.extend(input_path.glob(f"*{ext.upper()}"))
        
        print(f"🔍 Tìm thấy {len(image_files)} file ảnh trong {input_folder}")
        
        for image_file in image_files:
            try:
                print(f"\n{'='*60}")
                preview, diagrams, stats = self.extract_diagrams(str(image_file))
                results[image_file.name] = {
                    'preview': preview,
                    'diagrams': diagrams,
                    'stats': stats,
                    'success': True
                }
            except Exception as e:
                print(f"❌ Lỗi khi xử lý {image_file.name}: {e}")
                results[image_file.name] = {
                    'error': str(e),
                    'success': False
                }
        
        return results
