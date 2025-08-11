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
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True,
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
    
    def get_supported_pdf_formats(self):
        """Trả về list các format PDF được hỗ trợ"""
        return ['.pdf']
    
    def is_supported_image(self, image_path):
        """Kiểm tra xem file ảnh có được hỗ trợ không"""
        if not os.path.exists(image_path):
            return False
        
        ext = os.path.splitext(image_path)[1].lower()
        return ext in self.get_supported_formats()
    
    def is_supported_pdf(self, file_path):
        """Kiểm tra xem file PDF có được hỗ trợ không"""
        if not os.path.exists(file_path):
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.get_supported_pdf_formats()
    
    def is_supported_file(self, file_path):
        """Kiểm tra xem file có được hỗ trợ không (ảnh hoặc PDF)"""
        return self.is_supported_image(file_path) or self.is_supported_pdf(file_path)
    
    def upload_pdf(self, pdf_path, options=None):
        """
        Upload PDF để xử lý với Mathpix API
        Args:
            pdf_path: đường dẫn file PDF
            options: dict các tùy chọn xử lý
        Returns:
            dict response chứa pdf_id hoặc None nếu lỗi
        """
        if not self.is_configured():
            print("❌ Mathpix chưa được cấu hình!")
            return None
            
        if not os.path.exists(pdf_path):
            print(f"❌ Không tìm thấy file PDF: {pdf_path}")
            return None
        
        if not self.is_supported_pdf(pdf_path):
            print(f"❌ File không phải PDF: {pdf_path}")
            return None
        
        # Default options for PDF processing
        default_options = {
            "conversion_formats": {"docx": True, "md": True},
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True
        }
        
        if options:
            default_options.update(options)
        
        try:
            print(f"🔄 Đang upload PDF: {os.path.basename(pdf_path)}")
            
            with open(pdf_path, "rb") as f:
                response = requests.post(
                    self.pdf_base_url,
                    files={"file": f},
                    data={
                        "options_json": json.dumps(default_options)
                    },
                    headers=self.get_headers()
                )
            
            if response.status_code == 200:
                result = response.json()
                pdf_id = result.get('pdf_id')
                
                # Debug: in ra response để kiểm tra
                print(f"📊 Response: {result}")
                
                if pdf_id:
                    print(f"✅ Upload thành công! PDF ID: {pdf_id}")
                    return result
                else:
                    # Thử các key khác có thể chứa PDF ID
                    possible_keys = ['id', 'document_id', 'file_id', 'processing_id']
                    for key in possible_keys:
                        if key in result:
                            pdf_id = result[key]
                            print(f"✅ Upload thành công! PDF ID ({key}): {pdf_id}")
                            # Update result với key chuẩn
                            result['pdf_id'] = pdf_id
                            return result
                    
                    print(f"❌ Không tìm thấy PDF ID trong response!")
                    print(f"📋 Available keys: {list(result.keys())}")
                    return None
            else:
                print(f"❌ Lỗi upload: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi upload PDF: {str(e)}")
            return None
    
    def check_pdf_status(self, pdf_id):
        """
        Kiểm tra trạng thái xử lý PDF
        Args:
            pdf_id: ID của PDF đã upload
        Returns:
            dict response status hoặc None nếu lỗi
        """
        if not self.is_configured():
            return None
        
        try:
            response = requests.get(
                self.get_status_url(pdf_id),
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Lỗi check status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi check status: {str(e)}")
            return None
    
    def download_pdf_result(self, pdf_id, format_type="docx"):
        """
        Download kết quả xử lý PDF
        Args:
            pdf_id: ID của PDF
            format_type: định dạng output (docx, tex)
        Returns:
            text content hoặc None nếu lỗi
        """
        if not self.is_configured():
            return None
        
        try:
            response = requests.get(
                self.get_download_url(pdf_id, format_type),
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"❌ Lỗi download: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi download: {str(e)}")
            return None
    
    def process_pdf(self, pdf_path, timeout=60, check_interval=2):
        """
        Xử lý PDF hoàn chỉnh: upload -> wait -> download
        Args:
            pdf_path: đường dẫn file PDF
            timeout: thời gian chờ tối đa (giây)
            check_interval: khoảng thời gian check status (giây)
        Returns:
            text content hoặc None nếu lỗi
        """
        print(f"🔄 Bắt đầu xử lý PDF: {os.path.basename(pdf_path)}")
        
        # Step 1: Upload PDF
        upload_result = self.upload_pdf(pdf_path)
        if not upload_result:
            return None
        
        pdf_id = upload_result.get('pdf_id')
        if not pdf_id:
            print("❌ Không nhận được PDF ID!")
            return None
        
        # Step 2: Wait for processing
        import time
        elapsed_time = 0
        
        print("⏳ Đang chờ xử lý...")
        while elapsed_time < timeout:
            status_result = self.check_pdf_status(pdf_id)
            
            if status_result:
                status = status_result.get('status', 'unknown')
                print(f"📊 Status: {status} (đã chờ {elapsed_time}s)")
                
                if status == 'completed':
                    print("✅ Xử lý hoàn thành!")
                    break
                elif status == 'error':
                    print("❌ Xử lý thất bại!")
                    return None
            
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        if elapsed_time >= timeout:
            print(f"⏰ Timeout sau {timeout}s!")
            return None
        
        # Step 3: Download result
        print("📥 Đang download kết quả...")
        result_text = self.download_pdf_result(pdf_id, "docx")
        
        if result_text:
            print("✅ Đã nhận được kết quả PDF!")
            return result_text
        else:
            print("❌ Không thể download kết quả!")
            return None

# Tạo instance global để sử dụng trong toàn bộ ứng dụng
mathpix_config = MathpixConfig()
