"""
Exam Processor - Module xử lý nội dung đề thi và thêm template lời giải
"""

class ExamProcessor:
    """Class xử lý các loại câu hỏi trong đề thi"""
    
    @staticmethod
    def process_exam_content(content):
        """
        Xử lý nội dung OCR để thêm template lời giải theo cấu trúc
        Args:
            content: nội dung OCR gốc
        Returns:
            nội dung đã được xử lý với template lời giải
        """
        try:
            lines = content.split('\n')
            processed_lines = []
            current_section = None
            template_added = 0
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                processed_lines.append(lines[i])
                
                # Xác định phần hiện tại
                if "phần i" in line.lower():
                    current_section = "multiple_choice"
                elif "phần ii" in line.lower():
                    current_section = "true_false"
                elif "phần iii" in line.lower():
                    current_section = "essay"
                
                # Xử lý câu hỏi
                if line.startswith("**Câu ") and ":**" in line:
                    # Tìm đáp án cho câu hỏi
                    answer = ExamProcessor._find_answer_for_question(lines, i, current_section)
                    
                    # Thêm template lời giải
                    if current_section == "multiple_choice":
                        template = ExamProcessor._generate_multiple_choice_template(answer)
                    elif current_section == "true_false":
                        template = ExamProcessor._generate_true_false_template(answer)
                    elif current_section == "essay":
                        template = ExamProcessor._generate_essay_template()
                    else:
                        # Tự động phát hiện dựa trên nội dung
                        if ExamProcessor._has_abcd_options(lines, i):
                            template = ExamProcessor._generate_multiple_choice_template(
                                ExamProcessor._find_bold_answer(lines, i)
                            )
                        elif ExamProcessor._has_abcd_lowercase_options(lines, i):
                            template = ExamProcessor._generate_true_false_template(
                                ExamProcessor._find_true_false_answers(lines, i)
                            )
                        else:
                            template = ExamProcessor._generate_essay_template()
                    
                    # Chèn template ngay sau câu hỏi hiện tại
                    processed_lines.extend(template)
                    template_added += 1
                
                i += 1
            
            print(f"✅ Đã thêm {template_added} template lời giải")
            return '\n'.join(processed_lines)
            
        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý nội dung: {e}")
            import traceback
            traceback.print_exc()
            return content  # Trả về nội dung gốc nếu có lỗi

    @staticmethod
    def _find_answer_for_question(lines, start_idx, section_type):
        """Tìm đáp án cho câu hỏi"""
        if section_type == "multiple_choice":
            return ExamProcessor._find_bold_answer(lines, start_idx)
        elif section_type == "true_false":
            return ExamProcessor._find_true_false_answers(lines, start_idx)
        else:
            return None

    @staticmethod
    def _find_bold_answer(lines, start_idx):
        """Tìm đáp án được in đậm cho trắc nghiệm (A, B, C, D)"""
        # Tìm trong vòng 20 dòng tiếp theo
        for i in range(start_idx + 1, min(start_idx + 21, len(lines))):
            line = lines[i].strip()
            
            # Tìm pattern **A.**, **B.**, **C.**, **D.**
            if "**A.**" in line:
                return "1"
            elif "**B.**" in line:
                return "2"
            elif "**C.**" in line:
                return "3"
            elif "**D.**" in line:
                return "4"
        
        return "~"  # Không tìm thấy đáp án

    @staticmethod
    def _find_true_false_answers(lines, start_idx):
        """Tìm đáp án đúng/sai cho câu hỏi có 4 ý a,b,c,d"""
        answers = []
        
        # Tìm trong vòng 30 dòng tiếp theo
        for i in range(start_idx + 1, min(start_idx + 31, len(lines))):
            line = lines[i].strip()
            
            # Tìm các ý a), b), c), d) và xem có được in đậm không
            if line.startswith("a)"):
                # Kiểm tra xem có được in đậm không (có thể có dấu hiệu như **)
                answers.append("1" if "**" in line else "0")
            elif line.startswith("b)"):
                answers.append("1" if "**" in line else "0")
            elif line.startswith("c)"):
                answers.append("1" if "**" in line else "0")
            elif line.startswith("d)"):
                answers.append("1" if "**" in line else "0")
        
        # Nếu không tìm thấy đủ 4 ý, trả về mặc định
        while len(answers) < 4:
            answers.append("0")
        
        return "".join(answers[:4])

    @staticmethod
    def _has_abcd_options(lines, start_idx):
        """Kiểm tra xem câu hỏi có lựa chọn A, B, C, D không"""
        for i in range(start_idx + 1, min(start_idx + 15, len(lines))):
            line = lines[i].strip()
            if any(option in line for option in ["A.", "B.", "C.", "D."]):
                return True
        return False

    @staticmethod
    def _has_abcd_lowercase_options(lines, start_idx):
        """Kiểm tra xem câu hỏi có lựa chọn a), b), c), d) không"""
        for i in range(start_idx + 1, min(start_idx + 20, len(lines))):
            line = lines[i].strip()
            if any(option in line for option in ["a)", "b)", "c)", "d)"]):
                return True
        return False

    @staticmethod
    def _generate_multiple_choice_template(answer):
        """Tạo template cho câu trắc nghiệm"""
        return [
            "",
            "```",
            "Lời giải",
            answer,
            "####",
            "```",
            ""
        ]

    @staticmethod
    def _generate_true_false_template(answers):
        """Tạo template cho câu đúng/sai"""
        return [
            "",
            "```", 
            "Lời giải",
            answers,
            "####",
            "```",
            ""
        ]

    @staticmethod
    def _generate_essay_template():
        """Tạo template cho câu tự luận"""
        return [
            "",
            "```",
            "Lời giải",
            "####",
            "```", 
            ""
        ]
