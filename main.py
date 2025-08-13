import os
import time
import traceback
import multiprocessing as mp
from config import app_config
from datetime import datetime
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from concurrent.futures import ProcessPoolExecutor, as_completed
from processors import QuestionAnswerMapper
from processors.image_processor import save_diagrams_from_line_data, insert_diagrams_into_text
from processors.md2json import process_markdown_with_vertex_ai
from data.prompt.prompts import VERTEX_AI_OCR

try:
    from pdf2image import convert_from_path
    import tempfile
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️ PDF support cho Mode 1 không khả dụng. Cài đặt: pip install pdf2image")
    print("⚠️ Và cài đặt poppler-utils (Windows: choco install poppler)")

try:
    import aspose.words as aw
    import shutil
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("⚠️ DOCX support không khả dụng. Cài đặt: pip install aspose-words")

def convert_md_to_json_final(md_file_path: str) -> str:
    """
    Wrapper function để chuyển đổi MD thành JSON sử dụng logic từ md2json.py
    
    Args:
        md_file_path: Đường dẫn file .md cần chuyển đổi
        
    Returns:
        Đường dẫn file JSON đã tạo hoặc None nếu lỗi
    """
    try:
        print(f"🔄 Đang chuyển đổi MD sang JSON: {os.path.basename(md_file_path)}")
        result = process_markdown_with_vertex_ai(md_file_path)
        
        if result[1]:  # result[1] là đường dẫn JSON output
            print(f"✅ Đã tạo JSON: {os.path.basename(result[1])}")
            return result[1]
        else:
            print(f"❌ Lỗi khi chuyển đổi {os.path.basename(md_file_path)} sang JSON")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi không xác định khi chuyển đổi MD sang JSON: {str(e)}")
        return None

def convert_pdf_to_images(pdf_path, dpi=200):
    """
    Convert PDF thành list các ảnh để xử lý bằng Vertex AI
    Args:
        pdf_path: đường dẫn file PDF
        dpi: độ phân giải (200 DPI = balance quality vs speed)
    Returns:
        list các đường dẫn ảnh tạm hoặc None nếu lỗi
    """
    if not PDF_SUPPORT:
        print("❌ PDF support không khả dụng!")
        return None
    
    try:
        print(f"🔄 Đang convert PDF thành ảnh: {os.path.basename(pdf_path)}")
        
        # Convert PDF to images với optimization
        images = convert_from_path(
            pdf_path, 
            dpi=dpi,
            fmt='JPEG',  # Format ảnh output
            thread_count=mp.cpu_count(),  # Sử dụng multiple threads
            use_pdftocairo=True  # Faster rendering
        )
        
        print(f"✅ Đã convert thành {len(images)} ảnh")
        
        # Lưu ảnh tạm
        temp_image_paths = []
        temp_dir = tempfile.mkdtemp(prefix="qprocess_pdf_")
        
        for i, image in enumerate(images):
            temp_path = os.path.join(temp_dir, f"page_{i+1:03d}.png")
            image.save(temp_path, 'PNG', optimize=True)
            temp_image_paths.append(temp_path)
            print(f"💾 Trang {i+1}: {os.path.basename(temp_path)}")
        
        return temp_image_paths
        
    except Exception as e:
        print(f"❌ Lỗi convert PDF: {str(e)}")
        return None

def cleanup_temp_images(image_paths):
    """
    Dọn dẹp các file ảnh tạm
    Args:
        image_paths: list đường dẫn ảnh tạm
    """
    if not image_paths:
        return
    
    try:
        # Xóa file
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
        
        # Xóa thư mục tạm
        temp_dir = os.path.dirname(image_paths[0])
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
            
        print(f"🧹 Đã dọn dẹp {len(image_paths)} file ảnh tạm")
        
    except Exception as e:
        print(f"⚠️ Lỗi dọn dẹp temp files: {str(e)}")

def convert_docx_to_pdf(docx_path):
    """
    Convert file DOCX thành PDF sử dụng aspose-words
    Args:
        docx_path: đường dẫn file DOCX
    Returns:
        str: đường dẫn file PDF tạm hoặc None nếu lỗi
    """
    if not DOCX_SUPPORT:
        print("❌ DOCX support không khả dụng!")
        return None
    
    try:
        print(f"🔄 Đang convert DOCX thành PDF: {os.path.basename(docx_path)}")
        
        # Tạo tên file PDF tạm với timestamp
        temp_pdf_name = f"temp_docx_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        temp_pdf_path = os.path.join(os.path.dirname(docx_path), temp_pdf_name)
        
        # Load DOCX document và save as PDF
        doc = aw.Document(docx_path)
        doc.save(temp_pdf_path)
        
        if os.path.exists(temp_pdf_path):
            print(f"✅ Đã convert thành PDF: {os.path.basename(temp_pdf_path)}")
            return temp_pdf_path
        else:
            print("❌ Không thể tạo file PDF")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi convert DOCX to PDF: {e}")
        return None

def cleanup_temp_pdf(pdf_path):
    """
    Dọn dẹp file PDF tạm
    Args:
        pdf_path: đường dẫn file PDF tạm
    """
    if not pdf_path:
        return
    
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"🗑️ Đã xóa file PDF tạm: {os.path.basename(pdf_path)}")
    except Exception as e:
        print(f"❌ Lỗi dọn dẹp temp PDF: {e}")

