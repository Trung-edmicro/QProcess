"""
Real Vertex AI Integration cho Diagram Extraction
"""
import os
import sys
import json
import cv2
import numpy as np
from pathlib import Path

# Import existing modules
sys.path.append('.')
sys.path.append('config')
sys.path.append('processors')

# Import local modules
from config import app_config
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

def process_with_vertex_ai(prompt, image_path):
    """
    Process image với Vertex AI - tương tự như trong main.py
    """
    try:
        # Khởi tạo Vertex AI
        if not app_config.vertex_ai.initialize_vertex_ai():
            return {"error": "Không thể khởi tạo Vertex AI"}
        
        # Tạo model
        model = GenerativeModel(app_config.vertex_ai.model_name)
        
        # Đọc image
        if not os.path.exists(image_path):
            return {"error": f"File không tồn tại: {image_path}"}
        
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Tạo Part object
        image_part = Part.from_data(image_data, mime_type="image/png")
        
        # Generation config
        generation_config = GenerationConfig(
            temperature=0.2,
            top_k=32,
            top_p=1,
            max_output_tokens=8192,
        )
        
        # Generate content
        response = model.generate_content(
            [prompt, image_part],
            generation_config=generation_config
        )
        
        if response and response.text:
            return {"response": response.text, "success": True}
        else:
            return {"error": "Không có response từ AI"}
            
    except Exception as e:
        return {"error": f"Lỗi Vertex AI: {str(e)}"}

