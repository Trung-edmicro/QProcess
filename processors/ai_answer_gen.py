import json
import re
from typing import List, Dict, Any
from config.response_schema import AI_ANSWER_GEN,ARRAY_BASED_SCHEMA
import vertexai
from vertexai.generative_models import  GenerativeModel,Tool,FunctionDeclaration 
from vertexai.generative_models._generative_models import ToolConfig

import copy
from config.vertex_ai_config import vertex_ai_config 
TYPE_ANSWER_DATA = [
    { "id": 0, "text": 'Trắc nghiệm 1 đáp án', "disabled": False },
    { "id": 1, "text": 'Trắc nghiệm nhiều đáp án có thể là dạng đúng sai', "disabled": False },
    { "id": 2, "text": 'Tự luận điền đáp án', "disabled": True },
    { "id": 3, "text": 'Tự luận', "disabled": False },
    { "id": 4, "text": 'Tự luận 1 đáp án', "disabled": True },
    { "id": 5, "text": 'Tự luận nhiều đáp án có thứ tự', "disabled": True },
    { "id": 999, "text": 'Không xác định', "disabled": True },
]

def get_type_answer_text(type_id):
    """
    Lấy chuỗi mô tả loại câu trả lời dựa vào ID.

    Args:
        type_id (int): ID của loại câu trả lời.

    Returns:
        str: Chuỗi mô tả tương ứng, hoặc 'Không xác định' nếu không tìm thấy.
    """
    # Lặp qua từng dictionary trong danh sách
    for item in TYPE_ANSWER_DATA:
        # Nếu tìm thấy id khớp, trả về text
        if int(item["id"]) == int(type_id):
            return item["text"]
    
    # Nếu vòng lặp kết thúc mà không tìm thấy, trả về giá trị mặc định
    return "Không xác định"

def _cau_hoi_da_co_dap_an(question_obj):
    """Hàm phụ để kiểm tra xem câu hỏi đã có đáp án hay chưa."""
    # Nếu có optionAnswer và không rỗng thì đã có đáp án
    if question_obj.get("optionAnswer") and len(question_obj["optionAnswer"])> 0 and question_obj.get("explainQuestion","") != "":
        return True

    # Hoặc nếu có bất kỳ isAnswer nào là true
    if "options" in question_obj:
        for opt in question_obj["options"]:
            if opt.get("isAnswer") is True and "explainQuestion" in question_obj:
                return True
    return False

def _chuan_bi_json_cho_ai(question_obj):
    """Hàm phụ để tạo một bản sao của câu hỏi và loại bỏ các trường đáp án."""
    clean_question = copy.deepcopy(question_obj)
    print("TRƯỚC KHÚ XỬ LÝ AI ", question_obj)
    # Loại bỏ các trường liên quan đến đáp án
   
    clean_question.pop("isExplain", None)
   
    clean_question.pop("scores", None)
    clean_question.pop("mappingScore", None)
    clean_question.pop("index", None)
    clean_question.pop("numberId", None)
    clean_question.pop("indexPart", None)

    if clean_question.get("typeAnswer",None):
        clean_question["typeAnswer"]=get_type_answer_text(question_obj.get("typeAnswer",None))
       
    # Reset isAnswer trong các options
    if "options" in clean_question:
        for opt in clean_question["options"]:
            # opt.pop("isAnswer", None)
            # Giữ lại các trường cần thiết để AI hiểu câu hỏi
            opt.pop("index", None)
            
    return clean_question
def validate_vertex_ai_config() -> bool:
    """
    Kiểm tra và khởi tạo cấu hình Vertex AI.
    
    Returns:
        bool: True nếu cấu hình hợp lệ và khởi tạo thành công, False nếu không.
    """
    if not vertex_ai_config.is_configured():
        print("Lỗi: Cấu hình Vertex AI không hợp lệ.")
        return False

    if not vertex_ai_config.initialize_vertex_ai():
        print("Lỗi: Không thể khởi tạo Vertex AI.")
        return False
        
    return True

