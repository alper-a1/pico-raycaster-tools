# @file texture_generator.py
# @brief Generates raw texture data header for pico-raycaster
# This script creates a C++ header file containing textures
# @author Alper Alpcan

import math 
import struct
import json
import numpy as np
from numpy.typing import NDArray

# XIP
GENERATOR_VERSION = 100001 # version 1.0.01
XIP_MAGIC = b'XIP0'
XIP_MAGIC_BYTES = 0x30504958

# Constants
TEX_PX_SIZE = 64
SHADED_VARIANT_INTENSITY = 0.55

# ========================================================
# Generation Helper Functions
# ========================================================

def to_rgb565(r, g, b) -> np.uint16:
    """
    Converts RGB to 16-bit RGB565
    """
    # Clamp
    r = np.uint16(np.clip(r, 0, 255))
    g = np.uint16(np.clip(g, 0, 255))
    b = np.uint16(np.clip(b, 0, 255))
    
    # 1. Standard RGB565 (Little Endian on x86)
    # R: 5 bits, G: 6 bits, B: 5 bits
    val = np.uint16(((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3))
    
    return val

def get_representitive_color_rgb(pixel_data: NDArray[np.uint16]) -> np.uint16:
    """
    Calculate the representitive color (average) of a texture
    
    @param pixel_data: numpy array of uint16 RGB565 pixels
    @return: uint16 RGB565 average color
    """
    
    r5 = (pixel_data >> 11) & 0x1F
    g6 = (pixel_data >> 5)  & 0x3F
    b5 =  pixel_data        & 0x1F

    r5_avg = np.uint16(np.round(np.mean(r5)))
    g6_avg = np.uint16(np.round(np.mean(g6)))
    b5_avg = np.uint16(np.round(np.mean(b5)))

    # Clamp in case of floating rounding precision
    r5_avg = np.clip(r5_avg, 0, 31)
    g6_avg = np.clip(g6_avg, 0, 63)
    b5_avg = np.clip(b5_avg, 0, 31)

    return np.uint16((r5_avg << 11) | (g6_avg << 5) | b5_avg)

def create_shaded_variant(pixel_data):
    """
    Takes a list of RGB565 pixels, unpacks them, 
    darkens them, and returns a new list.
    """
    dark_pixels = []
    
    for val in pixel_data:
        # 1. Extract channels (Masks: R=0xF800, G=0x07E0, B=0x001F)
        r = (val >> 11) & 0x1F
        g = (val >> 5)  & 0x3F
        b = (val)       & 0x1F
        
        # 2. Darken (multiply by intensity)
        r = int(r * SHADED_VARIANT_INTENSITY)
        g = int(g * SHADED_VARIANT_INTENSITY)
        b = int(b * SHADED_VARIANT_INTENSITY)
        
        # # 3. Repack
        new_val = (r << 11) | (g << 5) | b
        
        dark_pixels.append(new_val)
        
    return dark_pixels
    


# ========================================================
# Texture Generation Functions (temporary)
# ========================================================

def get_xor_pixel(x, y):
    val = (x ^ y)
    return to_rgb565(val * 4, val * 2, val * 4)

def get_gradient_pixel(x, y):
    # Vertical gradient logic
    r = int((y / TEX_PX_SIZE) * 255)
    g = int((x / TEX_PX_SIZE) * 50) # Slight horizontal tint
    b = int(((TEX_PX_SIZE - y) / TEX_PX_SIZE) * 255)
    return to_rgb565(r, g, b)

def get_checkers_pixel(x, y):
    size = 8
    if ((x // size) % 2) ^ ((y // size) % 2):
        return to_rgb565(200, 200, 200) # Light
    else:
        return to_rgb565(50, 50, 50)    # Dark

def get_bricks_pixel(x, y):
    brick_w, brick_h = 16, 16
    mortar = 1
    
    # Calculate row to determine offset
    row = y // brick_h
    x_offset = (brick_w // 2) if (row % 2) else 0
    
    tx = (x + x_offset) % brick_w
    ty = y % brick_h
    
    if tx < mortar or ty < mortar:
        return to_rgb565(80, 80, 80) # Grey mortar
    else:
        # Pseudo-random noise based on coords (deterministic)
        noise = ((x * y * 57) % 30) - 15
        return to_rgb565(160 + noise, 50 + noise, 40 + noise)


def get_stone_bricks_pixel(x, y):
    """Irregular grey stone bricks with noise."""
    block_w, block_h = 32, 16
    mortar = 2
    
    # Calculate row for offset
    row = y // block_h
    # Offset every odd row by half width
    off = (block_w // 2) if (row % 2) else 0
    
    tx = (x + off) % block_w
    ty = y % block_h
    
    # Mortar lines
    if tx < mortar or ty < mortar:
        return to_rgb565(20, 20, 20) # Very dark grey
    
    # Internal stone texture (heavy noise)
    noise = ((x * 13 ^ y * 29) % 50) - 25
    
    # Base grey + noise
    r = 100 + noise
    g = 100 + noise
    b = 110 + noise
    return to_rgb565(r, g, b)

def get_symbol_wall_pixel(x, y):
    """A wall with a glowing red runic eye in the center."""
    # Center coordinates
    cx, cy = 32, 32
    
    # Distance from center
    dx = x - cx
    dy = y - cy
    dist_sq = dx*dx + dy*dy
    dist = math.sqrt(dist_sq)
    
    # 1. The Pupil (Vertical Slit)
    if dist < 12 and abs(dx) < 3:
        return to_rgb565(0, 0, 0) # Black
        
    # 2. The Iris (Glowing Red)
    if dist < 12:
        # Gradient based on distance for glowing effect
        glow = int(255 - (dist * 10))
        return to_rgb565(glow, 20, 20)
        
    # 3. The Gold Ring
    if 12 <= dist < 16:
        return to_rgb565(200, 180, 50)
        
    # 4. The Background Wall (Dark Brick pattern)
    if ((x // 16) + (y // 16)) % 2 == 0:
         return to_rgb565(60, 60, 65)
    else:
         return to_rgb565(50, 50, 55)

def get_wood_pixel(x, y):
    """Vertical wood planks with knots."""
    plank_width = 16
    
    # Plank separator
    if x % plank_width == 0:
        return to_rgb565(20, 10, 5) # Dark gap
        
    # Wood Grain logic
    # Sine wave distortion for grain look
    grain_offset = math.sin(y * 0.1) * 5
    val = (x + grain_offset) * 5
    
    # Add a "knot" in the wood occasionally
    if ((x//plank_width) % 2 == 0) and (20 < y < 30):
        # Simple darken area
        dx = (x % plank_width) - 8
        dy = y - 25
        if (dx*dx + dy*dy) < 20:
            val += 50 # Darker (logic inverted below)

    # Base brown color modulation
    intensity = (val % 40)
    
    r = 120 + intensity
    g = 80 + intensity
    b = 40 + (intensity // 2)
    
    return to_rgb565(r, g, b)

def get_vent_pixel(x, y):
    """Sci-fi style metal vent."""
    # Frame border
    if x < 2 or x > 61 or y < 2 or y > 61:
        return to_rgb565(150, 150, 160) # Light metal
        
    # Horizontal Slats
    slat_h = 8
    local_y = (y - 2) % slat_h
    
    if local_y < 2:
        return to_rgb565(20, 20, 25) # Dark gap/shadow
    elif local_y == 2:
        return to_rgb565(60, 60, 70) # Slat edge (shaded)
    else:
        # Gradient on the slat itself
        c = 100 + (local_y * 10)
        return to_rgb565(c, c, c+10)

# ========================================================
# Texture Generation & Output
# ========================================================

def generate_texture_data(func):
    """
    Generates pixel data in COLUMN MAJOR order.
    Outer Loop: X (Columns)
    Inner Loop: Y (Rows)
    """
    data = []
    for x in range(TEX_PX_SIZE):      # Column
        for y in range(TEX_PX_SIZE): # Row
            data.append(func(x, y))
    return data

def write_to_xip_file(textures, filename):
    tex_count = len(textures)
    
    # layout:
    # uint32 Magic 
    # uint32 Version 
    # uint32 Texture Count
    # uint32 Reserved (0)
    # uint32 Offsets[Texture Count]
    header_size = 4 + 4 + 4 + 4 + tex_count * 4 
    
    offsets = []
    
    with open("assets/" + filename, "wb") as f:
        f.write(b'\00' * header_size)  # Placeholder for header
        
        for _, tex_data in textures:
            offsets.append(f.tell())
            
            # big endian uint16 packing (generated data is little endian)
            packed = struct.pack(">" + "H"*len(tex_data), *tex_data)
            
            f.write(packed)
    
        # Go back and write header 
        f.seek(0)
        
        # magic 'XIP0'
        f.write(XIP_MAGIC)
        
        # version uint32
        f.write(struct.pack("<I", GENERATOR_VERSION))
        
        # texture count uint32
        f.write(struct.pack("<I", tex_count))
        
        # reserved uint32
        f.write(struct.pack("<I", 0))
        
        # offsets uint32[tex_count]
        for offset in offsets:
            f.write(struct.pack("<I", offset))

def write_to_json_file(textures, filename):
    textures_list = []
    
    # Populate list
    for i, (name, pixel_data) in enumerate(textures):
        representitive_color = get_representitive_color_rgb(np.array(pixel_data, dtype=np.uint16))
        
        textures_list.append({
            "id": i,
            "name": name,
            "rcolor": hex(representitive_color)
        })
        
    # Final dict
    textures_dict = {
        "version": GENERATOR_VERSION,
        "texture_count": len(textures_list),
        "textures": textures_list
    }
        
    with open("assets/" + filename, "w") as f:
        json.dump(textures_dict, f, indent=4)


def main():
    # Define textures names and their generation functions
    textures = [
        ("tex_xor", get_xor_pixel),
        ("tex_gradient", get_gradient_pixel),
        ("tex_checkers", get_checkers_pixel),
        ("tex_bricks", get_bricks_pixel),
        ("tex_stone_bricks", get_stone_bricks_pixel),
        ("tex_symbol_wall", get_symbol_wall_pixel),
        ("tex_wood", get_wood_pixel),
        ("tex_vent", get_vent_pixel),
    ]
    
    textures_data = []
    for name, func in textures:
        pixels = generate_texture_data(func)
        textures_data.append( (name, pixels) )
        
        shaded_pixels = create_shaded_variant(pixels)
        shaded_name = f"{name}_shaded"
        textures_data.append( (shaded_name, shaded_pixels) )
    
    
    write_to_xip_file(textures_data, "textures.xip")
    
    write_to_json_file(textures_data, "textures.json")
    
    print("Texture generation complete. Binary written to assets/textures.xip, metadata to assets/textures.json")
    
        
if __name__ == "__main__":
    main()