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
                    model_name="gemini-2.5-flash",  # Sử dụng Flash model cho mapping nhanh hơn
                    generation_config=GenerationConfig(
                        temperature=0.1,  # Thấp để đảm bảo mapping chính xác
                        top_p=0.8,
                        top_k=20,
                        max_output_tokens=32768  # Tăng lên 32K để xử lý mapping đầy đủ
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
    
    def process_single_file(self, input_file, output_file=None):
        """
        Xử lý mapping từ 1 file .md đơn lẻ (chứa cả câu hỏi và đáp án)
        Args:
            input_file: File .md chứa cả câu hỏi và đáp án/lời giải
            output_file: File output (auto generate nếu None)
        Returns:
            str: Path của file output hoặc None nếu lỗi
        """
        try:
            # Đọc nội dung file
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📖 Đã đọc file: {os.path.basename(input_file)}")
            
            if not self.model:
                print("❌ Không thể khởi tạo AI model cho mapping")
                return None
            
            # Gửi toàn bộ nội dung cho AI để xử lý mapping
            print("🤖 Đang gửi nội dung cho AI để mapping...")
            mapped_content = self._process_content_with_ai(content)
            
            if not mapped_content:
                print("❌ AI không thể xử lý mapping")
                return None
            
            # Tạo tên file output nếu chưa có
            if not output_file:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"data/output/{base_name}_mapped_{timestamp}.md"
            
            # Đảm bảo thư mục output tồn tại
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Ghi file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(mapped_content)
            
            print(f"✅ Đã tạo file mapping: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Lỗi xử lý file: {e}")
            return None
    
    def _process_content_with_ai(self, content):
        """
        Gửi toàn bộ nội dung cho AI để xử lý mapping
        Args:
            content: Nội dung đầy đủ từ file .md
        Returns:
            str: Nội dung đã được AI mapping hoặc None nếu lỗi
        """
        try:
            # Kiểm tra độ dài content để quyết định cách xử lý
            content_length = len(content)
            print(f"📏 Độ dài nội dung: {content_length:,} ký tự")
            
            # Nếu content quá lớn (>15k ký tự), chia nhỏ để xử lý
            if content_length > 15000:
                print("⚠️ Nội dung lớn, sẽ chia nhỏ để xử lý...")
                return self._process_large_content_in_chunks(content)
            
            # Tạo prompt ngắn gọn cho AI
            prompt = f"""
Hãy mapping tất cả câu hỏi với đáp án từ đề thi.

**Quy tắc:**
- Tìm câu hỏi: **Câu X:**
- Tìm đáp án trong bảng đáp án (A, B, C, D) hoặc lời giải chi tiết
- Với trắc nghiệm: Chỉ cần đáp án + giải thích ngắn
- Với tự luận: Copy lời giải đầy đủ

**Format:**
**Câu X:** [câu hỏi]
Lời giải
[đáp án + giải thích]

**Đề thi:**
{content}
"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                print("✅ AI đã xử lý mapping thành công")
                return response.text
            else:
                print("❌ AI không trả về kết quả")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi gửi cho AI: {e}")
            return None
    
    def _process_large_content_in_chunks(self, content):
        """
        Chia content lớn thành các chunk nhỏ hơn để xử lý
        Args:
            content: Nội dung lớn cần chia nhỏ
        Returns:
            str: Nội dung đã được mapping từ tất cả các chunk
        """
        try:
            # Tách phần đáp án trước
            answer_section = ""
            content_main = content
            
            # Tìm phần đáp án
            if "| Câu | 1 | 2 |" in content or "Đáp án |" in content:
                # Tìm vị trí bắt đầu bảng đáp án
                answer_start = content.find("**Phần I**")
                if answer_start == -1:
                    answer_start = content.find("| Câu | 1 | 2 |")
                if answer_start == -1:
                    answer_start = content.find("Đáp án |")
                    
                if answer_start != -1:
                    answer_section = content[answer_start:]
                    content_main = content[:answer_start]
                    print(f"🔍 Tách được phần đáp án: {len(answer_section)} ký tự")
            
            # Chia content theo từng phần
            sections = []
            current_section = ""
            
            lines = content_main.split('\n')
            
            for line in lines:
                # Nếu gặp câu hỏi mới và section hiện tại đã đủ lớn
                if line.startswith('**Câu ') and len(current_section) > 3000:
                    if current_section.strip():
                        sections.append(current_section.strip())
                    current_section = line + '\n'
                else:
                    current_section += line + '\n'
            
            # Thêm section cuối
            if current_section.strip():
                sections.append(current_section.strip())
            
            print(f"� Chia content thành {len(sections)} section(s)")
            
            processed_sections = []
            
            for i, section in enumerate(sections):
                section_length = len(section)
                print(f"🔄 Xử lý section {i+1}/{len(sections)} ({section_length:,} ký tự)")
                
                # Tạo prompt cho từng section với thông tin đáp án
                section_with_answers = section + "\n\n" + answer_section
                result = self._process_section_with_answers(section_with_answers)
                if result:
                    processed_sections.append(result)
            
            # Gộp tất cả kết quả
            final_result = '\n\n'.join(processed_sections)
            print(f"✅ Đã xử lý xong {len(processed_sections)} section(s)")
            
            return final_result
            
        except Exception as e:
            print(f"❌ Lỗi khi xử lý content lớn: {e}")
            return None
    
    def _process_section_with_answers(self, section_content):
        """
        Xử lý một section với thông tin đáp án
        """
        try:
            prompt = f"""
Mapping câu hỏi với đáp án. Từ nội dung sau:

1. Tìm các câu hỏi (format **Câu X:**)
2. Tìm đáp án tương ứng trong bảng đáp án
3. Tạo lời giải ngắn gọn

Format output:
**Câu [X]:** [Nội dung câu hỏi]
[Nội dung option]
Lời giải
Đáp án: [A/B/C/D]. [Giải thích ngắn]

Nội dung:
{section_content}
"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text
            else:
                print("⚠️ Section không được xử lý thành công")
                return None
                
        except Exception as e:
            print(f"⚠️ Lỗi xử lý section: {e}")
            return None
    
    def _split_chunk_further(self, chunk):
        """
        Chia chunk lớn thành các sub-chunk nhỏ hơn
        """
        # Chia theo paragraphs
        paragraphs = chunk.split('\n\n')
        sub_chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk + paragraph) < 35000:
                current_chunk += paragraph + '\n\n'
            else:
                if current_chunk:
                    sub_chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
        
        if current_chunk:
            sub_chunks.append(current_chunk.strip())
        
        return sub_chunks
    
    def _process_single_chunk(self, chunk):
        """
        Xử lý một chunk đơn lẻ
        """
        try:
            prompt = f"""
Hãy ánh xạ (mapping) câu hỏi với lời giải trong nội dung sau và trả về theo format:

**Câu [Số]:** [Nội dung câu hỏi]
Lời giải
[Nội dung lời giải]

Nội dung cần xử lý:
{chunk}
"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text
            else:
                print("⚠️ Chunk không được xử lý thành công")
                return None
                
        except Exception as e:
            print(f"⚠️ Lỗi xử lý chunk: {e}")
            return None
    
    def process_content_with_ai(self, content):
        """
        Public method để gửi nội dung cho AI xử lý mapping
        Args:
            content: Nội dung cần mapping
        Returns:
            str: Nội dung đã mapping hoặc None
        """
        return self._process_content_with_ai(content)
    
    def _split_content_for_mapping(self, content):
        """
        Tách nội dung thành 2 phần: câu hỏi và lời giải
        Args:
            content: Nội dung đầy đủ từ file .md
        Returns:
            tuple: (questions_content, answers_content)
        """
        # Cách 1: Tìm phần "đáp án" hoặc "lời giải"
        content_lower = content.lower()
        
        # Tìm các từ khóa phân tách
        split_keywords = [
            'đáp án', 'lời giải', 'hướng dẫn giải', 'giải chi tiết',
            'answer', 'solution', 'explanation', 'detailed solution',
            'key answer', 'answer key', 'solutions'
        ]
        
        split_pos = -1
        split_keyword = ""
        
        for keyword in split_keywords:
            pos = content_lower.find(keyword)
            if pos != -1:
                split_pos = pos
                split_keyword = keyword
                print(f"🔍 Tìm thấy từ khóa phân tách: '{keyword}' tại vị trí {pos}")
                break
        
        if split_pos != -1:
            # Tách tại vị trí tìm thấy
            questions_content = content[:split_pos].strip()
            answers_content = content[split_pos:].strip()
            print(f"✅ Đã tách nội dung dựa trên từ khóa '{split_keyword}'")
            return questions_content, answers_content
        
        # Cách 2: Tìm theo pattern ### hoặc ## hoặc ---
        lines = content.split('\n')
        questions_lines = []
        answers_lines = []
        
        current_section = 'questions'
        section_changed = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Kiểm tra các pattern phân tách section
            if (line.startswith('---') or 
                (line.startswith('#') and any(keyword in line_lower for keyword in split_keywords)) or
                any(keyword in line_lower for keyword in split_keywords)):
                if not section_changed:
                    current_section = 'answers'
                    section_changed = True
                    print(f"🔍 Chuyển sang phần đáp án tại dòng {i+1}: '{line[:50]}...'")
            
            if current_section == 'questions':
                questions_lines.append(line)
            else:
                answers_lines.append(line)
        
        questions_content = '\n'.join(questions_lines).strip()
        answers_content = '\n'.join(answers_lines).strip()
        
        # Cách 3: Nếu vẫn không tách được, tìm theo pattern câu hỏi liền kề đáp án
        if not section_changed and questions_content == answers_content:
            # Tìm pattern: Câu X + options + Câu Y (có thể là đáp án)
            question_answer_pairs = self._detect_question_answer_pairs(content)
            if question_answer_pairs:
                questions_content = '\n\n'.join([pair['question'] for pair in question_answer_pairs])
                answers_content = '\n\n'.join([pair['answer'] for pair in question_answer_pairs if pair['answer']])
                print(f"✅ Đã tách {len(question_answer_pairs)} cặp câu hỏi-đáp án")
                return questions_content, answers_content
        
        # Nếu không tách được, trả về toàn bộ content cho cả 2 phần
        if not questions_content or not answers_content:
            print("⚠️ Không thể tách rõ ràng, sử dụng toàn bộ nội dung cho cả câu hỏi và đáp án")
            return content, content
        
        print(f"✅ Đã tách nội dung: {len(questions_lines)} dòng câu hỏi, {len(answers_lines)} dòng đáp án")
        return questions_content, answers_content
    
    def _detect_question_answer_pairs(self, content):
        """
        Phát hiện các cặp câu hỏi-đáp án trong cùng một nội dung
        Returns:
            list: [{'question': str, 'answer': str}, ...]
        """
        pairs = []
        
        # Pattern phức tạp hơn để tìm câu hỏi + đáp án
        pattern = r'(?:^|\n)\s*(?:\*\*)?(?:Câu|Question)\s*(\d+)(?:\*\*)?[:\.]?\s*(.+?)(?=(?:^|\n)\s*(?:\*\*)?(?:Câu|Question)\s*\d+|\Z)'
        
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            question_num = match.group(1)
            full_content = match.group(2).strip()
            
            # Tìm xem trong nội dung này có đáp án không
            answer_patterns = [
                r'(?:đáp án|answer)[:\s]*([A-D]\.?.*?)(?=\n|$)',
                r'(?:lời giải|solution)[:\s]*(.+?)(?=\n\n|$)',
                r'\*\*([A-D])\*\*',
                r'^([A-D])[\.\)]\s*(.+?)$'
            ]
            
            question_text = full_content
            answer_text = ""
            
            for ans_pattern in answer_patterns:
                ans_match = re.search(ans_pattern, full_content, re.MULTILINE | re.IGNORECASE)
                if ans_match:
                    answer_text = ans_match.group(0)
                    question_text = full_content.replace(answer_text, '').strip()
                    break
            
            if question_text:
                pairs.append({
                    'question': f"Câu {question_num}: {question_text}",
                    'answer': f"Câu {question_num}: {answer_text}" if answer_text else ""
                })
        
        return pairs
