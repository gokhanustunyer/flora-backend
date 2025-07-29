#!/usr/bin/env python3
"""
Script to generate a placeholder GNB logo image.
This creates a simple logo with GNB branding colors for testing.
In production, replace with the actual GNB logo file.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_logo():
    """Create a simple placeholder logo for GNB."""
    # Create a 200x100 image with GNB colors (forest green background)
    img = Image.new('RGBA', (200, 100), (34, 139, 34, 255))  # Forest green
    draw = ImageDraw.Draw(img)
    
    # Add a simple "GNB" text in white
    text = "GNB"
    
    try:
        # Try to use a default font
        font = ImageFont.load_default()
        
        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center the text
        x = (200 - text_width) // 2
        y = (100 - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        
    except Exception:
        # Fallback if font loading fails
        draw.text((75, 40), text, fill=(255, 255, 255, 255))
    
    return img

def main():
    """Generate and save the placeholder logo."""
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Generate the placeholder logo
    logo = create_placeholder_logo()
    
    # Save the logo
    logo_path = 'static/gnb_logo.png'
    logo.save(logo_path, 'PNG')
    
    print(f"✅ Placeholder GNB logo created at {logo_path}")
    print("   Replace this with the actual GNB logo in production")

if __name__ == "__main__":
    main() 