import struct
import zlib
import math
import os

def create_png(width, height, get_pixel_func):
    """
    Pure Python RGBA PNG Generator.
    get_pixel_func(x, y) returns (r, g, b, a) in 0-255.
    """
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # Filter type 0 (None)
        for x in range(width):
            r, g, b, a = get_pixel_func(x, y)
            raw_data.extend([int(r), int(g), int(b), int(a)])

    compressed = zlib.compress(bytes(raw_data), 9)

    png = bytearray(b'\x89PNG\r\n\x1a\n')

    # IHDR Chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
    png.extend(struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc))

    # IDAT Chunk
    idat_crc = zlib.crc32(b'IDAT' + compressed)
    png.extend(struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc))

    # IEND Chunk
    iend_crc = zlib.crc32(b'IEND')
    png.extend(struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc))

    return bytes(png)


def create_ico(png_buffers):
    """
    Create a valid Windows ICO file containing multiple PNG buffers.
    png_buffers is a list of (width, height, png_bytes).
    """
    num_images = len(png_buffers)
    ico = bytearray(struct.pack('<HHH', 0, 1, num_images))
    
    offset = 6 + (16 * num_images)
    for width, height, data in png_buffers:
        w_byte = width if width < 256 else 0
        h_byte = height if height < 256 else 0
        ico.extend(struct.pack('<BBBBHHII', w_byte, h_byte, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
        
    for _, _, data in png_buffers:
        ico.extend(data)
        
    return bytes(ico)


def render_ozhzo_icon(size, is_dark=False, is_circle=False, has_bg=True, is_z_only=False):
    """
    Renders the exact geometric Ozhzo Verse brand icon with anti-aliasing.
    Colors:
    - Primary Blue: #0061FF (0, 97, 255)
    - Dark Blue: #0A2E7A (10, 46, 122)
    - Primary Green: #00B050 (0, 176, 80)
    - White: #FFFFFF (255, 255, 255)
    - Dark Background: #0A2E7A
    """
    # Supersampling 2x for smooth antialiasing
    scale = 2
    sw = size * scale
    sh = size * scale
    
    # Pre-render supersampled grid
    grid = []
    
    # Colors
    c_blue = (0, 97, 255, 255)
    c_dark_blue = (10, 46, 122, 255)
    c_green = (0, 176, 80, 255)
    c_white = (255, 255, 255, 255)
    c_bg_dark = (10, 46, 122, 255)
    c_bg_light = (255, 255, 255, 255)
    c_transparent = (0, 0, 0, 0)
    
    corner_rad = sw * 0.22 if not is_circle else sw * 0.5
    
    def in_rounded_rect(px, py, w, h, r):
        if px < r and py < r:
            return math.hypot(px - r, py - r) <= r
        if px > w - r and py < r:
            return math.hypot(px - (w - r), py - r) <= r
        if px < r and py > h - r:
            return math.hypot(px - r, py - (h - r)) <= r
        if px > w - r and py > h - r:
            return math.hypot(px - (w - r), py - (h - r)) <= r
        return 0 <= px <= w and 0 <= py <= h

    for sy in range(sh):
        row = []
        ny = sy / sh  # 0.0 to 1.0
        for sx in range(sw):
            nx = sx / sw  # 0.0 to 1.0
            
            # Check background
            if has_bg:
                if is_circle:
                    dist = math.hypot(sx - sw/2, sy - sh/2)
                    if dist > sw * 0.48:
                        row.append(c_transparent)
                        continue
                    bg_color = c_bg_dark if is_dark else c_bg_light
                else:
                    if not in_rounded_rect(sx, sy, sw, sh, corner_rad):
                        row.append(c_transparent)
                        continue
                    bg_color = c_bg_dark if is_dark else c_bg_light
            else:
                bg_color = c_transparent
                
            pixel = bg_color
            
            if is_z_only:
                # Scaled Z mark in center
                zx = (nx - 0.25) / 0.5
                zy = (ny - 0.25) / 0.5
                z_col = c_white if is_dark else c_blue
                if 0 <= zx <= 1 and 0 <= zy <= 1:
                    # Top bar
                    if 0.1 <= zy <= 0.35 and 0.1 <= zx <= 0.9:
                        pixel = z_col
                    # Diagonal
                    diag_dist = abs(zx - (1.0 - zy))
                    if diag_dist < 0.18 and 0.15 <= zy <= 0.85:
                        pixel = z_col
                    # Bottom bar
                    if 0.65 <= zy <= 0.9 and 0.1 <= zx <= 0.9:
                        pixel = z_col
            else:
                # 1. Green Roof
                # Apex at (0.50, 0.22), Left at (0.24, 0.44), Right at (0.76, 0.44)
                roof_apex_y = 0.22
                roof_bottom_y = 0.44
                roof_thickness = 0.08
                
                # Check roof slope
                dx = abs(nx - 0.50)
                expected_y_top = roof_apex_y + dx * 0.85
                expected_y_bottom = expected_y_top + roof_thickness
                
                if 0.20 <= nx <= 0.80 and expected_y_top <= ny <= expected_y_bottom and ny <= roof_bottom_y:
                    pixel = c_green
                    
                # 2. Blue Left Pillar
                if 0.32 <= nx <= 0.40 and 0.42 <= ny <= 0.76:
                    pixel = c_blue
                # 3. Blue Right Pillar
                if 0.60 <= nx <= 0.68 and 0.42 <= ny <= 0.76:
                    pixel = c_blue
                    
                # 4. Stylized Z in center (0.42 to 0.58 x, 0.46 to 0.70 y)
                z_col = c_white if is_dark else c_blue
                if 0.41 <= nx <= 0.59 and 0.46 <= ny <= 0.70:
                    rel_x = (nx - 0.41) / 0.18
                    rel_y = (ny - 0.46) / 0.24
                    
                    # Top bar
                    if 0.0 <= rel_y <= 0.32 and 0.0 <= rel_x <= 1.0:
                        pixel = z_col
                    # Diagonal
                    diag_dist = abs(rel_x - (1.0 - rel_y))
                    if diag_dist < 0.24 and 0.15 <= rel_y <= 0.85:
                        pixel = z_col
                    # Bottom bar
                    if 0.68 <= rel_y <= 1.0 and 0.0 <= rel_x <= 1.0:
                        pixel = z_col

            row.append(pixel)
        grid.append(row)
        
    # Downsample from supersampled grid with averaging
    def get_pixel(x, y):
        r_sum = g_sum = b_sum = a_sum = 0
        for dy in range(scale):
            for dx in range(scale):
                r, g, b, a = grid[y * scale + dy][x * scale + dx]
                r_sum += r * (a / 255.0)
                g_sum += g * (a / 255.0)
                b_sum += b * (a / 255.0)
                a_sum += a
        samples = scale * scale
        avg_a = a_sum / samples
        if avg_a == 0:
            return (0, 0, 0, 0)
        return (
            min(255, int((r_sum / samples) * (255.0 / avg_a))),
            min(255, int((g_sum / samples) * (255.0 / avg_a))),
            min(255, int((b_sum / samples) * (255.0 / avg_a))),
            min(255, int(avg_a))
        )
        
    return create_png(size, size, get_pixel)


def generate_all():
    sizes = [16, 32, 48, 64, 72, 96, 128, 144, 152, 180, 192, 256, 512]
    
    web_brand_dir = "/Users/vivek/ozHzo/ozhzo verse/apps/web/public/brand"
    web_favicon_dir = "/Users/vivek/ozHzo/ozhzo verse/apps/web/public/brand/favicon"
    web_icons_dir = "/Users/vivek/ozHzo/ozhzo verse/apps/web/public/brand/icons"
    web_public_dir = "/Users/vivek/ozHzo/ozhzo verse/apps/web/public"
    mobile_icons_dir = "/Users/vivek/ozHzo/ozhzo verse/apps/mobile/assets/icons"
    mobile_brand_dir = "/Users/vivek/ozHzo/ozhzo verse/apps/mobile/assets/brand"
    
    for d in [web_brand_dir, web_favicon_dir, web_icons_dir, web_public_dir, mobile_icons_dir, mobile_brand_dir]:
        os.makedirs(d, exist_ok=True)
        
    print("Generating Master Primary PNG Icons (White Squircle)...")
    for s in sizes:
        png_data = render_ozhzo_icon(s, is_dark=False, has_bg=True)
        with open(f"{web_icons_dir}/ozhzo-icon-{s}.png", "wb") as f:
            f.write(png_data)
        with open(f"{mobile_icons_dir}/ozhzo-icon-{s}.png", "wb") as f:
            f.write(png_data)
            
    print("Generating Dark PNG Icons (Dark Squircle)...")
    for s in sizes:
        png_data = render_ozhzo_icon(s, is_dark=True, has_bg=True)
        with open(f"{web_icons_dir}/ozhzo-icon-dark-{s}.png", "wb") as f:
            f.write(png_data)
        with open(f"{mobile_icons_dir}/ozhzo-icon-dark-{s}.png", "wb") as f:
            f.write(png_data)

    print("Generating Transparent Emblem PNGs...")
    for s in [128, 192, 256, 512]:
        png_data = render_ozhzo_icon(s, is_dark=False, has_bg=False)
        with open(f"{web_icons_dir}/ozhzo-mark-{s}.png", "wb") as f:
            f.write(png_data)
        with open(f"{mobile_icons_dir}/ozhzo-mark-{s}.png", "wb") as f:
            f.write(png_data)

    # Standard Named Files
    # Favicons (16, 32, 48)
    fav_16 = render_ozhzo_icon(16, is_dark=False, has_bg=True)
    fav_32 = render_ozhzo_icon(32, is_dark=False, has_bg=True)
    fav_48 = render_ozhzo_icon(48, is_dark=False, has_bg=True)
    
    with open(f"{web_favicon_dir}/ozhzo-favicon-16.png", "wb") as f:
        f.write(fav_16)
    with open(f"{web_favicon_dir}/ozhzo-favicon-32.png", "wb") as f:
        f.write(fav_32)
    with open(f"{web_favicon_dir}/ozhzo-favicon-48.png", "wb") as f:
        f.write(fav_48)

    # Generate multi-size favicon.ico
    print("Generating Multi-Resolution favicon.ico (16, 32, 48)...")
    ico_data = create_ico([
        (16, 16, fav_16),
        (32, 32, fav_32),
        (48, 48, fav_48)
    ])
    with open(f"{web_public_dir}/favicon.ico", "wb") as f:
        f.write(ico_data)
    with open(f"{web_favicon_dir}/favicon.ico", "wb") as f:
        f.write(ico_data)

    # PWA Icons (192, 512)
    icon_192 = render_ozhzo_icon(192, is_dark=False, has_bg=True)
    icon_512 = render_ozhzo_icon(512, is_dark=False, has_bg=True)
    with open(f"{web_public_dir}/ozhzo-icon-192.png", "wb") as f:
        f.write(icon_192)
    with open(f"{web_public_dir}/ozhzo-icon-512.png", "wb") as f:
        f.write(icon_512)
    with open(f"{web_icons_dir}/ozhzo-icon-192.png", "wb") as f:
        f.write(icon_192)
    with open(f"{web_icons_dir}/ozhzo-icon-512.png", "wb") as f:
        f.write(icon_512)

    # Apple Touch Icon (180x180)
    apple_180 = render_ozhzo_icon(180, is_dark=False, has_bg=True)
    with open(f"{web_public_dir}/apple-touch-icon.png", "wb") as f:
        f.write(apple_180)
    with open(f"{web_icons_dir}/apple-touch-icon.png", "wb") as f:
        f.write(apple_180)

    # Simplified Z Mark (16 to 512)
    for s in [16, 32, 64, 128, 256, 512]:
        z_data = render_ozhzo_icon(s, is_dark=False, has_bg=True, is_z_only=True)
        with open(f"{web_icons_dir}/ozhzo-mark-z-{s}.png", "wb") as f:
            f.write(z_data)

    print("All Brand Assets & Favicons Generated Successfully (100%).")

if __name__ == "__main__":
    generate_all()
