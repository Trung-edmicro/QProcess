# --- CÁC IMPORT CẦN THIẾT ---
import json
import vertexai
from vertexai.preview.generative_models import (
    GenerativeModel,
    Part,
    GenerationConfig,
    FunctionDeclaration,
    Tool
)

# Import cấu hình và schema của bạn
from config.vertex_ai_config import vertex_ai_config
from config.response_schema import ARRAY_BASED_SCHEMA

# --- CÁC HÀM TIỆN ÍCH VÀ KHỞI TẠO ---

def validate_vertex_ai_config() -> bool:
    """Kiểm tra và khởi tạo cấu hình Vertex AI."""
    if not vertex_ai_config.is_configured():
        print("Lỗi: Cấu hình Vertex AI không hợp lệ.")
        return False
    if not vertex_ai_config.initialize_vertex_ai():
        print("Lỗi: Không thể khởi tạo Vertex AI.")
        return False
    return True

# --- ĐỊNH NGHĨA CÔNG CỤ (TOOL) ---

def find_substring_indices(main_content: str, substring_to_find: str) -> dict:
    """Tìm chỉ số bắt đầu (start) và kết thúc (end) của một chuỗi con trong một chuỗi văn bản lớn."""
    print(f"--- 🔎 Đang thực thi công cụ: Tìm chuỗi: '{substring_to_find[:50]}...'")
    start_index = main_content.find(substring_to_find)
    if start_index == -1:
        print("    -> ❌ Không tìm thấy.")
        return {"start": -1, "end": -1, "message": "Không tìm thấy chuỗi con."}
    else:
        end_index = start_index + len(substring_to_find)
        print(f"    -> ✅ Tìm thấy tại: ({start_index}, {end_index})")
        return {"start": start_index, "end": end_index}

# --- MAIN LOGIC ---

def main():
    """Hàm chính thực thi luồng xử lý chuyển đổi Markdown sang JSON."""
    if not validate_vertex_ai_config():
        return

    # --- Bước 1: Khai báo công cụ và đọc dữ liệu ---
    find_indices_func_declaration = FunctionDeclaration(
        name="find_substring_indices",
        description="Tìm chỉ số bắt đầu (start) và kết thúc (end) của một chuỗi con (substring) trong một chuỗi văn bản lớn (main content). Sử dụng công cụ này cho MỌI TRƯỜNG `startIndex` và `endIndex` trong schema.",
        parameters={
            "type": "object",
            "properties": {
                "main_content": {"type": "string", "description": "Toàn bộ nội dung văn bản gốc để tìm kiếm bên trong."},
                "substring_to_find": {"type": "string", "description": "Đoạn văn bản cụ thể cần tìm chỉ số (ví dụ: nội dung một câu hỏi, nội dung một lựa chọn)."}
            },
            "required": ["main_content", "substring_to_find"]
        },
    )

    index_finder_tool = Tool(function_declarations=[find_indices_func_declaration])

    md_path = r"D:\Download\aicall\QProcess\data\output\mathpix_result_20250821_012221.md"
    try:
        with open(md_path, "r", encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file tại đường dẫn: {md_path}")
        return

    # --- Bước 2: Khởi tạo mô hình với Response Schema ---
    generation_config = GenerationConfig(
        response_mime_type="application/json",
        response_schema=ARRAY_BASED_SCHEMA,
        temperature=0.0
    )

    model = GenerativeModel(
        "gemini-2.5-flash", # Vẫn khuyến khích dùng model Pro
        tools=[index_finder_tool],
        generation_config=generation_config
    )
    chat = model.start_chat()

    # --- Bước 3: Tạo prompt và gửi yêu cầu đầu tiên ---
    prompt = f"""
    Bạn là một chuyên gia trích xuất dữ liệu.
    Nhiệm vụ của bạn là phân tích văn bản Markdown dưới đây và chuyển đổi nó thành một cấu trúc JSON theo schema đã được cung cấp.

    QUY TẮC QUAN TRỌNG:
    1.  Hãy gọi công cụ `find_substring_indices` nhiều lần cho tất cả các phần tử (học liệu, câu hỏi, lựa chọn, v.v.) mà bạn cần lấy chỉ số.
    2.  Sau khi đã thu thập ĐỦ thông tin từ các công cụ, bước cuối cùng của bạn là trả về một ĐOẠN VĂN BẢN JSON hoàn chỉnh và không gọi thêm bất kỳ công cụ nào nữa.

    Đây là văn bản gốc:
    ```markdown
    {content}
    ```
    Hãy bắt đầu quá trình phân tích và gọi các công cụ cần thiết.
    """

    print("--- 🚀 Bắt đầu gửi yêu cầu tới AI ---")
    response = chat.send_message(prompt)

    # --- Bước 4 & 5: Vòng lặp xử lý cho đến khi nhận được kết quả cuối cùng ---
    while response.candidates[0].content.parts[0].function_call:
        api_responses = []
        function_calls = response.candidates[0].content.parts
        
        print(f"\n--- 🤖 AI đã đề xuất {len(function_calls)} lần gọi công cụ. Bắt đầu thực thi... ---")

        for part in function_calls:
            if fc := part.function_call: # Sử dụng walrus operator cho gọn
                if fc.name == "find_substring_indices":
                    args = fc.args
                    result = find_substring_indices(
                        main_content=args["main_content"],
                        substring_to_find=args["substring_to_find"]
                    )
                    api_responses.append(Part.from_function_response(
                        name="find_substring_indices",
                        response={"content": result}
                    ))

        if not api_responses:
            print("\n--- ⚠️ AI không yêu cầu gọi công cụ hợp lệ. Dừng lại. ---")
            break

        print("\n--- 📤 Đã thực thi xong. Gửi lại toàn bộ kết quả cho AI để tiếp tục xử lý... ---")
        response = chat.send_message(api_responses)
        # Vòng lặp sẽ kiểm tra lại điều kiện ở đầu: AI có trả về function_call nữa không?
        # Nếu không, vòng lặp kết thúc.

    # --- Bước 6: Xử lý kết quả cuối cùng ---
    print("\n--- ✅ AI đã trả về kết quả cuối cùng (không còn gọi hàm)! ---")
    try:
        # Bây giờ, response.text sẽ tồn tại vì AI không trả về function_call nữa
        final_json_output = json.loads(response.text)
        pretty_json = json.dumps(final_json_output, indent=2, ensure_ascii=False)
        print("\nKết quả JSON hoàn chỉnh:\n")
        print(pretty_json)
    except (AttributeError, json.JSONDecodeError) as e:
        print(f"\nLỗi: Không thể lấy hoặc phân tích JSON từ phản hồi cuối cùng. Lỗi: {e}")
        print("Phản hồi thô từ AI:", response)

if __name__ == "__main__":
    main()