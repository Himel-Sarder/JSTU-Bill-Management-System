#!/usr/bin/env python3
"""
Script to download Bengali fonts for WeasyPrint PDF generation
"""
import os
import requests

def download_bengali_fonts():
    """Download Bengali fonts for PDF generation"""
    fonts_dir = os.path.join(os.path.dirname(__file__), 'static', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Font URLs (you may need to update these)
    font_urls = {
        'Kalpurush.ttf': 'https://github.com/fonts-bengali/kalpurush/raw/master/Kalpurush.ttf',
        'SolaimanLipi.ttf': 'https://github.com/0xMamun/bangla-fonts/raw/main/SolaimanLipi.ttf',
    }
    
    downloaded = 0
    
    for font_name, url in font_urls.items():
        font_path = os.path.join(fonts_dir, font_name)
        
        if os.path.exists(font_path):
            print(f"✅ {font_name} already exists")
            downloaded += 1
            continue
            
        try:
            print(f"📥 Downloading {font_name}...")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Successfully downloaded {font_name}")
                downloaded += 1
            else:
                print(f"❌ Failed to download {font_name} (HTTP {response.status_code})")
        except Exception as e:
            print(f"❌ Error downloading {font_name}: {e}")
    
    if downloaded == 0:
        print("\n" + "="*60)
        print("❌ Could not download Bengali fonts automatically.")
        print("="*60)
        print("""
📝 Manual Installation Required:

1. Download Bengali TTF fonts from:
   - Kalpurush: https://www.omicronlab.com/bangla-fonts.html
   - SolaimanLipi: https://www.ekushey.org/?page/fonts

2. Save the font files in:
   📁 static/fonts/Kalpurush.ttf
   📁 static/fonts/SolaimanLipi.ttf

3. The PDF generation will automatically use these fonts.
        """)
    else:
        print(f"\n✅ Successfully downloaded {downloaded}/{len(font_urls)} fonts")

if __name__ == "__main__":
    download_bengali_fonts()