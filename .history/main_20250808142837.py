"""
Main file để test các chức năng OCR và xử lý ảnh với multiprocessing
"""
import os
import sys
from config import app_config
from datetime import datetime
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def process_single_image(image_info):
    """
    Xử lý một ảnh đơn lẻ - được sử dụng trong multiprocessing
    Args:
        image_info: tuple (index, image_path)
    Returns:
        tuple (index, result_text, image_path, success, error_msg)
    """
    index, image_path = image_info
    
    try:
        print(f"🔄 [Process {index}] Bắt đầu xử lý: {os.path.basename(image_path)}")
        
        # Import lại config trong process mới
        from config import app_config
        
        # Kiểm tra file ảnh có tồn tại không
        if not os.path.exists(image_path):
            return (index, None, image_path, False, f"File không tồn tại: {image_path}")
        
        # Kiểm tra cấu hình Vertex AI
        if not app_config.vertex_ai.is_configured():
            return (index, None, image_path, False, "Vertex AI chưa được cấu hình đúng!")
        
        # Khởi tạo Vertex AI
        if not app_config.vertex_ai.initialize_vertex_ai():
            return (index, None, image_path, False, "Không thể khởi tạo Vertex AI!")
        
        # Tạo model
        model = GenerativeModel(app_config.vertex_ai.model_name)
        
        # Đọc ảnh và tạo Part object
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        
        # Xác định mime type
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.png': 
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'): 
            mime_type = 'image/jpeg'
        elif ext == '.gif': 
            mime_type = 'image/gif'
        elif ext == '.webp': 
            mime_type = 'image/webp'
        else: 
            mime_type = 'image/png'
        
        image_part = Part.from_data(data=image_bytes, mime_type=mime_type)
        
        # Tạo prompt cho OCR
        text_prompt = """
        Hãy đọc và trích xuất toàn bộ text từ ảnh này. 
        Yêu cầu chung:
        1. Đọc chính xác tất cả text có trong ảnh
        2. Giữ nguyên format và cấu trúc của text
        3. Nếu có công thức toán học, hãy chuyển sang định dạng LaTeX
        4. Trả về kết quả chỉ gồm nội dung OCR được, không cần giải thích hay bình luận gì thêm.
        
        Yêu cầu cụ thể:
        1. Trường hợp ảnh có kí tự đặc biệt (như chữ ký, hình vẽ tay) thì không trả về ở kết quả.
        2. Với ảnh là đề thi thì cần loại bỏ các phần không liên quan như thông tin trường học/học sinh, hướng dẫn, số trang, mã đề.
        3. Vì là nội dung OCR liên quan đến các câu hỏi nên cần đảm bảo có các phần tiêu đề, câu hỏi, đáp án rõ ràng.
        """
        
        text_part = Part.from_text(text_prompt)
        
        # Tạo generation config
        generation_config = GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            max_output_tokens=8192
        )
        
        # Gọi API với retry logic
        prompt_parts = [text_part, image_part]
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔄 [Process {index}] Thử lần {attempt + 1}/{max_retries}...")
                
                response = model.generate_content(
                    prompt_parts, 
                    generation_config=generation_config, 
                    stream=False
                )
                
                if response and response.text:
                    print(f"✅ [Process {index}] Hoàn thành: {os.path.basename(image_path)}")
                    return (index, response.text, image_path, True, None)
                else:
                    print(f"⚠️ [Process {index}] Lần thử {attempt + 1}: Không nhận được kết quả từ Vertex AI")
                    if attempt < max_retries - 1:  # Không sleep ở lần thử cuối
                        time.sleep(2)  # Đợi 2 giây trước khi retry
                        
            except Exception as api_error:
                print(f"⚠️ [Process {index}] Lần thử {attempt + 1}: Lỗi API - {str(api_error)}")
                if attempt < max_retries - 1:  # Không sleep ở lần thử cuối
                    time.sleep(2)  # Đợi 2 giây trước khi retry
        
        # Nếu tất cả attempts đều thất bại
        return (index, None, image_path, False, f"Không nhận được kết quả từ Vertex AI sau {max_retries} lần thử")
            
    except Exception as e:
        error_msg = f"Lỗi khi xử lý ảnh {image_path}: {str(e)}"
        print(f"❌ [Process {index}] {error_msg}")
        return (index, None, image_path, False, error_msg)

