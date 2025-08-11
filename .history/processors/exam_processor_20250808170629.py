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
            templates_to_insert = []  # Lưu trữ các template cần chèn
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Xác định phần hiện tại  
                line_lower = line.lower()
                if ("phần iii" in line_lower or "phần 3" in line_lower or 
                    "part iii" in line_lower or "part 3" in line_lower or
                    "section iii" in line_lower or "section 3" in line_lower):
                    current_section = "essay"
                elif ("phần ii" in line_lower or "phần 2" in line_lower or
                      "part ii" in line_lower or "part 2" in line_lower or
                      "section ii" in line_lower or "section 2" in line_lower):
                    current_section = "true_false"
                elif ("phần i" in line_lower or "phần 1" in line_lower or
                      "part i" in line_lower or "part 1" in line_lower or
                      "section i" in line_lower or "section 1" in line_lower):
                    current_section = "multiple_choice"
                
                # Xử lý câu hỏi (cả in đậm và không in đậm, cả tiếng Việt và tiếng Anh)
                is_question = (line.startswith("**Câu ") and ":**" in line) or \
                             (line.startswith("Câu ") and ":" in line and not line.startswith("**")) or \
                             (line.startswith("**Question ") and ":**" in line) or \
                             (line.startswith("Question ") and ":" in line and not line.startswith("**"))
                
                if is_question:
                    # Kiểm tra xem câu hỏi đã có template lời giải chưa
                    has_template = ExamProcessor._check_existing_template(lines, i)
                    
                    if not has_template:
                        # Tìm vị trí cuối của câu hỏi (trước câu hỏi tiếp theo hoặc cuối file)
                        question_end = ExamProcessor._find_question_end(lines, i)
                        
                        # Thêm template lời giải dựa trên phần hiện tại
                        if current_section == "multiple_choice":
                            answer = ExamProcessor._find_answer_for_question(lines, i, current_section)
                            template = ExamProcessor._generate_multiple_choice_template(answer)
                        elif current_section == "true_false":
                            answer = ExamProcessor._find_answer_for_question(lines, i, current_section)
                            template = ExamProcessor._generate_true_false_template(answer)
                        elif current_section == "essay":
                            # Phần tự luận không cần tìm đáp án
                            template = ExamProcessor._generate_essay_template()
                        else:
                            # Tự động phát hiện dựa trên nội dung (khi không xác định được phần)
                            print(f"⚠️ Không xác định được phần cho câu hỏi: {line[:50]}...")
                            if ExamProcessor._has_abcd_options(lines, i):
                                answer = ExamProcessor._find_bold_answer(lines, i)
                                template = ExamProcessor._generate_multiple_choice_template(answer)
                                print(f"   → Phát hiện định dạng trắc nghiệm A,B,C,D")
                            elif ExamProcessor._has_abcd_lowercase_options(lines, i):
                                answer = ExamProcessor._find_true_false_answers(lines, i)
                                template = ExamProcessor._generate_true_false_template(answer)
                                print(f"   → Phát hiện định dạng đúng/sai a),b),c),d)")
                            else:
                                template = ExamProcessor._generate_essay_template()
                                print(f"   → Mặc định sử dụng template tự luận")
                        
                        # Lưu template để chèn tại vị trí thích hợp
                        templates_to_insert.append({
                            'template': template,
                            'insert_after': question_end,
                            'line_number': question_end
                        })
                        template_added += 1
                
                processed_lines.append(lines[i])
                
                # Kiểm tra xem có cần chèn template tại vị trí này không
                for template_info in templates_to_insert:
                    if template_info['line_number'] == i:
                        processed_lines.extend(template_info['template'])
                        break
                
                i += 1
            
            print(f"✅ Đã thêm {template_added} template lời giải")
            return '\n'.join(processed_lines)
            
        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý nội dung: {e}")
            import traceback
            traceback.print_exc()
            return content  # Trả về nội dung gốc nếu có lỗi

    @staticmethod
    def _find_question_end(lines, start_idx):
        """Tìm vị trí cuối của câu hỏi (trước câu hỏi tiếp theo hoặc cuối file)"""
        for i in range(start_idx + 1, len(lines)):
            line = lines[i].strip()
            
            # Nếu gặp câu hỏi tiếp theo (cả in đậm và không in đậm, cả tiếng Việt và tiếng Anh), trả về vị trí trước đó
            is_next_question = (line.startswith("**Câu ") and ":**" in line) or \
                              (line.startswith("Câu ") and ":" in line and not line.startswith("**")) or \
                              (line.startswith("**Question ") and ":**" in line) or \
                              (line.startswith("Question ") and ":" in line and not line.startswith("**"))
            if is_next_question:
                return i - 1
                
            # Nếu gặp phần mới (PHẦN), trả về vị trí trước đó
            if "phần" in line.lower() and ("i" in line.lower() or "ii" in line.lower() or "iii" in line.lower()):
                return i - 1
        
        # Nếu không tìm thấy câu hỏi tiếp theo, trả về cuối file
        return len(lines) - 1

    @staticmethod
    def _check_existing_template(lines, start_idx):
        """Kiểm tra xem câu hỏi đã có template lời giải chưa"""
        # Tìm trong vòng 10 dòng tiếp theo
        for i in range(start_idx + 1, min(start_idx + 11, len(lines))):
            line = lines[i].strip()
            
            # Nếu gặp "Lời giải" hoặc "```" có nghĩa là đã có template
            if "Lời giải" in line or line == "```":
                return True
                
            # Nếu gặp câu hỏi tiếp theo thì dừng tìm kiếm (cả in đậm và không in đậm)
            is_next_question = (line.startswith("**Câu ") and ":**" in line) or \
                              (line.startswith("Câu ") and ":" in line and not line.startswith("**"))
            if is_next_question:
                break
                
        return False

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
        count = 0
        for i in range(start_idx + 1, min(start_idx + 15, len(lines))):
            line = lines[i].strip()
            # Kiểm tra định dạng rất chính xác: phải bắt đầu bằng A. B. C. D. ở đầu dòng
            if line.startswith("A.") or line.startswith("**A.**"):
                count += 1
            elif line.startswith("B.") or line.startswith("**B.**"):
                count += 1
            elif line.startswith("C.") or line.startswith("**C.**"):
                count += 1  
            elif line.startswith("D.") or line.startswith("**D.**"):
                count += 1
        
        # Chỉ coi là trắc nghiệm nếu có ít nhất 3 lựa chọn A,B,C,D
        return count >= 3

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
            "Lời giải",
            answer,
            "####",
            ""
        ]

    @staticmethod
    def _generate_true_false_template(answers):
        """Tạo template cho câu đúng/sai"""
        return [
            "Lời giải",
            answers,
            "####",
            ""
        ]

    @staticmethod
    def _generate_essay_template():
        """Tạo template cho câu tự luận"""
        return [
            "Lời giải",
            "####",
            ""
        ]
