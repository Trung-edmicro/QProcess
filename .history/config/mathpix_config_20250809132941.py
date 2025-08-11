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
        return self.base_url
    
    def get_status_url(self, pdf_id):
        """Trả về URL để check status của PDF"""
        return f"{self.base_url}/{pdf_id}"
    
    def get_download_url(self, pdf_id, format_type="docx"):
        """Trả về URL để download file đã convert"""
        return f"{self.base_url}/{pdf_id}.{format_type}"

# Tạo instance global để sử dụng trong toàn bộ ứng dụng
mathpix_config = MathpixConfig()
