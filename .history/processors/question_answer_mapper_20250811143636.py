"""
Question Answer Mapper - Module mapping câu hỏi với lời giải/đáp án
"""
import os
import re
from datetime import datetime
from config.vertex_ai_config import VertexAIConfig
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

class QuestionAnswerMapper:
    """Class xử lý mapping câu hỏi với đáp án/lời giải"""
    
    def __init__(self):
        self.vertex_config = VertexAIConfig()
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Khởi tạo Vertex AI model"""
        try:
            if self.vertex_config.is_configured():
                self.vertex_config.initialize_vertex_ai()
                self.model = GenerativeModel(
                    model_name=self.vertex_config.model_name,
                    generation_config=GenerationConfig(
                        temperature=0.1,  # Thấp để đảm bảo mapping chính xác
                        top_p=0.8,
                        top_k=20,
                        max_output_tokens=8192
                    )
                )
                print("✅ Vertex AI model đã được khởi tạo cho Question-Answer Mapper")
            else:
                print("❌ Vertex AI chưa được cấu hình đúng")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo Vertex AI model: {e}")
    
    def extract_questions_and_answers(self, questions_content, answers_content):
        """
        Trích xuất và phân tích câu hỏi và đáp án từ nội dung
        Args:
            questions_content: Nội dung chứa câu hỏi
            answers_content: Nội dung chứa đáp án/lời giải
        Returns:
            dict: {'questions': [], 'answers': []}
        """
        questions = self._extract_questions(questions_content)
        answers = self._extract_answers(answers_content)
        
        return {
            'questions': questions,
            'answers': answers
        }
    
    def _extract_questions(self, content):
        """Trích xuất danh sách câu hỏi"""
        questions = []
        
        # Pattern để tìm câu hỏi (linh hoạt với nhiều format)
        question_patterns = [
            r'(?:^|\n)\s*(?:\*\*)?(?:Câu|Question)\s*(\d+)(?:\*\*)?[:\.]?\s*(.+?)(?=(?:^|\n)\s*(?:\*\*)?(?:Câu|Question)\s*\d+|\Z)',
            r'(?:^|\n)\s*(\d+)[:\.\)]\s*(.+?)(?=(?:^|\n)\s*\d+[:\.\)]|\Z)'
        ]
        
        for pattern in question_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            for match in matches:
                question_num = match.group(1)
                question_text = match.group(2).strip()
                
                if question_text and len(question_text) > 10:  # Filter out very short matches
                    questions.append({
                        'number': int(question_num),
                        'text': question_text,
                        'raw_match': match.group(0)
                    })
            
            if questions:  # Nếu đã tìm thấy câu hỏi thì dừng
                break
        
        # Sắp xếp theo số thứ tự
        questions.sort(key=lambda x: x['number'])
        return questions
    
    def _extract_answers(self, content):
        """Trích xuất danh sách đáp án/lời giải"""
        answers = []
        
        # Pattern để tìm đáp án (linh hoạt với nhiều format)
        answer_patterns = [
            r'(?:^|\n)\s*(?:\*\*)?(?:Câu|Question)\s*(\d+)(?:\*\*)?[:\.]?\s*(.+?)(?=(?:^|\n)\s*(?:\*\*)?(?:Câu|Question)\s*\d+|\Z)',
            r'(?:^|\n)\s*(\d+)[:\.\)]\s*(.+?)(?=(?:^|\n)\s*\d+[:\.\)]|\Z)',
            r'(?:^|\n)\s*(?:Đáp án|Answer)\s*(?:câu\s*)?(\d+)[:\.]?\s*(.+?)(?=(?:^|\n)\s*(?:Đáp án|Answer)|\Z)'
        ]
        
        for pattern in answer_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            for match in matches:
                answer_num = match.group(1)
                answer_text = match.group(2).strip()
                
                if answer_text and len(answer_text) > 5:  # Filter out very short matches
                    answers.append({
                        'number': int(answer_num),
                        'text': answer_text,
                        'raw_match': match.group(0)
                    })
            
            if answers:  # Nếu đã tìm thấy đáp án thì dừng
                break
        
        # Sắp xếp theo số thứ tự
        answers.sort(key=lambda x: x['number'])
        return answers
    
    def map_questions_with_answers_ai(self, questions, answers):
        """
        Sử dụng AI để mapping câu hỏi với đáp án
        Args:
            questions: List câu hỏi
            answers: List đáp án
        Returns:
            List các cặp question-answer đã được mapping
        """
        if not self.model:
            print("❌ Model chưa được khởi tạo")
            return []
        
        try:
            # Tạo prompt cho AI
            prompt = self._create_mapping_prompt(questions, answers)
            
            print(f"🤖 Đang mapping {len(questions)} câu hỏi với {len(answers)} đáp án...")
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                mapped_pairs = self._parse_ai_mapping_response(response.text, questions, answers)
                print(f"✅ Đã mapping thành công {len(mapped_pairs)} cặp câu hỏi-đáp án")
                return mapped_pairs
            else:
                print("❌ AI không trả về kết quả mapping")
                return []
                
        except Exception as e:
            print(f"❌ Lỗi khi mapping bằng AI: {e}")
            return []
    
    def _create_mapping_prompt(self, questions, answers):
        """Tạo prompt cho AI để mapping"""
        prompt = """