def giai_cau_hoi_bang_ai(json_input) :
    """
    Hàm nhận một chuỗi JSON chứa các câu hỏi, sử dụng Vertex AI để giải các câu hỏi
    chưa có đáp án và trả về chuỗi JSON đã được cập nhật.

    Args:
        json_input_string: Chuỗi JSON đầu vào.

    Returns:
        Chuỗi JSON đầu ra đã được điền đáp án.
    """
    if not validate_vertex_ai_config():
        print(f"Bỏ qua file  do lỗi cấu hình Vertex AI.")
        
    data=json_input

    # Cấu hình model với function calling
    model = GenerativeModel(
        "gemini-2.5-pro",
        tools=[Tool(function_declarations=[
            FunctionDeclaration(
                name="giai_cau_hoi",
                description="Giải câu hỏi trắc nghiệm và cung cấp giải thích.",
                parameters=ARRAY_BASED_SCHEMA,
            )
        ])]
    )

   
    tool_config = ToolConfig(
        function_calling_config= ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.ANY,
                allowed_function_names= ["giai_cau_hoi"]
        )
    )
    # Lặp qua các khối câu hỏi
    for question_block in data.get("questions", []):
        # Trường hợp 1: Khối câu hỏi có đoạn văn (isHL = true)
        if question_block.get("isHL"):
            passage = question_block.get("content", "")
            for question in question_block.get("data", []):
                if not _cau_hoi_da_co_dap_an(question):
                    print(f"-> Đang giải câu hỏi numberId: {question.get('numberId')}...")
                    
                    # Chuẩn bị JSON "sạch" để gửi cho AI
                    clean_question_json = _chuan_bi_json_cho_ai(question)
                    
                    # Tạo prompt
                    prompt = f"""
                    Dựa vào đoạn văn và câu hỏi dưới đây, hãy giải câu hỏi và trả lời bằng cách gọi hàm 'giai_cau_hoi'.

                    ĐOẠN VĂN:
                    {passage}
                    
                    CÂU HỎI (định dạng JSON):
                    {json.dumps(clean_question_json, indent=2, ensure_ascii=False)}
                    """
                    
                    # Gọi API
                    print("promt cho ai ",prompt)
                    response = model.generate_content(prompt, tool_config=tool_config)
                    
                    # Xử lý và cập nhật kết quả
                    try:
                     
                        args = response.candidates[0].content.parts[0].function_call.args
                       
                        question["explainQuestion"] = args.get("explainQuestion", "")
                        question["optionAnswer"] = args.get("optionAnswer", [])
                        # question["typeAnswer"] = args.get("typeAnswer", "999")
                        question["isExplain"] = True
                        # Cập nhật isAnswer trong options
                        if "options" in question_block:
                            for i, opt in enumerate(question_block["options"]):
                                opt["isAnswer"] = args["options"][i].get("isAnswer", False)
                        else:
                            question_block["options"] = args.get("options", [])
                        
                        print(f"   => Đã giải xong!")
                    except (IndexError, AttributeError, KeyError) as e:
                        print(f"   => LỖI: Không thể lấy đáp án từ AI cho câu hỏi {question.get('numberId')}. Lỗi: {e}")

        # Trường hợp 2: Câu hỏi đứng một mình
        else:
            if not _cau_hoi_da_co_dap_an(question_block):
                print(f"-> Đang giải câu hỏi standalone numberId: {question_block.get('numberId')}...")
                
                clean_question_json = _chuan_bi_json_cho_ai(question_block)
                
                prompt = f"""
                Dựa vào câu hỏi dưới đây, hãy giải câu hỏi và trả lời bằng cách gọi hàm 'giai_cau_hoi'.

                CÂU HỎI (định dạng JSON):
                {json.dumps(clean_question_json, indent=2, ensure_ascii=False)}
                """
                print("promt cho ai ",prompt)
                response = model.generate_content(prompt, tool_config=tool_config)
                
                try:
                    args = response.candidates[0].content.parts[0].function_call.args
                    print("sau khi gen từ ai",args )
                    question_block["explainQuestion"] = args.get("explainQuestion", "")
                    question_block["optionAnswer"] = args.get("optionAnswer", [])
                    # question_block["typeAnswer"] = args.get("typeAnswer", "999")
                    question_block["isExplain"] = True
                    if "options" in question_block:
                        for i, opt in enumerate(question_block["options"]):
                            opt["isAnswer"] = args["options"][i].get("isAnswer", False)
                    else:
                        question_block["options"] = args.get("options", [])

                    print(f"   => Đã giải xong!")
                except (IndexError, AttributeError, KeyError) as e:
                    print(f"   => LỖI: Không thể lấy đáp án từ AI cho câu hỏi {question_block.get('numberId')}. Lỗi: {e}")
                    
    # Trả về JSON đã được cập nhật
    return data
