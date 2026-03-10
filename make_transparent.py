from PIL import Image
import numpy as np

Image.MAX_IMAGE_PIXELS = None

def optimize_logo(img_path):
    print("Opening...")
    img = Image.open(img_path).convert("RGBA")
    data = np.array(img)
    
    print("Making transparent...")
    r, g, b, a = data.T
    white_areas = (r > 240) & (g > 240) & (b > 240)
    data[...][white_areas.T] = (255, 255, 255, 0)
    
    img2 = Image.fromarray(data)
    
    print("Cropping...")
    bbox = img2.getbbox()
    if bbox:
        img2 = img2.crop(bbox)
    
    print("Resizing...")
    max_width = 800
    if img2.width > max_width:
        ratio = max_width / img2.width
        new_size = (max_width, int(img2.height * ratio))
        img2 = img2.resize(new_size, Image.Resampling.LANCZOS)
    
    img2.save(img_path)
    print("Done!")

if __name__ == '__main__':
    optimize_logo('templates/logo.png')
