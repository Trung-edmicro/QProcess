#!/usr/bin/env python3
"""
Test case đơn giản cho chức năng Question-Answer Mapping
"""
import os
import sys
sys.path.append('c:/app/QProcess')

from processors.question_answer_mapper import QuestionAnswerMapper
from datetime import datetime

def simple_mapping_test():
    """Test đơn giản: đọc file .md -> gửi AI -> nhận kết quả"""
    
    print("="*60)
    print("🧪 TEST MAPPING ĐỔN GIẢN")
    print("="*60)
    
    # File test
    test_file = "c:/app/QProcess/data/output/testMapping.md"
    
    if not os.path.exists(test_file):
        print(f"❌ File test không tồn tại: {test_file}")
        return
    
    # Đọc file
    print(f"📖 Đọc file: {os.path.basename(test_file)}")
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📏 Độ dài: {len(content):,} ký tự")
    
    # Khởi tạo mapper
    print(f"\n🔧 Khởi tạo mapper...")
    mapper = QuestionAnswerMapper()
    
    if not mapper.model:
        print("❌ Không thể khởi tạo mapper!")
        return
    
    # Gửi cho AI
    print(f"\n🤖 Gửi nội dung cho AI...")
    start_time = datetime.now()
    
    try:
        result = mapper.process_content(content)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        if result:
            print(f"✅ Thành công! ({processing_time:.2f}s)")
            print(f"📏 Kết quả: {len(result):,} ký tự")
            
            # Lưu kết quả
            output_file = f"c:/app/QProcess/data/output/simple_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"💾 Đã lưu: {os.path.basename(output_file)}")
            
            # Preview
            print(f"\n📄 PREVIEW (300 ký tự đầu):")
            print("-" * 40)
            print(result[:300] + "..." if len(result) > 300 else result)
            
        else:
            print(f"❌ Thất bại! ({processing_time:.2f}s)")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)

if __name__ == "__main__":
    simple_mapping_test()
