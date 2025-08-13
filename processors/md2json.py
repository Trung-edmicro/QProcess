import re
import json
import os
import base64
from typing import Dict, Tuple, Optional, Union, Any
# --- CÁC IMPORT CẦN THIẾT ---
from vertexai.preview.generative_models import GenerativeModel, Part, GenerationConfig
import requests
# Import cấu hình và schema của bạn
from config.vertex_ai_config import vertex_ai_config 
from config.response_schema import ARRAY_BASED_SCHEMA
from data.prompt.prompts import MD2JSON


def deep_replace_placeholders(data_structure: Union[Dict, list, str, Any], 
                            replacement_mapping: Dict[str, str]) -> Union[Dict, list, str, Any]:
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


def validate_input_file(markdown_file_path: str) -> bool:
    """
    Kiểm tra tính hợp lệ của file đầu vào.
    
    Args:
        markdown_file_path: Đường dẫn đến file Markdown
        
    Returns:
        bool: True nếu file tồn tại, False nếu không.
    """
    if not os.path.exists(markdown_file_path):
        print(f"Lỗi: Không tìm thấy file '{markdown_file_path}'.")
        return False
    return True


def setup_output_directory(markdown_file_path: str) -> str:
    """
    Tạo thư mục output và trả về đường dẫn file JSON kết quả.
    
    Args:
        markdown_file_path: Đường dẫn file Markdown đầu vào
        
    Returns:
        str: Đường dẫn file JSON output
    """
    file_name, _ = os.path.splitext(os.path.basename(markdown_file_path))
    output_dir = os.path.join(os.path.dirname(markdown_file_path), "ai_struc_detec")
    os.makedirs(output_dir, exist_ok=True)
    output_json_path = os.path.join(output_dir, f"{file_name}.json")
    return output_json_path