def process_multiple_images(image_paths, max_workers=None):
    """
    Xử lý nhiều ảnh đồng thời bằng multiprocessing
    Args:
        image_paths: list đường dẫn các ảnh
        max_workers: số process tối đa (mặc định = số CPU)
    Returns:
        list kết quả theo thứ tự input
    """
    if not image_paths:
        print("❌ Không có ảnh nào để xử lý!")
        return []
    
    # Xác định số workers
    if max_workers is None:
        max_workers = min(len(image_paths), mp.cpu_count())
    
    print(f"🚀 Bắt đầu xử lý {len(image_paths)} ảnh với {max_workers} processes")
    
    # Tạo list (index, image_path) để giữ thứ tự
    image_info_list = [(i, path) for i, path in enumerate(image_paths)]
    
    # Khởi tạo list kết quả với None
    results = [None] * len(image_paths)
    
    start_time = time.time()
    
    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit tất cả tasks
            future_to_info = {
                executor.submit(process_single_image, info): info 
                for info in image_info_list
            }
            
            # Collect results khi hoàn thành
            completed_count = 0
            for future in as_completed(future_to_info):
                try:
                    index, result_text, image_path, success, error_msg = future.result()
                    
                    # Lưu kết quả theo đúng thứ tự
                    results[index] = {
                        'index': index,
                        'image_path': image_path,
                        'result_text': result_text,
                        'success': success,
                        'error_msg': error_msg
                    }
                    
                    completed_count += 1
                    print(f"📊 Tiến độ: {completed_count}/{len(image_paths)} ảnh hoàn thành")
                    
                except Exception as e:
                    # Lấy thông tin từ future_to_info nếu có lỗi
                    info = future_to_info[future]
                    index, image_path = info
                    results[index] = {
                        'index': index,
                        'image_path': image_path,
                        'result_text': None,
                        'success': False,
                        'error_msg': f"Lỗi future: {str(e)}"
                    }
                    completed_count += 1
                    print(f"❌ Lỗi xử lý ảnh {image_path}: {str(e)}")
    
    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng trong multiprocessing: {str(e)}")
        return []
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Thống kê kết quả
    successful_count = sum(1 for r in results if r and r['success'])
    failed_count = len(results) - successful_count
    
    print(f"\n📊 KẾT QUẢ TỔNG KẾT:")
    print(f"⏱️  Thời gian xử lý: {total_time:.2f} giây")
    print(f"✅ Thành công: {successful_count}/{len(image_paths)} ảnh")
    print(f"❌ Thất bại: {failed_count}/{len(image_paths)} ảnh")
    print(f"🔄 Tốc độ trung bình: {total_time/len(image_paths):.2f} giây/ảnh")
    
    return results

