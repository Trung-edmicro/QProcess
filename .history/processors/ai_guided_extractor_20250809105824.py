"""
AI-Guided Diagram Extractor - Sử dụng AI để nhận diện vị trí hình vẽ, OpenCV để cắt chính xác
"""
import os
import cv2
import numpy as np
from pathlib import Path
import base64
import json

class AIGuidedDiagramExtractor:
    """Class sử dụng AI để nhận diện hình vẽ và OpenCV để cắt chính xác"""
    
    def __init__(self, output_dir="data/images"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def encode_image_to_base64(self, image_path):
        """Encode ảnh thành base64 để gửi cho AI"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_image_with_ai(self, image_path):
        """
        Sử dụng AI để phân tích và tìm vị trí hình vẽ/bảng biểu
        Trả về danh sách bounding boxes cho các hình vẽ
        """
        # Template prompt cho AI
        prompt = """
        Hãy phân tích ảnh này và tìm tất cả các hình vẽ, biểu đồ, bảng biểu, hình học trong ảnh.
        
        Yêu cầu:
        1. KHÔNG bao gồm text thuần túy
        2. CHỈ bao gồm: hình học, biểu đồ, bảng, sơ đồ, đồ thị
        3. Trả về tọa độ bounding box dạng [x, y, width, height] (pixel)
        4. Thêm mô tả ngắn gọn cho mỗi hình vẽ
        
        Format JSON:
        {
            "diagrams": [
                {
                    "bbox": [x, y, width, height],
                    "description": "mô tả hình vẽ",
                    "type": "geometry/chart/table/diagram"
                }
            ]
        }
        """
        
        # TODO: Tích hợp với AI service (Vertex AI, OpenAI, etc.)
        # Hiện tại return mock data để demo
        return self._mock_ai_analysis(image_path)
    
    def _mock_ai_analysis(self, image_path):
        """Mock AI analysis để demo - sẽ thay bằng real AI call"""
        print(f"🤖 [MOCK] AI đang phân tích {image_path}...")
        
        # Đọc ảnh để lấy kích thước
        img = cv2.imread(image_path)
        if img is None:
            return {"diagrams": []}
        
        h, w = img.shape[:2]
        
        # Mock data - giả sử AI tìm thấy một số hình vẽ
        mock_results = {
            "diagrams": [
                {
                    "bbox": [int(w*0.1), int(h*0.2), int(w*0.3), int(h*0.2)],
                    "description": "Hình học tam giác",
                    "type": "geometry"
                },
                {
                    "bbox": [int(w*0.6), int(h*0.4), int(w*0.25), int(h*0.3)],
                    "description": "Biểu đồ cột",
                    "type": "chart"
                }
            ]
        }
        
        print(f"🤖 AI tìm thấy {len(mock_results['diagrams'])} hình vẽ")
        return mock_results
    
    def extract_diagrams_with_ai(self, image_path, padding=10):
        """
        Sử dụng AI để nhận diện và OpenCV để cắt chính xác
        
        Args:
            image_path: đường dẫn ảnh
            padding: đệm khi cắt
            
        Returns:
            tuple (preview_path, diagram_paths, ai_results)
        """
        print(f"🔍 Bắt đầu xử lý với AI guidance: {image_path}")
        
        # Bước 1: AI analysis
        ai_results = self.analyze_image_with_ai(image_path)
        
        if not ai_results.get("diagrams"):
            print("⚠️ AI không tìm thấy hình vẽ nào")
            return None, [], ai_results
        
        # Bước 2: Load ảnh
        original_image = cv2.imread(image_path)
        if original_image is None:
            raise FileNotFoundError(f"Không thể đọc ảnh: {image_path}")
        
        h, w = original_image.shape[:2]
        
        # Bước 3: Tạo preview với AI bounding boxes
        preview_image = original_image.copy()
        diagram_paths = []
        base_name = Path(image_path).stem
        
        for i, diagram in enumerate(ai_results["diagrams"], 1):
            bbox = diagram["bbox"]
            x, y, width, height = bbox
            
            # Validate và adjust bbox
            x = max(0, min(x, w))
            y = max(0, min(y, h))
            width = min(width, w - x)
            height = min(height, h - y)
            
            if width <= 0 or height <= 0:
                print(f"⚠️ Bbox không hợp lệ cho diagram {i}: {bbox}")
                continue
            
            # Thêm padding
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(w, x + width + padding)
            y_end = min(h, y + height + padding)
            
            # Cắt diagram
            cropped = original_image[y_start:y_end, x_start:x_end]
            
            # Lưu diagram
            diagram_path = os.path.join(
                self.output_dir, 
                f"{base_name}_ai_diagram_{i:02d}.png"
            )
            cv2.imwrite(diagram_path, cropped)
            diagram_paths.append(diagram_path)
            
            # Vẽ bounding box trên preview
            color = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)][i % 5]
            cv2.rectangle(preview_image, (x, y), (x + width, y + height), color, 2)
            
            # Thêm label
            label = f"{i}. {diagram['type']}"
            cv2.putText(
                preview_image, label,
                (x, y - 10 if y > 20 else y + height + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )
            
            print(f"💾 Đã lưu AI diagram {i}: {diagram_path}")
            print(f"    📝 {diagram['description']} ({diagram['type']})")
        
        # Lưu preview
        preview_path = os.path.join(self.output_dir, f"{base_name}_ai_preview.png")
        cv2.imwrite(preview_path, preview_image)
        print(f"💾 Đã lưu AI preview: {preview_path}")
        
        return preview_path, diagram_paths, ai_results

class HybridDiagramExtractor:
    """Class kết hợp cả OpenCV traditional và AI-guided approaches"""
    
    def __init__(self, output_dir="data/images"):
        self.output_dir = output_dir
        self.ai_extractor = AIGuidedDiagramExtractor(output_dir)
        # Import traditional extractor
        from diagram_extractor import DiagramExtractor
        self.cv_extractor = DiagramExtractor(output_dir)
    
    def extract_with_comparison(self, image_path):
        """
        So sánh kết quả giữa traditional OpenCV và AI-guided
        
        Returns:
            dict chứa kết quả từ cả hai phương pháp
        """
        print(f"🔄 So sánh Traditional CV vs AI-guided cho: {image_path}")
        print("="*60)
        
        results = {}
        
        # Phương pháp 1: Traditional OpenCV (Strict mode)
        print("\n🔧 TRADITIONAL OPENCV (STRICT MODE):")
        try:
            cv_preview, cv_diagrams, cv_stats = self.cv_extractor.extract_diagrams(
                image_path,
                min_size=100,
                max_area_ratio=0.2,
                aspect_range=(0.5, 2.0),
                solidity_range=(0.3, 0.8)
            )
            results['opencv'] = {
                'preview': cv_preview,
                'diagrams': cv_diagrams,
                'stats': cv_stats,
                'count': len(cv_diagrams)
            }
            print(f"✅ OpenCV: {len(cv_diagrams)} diagrams")
        except Exception as e:
            print(f"❌ OpenCV error: {e}")
            results['opencv'] = {'error': str(e), 'count': 0}
        
        # Phương pháp 2: AI-guided
        print("\n🤖 AI-GUIDED APPROACH:")
        try:
            ai_preview, ai_diagrams, ai_results = self.ai_extractor.extract_diagrams_with_ai(image_path)
            results['ai_guided'] = {
                'preview': ai_preview,
                'diagrams': ai_diagrams,
                'ai_analysis': ai_results,
                'count': len(ai_diagrams) if ai_diagrams else 0
            }
            print(f"✅ AI-guided: {len(ai_diagrams) if ai_diagrams else 0} diagrams")
        except Exception as e:
            print(f"❌ AI-guided error: {e}")
            results['ai_guided'] = {'error': str(e), 'count': 0}
        
        # So sánh kết quả
        print(f"\n📊 COMPARISON SUMMARY:")
        cv_count = results.get('opencv', {}).get('count', 0)
        ai_count = results.get('ai_guided', {}).get('count', 0)
        print(f"   Traditional OpenCV: {cv_count} diagrams")
        print(f"   AI-guided: {ai_count} diagrams")
        
        if cv_count > 0 and ai_count > 0:
            print(f"   🎯 AI-guided có thể chính xác hơn (semantic understanding)")
        elif cv_count > ai_count:
            print(f"   📈 OpenCV tìm được nhiều hơn (có thể bao gồm false positives)")
        elif ai_count > cv_count:
            print(f"   🤖 AI tìm được nhiều hơn (có thể miss một số trong OpenCV)")
        
        return results

# Mock integration với Vertex AI (để demo)
def integrate_with_vertex_ai():
    """
    Template để tích hợp với Vertex AI thực tế
    """
    integration_code = '''
    # Tích hợp với Vertex AI Gemini
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    
    def analyze_image_with_vertex_ai(self, image_path):
        """Sử dụng Vertex AI Gemini để phân tích ảnh"""
        
        # Initialize Vertex AI
        vertexai.init(project="your-project-id", location="us-central1")
        
        # Load model
        model = GenerativeModel("gemini-2.0-flash-exp")
        
        # Prepare image
        image_part = Part.from_uri(image_path, mime_type="image/png")
        
        # Prompt
        prompt = """
        Analyze this image and identify all diagrams, charts, tables, and geometric figures.
        
        Requirements:
        1. DO NOT include plain text
        2. ONLY include: geometry, charts, tables, diagrams, graphs
        3. Return bounding box coordinates as [x, y, width, height] in pixels
        4. Add brief description for each figure
        
        Return JSON format:
        {
            "diagrams": [
                {
                    "bbox": [x, y, width, height],
                    "description": "description",
                    "type": "geometry/chart/table/diagram"
                }
            ]
        }
        """
        
        # Generate response
        response = model.generate_content([prompt, image_part])
        
        # Parse JSON response
        import json
        return json.loads(response.text)
    '''
    return integration_code

if __name__ == "__main__":
    print("🔧 AI-Guided Diagram Extractor Demo")
    print("="*50)
    print("📝 Đây là template để tích hợp AI vào việc cắt hình vẽ")
    print("🤖 Hiện tại sử dụng mock data, cần tích hợp với AI service thực tế")
    print("💡 Vertex AI integration code:")
    print(integrate_with_vertex_ai())
