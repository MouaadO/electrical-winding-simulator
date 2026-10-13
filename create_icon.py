"""
Create a professional icon for the Winding Simulator application
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Create multiple sizes for .ico file
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for size in sizes:
        # Create image with transparent background
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background circle - gradient blue
        center = size[0] // 2
        radius = int(size[0] * 0.45)
        
        # Draw circle background
        for i in range(radius, 0, -1):
            alpha = int(255 * (i / radius))
            color_value = int(20 + (100 * (i / radius)))
            draw.ellipse(
                [center - i, center - i, center + i, center + i],
                fill=(30, 144, 255, alpha)  # Dodger blue
            )
        
        # Draw stator-like design
        num_slots = 12
        slot_width = size[0] * 0.02
        inner_radius = radius * 0.4
        outer_radius = radius * 0.9
        
        import math
        for i in range(num_slots):
            angle = (2 * math.pi * i) / num_slots
            
            # Calculate slot positions
            x1 = center + inner_radius * math.cos(angle)
            y1 = center + inner_radius * math.sin(angle)
            x2 = center + outer_radius * math.cos(angle)
            y2 = center + outer_radius * math.sin(angle)
            
            # Draw slot line
            draw.line(
                [(x1, y1), (x2, y2)],
                fill=(255, 255, 255, 230),
                width=max(1, int(slot_width))
            )
        
        # Draw center circle
        center_radius = radius * 0.3
        draw.ellipse(
            [center - center_radius, center - center_radius,
             center + center_radius, center + center_radius],
            fill=(255, 255, 255, 255),
            outline=(30, 144, 255, 255),
            width=max(1, int(size[0] * 0.01))
        )
        
        # Draw sine wave symbol in center (representing AC)
        if size[0] >= 32:
            wave_width = center_radius * 1.5
            wave_height = center_radius * 0.4
            wave_y = center
            points = []
            
            for x in range(int(center - wave_width/2), int(center + wave_width/2), max(1, int(size[0]/64))):
                norm_x = (x - (center - wave_width/2)) / wave_width * 2 * math.pi
                y = wave_y + wave_height * math.sin(norm_x)
                points.append((x, y))
            
            if len(points) > 1:
                draw.line(points, fill=(30, 144, 255, 255), width=max(1, int(size[0] * 0.008)))
        
        images.append(img)
    
    # Save as .ico file
    icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    images[0].save(icon_path, format='ICO', sizes=[img.size for img in images])
    print(f"Icon created successfully: {icon_path}")
    
    # Also save as PNG for preview
    png_path = os.path.join(os.path.dirname(__file__), 'app_icon.png')
    images[0].save(png_path, format='PNG')
    print(f"PNG preview created: {png_path}")

if __name__ == "__main__":
    create_icon()
