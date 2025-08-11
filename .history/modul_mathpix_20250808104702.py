import requests 
import base64 
import os 
import json 
import time
from dotenv import load_dotenv

load_dotenv()

app_key = os.getenv('APP_KEY')
app_id = os.getenv('APP_ID')

class ConvertPDf: 
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.base_url = "https://api.mathpix.com/v3/pdf"

    def upload_to_mathpix(self):
        """Gửi PDF đến Mathpix API để convert"""
        try:
            with open(self.pdf_path, "rb") as f:
                print("📤 Đang gửi request đến Mathpix...")

                files = {
                    "file": (os.path.basename(self.pdf_path), f, "application/pdf")
                }

                response = requests.post(
                    self.base_url,
                    headers={
                        "app_id": app_id,
                        "app_key": app_key
                    },
                    files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    print("Gửi thành công!")
                    return result
                else:
                    print(f"Lỗi API: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"Lỗi: {e}")
            return None
        
def send_pdf_to_mathpix(file_path):
    """Gửi PDF đến Mathpix API để convert"""
    try:
        with open(file_path, "rb") as f:
            print("📤 Đang gửi request đến Mathpix...")

            files = {
                "file": (os.path.basename(file_path), f, "application/pdf")
            }

            response = requests.post(
                "https://api.mathpix.com/v3/pdf",
                headers={
                    "app_id": 'companyname_edmicroeducationcompanylimited_taxcode_0108115077_address_5thfloor_tayhabuilding_no_19tohuustreet_trungvanward_namtuliemdistrict_hanoicity_vietnam_d72a10_0d24ba',
                    "app_key": 'b39568046dd9cf1ca3bddca9ee7d25cb509df41b091c60f077d699011dcc9ec3'
                },
                files=files
                # data={"conversion_formats[docx]": "true"}
            )

            if response.status_code == 200:
                result = response.json()
                print("✅ Gửi thành công!")
                print(result)
                return result
            else:
                print(f"❌ Lỗi API: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return None

def check_conversion_status(pdf_id):
    """Kiểm tra trạng thái conversion"""
    headers = {'app_key': 'b39568046dd9cf1ca3bddca9ee7d25cb509df41b091c60f077d699011dcc9ec3', 'app_id': 'companyname_edmicroeducationcompanylimited_taxcode_0108115077_address_5thfloor_tayhabuilding_no_19tohuustreet_trungvanward_namtuliemdistrict_hanoicity_vietnam_d72a10_0d24ba'}
    
    try:
        url = f"https://api.mathpix.com/v3/pdf/{pdf_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"❌ Lỗi check status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Lỗi check status: {e}")
        return None

def download_docx(pdf_id, output_path):
    """Download file DOCX đã convert"""
    headers = {'app_key': app_key, 'app_id': app_id}
    print(pdf_id)
    time.sleep(15)
    try:
        url = f"https://api.mathpix.com/v3/pdf/{pdf_id}.docx"
        response = requests.get(url, headers=headers)
        # print(response.json())
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        with open(output_path, 'wb') as f:
            f.write(response.content)
            print(f"✅ Downloaded: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Lỗi download: {str(e)}")
        return None

def convert_pdf_to_docx(pdf_path, output_path=None):
    """Convert PDF to DOCX"""
    print("🎯 Bắt đầu convert PDF to DOCX")
    
    if not os.path.exists(pdf_path):
        print(f"❌ File không tồn tại: {pdf_path}")
        return None
    
    # Gửi PDF
    result = send_pdf_to_mathpix(pdf_path)
    if not result:
        return None
    
    pdf_id = result.get('pdf_id')
    # pdf_id = "2025_06_26_d7ac6f92205324b78fd9g"
    if not pdf_id:
        print("❌ Không nhận được pdf_id")
        return None
    
    print(f"📋 PDF ID: {pdf_id}")
    
    # Đợi 15 giây để server cập nhật
    print("⏳ Đợi 15 giây để server cập nhật PDF ID...")
    time.sleep(15)
    print("✅ Hoàn thành delay, bắt đầu check status...")
    
    # Chờ conversion
    # if not wait_for_conversion(pdf_id):
    #     return None
    
    # Tạo output path
    if not output_path:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.dirname(os.path.dirname(pdf_path)) + f"/output/{pdf_name}_converted.docx"

    # Download
    downloaded_file = download_docx(pdf_id, output_path)
    
    if downloaded_file:
        print(f"🎉 Hoàn thành! File DOCX: {downloaded_file}")
        return downloaded_file
    else:
        return None

# THỰC HIỆN CONVERT NGAY
if __name__ == "__main__": 
    # Đặt đường dẫn PDF của bạn ở đây
    pdf_folder = r"C:\Users\Admin\Desktop\Maru\ExtractImages\SeperateImage\PDF"
    print(f"🔑 App ID: {app_id[:10]}..." if app_id else "❌ APP_ID not found")
    print(f"🔑 App Key: {app_key[:10]}..." if app_key else "❌ APP_KEY not found")
    print()
    
    # CONVERT NGAY
    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, filename)
            print(f"📄 Đang convert: {pdf_path}")
            result = convert_pdf_to_docx(pdf_path)
            if result:
                print(f"✅ File đã convert: {result}")
            else:
                print("❌ Không thể convert file")
    if result:
        print(f"\n✅ SUCCESS! File đã convert: {result}")
    else:
        print(f"\n❌ FAILED! Không thể convert file")