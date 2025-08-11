"""
Question Answer Mapper - Version đơn giản
Chỉ gửi nội dung file .md cho AI và nhận kết quả
"""
import os
from datetime import datetime
from config.vertex_ai_config import VertexAIConfig
from vertexai.generative_models import GenerativeModel, GenerationConfig

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
                    model_name="gemini-2.5-flash",  # Sử dụng Flash cho mapping nhanh
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
            # Tạo prompt đơn giản và rõ ràng
            prompt = f"""
Bạn hãy đóng vai trò là một trợ lý biên tập tài liệu.
Nhiệm vụ của bạn là đọc toàn bộ nội dung được cung cấp, sau đó sắp xếp lại bằng cách ghép mỗi câu hỏi với lời giải chi tiết tương ứng của nó.

**Yêu cầu định dạng đầu ra:**
Mỗi cặp câu hỏi - lời giải phải tuân thủ nghiêm ngặt theo cấu trúc sau:

**Câu [Số]:** [Toàn bộ nội dung câu hỏi và các đáp án A, B, C, D...]
Lời giải
[Nội dung lời giải chi tiết tương ứng với câu hỏi đó]

**Lưu ý quan trọng:**
- Trả về nội dung gốc bao gồm Phần và câu, không lược bỏ nội dung quan trọng, nhiệm vụ chỉ là ghép cặp câu hỏi với lời giải.
- Tuyệt đối **không bịa nội dung**, không thêm từ ngữ nào khác (như "Dưới đây là nội dung đã được sắp xếp lại theo yêu cầu:"), không tự ý thêm lời giải nếu không có nguồn như "hướng dẫn giải" trong nội dung.
- Xử lý tất cả các câu hỏi có trong tài liệu.

Bây giờ, hãy xử lý nội dung dưới đây:
{content}
"""
            
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
