import os
import sys
from datetime import datetime
from config.vertex_ai_config import VertexAIConfig
from vertexai.generative_models import GenerativeModel, GenerationConfig

# Import prompts từ data/prompt
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data', 'prompt'))
from data.prompt.prompts import QUESTION_ANSWER_MAPPING

class QuestionAnswerMapper:
    """Class đơn giản để mapping câu hỏi với lời giải bằng AI"""
    
    def __init__(self):
        """Khởi tạo mapper với Vertex AI"""
        self.vertex_config = VertexAIConfig()
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Khởi tạo Vertex AI model"""
        try:
            if self.vertex_config.is_configured():
                self.vertex_config.initialize_vertex_ai()
                self.model = GenerativeModel(
                    model_name="gemini-2.5-flash",
                    generation_config=GenerationConfig(
                        temperature=0.1,
                        top_p=0.8,
                        top_k=20,
                        max_output_tokens=30000
                    )
                )
                print("✅ Vertex AI model đã được khởi tạo cho Question-Answer Mapper")
            else:
                print("❌ Vertex AI chưa được cấu hình đúng")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo Vertex AI model: {e}")
    
    def process_content(self, content):
        """
        Gửi nội dung cho AI để mapping câu hỏi với lời giải
        Args:
            content: Nội dung file .md
        Returns:
            str: Kết quả đã mapping hoặc None nếu lỗi
        """
        if not self.model:
            print("❌ Model chưa được khởi tạo")
            return None
        
        try:
            # Sử dụng prompt từ file data/prompt/prompts.py
            prompt = QUESTION_ANSWER_MAPPING.format(content=content)
            
            # Gửi cho AI
            print(f"🤖 Đang gửi {len(content):,} ký tự cho AI...")
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                print("✅ AI đã trả về kết quả")
                return response.text
            else:
                print("❌ AI không trả về kết quả")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi gửi cho AI: {e}")
            return None
    
    def process_file(self, input_file, output_file=None):
        """
        Xử lý mapping từ file input và lưu kết quả
        Args:
            input_file: File .md đầu vào
            output_file: File output (tự động tạo nếu None)
        Returns:
            str: Đường dẫn file output hoặc None nếu lỗi
        """
        try:
            # Đọc file input
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📖 Đã đọc file: {os.path.basename(input_file)} ({len(content):,} ký tự)")
            
            # Xử lý mapping
            result = self.process_content(content)
            
            if not result:
                print("❌ Không có kết quả để lưu")
                return None
            
            # Tạo tên file output nếu chưa có
            if not output_file:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"data/output/{base_name}_mapped_{timestamp}.md"
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Ghi file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"✅ Đã lưu kết quả: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Lỗi xử lý file: {e}")
            return None