def save_multiple_results_to_markdown(results, output_folder):
    """
    Lưu tất cả kết quả OCR thành một file markdown tổng hợp
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ocr_multiple_results_{timestamp}.md"
        output_file = os.path.join(output_folder, filename)
        
        successful_results = [r for r in results if r and r['success']]
        failed_results = [r for r in results if r and not r['success']]
        
        with open(output_file, "w", encoding="utf-8") as f:
            
            # Kết quả thành công
            if successful_results:
                for result in successful_results:
                    f.write(result['result_text'])
            
            # Kết quả thất bại
            if failed_results:
                f.write("## ❌ Kết quả thất bại\n\n")
                for result in failed_results:
                    f.write(f"### 📷 Ảnh {result['index'] + 1}: `{os.path.basename(result['image_path'])}`\n\n")
                    f.write(f"**Lỗi:** {result['error_msg']}\n\n")
            
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu file markdown tổng hợp: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_image_files_from_folder(folder_path):
    """Lấy danh sách tất cả file ảnh trong thư mục"""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}
    image_files = []
    
    if not os.path.exists(folder_path):
        print(f"❌ Thư mục không tồn tại: {folder_path}")
        return []
    
    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            image_files.append(os.path.join(folder_path, filename))
    
    image_files.sort()  # Sắp xếp theo tên file
    return image_files

def single_image_mode(image_path):
    """Test xử lý 1 ảnh đơn lẻ"""
    print(f"\n🔄 CHẾ ĐỘ: Xử lý ảnh đơn lẻ")
    print(f"📷 Ảnh: {os.path.basename(image_path)}")
    
    result = ocr_image(image_path)
    
    if result:
        print("\n🎉 TEST THÀNH CÔNG!")
        output_file = save_ocr_result_to_markdown(result, image_path, app_config.output_folder)
        
        if output_file:
            print(f"💾 Đã lưu kết quả vào: {os.path.basename(output_file)}")
    else:
        print("\n❌ TEST THẤT BẠI!")

def multiple_images_mode(image_paths, max_workers=None):
    """Test xử lý nhiều ảnh đồng thời"""
    print(f"\n🔄 CHẾ ĐỘ: Xử lý đa tiến trình")
    
    # Xử lý đa tiến trình
    results = process_multiple_images(image_paths, max_workers)
    
    if results:
        # Lưu kết quả tổng hợp
        output_file = save_multiple_results_to_markdown(results, app_config.output_folder)
        
        if output_file:
            print(f"Đã lưu kết quả tổng hợp vào: {os.path.basename(output_file)}")
            
    else:
        print("\n❌ TOÀN BỘ QUÁ TRÌNH THẤT BẠI!")

def save_individual_results(results, output_folder):
    """Lưu từng kết quả thành file riêng lẻ"""
    print("\n💾 Đang lưu kết quả từng ảnh riêng lẻ...")
    
    successful_count = 0
    for result in results:
        if result and result['success']:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_name = os.path.splitext(os.path.basename(result['image_path']))[0]
                filename = f"ocr_{image_name}_{timestamp}.md"
                output_file = os.path.join(output_folder, filename)
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result['result_text'])
                
                successful_count += 1
                
            except Exception as e:
                print(f"   ❌ Lỗi lưu {result['image_path']}: {e}")
    
    print(f"💾 Đã lưu {successful_count} file kết quả riêng lẻ")

def ocr_image(image_path):
    """Test chức năng OCR ảnh bằng Vertex AI (legacy function)"""
    print("=== TEST OCR IMAGE VỚI VERTEX AI ===")
    
    # Kiểm tra file ảnh có tồn tại không
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy file ảnh: {image_path}")
        return None
    
    print(f"📷 Đang xử lý ảnh: {os.path.basename(image_path)}")
    
    # Kiểm tra cấu hình Vertex AI
    if not app_config.vertex_ai.is_configured():
        print("❌ Vertex AI chưa được cấu hình đúng!")
        return None
    
    try:
        # Khởi tạo Vertex AI
        print("🚀 Đang khởi tạo Vertex AI...")
        if not app_config.vertex_ai.initialize_vertex_ai():
            print("❌ Không thể khởi tạo Vertex AI!")
            return None
        
        # Tạo model
        model = GenerativeModel(app_config.vertex_ai.model_name)
        print(f"✅ Đã khởi tạo model: {app_config.vertex_ai.model_name}")
        
        # Đọc ảnh và tạo Part object
        print("📖 Đang đọc và xử lý ảnh...")
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        
        # Xác định mime type
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.png': 
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'): 
            mime_type = 'image/jpeg'
        elif ext == '.gif': 
            mime_type = 'image/gif'
        elif ext == '.webp': 
            mime_type = 'image/webp'
        else: 
            mime_type = 'image/png'
        
        image_part = Part.from_data(data=image_bytes, mime_type=mime_type)
        print(f"✅ Đã tạo image part với mime type: {mime_type}")
        
        # Tạo prompt cho OCR
        text_prompt = """
        Hãy đọc và trích xuất toàn bộ text từ ảnh này. 
        Yêu cầu chung:
        1. Đọc chính xác tất cả text có trong ảnh
        2. Giữ nguyên format và cấu trúc của text
        3. Nếu có công thức toán học, hãy chuyển sang định dạng LaTeX
        4. Nếu có bảng biểu, hãy mô tả cấu trúc bảng
        5. Trả về kết quả chỉ gồm nội dung OCR được, không cần giải thích hay bình luận gì thêm.
        
        Yêu cầu cụ thể:
        1. Trường hợp ảnh có kí tự đặc biệt (như chữ ký, hình vẽ tay) thì không trả về ở kết quả.
        2. Với ảnh là đề thi thì cần loại bỏ các phần không liên quan như thông tin trường/học sinh, hướng dẫn, số trang, mã đề.
        3. Vì là nội dung OCR liên quan đến các câu hỏi nên cần đảm bảo có các phần tiêu đề, câu hỏi, đáp án rõ ràng.
        """
        
        text_part = Part.from_text(text_prompt)
        
        # Tạo generation config
        generation_config = GenerationConfig(
            temperature=0.1,  # Thấp để OCR chính xác
            top_p=0.8,
            max_output_tokens=8192
        )
        
        # Gọi API với retry logic
        print("🔄 Đang gửi request đến Vertex AI...")
        prompt_parts = [text_part, image_part]
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔄 Thử lần {attempt + 1}/{max_retries}...")
                
                response = model.generate_content(
                    prompt_parts, 
                    generation_config=generation_config, 
                    stream=False
                )
                
                if response and response.text:
                    print("✅ Đã nhận được kết quả OCR!")
                    print("\n" + "="*60)
                    print("📄 KẾT QUẢ OCR:")
                    print("="*60)
                    print(response.text)
                    print("="*60)
                    return response.text
                else:
                    print(f"⚠️ Lần thử {attempt + 1}: Không nhận được kết quả từ Vertex AI")
                    if attempt < max_retries - 1:  # Không sleep ở lần thử cuối
                        print("⏳ Đợi 2 giây trước khi thử lại...")
                        time.sleep(2)  # Đợi 2 giây trước khi retry
                        
            except Exception as api_error:
                print(f"⚠️ Lần thử {attempt + 1}: Lỗi API - {str(api_error)}")
                if attempt < max_retries - 1:  # Không sleep ở lần thử cuối
                    print("⏳ Đợi 2 giây trước khi thử lại...")
                    time.sleep(2)  # Đợi 2 giây trước khi retry
        
        # Nếu tất cả attempts đều thất bại
        print(f"❌ Không nhận được kết quả từ Vertex AI sau {max_retries} lần thử")
        return None
            
    except Exception as e:
        print(f"❌ Lỗi khi thực hiện OCR: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_ocr_result_to_markdown(result_text, image_path, output_folder):
    """Lưu kết quả OCR thành file markdown với format đẹp"""
    try:
        # Tạo tên file với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ocr_result_{timestamp}.md"
        output_file = os.path.join(output_folder, filename)
        
        # Ghi nội dung vào file markdown
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_text)
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu file markdown: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # Hiển thị thông tin cấu hình
    app_config.get_config_summary()
    print()
    
    # Lấy tất cả file ảnh trong thư mục input
    image_paths = get_image_files_from_folder(app_config.input_folder)
    
    if not image_paths:
        print(f"📁 Vui lòng thêm ảnh vào: {app_config.input_folder}")
        return
    
    # Tự động chọn mode dựa trên số lượng ảnh
    num_images = len(image_paths)
    print(f"📷 Tìm thấy {num_images} ảnh trong thư mục input:")
    for i, path in enumerate(image_paths):
        print(f"   {i+1}. {os.path.basename(path)}")
    
    if num_images == 1:
        # Mode 1: Xử lý 1 ảnh đơn lẻ
        single_image_mode(image_paths[0])
        
    else:
        # Xử lý với số process = số CPU hoặc số ảnh (tùy cái nào nhỏ hơn)
        max_workers = min(num_images, mp.cpu_count())
        print(f"🚀 Sử dụng {max_workers} processes")
        
        multiple_images_mode(image_paths, max_workers)

if __name__ == "__main__":
    main()
