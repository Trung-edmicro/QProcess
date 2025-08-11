"""
Main script để nhận diện và cắt hình vẽ từ ảnh
Usage: python extract_diagrams.py [image_path] [options]
"""
import argparse
import os
import sys
from pathlib import Path

# Import DiagramExtractor
try:
    from processors.diagram_extractor import DiagramExtractor
except ImportError:
    print("❌ Không thể import DiagramExtractor")
    print("💡 Kiểm tra lại đường dẫn hoặc cài đặt opencv-python")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Nhận diện và cắt hình vẽ, bảng biểu từ ảnh")
    
    # Arguments chính
    parser.add_argument("input", help="Đường dẫn ảnh hoặc thư mục input")
    parser.add_argument("-o", "--output", default="data/images", 
                       help="Thư mục output (mặc định: data/images)")
    
    # Tham số xử lý
    parser.add_argument("--width", type=int, default=1600,
                       help="Chiều rộng chuẩn hóa (mặc định: 1600)")
    parser.add_argument("--min-size", type=int, default=80,
                       help="Kích thước tối thiểu (mặc định: 80)")
    parser.add_argument("--max-area", type=float, default=0.3,
                       help="Tỷ lệ diện tích tối đa (mặc định: 0.3)")
    parser.add_argument("--padding", type=int, default=10,
                       help="Padding khi cắt (mặc định: 10)")
    
    # Preset modes
    parser.add_argument("--mode", choices=["strict", "normal", "loose"], default="normal",
                       help="Chế độ lọc: strict (nghiêm ngặt), normal (bình thường), loose (lỏng lẻo)")
    
    # Options
    parser.add_argument("--preview-only", action="store_true",
                       help="Chỉ tạo preview, không cắt diagrams")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Hiển thị chi tiết")
    
    args = parser.parse_args()
    
    # Kiểm tra input
    if not os.path.exists(args.input):
        print(f"❌ Không tìm thấy: {args.input}")
        return 1
    
    # Thiết lập parameters theo mode
    if args.mode == "strict":
        aspect_range = (0.5, 2.0)
        solidity_range = (0.3, 0.8)
        min_size = max(100, args.min_size)
        max_area = min(0.2, args.max_area)
    elif args.mode == "loose":
        aspect_range = (0.1, 10.0)
        solidity_range = (0.1, 0.99)
        min_size = min(40, args.min_size)
        max_area = max(0.5, args.max_area)
    else:  # normal
        aspect_range = (0.2, 4.0)
        solidity_range = (0.2, 0.9)
        min_size = args.min_size
        max_area = args.max_area
    
    # Khởi tạo extractor
    extractor = DiagramExtractor(output_dir=args.output)
    
    print(f"🚀 DIAGRAM EXTRACTOR")
    print(f"📁 Input: {args.input}")
    print(f"📁 Output: {args.output}")
    print(f"⚙️  Mode: {args.mode}")
    print(f"📏 Width: {args.width}, Min size: {min_size}")
    print(f"📐 Aspect range: {aspect_range}")
    print(f"🔲 Solidity range: {solidity_range}")
    print("="*60)
    
    try:
        if os.path.isfile(args.input):
            # Xử lý file đơn lẻ
            print(f"🔍 Xử lý file: {args.input}")
            
            preview_path, diagram_paths, stats = extractor.extract_diagrams(
                args.input,
                target_width=args.width,
                min_size=min_size,
                max_area_ratio=max_area,
                aspect_range=aspect_range,
                solidity_range=solidity_range,
                padding=args.padding
            )
            
            print(f"\n📊 THỐNG KÊ:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            print(f"\n📁 KẾT QUẢ:")
            print(f"   🖼️  Preview: {preview_path}")
            print(f"   📊 Diagrams: {len(diagram_paths)}")
            
            if args.verbose and diagram_paths:
                for i, path in enumerate(diagram_paths, 1):
                    print(f"      {i}. {path}")
                    
        elif os.path.isdir(args.input):
            # Xử lý thư mục
            print(f"🔍 Xử lý thư mục: {args.input}")
            
            results = extractor.extract_diagrams_from_folder(args.input)
            
            print(f"\n📊 TỔNG KẾT:")
            total_files = len(results)
            success_files = sum(1 for r in results.values() if r['success'])
            total_diagrams = sum(len(r.get('diagrams', [])) for r in results.values() if r['success'])
            
            print(f"   📁 Tổng files: {total_files}")
            print(f"   ✅ Thành công: {success_files}")
            print(f"   ❌ Lỗi: {total_files - success_files}")
            print(f"   📊 Tổng diagrams: {total_diagrams}")
            
            if args.verbose:
                print(f"\n📋 CHI TIẾT:")
                for filename, result in results.items():
                    if result['success']:
                        diagram_count = len(result['diagrams'])
                        print(f"   ✅ {filename}: {diagram_count} diagrams")
                    else:
                        print(f"   ❌ {filename}: {result['error']}")
        else:
            print(f"❌ {args.input} không phải file hoặc thư mục")
            return 1
            
        print(f"\n🎉 HOÀN THÀNH!")
        print(f"📁 Kiểm tra kết quả trong: {args.output}")
        return 0
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