def ocr_single_pdf_vertex_ai(pdf_path, index=None, show_result=False):
    """
    Xử lý OCR một PDF đơn lẻ bằng Vertex AI - Mode 1
    Args:
        pdf_path: đường dẫn PDF
        index: index của PDF (cho multiprocessing), None cho single mode
        show_result: có hiển thị kết quả chi tiết không (cho single mode)
    Returns:
        tuple (result_text, success, error_msg) cho single mode
        tuple (index, result_text, pdf_path, success, error_msg) cho multiprocessing
    """
    try:
        # Xác định prefix cho log messages
        prefix = f"[Process {index}]" if index is not None else ""
        
        if index is not None:
            print(f"🔄 {prefix} Bắt đầu xử lý PDF (Vertex AI): {os.path.basename(pdf_path)}")
        else:
            print("=== TEST OCR PDF VỚI VERTEX AI ===")
            print(f"📄 Đang xử lý PDF: {os.path.basename(pdf_path)}")
        
        # Kiểm tra PDF support
        if not PDF_SUPPORT:
            error_msg = "PDF support không khả dụng (thiếu pdf2image)"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        # Kiểm tra file
        if not os.path.exists(pdf_path):
            error_msg = f"File không tồn tại: {pdf_path}"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        # Convert PDF thành ảnh
        temp_image_paths = convert_pdf_to_images(pdf_path, dpi=150)  # Lower DPI for speed
        
        if not temp_image_paths:
            error_msg = "Không thể convert PDF thành ảnh"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        # Xử lý từng trang bằng Vertex AI với multiprocessing
        if index is None:
            print(f"🔄 Xử lý {len(temp_image_paths)} trang bằng Vertex AI (multiprocessing)...")
        
        # Sử dụng multiprocessing để xử lý các trang song song
        if len(temp_image_paths) > 1:
            # Tạo list (page_index, image_path) 
            page_info_list = [(i, path) for i, path in enumerate(temp_image_paths)]
            
            # Xử lý song song với số workers = min(số trang, số CPU)
            max_workers = min(len(temp_image_paths), mp.cpu_count())
            page_results = []
            
            try:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    # Submit jobs
                    future_to_page = {
                        executor.submit(ocr_single_image, image_path, page_idx, False): (page_idx, image_path)
                        for page_idx, image_path in page_info_list
                    }
                    
                    # Collect results
                    for future in as_completed(future_to_page):
                        try:
                            result = future.result()
                            page_results.append(result)
                        except Exception as e:
                            page_idx, image_path = future_to_page[future]
                            print(f"⚠️ Lỗi xử lý trang {page_idx + 1}: {str(e)}")
                            page_results.append((page_idx, None, image_path, False, str(e)))
                
                # Sắp xếp kết quả theo thứ tự trang
                page_results.sort(key=lambda x: x[0])
                
            except Exception as e:
                print(f"⚠️ Lỗi multiprocessing, chuyển sang xử lý tuần tự: {str(e)}")
                # Fallback to sequential processing
                page_results = []
                for i, image_path in enumerate(temp_image_paths):
                    result = ocr_single_image(image_path, index=None, show_result=False)
                    if result:
                        page_results.append((i, result[0], image_path, result[1], result[2]))
                    else:
                        page_results.append((i, None, image_path, False, "Unknown error"))
        else:
            # Chỉ có 1 trang, xử lý trực tiếp
            result = ocr_single_image(temp_image_paths[0], index=None, show_result=False)
            if result:
                page_results = [(0, result[0], temp_image_paths[0], result[1], result[2])]
            else:
                page_results = [(0, None, temp_image_paths[0], False, "Unknown error")]
        
        # Tổng hợp kết quả
        all_results = []
        successful_pages = 0
        
        for page_idx, result_text, image_path, success, error_msg in page_results:
            page_num = page_idx + 1
            
            if success and result_text:
                all_results.append(f"## Trang {page_num}\n\n{result_text}")
                successful_pages += 1
            else:
                if index is None:
                    print(f"⚠️ Lỗi trang {page_num}: {error_msg}")
                all_results.append(f"## Trang {page_num}\n\n❌ Lỗi xử lý: {error_msg}")
        
        # Dọn dẹp temp files
        cleanup_temp_images(temp_image_paths)
        
        # Tổng hợp kết quả
        if successful_pages > 0:
            combined_text = "\n\n".join(all_results)
            
            if index is not None:
                print(f"✅ {prefix} Hoàn thành: {successful_pages}/{len(temp_image_paths)} trang")
                return (index, combined_text, pdf_path, True, None)
            else:
                print(f"✅ Hoàn thành PDF: {successful_pages}/{len(temp_image_paths)} trang thành công")
                if show_result:
                    print("\n" + "="*60)
                    print("📄 KẾT QUẢ OCR PDF (VERTEX AI):")
                    print("="*60)
                    print(combined_text[:1000] + "..." if len(combined_text) > 1000 else combined_text)
                    print("="*60)
                return (combined_text, True, None)
        else:
            error_msg = f"Không có trang nào xử lý thành công (0/{len(temp_image_paths)})"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
                
    except Exception as e:
        error_msg = f"Lỗi khi xử lý PDF với Vertex AI {pdf_path}: {str(e)}"
        if index is not None:
            print(f"❌ {prefix} {error_msg}")
            return (index, None, pdf_path, False, error_msg)
        else:
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return (None, False, error_msg)

def ocr_single_image(image_path, index=None, show_result=False):
    """
    Xử lý OCR một ảnh đơn lẻ - function chung cho cả single mode và multiprocessing
    Args:
        image_path: đường dẫn ảnh
        index: index của ảnh (cho multiprocessing), None cho single mode
        show_result: có hiển thị kết quả chi tiết không (cho single mode)
    Returns:
        tuple (result_text, success, error_msg) cho single mode
        tuple (index, result_text, image_path, success, error_msg) cho multiprocessing
    """
    try:
        # Xác định prefix cho log messages
        prefix = f"[Process {index}]" if index is not None else ""
        
        if index is not None:
            print(f"🔄 {prefix} Bắt đầu xử lý: {os.path.basename(image_path)}")
        else:
            print("=== TEST OCR IMAGE VỚI VERTEX AI ===")
            print(f"📷 Đang xử lý ảnh: {os.path.basename(image_path)}")
            
        if not app_config.vertex_ai.initialize_vertex_ai():
            error_msg = "Không thể khởi tạo Vertex AI!"
            if index is not None:
                return (index, None, image_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        # Tạo model
        model = GenerativeModel(app_config.vertex_ai.model_name)
        if index is None:
            print(f"✅ Đã khởi tạo model: {app_config.vertex_ai.model_name}")
        
        # Đọc ảnh và tạo Part object
        if index is None:
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
        if index is None:
            print(f"✅ Đã tạo image part với mime type: {mime_type}")
        
        text_part = Part.from_text(VERTEX_AI_OCR)
        
        # Tạo generation config
        generation_config = GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            max_output_tokens=15000
        )
        
        # Gọi API với retry logic
        if index is None:
            print("🔄 Đang gửi request đến Vertex AI...")
            
        prompt_parts = [text_part, image_part]
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if index is not None:
                    print(f"🔄 {prefix} Thử lần {attempt + 1}/{max_retries}...")
                else:
                    print(f"🔄 Thử lần {attempt + 1}/{max_retries}...")
                
                response = model.generate_content(
                    prompt_parts, 
                    generation_config=generation_config, 
                    stream=False
                )
                
                if response and response.text:
                    # Thành công
                    if index is not None:
                        print(f"✅ {prefix} Hoàn thành: {os.path.basename(image_path)}")
                        return (index, response.text, image_path, True, None)
                    else:
                        print("✅ Đã nhận được kết quả OCR!")
                        if show_result:
                            print("\n" + "="*60)
                            print("📄 KẾT QUẢ OCR:")
                            print("="*60)
                            print(response.text)
                            print("="*60)
                        return (response.text, True, None)
                else:
                    # Không có kết quả
                    retry_msg = f"Lần thử {attempt + 1}: Không nhận được kết quả từ Vertex AI"
                    if index is not None:
                        print(f"⚠️ {prefix} {retry_msg}")
                    else:
                        print(f"⚠️ {retry_msg}")
                        
                    if attempt < max_retries - 1:  # Không sleep ở lần thử cuối
                        if index is None:
                            print("⏳ Đợi 2 giây trước khi thử lại...")
                        time.sleep(2)
                        
            except Exception as api_error:
                # Lỗi API
                error_msg = f"Lần thử {attempt + 1}: Lỗi API - {str(api_error)}"
                if index is not None:
                    print(f"⚠️ {prefix} {error_msg}")
                else:
                    print(f"⚠️ {error_msg}")
                    
                if attempt < max_retries - 1:  # Không sleep ở lần thử cuối
                    if index is None:
                        print("⏳ Đợi 2 giây trước khi thử lại...")
                    time.sleep(2)
        
        # Nếu tất cả attempts đều thất bại
        final_error = f"Không nhận được kết quả từ Vertex AI sau {max_retries} lần thử"
        if index is not None:
            return (index, None, image_path, False, final_error)
        else:
            print(f"❌ {final_error}")
            return (None, False, final_error)
            
    except Exception as e:
        error_msg = f"Lỗi khi xử lý ảnh {image_path}: {str(e)}"
        if index is not None:
            print(f"❌ {prefix} {error_msg}")
            return (index, None, image_path, False, error_msg)
        else:
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return (None, False, error_msg)