Bạn là một chuyên gia giáo dục. Nhiệm vụ của bạn là mapping (ghép) câu hỏi với đáp án/lời giải tương ứng.

DANH SÁCH CÂU HỎI:
"""
        
        for q in questions[:10]:  # Giới hạn 10 câu để tránh prompt quá dài
            prompt += f"\n--- Câu {q['number']} ---\n{q['text'][:500]}...\n"
        
        prompt += "\n\nDANH SÁCH ĐÁP ÁN/LỜI GIẢI:\n"
        
        for a in answers[:10]:  # Giới hạn 10 đáp án
            prompt += f"\n--- Đáp án {a['number']} ---\n{a['text'][:500]}...\n"
        
        prompt += """

NHIỆM VỤ:
1. Phân tích nội dung từng câu hỏi và đáp án
2. Xác định mối liên hệ giữa câu hỏi và đáp án dựa trên:
   - Số thứ tự (nếu tương ứng)
   - Nội dung kiến thức (môn học, chủ đề)
   - Từ khóa chung
   - Cấu trúc câu hỏi-đáp án

ĐỊNH DẠNG OUTPUT (JSON):
```json
{
  "mappings": [
    {
      "question_number": 1,
      "answer_number": 1,
      "confidence": 0.95,
      "reason": "Lý do mapping"
    }
  ]
}
```

