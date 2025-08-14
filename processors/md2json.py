import re
import json
import os
import base64
# --- CÁC IMPORT CẦN THIẾT ---
from vertexai.preview.generative_models import GenerativeModel, Part, GenerationConfig
import requests
# Import cấu hình và schema của bạn
from config.vertex_ai_config import vertex_ai_config 
from config.response_schema import ARRAY_BASED_SCHEMA
from data.prompt.prompts import MD2JSON

def deep_replace_placeholders(data_structure, replacement_mapping):
    """
    Duyệt đệ quy qua cấu trúc dữ liệu và thay thế các placeholder bằng giá trị 
    tương ứng từ mapping (trong trường hợp này là thẻ <img> Base64).

    Args:
        data_structure: Dict hoặc List cần được xử lý.
        replacement_mapping: Dictionary map từ placeholder sang giá trị thay thế.
    
    Returns:
        Cấu trúc dữ liệu đã được cập nhật.
    """
    if isinstance(data_structure, dict):
        return {key: deep_replace_placeholders(value, replacement_mapping) for key, value in data_structure.items()}
    elif isinstance(data_structure, list):
        return [deep_replace_placeholders(item, replacement_mapping) for item in data_structure]
    elif isinstance(data_structure, str):
        processed_string = data_structure
        # Logic thay thế đã được tổng quát hóa
        for placeholder, replacement_value in replacement_mapping.items():
            processed_string = processed_string.replace(placeholder, replacement_value)
        return processed_string
    else:
        return data_structure

