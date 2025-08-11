"""
Demo script để minh họa cách sử dụng DiagramExtractor
"""
from processors.diagram_extractor import DiagramExtractor
import os

def demo_basic_usage():
    """Demo cách sử dụng cơ bản"""
    print("🎯 DEMO: Cách sử dụng cơ bản DiagramExtractor")
    print("="*60)
    
    # Khởi tạo extractor
    extractor = DiagramExtractor(output_dir="data/images")
    
    # Xử lý một ảnh
    image_path = "data/input/testOCR1.png"
    if os.path.exists(image_path):
        print(f"📄 Xử lý: {image_path}")
        
        preview, diagrams, stats = extractor.extract_diagrams(
            image_path,
            min_size=100,           # Chỉ lấy diagram lớn hơn 100px
            max_area_ratio=0.25,    # Không quá 25% diện tích ảnh
            aspect_range=(0.3, 3.0) # Tỷ lệ hợp lý
        )
        
        print(f"✅ Tìm thấy {len(diagrams)} diagrams")
        print(f"🖼️  Preview: {preview}")
        
        return True
    else:
        print(f"❌ Không tìm thấy file: {image_path}")
        return False

def demo_batch_processing():
    """Demo xử lý hàng loạt"""
    print("\n🎯 DEMO: Xử lý hàng loạt")
    print("="*60)
    
    extractor = DiagramExtractor(output_dir="data/images")
    
    # Xử lý tất cả ảnh trong thư mục
    input_folder = "data/input"
    if os.path.exists(input_folder):
        results = extractor.extract_diagrams_from_folder(input_folder)
        
        total_diagrams = sum(len(r.get('diagrams', [])) for r in results.values() if r['success'])
        print(f"✅ Đã xử lý {len(results)} files")
        print(f"📊 Tổng cộng: {total_diagrams} diagrams")
        
        return True
    else:
        print(f"❌ Không tìm thấy thư mục: {input_folder}")
        return False

def demo_different_modes():
    """Demo các chế độ khác nhau"""
    print("\n🎯 DEMO: Các chế độ lọc khác nhau")
    print("="*60)
    
    extractor = DiagramExtractor(output_dir="data/images")
    image_path = "data/input/testOCR1.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy file: {image_path}")
        return False
    
    modes = {
        "Strict (Nghiêm ngặt)": {
            "min_size": 120,
            "max_area_ratio": 0.15,
            "aspect_range": (0.6, 1.8),
            "solidity_range": (0.4, 0.8)
        },
        "Normal (Bình thường)": {
            "min_size": 80,
            "max_area_ratio": 0.3,
            "aspect_range": (0.3, 3.0),
            "solidity_range": (0.25, 0.85)
        },
        "Loose (Lỏng lẻo)": {
            "min_size": 50,
            "max_area_ratio": 0.5,
            "aspect_range": (0.1, 5.0),
            "solidity_range": (0.1, 0.95)
        }
    }
    
    for mode_name, params in modes.items():
        print(f"\n🔧 {mode_name}:")
        try:
            _, diagrams, _ = extractor.extract_diagrams(image_path, **params)
            print(f"   📊 Tìm thấy: {len(diagrams)} diagrams")
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
    
    return True

def demo_integration_example():
    """Demo tích hợp với workflow khác"""
    print("\n🎯 DEMO: Tích hợp với workflow OCR")
    print("="*60)
    
    # Giả lập workflow: Extract diagrams → OCR từng diagram
    extractor = DiagramExtractor(output_dir="data/images")
    
    image_path = "data/input/testOCR1.png"
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy file: {image_path}")
        return False
    
    # Bước 1: Extract diagrams
    print("📋 Bước 1: Extract diagrams...")
    preview, diagrams, stats = extractor.extract_diagrams(
        image_path,
        min_size=80,
        max_area_ratio=0.3
    )
    
    print(f"✅ Đã extract {len(diagrams)} diagrams")
    
    # Bước 2: Giả lập OCR từng diagram (ở đây chỉ in tên file)
    print("📋 Bước 2: Xử lý từng diagram...")
    for i, diagram_path in enumerate(diagrams[:3], 1):  # Chỉ xử lý 3 đầu
        print(f"   📊 Diagram {i}: {os.path.basename(diagram_path)}")
        # Ở đây có thể gọi OCR API hoặc xử lý khác
        
    print("✅ Workflow hoàn thành!")
    return True

def main():
    """Chạy tất cả demos"""
    print("🎬 DIAGRAM EXTRACTOR DEMOS")
    print("="*60)
    
    demos = [
        ("Basic Usage", demo_basic_usage),
        ("Batch Processing", demo_batch_processing), 
        ("Different Modes", demo_different_modes),
        ("Integration Example", demo_integration_example)
    ]
    
    results = []
    for demo_name, demo_func in demos:
        try:
            success = demo_func()
            results.append((demo_name, success))
        except Exception as e:
            print(f"❌ Lỗi trong {demo_name}: {e}")
            results.append((demo_name, False))
    
    # Tổng kết
    print("\n" + "="*60)
    print("📋 TỔNG KẾT DEMOS")
    print("="*60)
    
    for demo_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   {status} {demo_name}")
    
    successful = sum(success for _, success in results)
    total = len(results)
    print(f"\n🎯 Kết quả: {successful}/{total} demos thành công")
    
    print(f"\n📁 Kiểm tra kết quả trong thư mục: data/images/")
    print("💡 Sử dụng: python extract_diagrams.py --help để xem hướng dẫn")

if __name__ == "__main__":
    main()