def ocr_single_image_mathpix(image_path, index=None, show_result=False):
    """
    Xử lý OCR một ảnh đơn lẻ bằng Mathpix API - Mode 2
    Args:
        image_path: đường dẫn ảnh
        index: index của ảnh (cho multiprocessing), None cho single mode
        show_result: có hiển thị kết quả chi tiết không (cho single mode)
    Returns:
        tuple (result_text, success, error_msg) cho single mode
        tuple (index, result_text, image_path, success, error_msg) cho multiprocessing
    """
    try:
        # Xác định prefix cho log messages
        prefix = f"[Process {index}]" if index is not None else ""
        
        if index is not None:
            print(f"🔄 {prefix} Bắt đầu xử lý (Mathpix): {os.path.basename(image_path)}")
        else:
            print(f"📷 Đang xử lý ảnh: {os.path.basename(image_path)}")
        
        # Kiểm tra cấu hình Mathpix
        if not app_config.mathpix.is_configured():
            error_msg = "Mathpix API chưa được cấu hình!"
            if index is not None:
                return (index, None, image_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                print("💡 Hãy thiết lập MATHPIX_APP_ID và MATHPIX_APP_KEY trong .env")
                return (None, False, error_msg)
        
        if index is None:
            print("✅ Mathpix API đã được cấu hình")
        
        # Kiểm tra file có tồn tại và được hỗ trợ
        if not os.path.exists(image_path):
            error_msg = f"File không tồn tại: {image_path}"
            if index is not None:
                return (index, None, image_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        if not app_config.mathpix.is_supported_image(image_path):
            error_msg = f"Format file không được hỗ trợ: {image_path}"
            if index is not None:
                return (index, None, image_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                supported = ', '.join(app_config.mathpix.get_supported_formats())
                print(f"💡 Các format được hỗ trợ: {supported}")
                return (None, False, error_msg)
        
        # Tùy chọn OCR
        mathpix_options = {
            "formats": ["mmd"],
            "math_inline_delimiters": ["$", "$"],
            "math_display_delimiters": ["$$", "$$"],
            "include_annotated_image": True,
            "include_image_links": True,
            "include_line_data": True,
            "include_diagram": True,
            "include_diagram_text": True,
            "rm_spaces": True,
            "rm_fonts": False,
            "numbers_default_to_math": True
        }
        
        if index is None:
            print("🔄 Đang gửi request đến Mathpix API...")
        
        # Gọi Mathpix API
        result = app_config.mathpix.ocr_image(image_path, mathpix_options)
        
        diagram_files = save_diagrams_from_line_data(image_path, result, base_outdir="data\diagrams")

        if diagram_files:
            print(f"🖼️ Đã lưu {len(diagram_files)} hình diagram vào:", os.path.dirname(diagram_files[0]["path"]))
            # In kèm id & bbox để debug
            for d in diagram_files:
                print(f"   - {os.path.basename(d['path'])}  id={d['id']}  bbox={d['bbox']}")

        if result and result.get('text'):
            # Post-process kết quả để phù hợp với format đề thi
            processed_text = post_process_mathpix_result(result)

            augmented_text = insert_diagrams_into_text(
                raw_text=processed_text,
                result=result,
                diagram_files=diagram_files,
                min_gap_px=8
            )
            
            if index is not None:
                print(f"✅ {prefix} Hoàn thành: {os.path.basename(image_path)}")
                return (index, augmented_text, image_path, True, None)
            else:
                print("✅ Đã nhận được kết quả OCR từ Mathpix!")
                if show_result:
                    print("\n" + "="*60)
                    print("📄 KẾT QUẢ OCR (MATHPIX):")
                    print("="*60)
                    print(augmented_text)
                    print("="*60)
                    print(f"🎯 Confidence: {result.get('confidence', 'N/A')}")
                    print(f"📏 Image size: {result.get('image_width', 'N/A')}x{result.get('image_height', 'N/A')}")
            
                    return (augmented_text, True, None)
                
        else:
            error_msg = "Không nhận được kết quả từ Mathpix API"
            if index is not None:
                return (index, None, image_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
                
    except Exception as e:
        error_msg = f"Lỗi khi xử lý ảnh với Mathpix {image_path}: {str(e)}"
        if index is not None:
            print(f"❌ {prefix} {error_msg}")
            return (index, None, image_path, False, error_msg)
        else:
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return (None, False, error_msg)

def post_process_mathpix_result(mathpix_result):
    """
    Post-process kết quả từ Mathpix để phù hợp với format đề thi
    Args:
        mathpix_result: dict kết quả từ Mathpix API
    Returns:
        str: text đã được xử lý
    """
    text = mathpix_result.get('text', '')
    
    if not text:
        return ''
    
    # Xử lý format đề thi
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            processed_lines.append('')
            continue
        
        # Xử lý các phần của đề thi
        line_lower = line.lower()
        
        # Phần I, II, III
        if any(keyword in line_lower for keyword in ['phần i', 'phần ii', 'phần iii', 'part i', 'part ii', 'part iii']):
            if not line.startswith('**'):
                line = f"**{line}**"
        
        # Câu hỏi (Câu 1, Câu 2, etc.)
        elif line.startswith('Câu ') or line.startswith('Question '):
            if ':' in line and not line.startswith('**'):
                parts = line.split(':', 1)
                line = f"**{parts[0]}:** {parts[1].strip()}" if len(parts) == 2 else f"**{line}**"
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def ocr_single_pdf_mathpix(pdf_path, index=None, show_result=False):
    """
    Xử lý OCR một PDF đơn lẻ bằng Mathpix API - Mode 2 
    Args:
        pdf_path: đường dẫn PDF
        index: index của PDF (cho multiprocessing), None cho single mode
        show_result: có hiển thị kết quả chi tiết không (cho single mode)
    Returns:
        tuple (result_text, success, error_msg) cho single mode
        tuple (index, result_text, pdf_path, success, error_msg) cho multiprocessing
    """
    try:
        # Xác định prefix cho log messages
        prefix = f"[Process {index}]" if index is not None else ""
        
        if index is not None:
            print(f"🔄 {prefix} Bắt đầu xử lý PDF (Mathpix): {os.path.basename(pdf_path)}")
        else:
            print("=== TEST OCR PDF VỚI MATHPIX API ===")
            print(f"📄 Đang xử lý PDF: {os.path.basename(pdf_path)}")
        
        # Kiểm tra cấu hình Mathpix
        if not app_config.mathpix.is_configured():
            error_msg = "Mathpix API chưa được cấu hình!"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                print("💡 Hãy thiết lập MATHPIX_APP_ID và MATHPIX_APP_KEY trong .env")
                return (None, False, error_msg)
        
        if index is None:
            print("✅ Mathpix API đã được cấu hình")
        
        # Kiểm tra file có tồn tại và là PDF
        if not os.path.exists(pdf_path):
            error_msg = f"File không tồn tại: {pdf_path}"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        if not app_config.mathpix.is_supported_pdf(pdf_path):
            error_msg = f"File không phải PDF: {pdf_path}"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        if index is None:
            print("🔄 Đang xử lý PDF với Mathpix API...")
        
        # Gọi Mathpix PDF API
        result_text = app_config.mathpix.process_pdf(pdf_path, timeout=120)
        
        if result_text and not result_text.startswith("PK"):  # Không phải binary
            # Post-process kết quả để phù hợp với format đề thi
            processed_text = post_process_mathpix_result({'text': result_text})
            
            if index is not None:
                print(f"✅ {prefix} Hoàn thành: {os.path.basename(pdf_path)}")
                return (index, processed_text, pdf_path, True, None)
            else:
                print("✅ Đã nhận được kết quả OCR từ Mathpix PDF!")
                if show_result:
                    print("\n" + "="*60)
                    print("📄 KẾT QUẢ OCR PDF (MATHPIX):")
                    print("="*60)
                    print(processed_text[:1000] + "..." if len(processed_text) > 1000 else processed_text)
                    print("="*60)
                return (processed_text, True, None)
        else:
            error_msg = "Không nhận được kết quả text từ Mathpix PDF API"
            if index is not None:
                return (index, None, pdf_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
                
    except Exception as e:
        error_msg = f"Lỗi khi xử lý PDF với Mathpix {pdf_path}: {str(e)}"
        if index is not None:
            print(f"❌ {prefix} {error_msg}")
            return (index, None, pdf_path, False, error_msg)
        else:
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return (None, False, error_msg)

def process_single_image_mathpix(image_info):
    """
    Wrapper cho multiprocessing - gọi ocr_single_image_mathpix
    Args:
        image_info: tuple (index, image_path)
    Returns:
        tuple (index, result_text, image_path, success, error_msg)
    """
    index, image_path = image_info
    return ocr_single_image_mathpix(image_path, index=index, show_result=False)

def process_single_file_mathpix(file_info):
    """
    Wrapper cho multiprocessing - gọi ocr_single_image_mathpix, ocr_single_pdf_mathpix hoặc process_single_docx_mathpix
    Args:
        file_info: tuple (index, file_path)
    Returns:
        tuple (index, result_text, file_path, success, error_msg)
    """
    index, file_path = file_info
    
    # Kiểm tra file type
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return ocr_single_pdf_mathpix(file_path, index=index, show_result=False)
    elif ext == '.docx':
        return process_single_docx_mathpix(file_path, index=index, show_result=False)
    else:
        return ocr_single_image_mathpix(file_path, index=index, show_result=False)

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
                executor.submit(ocr_single_image, image_path, index): (index, image_path) 
                for index, image_path in image_info_list
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

def process_multiple_files_mathpix(file_paths, max_workers=None):
    """
    Xử lý nhiều file (ảnh/PDF) đồng thời bằng multiprocessing với Mathpix API - Mode 2
    Args:
        file_paths: list đường dẫn các file
        max_workers: số process tối đa (mặc định = số CPU)
    Returns:
        list kết quả theo thứ tự input
    """
    if not file_paths:
        print("❌ Không có file nào để xử lý!")
        return []
    
    # Phân loại file
    image_count = sum(1 for f in file_paths if os.path.splitext(f)[1].lower() != '.pdf')
    pdf_count = sum(1 for f in file_paths if os.path.splitext(f)[1].lower() == '.pdf')
    
    # Xác định số workers
    if max_workers is None:
        max_workers = min(len(file_paths), mp.cpu_count())
    
    print(f"🚀 Bắt đầu xử lý {len(file_paths)} file với Mathpix API ({max_workers} processes)")
    print(f"   📷 Ảnh: {image_count}")
    print(f"   📄 PDF: {pdf_count}")
    
    # Tạo list (index, file_path) để giữ thứ tự
    file_info_list = [(i, path) for i, path in enumerate(file_paths)]
    
    # Khởi tạo list kết quả với None
    results = [None] * len(file_paths)
    
    start_time = time.time()
    
    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit tất cả tasks
            future_to_info = {
                executor.submit(process_single_file_mathpix, info): info 
                for info in file_info_list
            }
            
            # Collect results khi hoàn thành
            completed_count = 0
            for future in as_completed(future_to_info):
                try:
                    index, result_text, file_path, success, error_msg = future.result()
                    
                    # Lưu kết quả theo đúng thứ tự
                    results[index] = {
                        'index': index,
                        'image_path': file_path,  # Keep key name for compatibility
                        'result_text': result_text,
                        'success': success,
                        'error_msg': error_msg
                    }
                    
                    completed_count += 1
                    file_type = "PDF" if file_path.endswith('.pdf') else "Image"
                    print(f"📊 Tiến độ: {completed_count}/{len(file_paths)} file hoàn thành ({file_type})")
                    
                except Exception as e:
                    # Lấy thông tin từ future_to_info nếu có lỗi
                    info = future_to_info[future]
                    index, file_path = info
                    results[index] = {
                        'index': index,
                        'image_path': file_path,
                        'result_text': None,
                        'success': False,
                        'error_msg': f"Lỗi future: {str(e)}"
                    }
                    completed_count += 1
                    print(f"❌ Lỗi xử lý file {file_path}: {str(e)}")
    
    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng trong multiprocessing: {str(e)}")
        return []
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Thống kê kết quả
    successful_count = sum(1 for r in results if r and r['success'])
    failed_count = len(results) - successful_count
    
    print(f"\n📊 KẾT QUẢ TỔNG KẾT (MATHPIX):")
    print(f"⏱️  Thời gian xử lý: {total_time:.2f} giây")
    print(f"✅ Thành công: {successful_count}/{len(file_paths)} file")
    print(f"❌ Thất bại: {failed_count}/{len(file_paths)} file")
    print(f"🔄 Tốc độ trung bình: {total_time/len(file_paths):.2f} giây/file")
    
    return results

def save_multiple_results_to_markdown(results, output_folder):
    """
    Lưu tất cả kết quả OCR thành một file markdown tổng hợp với template lời giải
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ocr_multiple_results_{timestamp}.md"
        output_file = os.path.join(output_folder, filename)
        
        successful_results = [r for r in results if r and r['success']]
        failed_results = [r for r in results if r and not r['success']]
        
        with open(output_file, "w", encoding="utf-8") as f:
            
            # Kết quả thành công - xử lý và thêm template
            if successful_results:
                # Gộp tất cả nội dung OCR
                combined_content = ""
                for result in successful_results:
                    combined_content += result['result_text']
                
                # Ghi trực tiếp nội dung đã OCR
                f.write(combined_content)
            
            # Kết quả thất bại
            if failed_results:
                f.write("\n\n## ❌ Kết quả thất bại\n\n")
                for result in failed_results:
                    f.write(f"### 📷 Ảnh {result['index'] + 1}: `{os.path.basename(result['image_path'])}`\n\n")
                    f.write(f"**Lỗi:** {result['error_msg']}\n\n")
            
        print(f"✅ Đã lưu file MD: {os.path.basename(output_file)}")
        
        # Chuyển đổi MD sang JSON
        try:
            json_file = convert_md_to_json_final(output_file)
            if json_file:
                print(f"✅ Hoàn thành pipeline: MD → JSON")
            else:
                print(f"⚠️ Không thể chuyển đổi sang JSON")
        except Exception as json_error:
            print(f"⚠️ Lỗi khi chuyển đổi sang JSON: {str(json_error)}")
        
        print(f"✅ Đã xử lý và lưu kết quả OCR")
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu file markdown tổng hợp: {e}")
        traceback.print_exc()
        return None

def save_multiple_results_to_markdown_mathpix(results, output_folder):
    """
    Lưu tất cả kết quả OCR Mathpix thành một file markdown tổng hợp với template lời giải
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mathpix_multiple_results_{timestamp}.md"
        output_file = os.path.join(output_folder, filename)
        
        successful_results = [r for r in results if r and r['success']]
        failed_results = [r for r in results if r and not r['success']]
        
        with open(output_file, "w", encoding="utf-8") as f:
            
            # Kết quả thành công - xử lý và thêm template
            if successful_results:
                # Gộp tất cả nội dung OCR
                combined_content = ""
                for result in successful_results:
                    combined_content += result['result_text'] + "\n\n"
                
                # Ghi trực tiếp nội dung đã OCR
                f.write(combined_content)
            
            # Kết quả thất bại
            if failed_results:
                f.write("\n\n## ❌ Kết quả thất bại\n\n")
                for result in failed_results:
                    f.write(f"### 📷 Ảnh {result['index'] + 1}: `{os.path.basename(result['image_path'])}`\n\n")
                    f.write(f"**Lỗi:** {result['error_msg']}\n\n")
            
        print(f"✅ Đã lưu file MD: {os.path.basename(output_file)}")
        
        # Chuyển đổi MD sang JSON
        try:
            json_file = convert_md_to_json_final(output_file)
            if json_file:
                print(f"✅ Hoàn thành pipeline: MD → JSON")
            else:
                print(f"⚠️ Không thể chuyển đổi sang JSON")
        except Exception as json_error:
            print(f"⚠️ Lỗi khi chuyển đổi sang JSON: {str(json_error)}")
        
        print(f"✅ Đã xử lý và lưu kết quả OCR (Mathpix)")
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu file markdown tổng hợp Mathpix: {e}")
        traceback.print_exc()
        return None

def save_single_result_to_markdown_mathpix(result_text, image_path, output_folder):
    """
    Lưu kết quả OCR Mathpix đơn lẻ thành file markdown và chuyển đổi sang JSON
    Args:
        result_text: nội dung OCR
        image_path: đường dẫn ảnh gốc
        output_folder: thư mục output
    Returns:
        đường dẫn file đã lưu hoặc None nếu lỗi
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mathpix_result_{timestamp}.md"
        output_file = os.path.join(output_folder, filename)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_text)
        
        print(f"✅ Đã lưu file MD: {os.path.basename(output_file)}")
        
        # Chuyển đổi MD sang JSON
        try:
            json_file = convert_md_to_json_final(output_file)
            if json_file:
                print(f"✅ Hoàn thành pipeline: MD → JSON")
            else:
                print(f"⚠️ Không thể chuyển đổi sang JSON")
        except Exception as json_error:
            print(f"⚠️ Lỗi khi chuyển đổi sang JSON: {str(json_error)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu file markdown đơn lẻ Mathpix: {e}")
        traceback.print_exc()
        return None

def get_supported_files_from_folder(folder_path):
    """Lấy danh sách tất cả file ảnh, PDF và DOCX trong thư mục"""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}
    pdf_extensions = {'.pdf'}
    docx_extensions = {'.docx'}
    supported_extensions = image_extensions | pdf_extensions | docx_extensions
    
    supported_files = []
    
    if not os.path.exists(folder_path):
        print(f"❌ Thư mục không tồn tại: {folder_path}")
        return []
    
    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_extensions:
            supported_files.append(os.path.join(folder_path, filename))
    
    supported_files.sort()  # Sắp xếp theo tên file
    return supported_files

def process_single_docx_vertex_ai(docx_path, index=None, show_result=False):
    """
    Xử lý DOCX với Vertex AI: DOCX → PDF → OCR → Mapping
    Args:
        docx_path: đường dẫn file DOCX
        index: index của file (cho multiprocessing), None cho single mode
        show_result: có hiển thị kết quả chi tiết không (cho single mode)
    Returns:
        tuple (result_text, success, error_msg) cho single mode
        tuple (index, result_text, docx_path, success, error_msg) cho multiprocessing
    """
    try:
        prefix = f"[Process {index}]" if index is not None else ""
        
        if index is not None:
            print(f"🔄 {prefix} Bắt đầu xử lý DOCX (Vertex AI): {os.path.basename(docx_path)}")
        else:
            print(f"📄 Đang xử lý DOCX với Vertex AI: {os.path.basename(docx_path)}")
        
        # Convert DOCX to PDF
        temp_pdf_path = convert_docx_to_pdf(docx_path)
        
        if not temp_pdf_path:
            error_msg = "Không thể convert DOCX to PDF"
            if index is not None:
                return (index, None, docx_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        # Sử dụng OCR PDF với Vertex AI
        result = ocr_single_pdf_vertex_ai(temp_pdf_path, index=None, show_result=False)
        
        # Dọn dẹp file PDF tạm
        cleanup_temp_pdf(temp_pdf_path)
        
        if result and result[1]:  # success
            if index is not None:
                print(f"✅ {prefix} Hoàn thành DOCX: {os.path.basename(docx_path)}")
                return (index, result[0], docx_path, True, None)
            else:
                print("✅ Đã xử lý DOCX thành công!")
                if show_result:
                    print("\n" + "="*60)
                    print("📄 KẾT QUẢ XỬ LÝ DOCX (VERTEX AI):")
                    print("="*60)
                    print(result[0][:1000] + "..." if len(result[0]) > 1000 else result[0])
                    print("="*60)
                return (result[0], True, None)
        else:
            error_msg = result[2] if result and len(result) > 2 else "Lỗi OCR PDF"
            if index is not None:
                return (index, None, docx_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
                
    except Exception as e:
        error_msg = f"Lỗi khi xử lý DOCX với Vertex AI {docx_path}: {str(e)}"
        if index is not None:
            print(f"❌ {prefix} {error_msg}")
            return (index, None, docx_path, False, error_msg)
        else:
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return (None, False, error_msg)

def process_single_docx_mathpix(docx_path, index=None, show_result=False):
    """
    Xử lý DOCX với Mathpix: DOCX → PDF → OCR → Mapping
    Args:
        docx_path: đường dẫn file DOCX
        index: index của file (cho multiprocessing), None cho single mode
        show_result: có hiển thị kết quả chi tiết không (cho single mode)
    Returns:
        tuple (result_text, success, error_msg) cho single mode
        tuple (index, result_text, docx_path, success, error_msg) cho multiprocessing
    """
    try:
        prefix = f"[Process {index}]" if index is not None else ""
        
        if index is not None:
            print(f"🔄 {prefix} Bắt đầu xử lý DOCX (Mathpix): {os.path.basename(docx_path)}")
        else:
            print(f"📄 Đang xử lý DOCX với Mathpix: {os.path.basename(docx_path)}")
        
        # Convert DOCX to PDF
        temp_pdf_path = convert_docx_to_pdf(docx_path)
        
        if not temp_pdf_path:
            error_msg = "Không thể convert DOCX to PDF"
            if index is not None:
                return (index, None, docx_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
        
        # Sử dụng OCR PDF với Mathpix
        result = ocr_single_pdf_mathpix(temp_pdf_path, index=None, show_result=False)
        
        # Dọn dẹp file PDF tạm
        cleanup_temp_pdf(temp_pdf_path)
        
        if result and result[1]:  # success
            if index is not None:
                print(f"✅ {prefix} Hoàn thành DOCX: {os.path.basename(docx_path)}")
                return (index, result[0], docx_path, True, None)
            else:
                print("✅ Đã xử lý DOCX thành công!")
                if show_result:
                    print("\n" + "="*60)
                    print("📄 KẾT QUẢ XỬ LÝ DOCX (MATHPIX):")
                    print("="*60)
                    print(result[0][:1000] + "..." if len(result[0]) > 1000 else result[0])
                    print("="*60)
                return (result[0], True, None)
        else:
            error_msg = "Không thể OCR bất kỳ ảnh nào từ DOCX"
            if index is not None:
                return (index, None, docx_path, False, error_msg)
            else:
                print(f"❌ {error_msg}")
                return (None, False, error_msg)
                
    except Exception as e:
        error_msg = f"Lỗi khi xử lý DOCX với Mathpix {docx_path}: {str(e)}"
        if index is not None:
            print(f"❌ {prefix} {error_msg}")
            return (index, None, docx_path, False, error_msg)
        else:
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return (None, False, error_msg)

def get_image_files_from_folder(folder_path):
    """Lấy danh sách tất cả file ảnh trong thư mục - giữ để backward compatibility"""
    return [f for f in get_supported_files_from_folder(folder_path) 
            if os.path.splitext(f)[1].lower() != '.pdf']

def single_image_mode(image_path):
    print(f"\n🔄 CHẾ ĐỘ: Xử lý ảnh đơn lẻ")
    print(f"📷 Ảnh: {os.path.basename(image_path)}")
    
    result = ocr_single_image(image_path, index=None, show_result=True)

    if result:
        # Áp dụng mapping nếu user muốn
        final_content = post_process_with_mapping(result, os.path.basename(image_path), "Vertex AI")
        
        output_file = save_ocr_result_to_markdown(final_content, image_path, app_config.output_folder)
        
        if output_file:
            print(f"💾 Đã lưu kết quả vào: {os.path.basename(output_file)}")
    else:
        print("\n❌ THẤT BẠI!")

def single_file_mode_vertex_ai(file_path):
    """Xử lý 1 file đơn lẻ (ảnh/PDF/DOCX) với Vertex AI - Mode 1"""
    if file_path.endswith('.pdf'):
        file_type = "PDF"
    elif file_path.endswith('.docx'):
        file_type = "DOCX"
    else:
        file_type = "ảnh"
        
    print(f"\n🔄 CHẾ ĐỘ: Xử lý {file_type} đơn lẻ (Vertex AI)")
    print(f"📁 File: {os.path.basename(file_path)}")
    
    # Gọi function phù hợp
    if file_path.endswith('.pdf'):
        result = ocr_single_pdf_vertex_ai(file_path, index=None, show_result=True)
    elif file_path.endswith('.docx'):
        result = process_single_docx_vertex_ai(file_path, index=None, show_result=True)
    else:
        result = ocr_single_image(file_path, index=None, show_result=True)

    if result and result[1]:  # result[1] là success flag
        # Áp dụng mapping
        final_content = post_process_with_mapping(result[0], os.path.basename(file_path), "Vertex AI")
        
        # Lưu kết quả
        output_file = save_ocr_result_to_markdown(final_content, file_path, app_config.output_folder)
        
        if output_file:
            print(f"💾 Đã lưu kết quả vào: {os.path.basename(output_file)}")
        else:
            print("❌ Lỗi khi lưu file!")
    else:
        print("\n❌ THẤT BẠI!")

def single_file_mode_mathpix(file_path):
    """Xử lý 1 file đơn lẻ (ảnh/PDF/DOCX) với Mathpix API - Mode 2"""
    if file_path.endswith('.pdf'):
        file_type = "PDF"
    elif file_path.endswith('.docx'):
        file_type = "DOCX"
    else:
        file_type = "ảnh"
        
    print(f"\n🔄 CHẾ ĐỘ: Xử lý {file_type} đơn lẻ (Mathpix API)")
    print(f"📁 File: {os.path.basename(file_path)}")
    
    # Gọi function phù hợp
    if file_path.endswith('.pdf'):
        result = ocr_single_pdf_mathpix(file_path, index=None, show_result=True)
    elif file_path.endswith('.docx'):
        result = process_single_docx_mathpix(file_path, index=None, show_result=True)
    else:
        result = ocr_single_image_mathpix(file_path, index=None, show_result=True)

    if result and result[1]:  # result[1] là success flag
        # Áp dụng mapping nếu user muốn
        final_content = post_process_with_mapping(result[0], os.path.basename(file_path), "Mathpix API")
        
        # Lưu kết quả sử dụng function mới
        output_file = save_single_result_to_markdown_mathpix(
            final_content,  # result_text đã được mapping
            file_path,  # file_path
            app_config.output_folder
        )
        
        if output_file:
            print(f"💾 Đã lưu kết quả vào: {os.path.basename(output_file)}")
        else:
            print("❌ Lỗi khi lưu file!")
    else:
        print("\n❌ THẤT BẠI!")

def single_image_mode_mathpix(image_path):
    return single_file_mode_mathpix(image_path)

def multiple_files_mode_mathpix(file_paths, max_workers=None):
    """Xử lý nhiều file đồng thời với Mathpix API - Mode 2"""
    print(f"\n🔄 CHẾ ĐỘ: Xử lý đa tiến trình (Mathpix API)")
    
    # Xử lý đa tiến trình
    results = process_multiple_files_mathpix(file_paths, max_workers)
    
    if results:
        # Lưu kết quả tổng hợp
        output_file = save_multiple_results_to_markdown_mathpix(results, app_config.output_folder)
        
        if output_file:
            print(f"💾 Đã lưu kết quả tổng hợp vào: {os.path.basename(output_file)}")
            
    else:
        print("\n❌ TOÀN BỘ QUÁ TRÌNH THẤT BẠI!")

def multiple_images_mode_mathpix(image_paths, max_workers=None):
    """Test xử lý nhiều ảnh đồng thời với Mathpix API - Mode 2 - Backward compatibility"""
    return multiple_files_mode_mathpix(image_paths, max_workers)

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

def save_ocr_result_to_markdown(result_text, image_path, output_folder):
    """Lưu kết quả OCR thành file markdown và chuyển đổi sang JSON"""
    try:
        # Tạo tên file với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ocr_result_{timestamp}.md"
        output_file = os.path.join(output_folder, filename)
        
        # Ghi nội dung vào file markdown
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_text)
        
        print(f"✅ Đã lưu file MD: {os.path.basename(output_file)}")
        
        # Chuyển đổi MD sang JSON
        try:
            json_file = convert_md_to_json_final(output_file)
            if json_file:
                print(f"✅ Hoàn thành pipeline: MD → JSON")
            else:
                print(f"⚠️ Không thể chuyển đổi sang JSON")
        except Exception as json_error:
            print(f"⚠️ Lỗi khi chuyển đổi sang JSON: {str(json_error)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu file markdown: {e}")
        traceback.print_exc()
        return None

def single_pdf_mode_vertex_ai(pdf_path):
    """Xử lý 1 PDF đơn lẻ với Vertex AI"""
    print(f"\n📄 SINGLE PDF MODE (VERTEX AI)")
    print(f"📁 File: {os.path.basename(pdf_path)}")
    
    start_time = time.time()
    
    # Gọi OCR
    result = ocr_single_pdf_vertex_ai(pdf_path, show_result=True)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    if result[1]:  # success
        # Áp dụng mapping nếu user muốn
        final_content = post_process_with_mapping(result[0], os.path.basename(pdf_path), "Vertex AI")
        
        # Lưu kết quả
        output_file = os.path.join(app_config.output_folder, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_vertex_processed.md")
        
        try:
            os.makedirs(app_config.output_folder, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            print(f"\n✅ Hoàn thành trong {processing_time:.2f} giây")
            print(f"💾 Đã lưu: {os.path.basename(output_file)}")
            
        except Exception as e:
            print(f"❌ Lỗi khi lưu file: {e}")
    else:
        print(f"❌ Xử lý thất bại trong {processing_time:.2f} giây")
        print(f"   Lỗi: {result[2]}")

def multiple_pdfs_mode_vertex_ai(pdf_paths, max_workers):
    """Xử lý nhiều PDF với Vertex AI - Mode 1"""
    print(f"\n📄 MULTIPLE PDFs MODE (VERTEX AI)")
    print(f"📁 {len(pdf_paths)} PDFs")
    
    start_time = time.time()
    
    # Xử lý tuần tự từng PDF (vì mỗi PDF đã multiprocessing internally)
    combined_results = []
    successful_count = 0
    failed_files = []
    
    for i, pdf_path in enumerate(pdf_paths):
        filename = os.path.basename(pdf_path)
        print(f"\n📄 [{i+1}/{len(pdf_paths)}] Đang xử lý: {filename}")
        
        # Gọi function xử lý PDF đơn lẻ (có multiprocessing cho các trang)
        result = ocr_single_pdf_vertex_ai(pdf_path, index=i, show_result=False)
        
        if result[1] and result[1]:  # success và có result_text
            successful_count += 1
            combined_results.append(f"# {filename}\n\n{result[1]}")
            
            # Lưu file riêng lẻ
            individual_output = os.path.join(app_config.output_folder, f"{os.path.splitext(filename)[0]}_vertex_processed.md")
            try:
                os.makedirs(app_config.output_folder, exist_ok=True)
                with open(individual_output, 'w', encoding='utf-8') as f:
                    f.write(result[1])
                print(f"✅ [File {i+1}] Đã lưu: {os.path.basename(individual_output)}")
            except Exception as e:
                print(f"⚠️ [File {i+1}] Lỗi lưu {filename}: {e}")
        else:
            error_msg = result[2] if len(result) > 2 else "Unknown error"
            failed_files.append((filename, error_msg))
            print(f"❌ [File {i+1}] Lỗi {filename}: {error_msg}")
    
    # Lưu file tổng hợp
    if successful_count > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_output_file = os.path.join(app_config.output_folder, f"vertex_multiple_pdfs_{timestamp}_processed.md")
        
        try:
            with open(combined_output_file, 'w', encoding='utf-8') as f:
                f.write("# Kết quả OCR Multiple PDFs (Vertex AI)\n\n")
                f.write(f"**Thời gian xử lý:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Mode:** Vertex AI (Google Gemini 2.5-pro)\n")
                f.write(f"**Tổng files:** {len(pdf_paths)}\n")
                f.write(f"**Thành công:** {successful_count}\n")
                f.write(f"**Thất bại:** {len(failed_files)}\n\n")
                
                if failed_files:
                    f.write("## ❌ Files thất bại:\n\n")
                    for filename, error in failed_files:
                        f.write(f"- **{filename}**: {error}\n")
                    f.write("\n")
                
                f.write("---\n\n")
                f.write("\n\n".join(combined_results))
            
            print(f"📋 File tổng hợp: {os.path.basename(combined_output_file)}")
        except Exception as e:
            print(f"⚠️ Lỗi tạo file tổng hợp: {e}")
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print("\n" + "="*60)
    print("📊 TỔNG KẾT BATCH OCR PDFs (VERTEX AI)")
    print("="*60)
    print(f"📄 Tổng files PDF: {len(pdf_paths)}")
    print(f"✅ Thành công: {successful_count}")
    print(f"❌ Thất bại: {len(failed_files)}")
    print(f"⏱️ Thời gian xử lý: {processing_time:.2f} giây")
    print(f"⚡ Tốc độ trung bình: {processing_time/len(pdf_paths):.2f} giây/file")
    print("="*60)

def save_mapping_result(mapped_content, input_filename, mode_name):
    """
    Lưu kết quả mapping vào file riêng trong thư mục output
    Args:
        mapped_content: Nội dung đã được mapping
        input_filename: Tên file input gốc
        mode_name: Tên mode xử lý
    Returns:
        str: Đường dẫn file đã lưu hoặc None nếu lỗi
    """
    try:
        # Tạo tên file với timestamp và mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(input_filename)[0]
        mode_short = "vertex" if "Vertex" in mode_name else "mathpix"
        filename = f"{base_name}_{mode_short}_mapped_{timestamp}.md"
        
        output_file = os.path.join(app_config.output_folder, filename)
        
        # Ghi nội dung vào file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(mapped_content)
        
        print(f"💾 Đã lưu kết quả mapping: {os.path.basename(output_file)}")
        return output_file
        
    except Exception as e:
        print(f"⚠️ Lỗi khi lưu kết quả mapping: {str(e)}")
        return None

def post_process_with_mapping(content, input_filename, mode_name):
    """
    Xử lý nội dung sau OCR để mapping câu hỏi với lời giải
    Args:
        content: Nội dung OCR đã xử lý
        input_filename: Tên file input gốc
        mode_name: Tên mode (để ghi trong output)
    Returns:
        str: Nội dung đã được mapping (nếu có) hoặc nội dung gốc
    """
    try:
        print(f"\n🧩 QUESTION-ANSWER MAPPING")
        print("━" * 50)
        print(f"🤖 Tự động mapping câu hỏi với lời giải bằng AI ({mode_name})")
        
        # Khởi tạo mapper
        print("🔄 Khởi tạo AI mapper...")
        mapper = QuestionAnswerMapper()
        
        if not mapper.model:
            print("❌ Không thể khởi tạo AI model cho mapping")
            print("⏭️ Tiếp tục với nội dung OCR gốc")
            return content
        
        # Gửi trực tiếp nội dung cho AI để xử lý
        print(f"🤖 Đang gửi {len(content):,} ký tự cho AI...")
        start_time = datetime.now()
        
        mapped_content = mapper.process_content(content)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        if mapped_content:
            print(f"✅ Mapping thành công! ({processing_time:.2f}s)")
            print(f"📏 Kết quả: {len(mapped_content):,} ký tự")
            
            # Lưu kết quả mapping vào file riêng
            save_mapping_result(mapped_content, input_filename, mode_name)
            
            return mapped_content
        else:
            print(f"❌ Mapping thất bại ({processing_time:.2f}s)")
            print("⏭️ Tiếp tục với nội dung OCR gốc")
            return content
        
    except Exception as e:
        print(f"❌ Lỗi trong quá trình mapping: {e}")
        print("⏭️ Tiếp tục với nội dung OCR gốc")
        return content

def main():
    # Hiển thị thông tin cấu hình
    app_config.get_config_summary()
    print()
    
    # Hiển thị PDF support status
    if PDF_SUPPORT:
        print("📄 PDF SUPPORT: ✅ Có hỗ trợ (pdf2image đã cài đặt)")
    else:
        print("📄 PDF SUPPORT: ❌ Không hỗ trợ (cần cài: pip install pdf2image)")
        print("   💡 Mode 1 chỉ hỗ trợ ảnh, Mode 2 vẫn hỗ trợ đầy đủ")
    
    # Hiển thị DOCX support status
    if DOCX_SUPPORT:
        print("📄 DOCX SUPPORT: ✅ Có hỗ trợ (aspose-words đã cài đặt)")
    else:
        print("📄 DOCX SUPPORT: ❌ Không hỗ trợ (cần cài: pip install aspose-words)")
    print()
    
    # Cho phép user chọn mode
    print("🎯 CHỌN MODE XỬ LÝ:")
    if PDF_SUPPORT and DOCX_SUPPORT:
        print("1️⃣  Mode 1: Gemini OCR + Q&A Mapping (Ảnh + PDF + DOCX)")
    elif PDF_SUPPORT:
        print("1️⃣  Mode 1: Gemini OCR + Q&A Mapping (Ảnh + PDF)")
    else:
        print("1️⃣  Mode 1: Gemini OCR + Q&A Mapping (Chỉ ảnh)")
    
    if DOCX_SUPPORT:
        print("2️⃣  Mode 2: Mathpix + Q&A Mapping (Ảnh + PDF + DOCX)")
    else:
        print("2️⃣  Mode 2: Mathpix + Q&A Mapping (Ảnh + PDF)")
    print("0️⃣  Thoát")
    
    while True:
        try:
            choice = input("\n👉 Nhập lựa chọn (1/2/0): ").strip()
            
            if choice == "0":
                return
            elif choice in ["1", "2"]:
                break
            else:
                print("❌ Lựa chọn không hợp lệ! Vui lòng nhập 1, 2 hoặc 0.")
        except KeyboardInterrupt:
            return
    
    mode = int(choice)
    
    # Lấy tất cả file ảnh, PDF và DOCX trong thư mục input
    file_paths = get_supported_files_from_folder(app_config.input_folder)
    
    # Tạo mô tả file type name
    if mode == 1:
        support_types = ["ảnh"]
        if PDF_SUPPORT:
            support_types.append("PDF")
        if DOCX_SUPPORT:
            support_types.append("DOCX")
        file_type_name = "/".join(support_types)
    else:  # mode == 2
        support_types = ["ảnh", "PDF"]
        if DOCX_SUPPORT:
            support_types.append("DOCX")
        file_type_name = "/".join(support_types)
    
    if not file_paths:
        print(f"📁 Vui lòng thêm {file_type_name} vào: {app_config.input_folder}")
        return
    
    # Tự động chọn mode dựa trên số lượng file
    num_files = len(file_paths)
    print(f"\n📁 Tìm thấy {num_files} {file_type_name} trong thư mục input:")
    for i, path in enumerate(file_paths, 1):
        if path.endswith('.pdf'):
            file_type = "📄 PDF"
        elif path.endswith('.docx'):
            file_type = "📄 DOCX"
        else:
            file_type = "📷 IMG"
        print(f"   {i}. {file_type} {os.path.basename(path)}")
    
    if mode == 1:
        # Mode 1: Vertex AI OCR + Q&A Mapping
        print(f"\n🤖 Sử dụng Mode 1: Vertex AI OCR + Q&A Mapping")
        
        support_list = ["Ảnh"]
        if PDF_SUPPORT:
            support_list.append("PDF")
        if DOCX_SUPPORT:
            support_list.append("DOCX")
        print(f"📄 Hỗ trợ: {' + '.join(support_list)}")
        
        if num_files == 1:
            # Mode 1: Xử lý 1 file đơn lẻ
            file_path = file_paths[0]
            if file_path.lower().endswith('.pdf'):
                if PDF_SUPPORT:
                    single_pdf_mode_vertex_ai(file_path)
                else:
                    print("❌ PDF không được hỗ trợ. Cần cài đặt: pip install pdf2image")
            elif file_path.lower().endswith('.docx'):
                if DOCX_SUPPORT:
                    single_file_mode_vertex_ai(file_path)
                else:
                    print("❌ DOCX không được hỗ trợ. Cần cài đặt: pip install docx2pdf")
            else:
                single_image_mode(file_path)
        else:
            # Xử lý với số process = số CPU hoặc số file (tùy cái nào nhỏ hơn)
            max_workers = min(num_files, mp.cpu_count())
            print(f"🚀 Sử dụng {max_workers} processes")
            
            # Phân loại files
            image_files = [f for f in file_paths if not f.lower().endswith(('.pdf', '.docx'))]
            pdf_files = [f for f in file_paths if f.lower().endswith('.pdf')]
            docx_files = [f for f in file_paths if f.lower().endswith('.docx')]
            
            if image_files:
                print(f"📷 Xử lý {len(image_files)} ảnh với Vertex AI...")
                multiple_images_mode(image_files, max_workers)
            
            if pdf_files:
                if PDF_SUPPORT:
                    print(f"📄 Xử lý {len(pdf_files)} PDF với Vertex AI...")
                    multiple_pdfs_mode_vertex_ai(pdf_files, max_workers)
                else:
                    print(f"❌ Bỏ qua {len(pdf_files)} PDF (cần cài pdf2image)")
            
            if docx_files:
                if DOCX_SUPPORT:
                    print(f"📄 Xử lý {len(docx_files)} DOCX với Vertex AI...")
                    # Xử lý DOCX tuần tự vì có convert step
                    for docx_file in docx_files:
                        single_file_mode_vertex_ai(docx_file)
                else:
                    print(f"❌ Bỏ qua {len(docx_files)} DOCX (cần cài docx2pdf)")
                    
    elif mode == 2:
        # Mode 2: Mathpix OCR + Q&A Mapping
        print(f"\n📐 Sử dụng Mode 2: Mathpix API OCR + Q&A Mapping")
        
        if num_files == 1:
            # Mode 2: Xử lý 1 file đơn lẻ
            single_file_mode_mathpix(file_paths[0])
        else:
            # Xử lý với số process = số CPU hoặc số file (tùy cái nào nhỏ hơn)
            max_workers = min(num_files, mp.cpu_count())
            print(f"🚀 Sử dụng {max_workers} processes")
            multiple_files_mode_mathpix(file_paths, max_workers)

if __name__ == "__main__":
    main()
