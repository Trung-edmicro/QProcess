"""
Cấu hình API cho Google Vertex AI
"""
import os
from google.oauth2 import service_account
import vertexai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VertexAIConfig:
    """Cấu hình cho Vertex AI API"""
    
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID")
        self.region = "us-central1"  # Region mặc định
        self.model_name = "gemini-2.5-flash"  # Model mặc định - đổi sang Flash để nhanh hơn
        self.credentials = None
        
        # Thiết lập credentials
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Thiết lập credentials từ service account"""
        try:
            service_account_data = {
                "type": os.getenv("TYPE"),
                "project_id": os.getenv("PROJECT_ID"),
                "private_key_id": os.getenv("PRIVATE_KEY_ID"),
                "private_key": os.getenv("PRIVATE_KEY").replace('\\n', '\n') if os.getenv("PRIVATE_KEY") else None,
                "client_email": os.getenv("CLIENT_EMAIL"),
                "client_id": os.getenv("CLIENT_ID", ""),
                "auth_uri": os.getenv("AUTH_URI"),
                "token_uri": os.getenv("TOKEN_URI"),
                "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
                "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
                "universe_domain": os.getenv("UNIVERSE_DOMAIN")
            }
            
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_data,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            
        except Exception as e:
            print(f"Lỗi khi tạo credentials từ service account: {e}")
            self.credentials = None
    
    def initialize_vertex_ai(self):
        """Khởi tạo Vertex AI với credentials"""
        try:
            if not self.is_configured():
                raise ValueError("Vertex AI chưa được cấu hình đúng")
                
            vertexai.init(
                project=self.project_id, 
                location=self.region, 
                credentials=self.credentials
            )
            return True
            
        except Exception as e:
            print(f"Lỗi khi khởi tạo Vertex AI: {e}")
            return False
    
    def is_configured(self):
        """Kiểm tra xem API đã được cấu hình chưa"""
        return bool(self.project_id and self.credentials)
    
    def get_generation_config(self, temperature=0.5, top_p=0.8, max_output_tokens=None):
        """Trả về generation config cho model"""
        config = {
            "temperature": temperature,
            "top_p": top_p
        }
        
        if max_output_tokens:
            config["max_output_tokens"] = max_output_tokens
            
        return config
    
    def get_project_info(self):
        """Trả về thông tin project"""
        return {
            "project_id": self.project_id,
            "region": self.region,
            "model_name": self.model_name,
            "is_configured": self.is_configured()
        }

# Tạo instance global để sử dụng trong toàn bộ ứng dụng
vertex_ai_config = VertexAIConfig()
