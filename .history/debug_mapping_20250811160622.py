import os
import sys
sys.path.append('c:/app/QProcess')

# Test debug mapping
from processors.question_answer_mapper import QuestionAnswerMapper

# Đọc file output để xem nội dung
output_file = 'c:/app/QProcess/data/output/mathpix_result_20250811_160228.md'

if os.path.exists(output_file):
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 File output: {os.path.basename(output_file)}")
    print(f"📏 Độ dài file output: {len(content):,} ký tự")
    print(f"📝 Số dòng: {len(content.splitlines())}")
    print("\n" + "="*50)
    print("🔍 CONTENT PREVIEW (đầu 500 ký tự):")
    print("="*50)
    print(content[:500])
    print("\n" + "="*50)
    print("🔍 CONTENT PREVIEW (cuối 500 ký tự):")
    print("="*50)
    print(content[-500:])
    
    # Test tạo mapper để kiểm tra
    mapper = QuestionAnswerMapper()
    if mapper.model:
        print(f"\n✅ Mapper khởi tạo thành công")
        
        # Test với content nhỏ
        test_content = """
**Câu 1:** Test question 1
A. Option A
B. Option B
**Câu 2:** Test question 2  
A. Option A
B. Option B

Lời giải:
Câu 1: Đáp án A vì...
Câu 2: Đáp án B vì...
"""
        print(f"\n🧪 Test với content mẫu ({len(test_content)} ký tự)")
        result = mapper._process_content_with_ai(test_content)
        if result:
            print(f"✅ Test mapping thành công: {len(result)} ký tự")
            print("Kết quả:", result[:200] + "...")
        else:
            print("❌ Test mapping thất bại")
    else:
        print("❌ Không thể khởi tạo mapper")

else:
    print(f"❌ File không tồn tại: {output_file}")