Hãy mapping chính xác và ghi rõ lý do cho mỗi cặp:
"""
        
        return prompt
    
    def _parse_ai_mapping_response(self, response_text, questions, answers):
        """Parse kết quả mapping từ AI"""
        mapped_pairs = []
        
        try:
            # Tìm JSON trong response
            import json
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                mapping_data = json.loads(json_match.group(1))
                
                for mapping in mapping_data.get('mappings', []):
                    q_num = mapping['question_number']
                    a_num = mapping['answer_number']
                    
                    # Tìm câu hỏi và đáp án tương ứng
                    question = next((q for q in questions if q['number'] == q_num), None)
                    answer = next((a for a in answers if a['number'] == a_num), None)
                    
                    if question and answer:
                        mapped_pairs.append({
                            'question': question,
                            'answer': answer,
                            'confidence': mapping.get('confidence', 0.0),
                            'reason': mapping.get('reason', '')
                        })
            
        except Exception as e:
            print(f"⚠️ Lỗi parse AI response, fallback to simple mapping: {e}")
            # Fallback: Simple number-based mapping
            mapped_pairs = self._simple_number_mapping(questions, answers)
        
        return mapped_pairs
    
    def _simple_number_mapping(self, questions, answers):
        """Mapping đơn giản dựa trên số thứ tự"""
        mapped_pairs = []
        
        for question in questions:
            # Tìm đáp án có cùng số thứ tự
            answer = next((a for a in answers if a['number'] == question['number']), None)
            if answer:
                mapped_pairs.append({
                    'question': question,
                    'answer': answer,
                    'confidence': 0.8,
                    'reason': 'Number-based mapping'
                })
        
        return mapped_pairs
    
    def generate_mapped_content(self, mapped_pairs, output_format='markdown'):
        """
        Tạo nội dung đã mapping
        Args:
            mapped_pairs: List các cặp đã mapping
            output_format: 'markdown' hoặc 'json'
        Returns:
            str: Nội dung formatted
        """
        if output_format == 'markdown':
            return self._generate_markdown_output(mapped_pairs)
        elif output_format == 'json':
            return self._generate_json_output(mapped_pairs)
        else:
            return self._generate_markdown_output(mapped_pairs)
    
    def _generate_markdown_output(self, mapped_pairs):
        """Tạo output Markdown"""
        content = f"# Đề thi đã mapping câu hỏi và lời giải\n\n"
        content += f"*Được tạo tự động vào {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*\n\n"
        content += f"**Tổng số câu đã mapping: {len(mapped_pairs)}**\n\n"
        content += "---\n\n"
        
        for i, pair in enumerate(mapped_pairs, 1):
            question = pair['question']
            answer = pair['answer']
            confidence = pair['confidence']
            
            content += f"## Câu {question['number']}\n\n"
            content += f"### 📝 Đề bài\n{question['text']}\n\n"
            content += f"### ✅ Lời giải\n{answer['text']}\n\n"
            content += f"*Độ tin cậy mapping: {confidence:.2f} - {pair['reason']}*\n\n"
            content += "---\n\n"
        
        return content
    
    def _generate_json_output(self, mapped_pairs):
        """Tạo output JSON"""
        import json
        
        output_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_pairs': len(mapped_pairs)
            },
            'mapped_questions': []
        }
        
        for pair in mapped_pairs:
            output_data['mapped_questions'].append({
                'question_number': pair['question']['number'],
                'question_text': pair['question']['text'],
                'answer_number': pair['answer']['number'],
                'answer_text': pair['answer']['text'],
                'mapping_confidence': pair['confidence'],
                'mapping_reason': pair['reason']
            })
        
        return json.dumps(output_data, ensure_ascii=False, indent=2)
    
    def process_files(self, questions_file, answers_file, output_file=None):
        """
        Xử lý mapping từ 2 file và tạo output
        Args:
            questions_file: File chứa câu hỏi
            answers_file: File chứa đáp án
            output_file: File output (auto generate nếu None)
        Returns:
            str: Path của file output
        """
        try:
            # Đọc nội dung files
            with open(questions_file, 'r', encoding='utf-8') as f:
                questions_content = f.read()
            
            with open(answers_file, 'r', encoding='utf-8') as f:
                answers_content = f.read()
            
            print(f"📖 Đã đọc file câu hỏi: {os.path.basename(questions_file)}")
            print(f"📖 Đã đọc file đáp án: {os.path.basename(answers_file)}")
            
            # Trích xuất câu hỏi và đáp án
            extracted = self.extract_questions_and_answers(questions_content, answers_content)
            questions = extracted['questions']
            answers = extracted['answers']
            
            print(f"🔍 Tìm thấy {len(questions)} câu hỏi và {len(answers)} đáp án")
            
            if not questions or not answers:
                print("❌ Không tìm thấy câu hỏi hoặc đáp án")
                return None
            
            # Mapping bằng AI
            mapped_pairs = self.map_questions_with_answers_ai(questions, answers)
            
            if not mapped_pairs:
                print("❌ Không thể mapping câu hỏi với đáp án")
                return None
            
            # Tạo output
            output_content = self.generate_mapped_content(mapped_pairs)
            
            # Tạo tên file output nếu chưa có
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"data/output/mapped_questions_answers_{timestamp}.md"
            
            # Đảm bảo thư mục output tồn tại
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Ghi file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            print(f"✅ Đã tạo file mapping: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Lỗi xử lý files: {e}")
            return None
