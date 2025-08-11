"""
Cấu hình API cho Mathpix
"""
import os
import json
import requests
from dotenv import load_dotenv
from sqlalchemy import true

# Load environment variables
load_dotenv()

class MathpixConfig:
    """Cấu hình cho Mathpix API"""
    
    def __init__(self):
        self.app_key = os.getenv('MATHPIX_APP_KEY')
        self.app_id = os.getenv('MATHPIX_APP_ID')
        self.pdf_base_url = "https://api.mathpix.com/v3/pdf"
        self.text_base_url = "https://api.mathpix.com/v3/text"
        
    def get_headers(self):
        """Trả về headers cho Mathpix API"""
        return {
            "app_id": self.app_id,
            "app_key": self.app_key
        }
    
    def is_configured(self):
        """Kiểm tra xem API đã được cấu hình chưa"""
        return bool(self.app_key and self.app_id)
    
    def get_upload_url(self):
        """Trả về URL để upload PDF"""
        return self.pdf_base_url
    
    def get_image_url(self):
        """Trả về URL để OCR ảnh"""
        return self.text_base_url
    
    def get_status_url(self, pdf_id):
        """Trả về URL để check status của PDF"""
        return f"{self.pdf_base_url}/{pdf_id}"
    
    def get_download_url(self, pdf_id, format_type="docx"):
        """Trả về URL để download file đã convert"""
        return f"{self.pdf_base_url}/{pdf_id}.{format_type}"
    
    def ocr_image(self, image_path, options=None):
        """
        OCR một ảnh bằng Mathpix API
        Args:
            image_path: đường dẫn đến file ảnh
            options: dict các tùy chọn OCR
        Returns:
            dict response từ API hoặc None nếu lỗi
        """
        if not self.is_configured():
            print("❌ Mathpix chưa được cấu hình!")
            return None
            
        if not os.path.exists(image_path):
            print(f"❌ Không tìm thấy file ảnh: {image_path}")
            return None
        
        if not self.is_supported_image(image_path):
            print(f"❌ Format ảnh không được hỗ trợ: {image_path}")
            print(f"💡 Các format được hỗ trợ: {', '.join(self.get_supported_formats())}")
            return None
        
        # Default options
        default_options = {
            "formats": ["mmd"],
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True,
            "include_annotated_image": True,
            "include_image_links": True,
        }
        
        if options:
            default_options.update(options)
        
        try:
            print(f"🔄 Đang OCR ảnh: {os.path.basename(image_path)}")
            
            with open(image_path, "rb") as f:
                response = requests.post(
                    self.text_base_url,
                    files={"file": f},
                    data={
                        "options_json": json.dumps(default_options)
                    },
                    headers=self.get_headers()
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ OCR thành công! Confidence: {result.get('confidence', 'N/A')}")
                return result
            else:
                print(f"❌ Lỗi API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi OCR ảnh: {str(e)}")
            return None
    
    def ocr_image_with_custom_options(self, image_path, **kwargs):
        """
        OCR ảnh với các tùy chọn tùy chỉnh
        Args:
            image_path: đường dẫn ảnh
            **kwargs: các tùy chọn OCR
                - math_inline_delimiters: list delimiters cho math inline
                - math_display_delimiters: list delimiters cho math display  
                - rm_spaces: bool remove extra spaces
                - rm_fonts: bool remove font info
                - numbers_default_to_math: bool convert numbers to math
        """
        return self.ocr_image(image_path, kwargs)
    
    def batch_ocr_images(self, image_paths, options=None):
        """
        OCR nhiều ảnh cùng lúc
        Args:
            image_paths: list đường dẫn ảnh
            options: dict tùy chọn OCR
        Returns:
            list kết quả OCR cho từng ảnh
        """
        results = []
        
        print(f"🔄 Bắt đầu batch OCR {len(image_paths)} ảnh...")
        
        for i, image_path in enumerate(image_paths, 1):
            print(f"\n📄 [{i}/{len(image_paths)}] {os.path.basename(image_path)}")
            result = self.ocr_image(image_path, options)
            results.append({
                'image_path': image_path,
                'result': result,
                'success': result is not None
            })
        
        success_count = sum(1 for r in results if r['success'])
        print(f"\n✅ Batch OCR hoàn thành: {success_count}/{len(image_paths)} thành công")
        
        return results
    
    def get_supported_formats(self):
        """Trả về list các format ảnh được hỗ trợ"""
        return ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    def is_supported_image(self, image_path):
        """Kiểm tra xem file ảnh có được hỗ trợ không"""
        if not os.path.exists(image_path):
            return False
        
        ext = os.path.splitext(image_path)[1].lower()
        return ext in self.get_supported_formats()

# Tạo instance global để sử dụng trong toàn bộ ứng dụng
mathpix_config = MathpixConfig()
