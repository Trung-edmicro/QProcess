"""
Cấu hình API cho Mathpix
"""
import os
import json
import requests
from dotenv import load_dotenv

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
        
        # Default options
        default_options = {
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True
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

# Tạo instance global để sử dụng trong toàn bộ ứng dụng
mathpix_config = MathpixConfig()
