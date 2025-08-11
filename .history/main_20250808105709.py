"""
Main file để test các chức năng OCR và xử lý ảnh
"""
import os
import sys
from config import app_config
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

def test_ocr_image(image_path):
    """Test chức năng OCR ảnh bằng Vertex AI"""
    print("=== TEST OCR IMAGE VỚI VERTEX AI ===")
    
    # Kiểm tra file ảnh có tồn tại không
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy file ảnh: {image_path}")
        return None
    
    print(f"📷 Đang xử lý ảnh: {os.path.basename(image_path)}")
    
    # Kiểm tra cấu hình Vertex AI
    if not app_config.vertex_ai.is_configured():
        print("❌ Vertex AI chưa được cấu hình đúng!")
        return None
    
    try:
        # Khởi tạo Vertex AI
        print("🚀 Đang khởi tạo Vertex AI...")
        if not app_config.vertex_ai.initialize_vertex_ai():
            print("❌ Không thể khởi tạo Vertex AI!")
            return None
        
        # Tạo model
        model = GenerativeModel(app_config.vertex_ai.model_name)
        print(f"✅ Đã khởi tạo model: {app_config.vertex_ai.model_name}")
        
        # Đọc ảnh và tạo Part object
        print("📖 Đang đọc và xử lý ảnh...")
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        
        # Xác định mime type
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.png': 
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'): 
            mime_type = 'image/jpeg'
        elif ext == '.gif': 
            mime_type = 'image/gif'
        elif ext == '.webp': 
            mime_type = 'image/webp'
        else: 
            mime_type = 'image/png'
        
        image_part = Part.from_data(data=image_bytes, mime_type=mime_type)
        print(f"✅ Đã tạo image part với mime type: {mime_type}")
        
        # Tạo prompt cho OCR
        text_prompt = """
        Hãy đọc và trích xuất toàn bộ text từ ảnh này. 
        Yêu cầu:
        1. Đọc chính xác tất cả text có trong ảnh
        2. Giữ nguyên format và cấu trúc của text
        3. Nếu có công thức toán học, hãy chuyển sang định dạng LaTeX
        4. Nếu có bảng biểu, hãy mô tả cấu trúc bảng
        5. Trả về kết quả bằng tiếng Việt
        
        Text trong ảnh:
        """
        
        text_part = Part.from_text(text_prompt)
        
        # Tạo generation config
        generation_config = GenerationConfig(
            temperature=0.1,  # Thấp để OCR chính xác
            top_p=0.8,
            max_output_tokens=8192
        )
        
        # Gọi API
        print("🔄 Đang gửi request đến Vertex AI...")
        prompt_parts = [text_part, image_part]
        
        response = model.generate_content(
            prompt_parts, 
            generation_config=generation_config, 
            stream=False
        )
        
        if response and response.text:
            print("✅ Đã nhận được kết quả OCR!")
            print("\n" + "="*60)
            print("📄 KẾT QUẢ OCR:")
            print("="*60)
            print(response.text)
            print("="*60)
            return response.text
        else:
            print("❌ Không nhận được kết quả từ Vertex AI")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi khi thực hiện OCR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Hàm main để test"""
    print("🎯 BẮT ĐẦU TEST OCR IMAGE")
    print("="*50)
    
    # Hiển thị thông tin cấu hình
    app_config.get_config_summary()
    print()
    
    # Đường dẫn ảnh test
    image_path = os.path.join(app_config.input_folder, "testOCR.png")
    
    # Test OCR
    result = test_ocr_image(image_path)
    
    if result:
        print("\n🎉 TEST THÀNH CÔNG!")
        
        # Lưu kết quả vào file
        output_file = os.path.join(app_config.output_folder, "ocr_result.txt")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=== KẾT QUẢ OCR ===\n")
                f.write(f"File ảnh: {image_path}\n")
                f.write(f"Thời gian: {import_datetime_now()}\n")
                f.write("="*50 + "\n")
                f.write(result)
            print(f"💾 Đã lưu kết quả vào: {output_file}")
        except Exception as e:
            print(f"⚠️ Không thể lưu file: {e}")
    else:
        print("\n❌ TEST THẤT BẠI!")

def import_datetime_now():
    """Helper function để lấy thời gian hiện tại"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    main()