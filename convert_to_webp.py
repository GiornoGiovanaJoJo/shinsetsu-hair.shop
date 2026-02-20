import os
from pathlib import Path
from PIL import Image

# Directories that contain images
IMAGE_DIRS = ['templates', 'uploads']

def bulk_convert_to_webp(directory_path, quality=85):
    path = Path(directory_path)
    count = 0
    saved_bytes = 0

    if not path.exists():
        print(f"Directory {directory_path} does not exist.")
        return

    print(f"[*] Инициализация сканирования директории: {directory_path}")
    
    for image_path in path.rglob('*'):
        if image_path.is_file() and image_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            try:
                img = Image.open(image_path)
                
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                webp_path = image_path.with_suffix('.webp')
                
                # Check for existing
                if webp_path.exists():
                    continue

                original_size = os.path.getsize(image_path)
                
                img.save(webp_path, 'webp', quality=quality)
                new_size = os.path.getsize(webp_path)
                
                diff = original_size - new_size
                saved_bytes += diff
                count += 1
                
                print(f"[+] Успешно: {image_path.name} -> {webp_path.name} | Сжали на {diff/1024:.2f} KB")
                
            except Exception as e:
                print(f"[-] Ошибка во время обработки {image_path.name}: {str(e)}")

    print(f"✅ Готово для {directory_path}! Конвертировано: {count}. Экономия: {saved_bytes / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    for d in IMAGE_DIRS:
        bulk_convert_to_webp(d)
