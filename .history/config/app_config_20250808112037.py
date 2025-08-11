"""
File cấu hình chính cho toàn bộ ứng dụng
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import các config classes
from .mathpix_config import mathpix_config
from .vertex_ai_config import vertex_ai_config

class AppConfig:
    """Cấu hình tổng cho ứng dụng"""
    
    def __init__(self):
        self.mathpix = mathpix_config
        self.vertex_ai = vertex_ai_config
        
        # Cấu hình paths
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_folder = os.path.join(self.project_root, "data")
        self.input_folder = os.path.join(self.data_folder, "input")
        self.output_folder = os.path.join(self.data_folder, "output")
        
        # Tạo thư mục nếu chưa có
        self._create_directories()
    
    def _create_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            self.data_folder,
            self.input_folder,
            self.output_folder
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def check_all_configs(self):
        """Kiểm tra tất cả các cấu hình"""
        status = {
            "mathpix": self.mathpix.is_configured(),
            "vertex_ai": self.vertex_ai.is_configured(),
            "directories": os.path.exists(self.data_folder)
        }
        
        return status
    
    def get_config_summary(self):
        """Trả về tóm tắt cấu hình"""
        status = self.check_all_configs()
        
        print("=== TÌNH TRẠNG CẤU HÌNH ===")
        print(f"📋 Mathpix API: {'✅ OK' if status['mathpix'] else '❌ Chưa cấu hình'}")
        print(f"🤖 Vertex AI: {'✅ OK' if status['vertex_ai'] else '❌ Chưa cấu hình'}")
        print(f"📁 Thư mục: {'✅ OK' if status['directories'] else '❌ Lỗi'}")
        
        return status

# Tạo instance global
app_config = AppConfig()