def process_markdown_with_vertex_ai(markdown_file_path: str) -> tuple[str, str | None]:
    """
    Xử lý file Markdown, chuyển đổi hình ảnh sang Base64 và nhúng vào kết quả JSON.
    """
    # ... (Phần kiểm tra và khởi tạo Vertex AI giữ nguyên) ...
    # 1. Kiểm tra và khởi tạo Vertex AI
    if not vertex_ai_config.is_configured():
        print(f"Lỗi: Cấu hình Vertex AI không hợp lệ. Bỏ qua file '{markdown_file_path}'.")
        return (markdown_file_path, None)

    if not vertex_ai_config.initialize_vertex_ai():
        print(f"Lỗi: Không thể khởi tạo Vertex AI. Bỏ qua file '{markdown_file_path}'.")
        return (markdown_file_path, None)

    # 2. Kiểm tra file và tạo đường dẫn output
    if not os.path.exists(markdown_file_path):
        print(f"Lỗi: Không tìm thấy file '{markdown_file_path}'.")
        return (markdown_file_path, None)
    
    file_name, _ = os.path.splitext(os.path.basename(markdown_file_path))
    output_dir = os.path.join(os.path.dirname(markdown_file_path), "ai_struc_detec")
    os.makedirs(output_dir, exist_ok=True)
    output_json_path = os.path.join(output_dir, f"{file_name}.json")
    
    print(f"Đang xử lý file: {os.path.basename(markdown_file_path)}...")

    try:
        with open(markdown_file_path, 'r', encoding='utf-8') as file:
            markdown_content = file.read()

        # BƯỚC 1: TIỀN XỬ LÝ - Tìm ảnh và tạo placeholder
        image_url_mapping = {} 
        def image_replacer(match):
            url = match.group(1)
            placeholder = f"[IMAGE_{len(image_url_mapping)}]"
            image_url_mapping[placeholder] = url
            return placeholder

        image_pattern = re.compile(r"!\[.*?\]\((.*?)\)")
        modified_markdown_content = image_pattern.sub(image_replacer, markdown_content)

        # BƯỚC 2: TẢI ẢNH, MÃ HÓA BASE64 VÀ TẠO MAPPING THAY THẾ
        base64_replacement_mapping = {}
        if image_url_mapping:
            print(f"Tìm thấy {len(image_url_mapping)} ảnh. Đang xử lý...")
            # Đổi tên biến 'url' thành 'path_or_url' cho rõ ràng
            for placeholder, path_or_url in image_url_mapping.items():
                try:
                    image_bytes = None
                    
                    # PHÂN BIỆT URL VÀ ĐƯỜNG DẪN CỤC BỘ
                    if path_or_url.lower().startswith('http://') or path_or_url.lower().startswith('https://'):
                        # TRƯỜNG HỢP 1: ĐÂY LÀ URL -> DÙNG REQUESTS
                        print(f"  {placeholder}: Đang tải từ URL {path_or_url}...")
                        response = requests.get(path_or_url, timeout=20)
                        response.raise_for_status()  # Báo lỗi nếu request không thành công
                        image_bytes = response.content
                    else:
                        # TRƯỜNG HỢP 2: ĐÂY LÀ ĐƯỜNG DẪN FILE TRÊN MÁY
                        print(f"  {placeholder}: Đang đọc từ đường dẫn file {path_or_url}...")
                        if not os.path.exists(path_or_url):
                            raise FileNotFoundError(f"Tệp không tồn tại tại '{path_or_url}'")
                        
                        # Mở và đọc file ở chế độ nhị phân ('rb')
                        with open(path_or_url, 'rb') as image_file:
                            image_bytes = image_file.read()

                    # --- PHẦN XỬ LÝ CHUNG SAU KHI ĐÃ CÓ image_bytes ---
                    
                    # Mã hóa sang Base64
                    base64_encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Xác định Mime Type (loại ảnh)
                    # Dùng os.path.splitext để lấy phần mở rộng file chính xác hơn
                    _, extension = os.path.splitext(path_or_url.lower())
                    mime_type = "image/jpeg" # Mặc định
                    if extension == ".png":
                        mime_type = "image/png"
                    elif extension == ".gif":
                        mime_type = "image/gif"
                    elif extension == ".svg":
                        mime_type = "image/svg+xml"

                    # Tạo thẻ <img> HTML hoàn chỉnh
                    html_tag = f'<img src="data:{mime_type};base64,{base64_encoded_data}" alt="" style="max-width: 100%;">'
                    
                    # Lưu vào mapping thay thế
                    base64_replacement_mapping[placeholder] = html_tag
                    print(f"  {placeholder}: Đã mã hóa thành công.")
                
                # Bắt cả lỗi mạng và lỗi file
                except (requests.exceptions.RequestException, IOError, FileNotFoundError) as e:
                    print(f"  LỖI với {placeholder}: Không thể xử lý ảnh từ '{path_or_url}'. Lỗi: {e}")
                    # Nếu lỗi, giữ lại một thông báo lỗi trong mapping
                    base64_replacement_mapping[placeholder] = f"[LỖI KHI XỬ LÝ ẢNH: {path_or_url}]"

        # ... (Phần prompt và gọi AI giữ nguyên) ...
        # 3. Cập nhật prompt cho model chỉ xử lý văn bản
        prompt_text = MD2JSON.format(modified_markdown_content=modified_markdown_content)
       
        generation_config = GenerationConfig(
            temperature=0.2,
            top_p=0.8,
            response_mime_type="application/json",
            response_schema=ARRAY_BASED_SCHEMA
        )
       
        # 4. Gọi model (chỉ gửi văn bản)
        model = GenerativeModel(vertex_ai_config.model_name)
       
        print("Đang gửi yêu cầu (chỉ văn bản) đến Vertex AI...")
        response = model.generate_content(
            contents=[prompt_text],
            generation_config=generation_config,
            stream=False
        )
        
        response_text = response.text.strip()
        
        # 5. Xử lý kết quả trả về
        if not response_text:
            print(f"Lỗi: AI không trả về nội dung cho file '{markdown_file_path}'.")
            return (markdown_file_path, None)

        if response_text.startswith('```json') and response_text.endswith('```'):
            response_text = response_text[7:-3].strip()

        json_object = json.loads(response_text)

        # BƯỚC 3: HẬU XỬ LÝ - KHÔI PHỤC ẢNH DẠNG BASE64
        print("AI đã xử lý xong. Đang nhúng ảnh Base64 vào cấu trúc JSON...")
        final_json_object = deep_replace_placeholders(json_object, base64_replacement_mapping)

        # Ghi file JSON cuối cùng
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(final_json_object, f, ensure_ascii=False, indent=4)
       
        print(f"✔️ Kết quả đã được lưu thành công tại '{output_json_path}'.\n")
        return (markdown_file_path, output_json_path)

    except json.JSONDecodeError as e:
        print(f"Lỗi: JSON không hợp lệ. Lỗi: {e}\nNội dung từ AI:\n{response_text}\n")
        return (markdown_file_path, None)
    except Exception as e:
        print(f"Đã xảy ra lỗi không xác định khi xử lý file '{markdown_file_path}': {e}\n")
        return (markdown_file_path, None)



# process_markdown_with_vertex_ai(r"C:\Users\Admin\Downloads\QProcess\data\output\pdf3_mathpix_mapped_20250813_141622.md")