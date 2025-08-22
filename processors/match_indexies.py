import json

def replace_indices_with_content(data, md_content: str, output_path: str = None):
    """
    Duyệt qua cấu trúc dữ liệu JSON, tìm các đối tượng chứa 'startIndex' và 'endIndex',
    và thêm một trường 'content' mới chứa nội dung trích xuất từ file Markdown.

    PHIÊN BẢN SỬA LỖI:
    - Sửa lại logic đệ quy để xác định đúng đối tượng cần xử lý.
    - Thêm trường 'content' thay vì thay thế toàn bộ đối tượng.
    - Chuẩn hóa ký tự xuống dòng ('\r\n' -> '\n') để đảm bảo tính nhất quán.

    Args:
        data (dict): Dữ liệu đầu vào dưới dạng dictionary.
        md_content (str): Nội dung nguồn từ file Markdown.
        output_path (str, optional): Nếu được cung cấp, kết quả sẽ được lưu vào đường dẫn file này.

    Returns:
        dict: Một dictionary chứa dữ liệu đã được xử lý.
    """
    
    # Chuẩn hóa ký tự xuống dòng để xử lý khác biệt giữa các hệ điều hành.
    md_content = md_content.replace('\r\n', '\n')

    def _recursive_add_content(obj):
        """
        Hàm đệ quy để duyệt và thêm nội dung.
        Hàm này sẽ sửa đổi trực tiếp đối tượng đầu vào (in-place).
        """
        if isinstance(obj, dict):
            # Kiểm tra xem chính đối tượng này có chứa chỉ số không.
            if 'startIndex' in obj and 'endIndex' in obj:
                start = obj['startIndex']
                end = obj['endIndex']
                
                # Kiểm tra tính hợp lệ của chỉ số trước khi cắt chuỗi.
                if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end and end <= len(md_content):
                    obj['content'] = md_content[start:end]
                else:
                    # Gán một thông báo lỗi nếu chỉ số không hợp lệ.
                    print(f"Cảnh báo: Chỉ số không hợp lệ hoặc vượt ngoài giới hạn [{start}:{end}].")
                    obj['content'] = f"LỖI_CHỈ_SỐ_[{start}:{end}]"
            
            # Tiếp tục đệ quy cho các giá trị bên trong từ điển.
            for key, value in obj.items():
                _recursive_add_content(value)

        elif isinstance(obj, list):
            # Nếu là một danh sách, lặp qua và đệ quy cho từng phần tử.
            for item in obj:
                _recursive_add_content(item)
        
        return obj

    processed_data = _recursive_add_content(data)

    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as out_file:
                json.dump(processed_data, out_file, indent=4, ensure_ascii=False)
            print(f"Đã xử lý và lưu kết quả thành công vào: {output_path}")
        except IOError as e:
            print(f"Lỗi: Không thể ghi vào file output - {e}")
        except TypeError as e:
            print(f"Lỗi: Có vấn đề khi chuyển đổi dữ liệu thành JSON - {e}")


    return processed_data

# --- Dữ liệu đầu vào của bạn ---
json_data={
  "materials": [],
  "sections": [
    {
      "sectionTitle": "Câu trắc nghiệm",
      "questions": [
        {
          "startIndex": 0,
          "endIndex": 713,
          "typeAnswer": "0",
          "correctOption": [
            0
          ],
          "options": [
            {
              "startIndex": 642,
              "endIndex": 660,
              "isAnswer": True,
              "optionLabel": "A"
            },
            {
              "startIndex": 660,
              "endIndex": 678,
              "isAnswer": False,
              "optionLabel": "B"
            },
            {
              "startIndex": 678,
              "endIndex": 696,
              "isAnswer": False,
              "optionLabel": "C"
            },
            {
              "startIndex": 696,
              "endIndex": 714,
              "isAnswer": False,
              "optionLabel": "D"
            }
          ]
        },
        {
          "startIndex": 715,
          "endIndex": 1429,
          "typeAnswer": "0",
          "correctOption": [
            0
          ],
          "options": [
            {
              "startIndex": 642, # Chỉ số này có vẻ bị lặp lại, cần kiểm tra lại dữ liệu gốc
              "endIndex": 660,
              "isAnswer": True,
              "optionLabel": "A"
            },
            {
              "startIndex": 660,
              "endIndex": 678,
              "isAnswer": False,
              "optionLabel": "B"
            },
            {
              "startIndex": 678,
              "endIndex": 696,
              "isAnswer": False,
              "optionLabel": "C"
            },
            {
              "startIndex": 696,
              "endIndex": 714,
              "isAnswer": False,
              "optionLabel": "D"
            }
          ]
        },
        {
          "startIndex": 1430,
          "endIndex": 1629,
          "typeAnswer": "0",
          "correctOption": [
            0
          ],
          "options": [
            {
              "startIndex": 1549,
              "endIndex": 1569,
              "isAnswer": True,
              "optionLabel": "A"
            },
            {
              "startIndex": 1569,
              "endIndex": 1589,
              "isAnswer": False,
              "optionLabel": "B"
            },
            {
              "startIndex": 1589,
              "endIndex": 1609,
              "isAnswer": False,
              "optionLabel": "C"
            },
            {
              "startIndex": 1609,
              "endIndex": 1629,
              "isAnswer": False,
              "optionLabel": "D"
            }
          ]
        },
        {
          "startIndex": 1630,
          "endIndex": 2156,
          "typeAnswer": "0",
          "correctOption": [
            0
          ],
          "options": [
            {
              "startIndex": 1925,
              "endIndex": 1970,
              "isAnswer": True,
              "optionLabel": "A"
            },
            {
              "startIndex": 1970,
              "endIndex": 2068,
              "isAnswer": False,
              "optionLabel": "B"
            },
            {
              "startIndex": 2068,
              "endIndex": 2089,
              "isAnswer": False,
              "optionLabel": "C"
            },
            {
              "startIndex": 2107,
              "endIndex": 2156,
              "isAnswer": False,
              "optionLabel": "D"
            }
          ]
        }
      ]
    }
  ]
}

# --- Chạy chương trình ---
md_content = None
# Vui lòng thay đổi đường dẫn này thành đường dẫn chính xác trên máy của bạn
file_path = r"D:\Download\aicall\QProcess\data\output\mathpix_result_20250821_012221.md" 

try:
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # Gọi hàm đã sửa lỗi
    replace_indices_with_content(json_data, md_content, "a.json") # Đổi tên file output thành .json cho đúng định dạng

except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file tại đường dẫn: {file_path}")
except Exception as e:
    print(f"Đã xảy ra lỗi không xác định: {e}")