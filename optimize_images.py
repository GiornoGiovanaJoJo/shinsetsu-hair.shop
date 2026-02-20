import os
from pathlib import Path
from PIL import Image

def optimize_images_to_webp(directory="templates"):
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Directory {directory} does not exist.")
        return

    print(f"Scanning directory: {dir_path.absolute()}")
    paths = list(dir_path.rglob("*"))
    
    for file_path in paths:
        if file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            webp_path = file_path.with_suffix(".webp")
            if not webp_path.exists():
                try:
                    with Image.open(file_path) as img:
                        # Convert RGBA to RGB if saving as JPEG (WebP supports RGBA but good practice)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGBA")
                        
                        # Save with 85% quality
                        img.save(webp_path, "webp", quality=85)
                    print(f"✅ Optimized: {webp_path.name}")
                except Exception as e:
                    print(f"❌ Error with {file_path.name}: {e}")
            else:
                print(f"⏭️  Already optimized: {webp_path.name}")

if __name__ == "__main__":
    optimize_images_to_webp()
