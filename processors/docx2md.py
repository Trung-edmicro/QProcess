import os
import pypandoc
import win32com.client
 
def preprocess_docx(docx_path):
    """Mở và lưu lại file .docx để chuẩn hóa cấu trúc XML."""
    try:
        word = win32com.client.Dispatch("Word.Application")
        doc = word.Documents.Open(os.path.abspath(docx_path))
        doc.Save()
        doc.Close()
        word.Quit()
        print(f"Đã tiền xử lý file: '{docx_path}'")
    except Exception as e:
        print(f"Lỗi khi tiền xử lý file .docx: {e}")
 
def convert_docx_to_md(docx_path: str,temp_dir: str = "temp_md"):
 
    # Kiểm tra xem file docx có tồn tại không
    if not os.path.exists(docx_path):
        print(f"Lỗi: File '{docx_path}' không tồn tại.")
        return
 
    base_name = os.path.splitext(docx_path)[0]
    md_path = base_name + '.md'
 
    print(f"Bắt đầu chuyển đổi file: '{docx_path}'...")
 
    extra_args = [f'--extract-media={temp_dir}']
    output_format = 'markdown'
 
    try:
        pypandoc.convert_file(
            source_file=docx_path,
            to=output_format,
            outputfile=md_path,
            extra_args=extra_args,
            encoding='utf-8'
        )
        print("-" * 30)
        print("🎉 Chuyển đổi thành công!")
        print(f"✔️ File Markdown đã được lưu tại: '{md_path}'")
        print(f"✔️ Ảnh đã được lưu trong thư mục: 'media'")
        print("-" * 30)
        return md_path
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
 
if __name__ == "__main__":
    input_file = r'C:\Users\Admin\Downloads\ghep_docx\output\1.merge\Lý 10\LY10_GK1_THPT NGUYỄN HUỆ_HCM.docx'
    if not os.path.exists(input_file):
        print(f"Không tìm thấy file '{input_file}'.")
    else:
        convert_docx_to_md(input_file)