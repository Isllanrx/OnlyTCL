"""
Generates Android TV Leanback Banner for Claude TV
Dimensions: 320x180 (16:9) standard Leanback Banner and 640x360 for high-density TV displays.
"""
from PIL import Image, ImageDraw, ImageFont
import math, os

def create_banner(width, height, out_path):
    img = Image.new('RGBA', (width, height), (26, 24, 23, 255))
    draw = ImageDraw.Draw(img)
    
    # Subtle gradient background
    for y in range(height):
        alpha = int(255 * (1 - 0.15 * (y / height)))
        draw.line([(0, y), (width, y)], fill=(32, 28, 26, 255))
    
    # Subtle accent glow on the left
    for r in range(120, 0, -5):
        glow_alpha = int(35 * (1 - r/120))
        draw.ellipse([80 - r, height//2 - r, 80 + r, height//2 + r], fill=(217, 119, 87, glow_alpha))
        
    # Draw Claude Starburst symbol on the left
    cx, cy = int(width * 0.22), height // 2
    r_outer = int(height * 0.35)
    r_inner = int(height * 0.12)
    star_color = (217, 119, 87, 255) # Anthropic Terracotta
    
    points = []
    num_rays = 12
    for i in range(num_rays * 2):
        angle = i * math.pi / num_rays
        r = r_outer if i % 2 == 0 else r_inner
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=star_color)
    
    # Text fonts
    try:
        font_large = ImageFont.truetype('arial.ttf', int(height * 0.30))
        font_sub = ImageFont.truetype('arial.ttf', int(height * 0.12))
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    text_x = int(width * 0.44)
    text_y = int(height * 0.22)
    draw.text((text_x, text_y), 'Claude', fill=(255, 255, 255, 255), font=font_large)
    draw.text((text_x + int(width * 0.36), text_y + int(height * 0.02)), 'TV', fill=(217, 119, 87, 255), font=font_large)
    draw.text((text_x, text_y + int(height * 0.38)), 'AI Assistant • Android TV', fill=(180, 175, 170, 255), font=font_sub)
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, 'PNG')
    print('Banner created at:', out_path)

if __name__ == '__main__':
    create_banner(320, 180, 'banner_320x180.png')
    create_banner(640, 360, 'banner_640x360.png')
