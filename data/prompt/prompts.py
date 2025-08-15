# Prompt cho Vertex AI OCR
VERTEX_AI_OCR = """
Hãy đọc và trích xuất toàn bộ text từ ảnh này. 
Yêu cầu chung:
1. Đọc chính xác tất cả text có trong ảnh
2. Giữ nguyên format và cấu trúc của text
3. Nếu có công thức toán học, hãy chuyển sang định dạng LaTeX
4. Bỏ qua bảng, hình ảnh, biểu đồ, v.v...
5. Trả về kết quả chỉ gồm nội dung OCR được, Không thêm câu dẫn, không cần giải thích hay bình luận gì thêm.

Yêu cầu cụ thể:
1. Trường hợp ảnh có kí tự đặc biệt (như chữ ký, hình vẽ tay) thì không trả về ở kết quả.
2. Với ảnh là đề thi thì cần loại bỏ các phần không liên quan như thông tin trường/học sinh, hướng dẫn, số trang, mã đề.
3. Vì là nội dung OCR liên quan đến các câu hỏi nên cần đảm bảo có các phần tiêu đề, câu hỏi, đáp án rõ ràng và được in đậm tên phần (**Phần I.{nội dung}**), số câu (**Câu 1:**).
"""

# Prompt cho Question-Answer Mapping
QUESTION_ANSWER_MAPPING = """Bạn là trợ lý biên tập tài liệu.  
Nhiệm vụ: Đọc toàn bộ nội dung sau, ghép **mỗi câu hỏi** với **lời giải chi tiết** tương ứng.  

**Với phần định dạng bắt buộc:**
```
**Phần (nếu là tiếng Anh thay Phần -> Part) [Số/Kí tự la mã]:** [Nguyên văn nội dung phần]
```

**Với định dạng câu hỏi và lời giải bắt buộc cho mỗi cặp:**
```
**Câu (nếu là tiếng Anh thay Câu -> Question) [Số]:** [Nguyên văn câu hỏi + các đáp án A, B, C, D...]   
Lời giải   
[Nguyên văn lời giải chi tiết tương ứng]
```

**Quy tắc bắt buộc:**
1. Hãy giữ nguyên toàn bộ nội dung gốc của phần, câu hỏi và lời giải, bao gồm số thứ tự, nội dung, ký hiệu, công thức…
2. Nếu có bảng đang ở dạng Markdown hay mã Latex thì bắt buộc chuyển đổi sang dạng mã HTML (không cần style).
3. Không lược bỏ hay thay đổi nội dung quan trọng.  
4. Lọc nội dung Lời giải và ghép vào câu hỏi tương ứng. Tuyệt đối tự ý bịa thêm lời giải hoặc thông tin ngoài nguồn.  
5. Không thêm câu dẫn hoặc mô tả ngoài định dạng yêu cầu.  
6. Xử lý tất cả câu hỏi có trong tài liệu, theo đúng thứ tự xuất hiện. Lưu ý không tự ý thêm lời giải nếu nội dung thiếu phần đáp án/lời giải.

Nội dung cần xử lý:  
{content}"""

MD2JSON = """
Bạn là một công cụ chuyển đổi Markdown sang JSON. Tôi sẽ cung cấp cho bạn một đoạn văn bản chứa nhiều dạng câu hỏi (gồm Trắc nghiệm, Đúng/Sai, Trắc nghiệm ngắn - Điền, Tự luận), có thể kèm theo hình ảnh.
Các hình ảnh đã được tôi gửi kèm theo yêu cầu này. Trong văn bản, chúng được đại diện bởi các placeholder như [IMAGE_0], [IMAGE_1], v.v.

Nhiệm vụ của bạn là phân tích và chuyển đổi mỗi câu hỏi thành một đối tượng JSON.

Hãy đảm bảo các chú ý sau:
- Trích xuất chính xác "Câu X:" và nội dung của câu hỏi.
- Nội dung sẽ có cả những câu hỏi được xây dựng dựa trên nội dung của một học liệu (là một đoạn nội dung và một số câu hỏi bên dưới có liên quan tới nội dung đó) nên cần phải kiểm soát kĩ và trả về đúng định dạng Json theo yêu cầu.
- Khi bạn thấy một placeholder như [IMAGE_0], HÃY GIỮ NGUYÊN placeholder đó trong trường "question_content" của JSON. Đừng cố gắng mô tả hình ảnh.
- Bao gồm cả các câu hỏi không có lời giải, đáp án, hoặc lựa chọn.


Bây giờ, hãy chuyển đổi đoạn văn bản sau:
```
{modified_markdown_content}
```
"""