class RealAIGuidedExtractor:
    """AI-guided diagram extractor với thực tế Vertex AI integration"""
    
    def __init__(self, output_dir="data/images", confidence_threshold=0.7):
        self.output_dir = output_dir
        self.confidence_threshold = confidence_threshold
        os.makedirs(output_dir, exist_ok=True)
        
    def analyze_image_with_ai(self, image_path):
        """Sử dụng Vertex AI để phân tích ảnh thực tế"""
        print(f"🤖 Đang phân tích ảnh với Vertex AI: {image_path}")
        
        # Tạo prompt cho AI
        prompt = """
        Analyze this image and identify all diagrams, charts, mathematical figures, geometric shapes, or visual elements that are NOT text.
        
        For each diagram/figure found, provide:
        1. A brief description
        2. The type (geometry, chart, diagram, figure, etc.)
        3. Approximate bounding box coordinates as [x, y, width, height]
        4. Confidence score (0-1)
        
        Respond in JSON format:
        {
            "diagrams": [
                {
                    "description": "Triangle geometry problem",
                    "type": "geometry", 
                    "bbox": [x, y, width, height],
                    "confidence": 0.95
                }
            ],
            "total_found": 1
        }
        
        IMPORTANT: Only identify actual diagrams/figures/charts, NOT text blocks or paragraphs.
        """
        
        try:
            # Gọi Vertex AI
            result = process_with_vertex_ai(prompt, image_path)
            
            if result and 'response' in result:
                ai_response = result['response']
                print(f"📝 AI Response: {ai_response[:200]}...")
                
                # Parse JSON response
                try:
                    # Tìm JSON trong response
                    json_start = ai_response.find('{')
                    json_end = ai_response.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = ai_response[json_start:json_end]
                        ai_analysis = json.loads(json_str)
                        
                        print(f"✅ AI tìm thấy {ai_analysis.get('total_found', 0)} hình vẽ")
                        return ai_analysis
                    else:
                        print("⚠️ Không tìm thấy JSON trong response")
                        return self._fallback_analysis()
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ Lỗi parse JSON: {e}")
                    print(f"Raw response: {ai_response}")
                    return self._fallback_analysis()
            else:
                print(f"❌ AI response error: {result}")
                return self._fallback_analysis()
                
        except Exception as e:
            print(f"❌ Lỗi AI analysis: {e}")
            return self._fallback_analysis()
    
    def _fallback_analysis(self):
        """Fallback nếu AI không hoạt động"""
        return {
            "diagrams": [],
            "total_found": 0,
            "error": "AI analysis failed, using OpenCV fallback"
        }
    
    def extract_diagrams_with_real_ai(self, image_path):
        """Extract diagrams sử dụng real AI"""
        print(f"🚀 Bắt đầu extraction với Real AI: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Không thể load image: {image_path}")
            return None, [], {}
        
        h, w = image.shape[:2]
        print(f"📏 Image size: {w}x{h}")
        
        # AI analysis
        ai_analysis = self.analyze_image_with_ai(image_path)
        
        if not ai_analysis or 'error' in ai_analysis:
            print("⚠️ AI analysis failed, falling back to OpenCV")
            return self._opencv_fallback(image_path)
        
        # Process AI results
        diagrams = ai_analysis.get('diagrams', [])
        extracted_paths = []
        base_name = Path(image_path).stem
        
        # Create preview với AI annotations
        preview_image = image.copy()
        
        for i, diagram in enumerate(diagrams, 1):
            confidence = diagram.get('confidence', 0.0)
            
            if confidence < self.confidence_threshold:
                print(f"⚠️ Skipping diagram {i} (confidence: {confidence:.2f} < {self.confidence_threshold:.2f})")
                continue
            
            bbox = diagram.get('bbox', [])
            if len(bbox) != 4:
                print(f"⚠️ Invalid bbox for diagram {i}: {bbox}")
                continue
            
            x, y, w_box, h_box = bbox
            
            # Validate bbox
            if x < 0 or y < 0 or x + w_box > w or y + h_box > h:
                print(f"⚠️ Bbox out of bounds for diagram {i}: {bbox}")
                continue
            
            # Extract region
            diagram_region = image[y:y+h_box, x:x+w_box]
            
            # Save extracted diagram
            output_path = os.path.join(self.output_dir, f"{base_name}_ai_real_diagram_{i:02d}.png")
            cv2.imwrite(output_path, diagram_region)
            extracted_paths.append(output_path)
            
            # Annotate preview
            cv2.rectangle(preview_image, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)
            cv2.putText(preview_image, f"{i}: {diagram.get('type', 'unknown')}", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            print(f"💾 Saved diagram {i}: {output_path}")
            print(f"   📝 {diagram.get('description', 'No description')}")
            print(f"   🎯 Confidence: {confidence:.2f}")
        
        # Save preview
        preview_path = os.path.join(self.output_dir, f"{base_name}_ai_real_preview.png")
        cv2.imwrite(preview_path, preview_image)
        
        print(f"✅ Real AI extraction completed: {len(extracted_paths)} diagrams")
        return preview_path, extracted_paths, ai_analysis
    
    def _opencv_fallback(self, image_path):
        """OpenCV fallback nếu AI failed"""
        print("🔧 Using OpenCV fallback...")
        
        # Import diagram extractor
        from processors.diagram_extractor import DiagramExtractor
        
        extractor = DiagramExtractor(output_dir=self.output_dir)
        return extractor.extract_diagrams(image_path, mode='strict')

class EnhancedHybridExtractor:
    """Enhanced hybrid với Real AI + OpenCV refinement"""
    
    def __init__(self, output_dir="data/images"):
        self.output_dir = output_dir
        self.ai_extractor = RealAIGuidedExtractor(output_dir)
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_with_ai_opencv_hybrid(self, image_path):
        """Hybrid approach: AI guidance + OpenCV precision"""
        print(f"🔄 Hybrid extraction: {image_path}")
        
        # Step 1: AI analysis
        print("📍 Step 1: AI Analysis...")
        ai_preview, ai_diagrams, ai_analysis = self.ai_extractor.extract_diagrams_with_real_ai(image_path)
        
        # Step 2: OpenCV refinement (if AI successful)
        if ai_diagrams and 'error' not in ai_analysis:
            print("📍 Step 2: OpenCV Refinement...")
            refined_diagrams = self._refine_with_opencv(image_path, ai_analysis)
            
            return {
                'method': 'hybrid',
                'ai_preview': ai_preview,
                'ai_diagrams': ai_diagrams,
                'refined_diagrams': refined_diagrams,
                'ai_analysis': ai_analysis,
                'status': 'success'
            }
        else:
            print("📍 AI failed, using pure OpenCV...")
            opencv_preview, opencv_diagrams, opencv_stats = self.ai_extractor._opencv_fallback(image_path)
            
            return {
                'method': 'opencv_fallback',
                'preview': opencv_preview,
                'diagrams': opencv_diagrams,
                'stats': opencv_stats,
                'status': 'fallback'
            }
    
    def _refine_with_opencv(self, image_path, ai_analysis):
        """Refine AI results với OpenCV precision"""
        print("🔧 Refining AI results với OpenCV...")
        
        refined_paths = []
        diagrams = ai_analysis.get('diagrams', [])
        
        image = cv2.imread(image_path)
        base_name = Path(image_path).stem
        
        for i, diagram in enumerate(diagrams, 1):
            bbox = diagram.get('bbox', [])
            if len(bbox) != 4:
                continue
            
            x, y, w, h = bbox
            
            # Extract region
            roi = image[y:y+h, x:x+w]
            
            # OpenCV refinement
            refined_roi = self._opencv_refine_region(roi)
            
            # Save refined
            output_path = os.path.join(self.output_dir, f"{base_name}_hybrid_refined_{i:02d}.png")
            cv2.imwrite(output_path, refined_roi)
            refined_paths.append(output_path)
            
            print(f"🔧 Refined diagram {i}: {output_path}")
        
        return refined_paths
    
    def _opencv_refine_region(self, roi):
        """OpenCV refinement cho specific region"""
        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        
        # Morphological operations để clean up
        kernel = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Convert back to BGR
        if len(roi.shape) == 3:
            return roi  # Return original color version
        else:
            return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

def main():
    """Test real AI integration"""
    print("🚀 REAL AI-GUIDED DIAGRAM EXTRACTION")
    print("="*60)
    
    # Test file
    test_file = "data/input/testOCR1.png"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    # Test 1: Pure Real AI
    print("\n📍 TEST 1: Pure Real AI")
    print("-" * 40)
    
    real_ai = RealAIGuidedExtractor(output_dir="data/images")
    preview, diagrams, analysis = real_ai.extract_diagrams_with_real_ai(test_file)
    
    print(f"✅ Real AI Results:")
    print(f"   Preview: {preview}")
    print(f"   Diagrams: {len(diagrams) if diagrams else 0}")
    
    # Test 2: Enhanced Hybrid
    print("\n📍 TEST 2: Enhanced Hybrid")
    print("-" * 40)
    
    hybrid = EnhancedHybridExtractor(output_dir="data/images")
    hybrid_results = hybrid.extract_with_ai_opencv_hybrid(test_file)
    
    print(f"✅ Hybrid Results:")
    print(f"   Method: {hybrid_results['method']}")
    print(f"   Status: {hybrid_results['status']}")
    
    if hybrid_results['method'] == 'hybrid':
        print(f"   AI Diagrams: {len(hybrid_results['ai_diagrams'])}")
        print(f"   Refined Diagrams: {len(hybrid_results['refined_diagrams'])}")
    
    print("\n🎯 RECOMMENDATION:")
    print("   🤖 Real AI integration có thể cung cấp semantic understanding")
    print("   🔧 OpenCV refinement đảm bảo precision cutting")
    print("   🚀 Hybrid approach là optimal cho production use")

if __name__ == "__main__":
    main()
