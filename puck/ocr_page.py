"""
用OCR读取页面内容
"""
import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import pytesseract
    from PIL import Image
    
    img = Image.open('C:\\tower-of-babel\\puck\\current_page.png')
    # 缩小图片加速OCR
    img = img.resize((1920, 1080))
    
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
    print("OCR结果:")
    print(text[:2000])
except ImportError as e:
    print(f"OCR不可用: {e}")
    print("尝试用飞书OCR...")