def extract_image_urls(markdown_content: str) -> Tuple[str, Dict[str, str]]:
    """
    Tìm và thay thế các URL ảnh trong markdown bằng placeholder.
    
    Args:
        markdown_content: Nội dung markdown gốc
        
    Returns:
        Tuple[str, Dict[str, str]]: (markdown_đã_sửa, mapping_placeholder_to_url)
    """
    image_url_mapping = {} 
    
    def image_replacer(match):
        url = match.group(1)
        placeholder = f"[IMAGE_{len(image_url_mapping)}]"
        image_url_mapping[placeholder] = url
        return placeholder

    # Pattern cho markdown image syntax: ![alt](url)
    markdown_image_pattern = re.compile(r"!\[.*?\]\((.*?)\)")
    
    # Pattern cho HTML img tag: <img src="url" ...>
    html_img_pattern = re.compile(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
    
    # Xử lý markdown images trước
    modified_content = markdown_image_pattern.sub(image_replacer, markdown_content)
    
    # Sau đó xử lý HTML img tags
    modified_content = html_img_pattern.sub(image_replacer, modified_content)
    
    return modified_content, image_url_mapping


def load_image_from_url(url: str) -> bytes:
    """
    Tải ảnh từ URL.
    
    Args:
        url: URL của ảnh
        
    Returns:
        bytes: Dữ liệu ảnh dạng bytes
        
    Raises:
        requests.exceptions.RequestException: Lỗi khi tải ảnh từ URL
    """
    print(f"  Đang tải từ URL {url}...")
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.content


def load_image_from_file(file_path: str) -> bytes:
    """
    Đọc ảnh từ file local.
    
    Args:
        file_path: Đường dẫn đến file ảnh
        
    Returns:
        bytes: Dữ liệu ảnh dạng bytes
        
    Raises:
        FileNotFoundError: File không tồn tại
        IOError: Lỗi khi đọc file
    """
    print(f"  Đang đọc từ đường dẫn file {file_path}...")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Tệp không tồn tại tại '{file_path}'")
    
    with open(file_path, 'rb') as image_file:
        return image_file.read()


def determine_mime_type(path_or_url: str) -> str:
    """
    Xác định MIME type dựa trên extension của file.
    
    Args:
        path_or_url: Đường dẫn hoặc URL của ảnh
        
    Returns:
        str: MIME type của ảnh
    """
    _, extension = os.path.splitext(path_or_url.lower())
    mime_mapping = {
        ".png": "image/png",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }
    return mime_mapping.get(extension, "image/jpeg")


def encode_image_to_base64_html(image_bytes: bytes, mime_type: str) -> str:
    """
    Mã hóa ảnh sang Base64 và tạo thẻ HTML img.
    
    Args:
        image_bytes: Dữ liệu ảnh dạng bytes
        mime_type: MIME type của ảnh
        
    Returns:
        str: Thẻ HTML img với data URI Base64
    """
    base64_encoded_data = base64.b64encode(image_bytes).decode('utf-8')
    html_tag = f'<img src="data:{mime_type};base64,{base64_encoded_data}" alt="" style="max-width: 100%;">'
    return html_tag


def process_single_image(placeholder: str, path_or_url: str) -> str:
    """
    Xử lý một ảnh đơn lẻ: tải, mã hóa Base64 và tạo thẻ HTML.
    
    Args:
        placeholder: Placeholder string trong markdown
        path_or_url: Đường dẫn hoặc URL của ảnh
        
    Returns:
        str: Thẻ HTML img hoặc thông báo lỗi
    """
    try:
        # Xác định loại nguồn ảnh và tải
        if path_or_url.lower().startswith(('http://', 'https://')):
            image_bytes = load_image_from_url(path_or_url)
        else:
            image_bytes = load_image_from_file(path_or_url)

        # Xác định MIME type và mã hóa
        mime_type = determine_mime_type(path_or_url)
        html_tag = encode_image_to_base64_html(image_bytes, mime_type)
        
        print(f"  {placeholder}: Đã mã hóa thành công.")
        return html_tag
        
    except (requests.exceptions.RequestException, IOError, FileNotFoundError) as e:
        print(f"  LỖI với {placeholder}: Không thể xử lý ảnh từ '{path_or_url}'. Lỗi: {e}")
        return f"[LỖI KHI XỬ LÝ ẢNH: {path_or_url}]"


def process_images_to_base64(image_url_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Xử lý tất cả ảnh và chuyển đổi sang Base64.
    
    Args:
        image_url_mapping: Dictionary mapping từ placeholder sang URL/path
        
    Returns:
        Dict[str, str]: Dictionary mapping từ placeholder sang thẻ HTML Base64
    """
    if not image_url_mapping:
        return {}
    
    print(f"Tìm thấy {len(image_url_mapping)} ảnh. Đang xử lý...")
    base64_replacement_mapping = {}
    
    for placeholder, path_or_url in image_url_mapping.items():
        html_tag = process_single_image(placeholder, path_or_url)
        base64_replacement_mapping[placeholder] = html_tag
    
    return base64_replacement_mapping


def call_vertex_ai_model(modified_markdown_content: str) -> str:
    """
    Gọi Vertex AI model để chuyển đổi markdown sang JSON.
    
    Args:
        modified_markdown_content: Nội dung markdown đã được xử lý
        
    Returns:
        str: JSON string từ AI model
        
    Raises:
        Exception: Lỗi khi gọi AI model hoặc xử lý response
    """
    prompt_text = MD2JSON.format(modified_markdown_content=modified_markdown_content)
   
    generation_config = GenerationConfig(
        temperature=0.2,
        top_p=0.8,
        response_mime_type="application/json",
        response_schema=ARRAY_BASED_SCHEMA
    )
   
    model = GenerativeModel(vertex_ai_config.model_name)
   
    print("Đang gửi yêu cầu (chỉ văn bản) đến Vertex AI...")
    response = model.generate_content(
        contents=[prompt_text],
        generation_config=generation_config,
        stream=False
    )
    
    response_text = response.text.strip()
    
    if not response_text:
        raise Exception("AI không trả về nội dung")
    
    # Xử lý format markdown code block nếu có
    if response_text.startswith('```json') and response_text.endswith('```'):
        response_text = response_text[7:-3].strip()
    
    return response_text


def save_json_result(json_object: Any, output_path: str) -> None:
    """
    Lưu kết quả JSON vào file.
    
    Args:
        json_object: Object JSON cần lưu
        output_path: Đường dẫn file output
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_object, f, ensure_ascii=False, indent=4)



def create_question_data(question, index, number_id, index_part, is_standalone=False):
    """
    Tạo dữ liệu question theo format mới
    """
    # Xử lý options
    processed_options = []
    if 'options' in question:
        for i, option in enumerate(question['options']):
            processed_option = {
                "content": option.get('content', ''),
                "index": i
            }
            
            # Thêm isAnswer nếu có
            if 'isAnswer' in option:
                processed_option['isAnswer'] = option['isAnswer']
            
            # Tự động tạo optionLabel
            if i < 26:  # A-Z
                processed_option['optionLabel'] = chr(65 + i)  # A, B, C, D...
            
            processed_options.append(processed_option)
    
    # Tạo base question data
    question_data = {
        "content": question.get('content', ''),
        "index": index,
        "numberId": number_id,
        "indexPart": index_part,
        "typeAnswer": question.get('typeAnswer', '999')
    }
    
    # Thêm các trường optional nếu có
    optional_fields = [
        'explainQuestion', 'isExplain', 'mappingScore', 
        'optionAnswer', 'scores', 'totalOption'
    ]
    
    for field in optional_fields:
        if field in question:
            question_data[field] = question[field]
    
    # Thêm options nếu có
    if processed_options:
        question_data['options'] = processed_options
    
    # Nếu là standalone question, thêm isHL=false
    if is_standalone:
        question_data['isHL'] = False
    
    return question_data

def process_json_data(json_object):
    """
    Chuyển đổi dữ liệu JSON đầu vào, giữ nguyên thứ tự các câu hỏi.
    - Các câu hỏi có cùng 'materialRef' sẽ được gộp lại thành một nhóm.
    - Các câu hỏi không có 'materialRef' sẽ được giữ nguyên là các câu hỏi độc lập.
    - Thứ tự của các nhóm và các câu hỏi độc lập được bảo toàn như ban đầu.
    """
    print("Đang xử lý dữ liệu JSON theo cấu trúc mới...")

    # Lấy dữ liệu gốc
    materials = {mat['id']: mat for mat in json_object.get('materials', [])}
    old_questions = json_object.get('questions', [])

    # Cấu trúc mới để lưu kết quả
    new_structure = []
    # Dùng một set để theo dõi các material group đã được xử lý
    processed_material_ids = set()
    current_index_part = 0
    index_in_current_part = 0
    # Duyệt qua từng câu hỏi THEO ĐÚNG THỨ TỰ BAN ĐẦU
    for question in old_questions:
        material_ref = question.get('materialRef')
        if current_index_part != question['indexPart']:
            current_index_part = question['indexPart']
            index_in_current_part = 0
        # --- TRƯỜNG HỢP 1: Câu hỏi thuộc về một nhóm tài liệu ---
        if material_ref and material_ref in materials:
            # Chỉ xử lý nhóm này nếu nó chưa được xử lý trước đó
            if material_ref not in processed_material_ids:
                # Tìm tất cả các câu hỏi khác trong `old_questions` có cùng material_ref
                group_questions = [
                    q for q in old_questions if q.get('materialRef') == material_ref
                ]

                # Tạo danh sách các câu hỏi con cho nhóm này
                child_questions = []
                for q_in_group in group_questions:
                    # Dùng hàm helper để format câu hỏi, giữ nguyên dữ liệu gốc
                    child_question = create_question_data(q_in_group,index=index_in_current_part, number_id=q_in_group['numberId'], index_part=q_in_group['indexPart'], is_standalone=False)
                    child_questions.append(child_question)

                # Tạo đối tượng nhóm tài liệu học tập
                material_group = {
                    "isHL": True,
                    "content": materials[material_ref].get('content', ''),
                    "data": child_questions
                }
                new_structure.append(material_group)

                # Đánh dấu là đã xử lý group này để không lặp lại
                processed_material_ids.add(material_ref)

        # --- TRƯỜNG HỢP 2: Câu hỏi đứng riêng (standalone) ---
        else:
            # Tạo đối tượng cho câu hỏi đứng riêng
            standalone_question_data =create_question_data(question,index=index_in_current_part, number_id=question['numberId'], index_part=question['indexPart'], is_standalone=True)

            standalone_item = {
                "isHL": False,
                **standalone_question_data # Dùng unpacking để thêm tất cả các key từ câu hỏi
            }
            new_structure.append(standalone_item)
        index_in_current_part+=1
    # Trả về kết quả cuối cùng
    result = {
        "questions": new_structure
        # Bạn có thể thêm các metadata khác vào đây nếu cần
    }

    print(f"Đã xử lý xong: {len(processed_material_ids)} nhóm tài liệu và "
          f"{len(new_structure) - len(processed_material_ids)} câu hỏi đứng riêng.")
    return result
def process_markdown_with_vertex_ai(markdown_file_path: str) -> Tuple[str, Optional[str]]:
    """
    Xử lý file Markdown, chuyển đổi hình ảnh sang Base64 và nhúng vào kết quả JSON.
    
    Args:
        markdown_file_path: Đường dẫn đến file Markdown
        
    Returns:
        Tuple[str, Optional[str]]: (đường_dẫn_input, đường_dẫn_output_hoặc_None)
    """
    # 1. Kiểm tra cấu hình và file đầu vào
    if not validate_vertex_ai_config():
        print(f"Bỏ qua file '{markdown_file_path}' do lỗi cấu hình Vertex AI.")
        return (markdown_file_path, None)
    
    if not validate_input_file(markdown_file_path):
        return (markdown_file_path, None)
    
    # 2. Thiết lập đường dẫn output
    output_json_path = setup_output_directory(markdown_file_path)
    print(f"Đang xử lý file: {os.path.basename(markdown_file_path)}...")
    
    try:
        # 3. Đọc nội dung file
        with open(markdown_file_path, 'r', encoding='utf-8') as file:
            markdown_content = file.read()
        
        # 4. Trích xuất và thay thế ảnh bằng placeholder
        modified_markdown_content, image_url_mapping = extract_image_urls(markdown_content)
        
        # 5. Xử lý ảnh và chuyển đổi sang Base64
        base64_replacement_mapping = process_images_to_base64(image_url_mapping)
        
        # 6. Gọi AI model
        response_text = call_vertex_ai_model(modified_markdown_content)
        
        # 7. Parse JSON response
        json_object = json.loads(response_text)
        
        # 8. Khôi phục ảnh Base64 vào JSON
        print("AI đã xử lý xong. Đang nhúng ảnh Base64 vào cấu trúc JSON...")
        image_replacement_json_object = deep_replace_placeholders(json_object, base64_replacement_mapping)
        # 9. Xử lý json về định dạng đúng
        final_json_object = process_json_data(image_replacement_json_object)
        # 10. Lưu kết quả
        save_json_result(final_json_object, output_json_path)
        print(f"✔️ Kết quả đã được lưu thành công tại '{output_json_path}'.\n")
        
        return (markdown_file_path, output_json_path)
        
    except json.JSONDecodeError as e:
        print(f"Lỗi: JSON không hợp lệ. Lỗi: {e}\nNội dung từ AI:\n{response_text}\n")
        return (markdown_file_path, None)
    except Exception as e:
        print(f"Đã xảy ra lỗi không xác định khi xử lý file '{markdown_file_path}': {e}\n")
        return (markdown_file_path, None)