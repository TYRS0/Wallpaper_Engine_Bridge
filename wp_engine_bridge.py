import os
import re
import time
import subprocess
import requests
from PIL import Image, ImageSequence
from apng import APNG

# --- CONFIGURATION ---
LOG_FILE_PATH = r"C:\Users\thesi\OneDrive\Documents\Tools\Other\CtrlEm\Saved\logs\commands.log"  # Path to your log file
DOWNLOAD_DIR = r"C:\WallpaperEngineLogDownloads"  # Where downloaded images will save

# Path to your Wallpaper Engine executable
WE_EXE_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\wallpaper64.exe"
# ---------------------

# --- ADD YOUR MONITOR RESOLUTION HERE ---
MONITOR_WIDTH = 2560
MONITOR_HEIGHT = 1440
# ---------------------

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def update_wallpaper_engine(image_path):
    """Tells Wallpaper Engine to immediately apply the file via CLI."""
    if not os.path.exists(WE_EXE_PATH):
        print(f"Error: wallpaper64.exe not found at {WE_EXE_PATH}")
        return

    command = [
        WE_EXE_PATH,
        "-control", "openWallpaper",
        "-file", image_path
    ]
    
    try:
        subprocess.run(command, check=True)
        print("Wallpaper Engine updated successfully.")
    except Exception as e:
        print(f"Failed to communicate with Wallpaper Engine: {e}")

def detect_extension(response):
    """Detects the real file extension from headers or magic bytes."""
    content_type = response.headers.get('Content-Type', '').lower()
    if 'image/gif' in content_type:
        return '.gif'
    if 'image/webp' in content_type:
        return '.webp'
    if 'image/png' in content_type:
        if b'acTL' in response.content[:1000]:
            return '.apng'
        return '.png'
    if 'image/jpeg' in content_type or 'image/jpg' in content_type:
        return '.jpg'
    
    # Fallback to magic bytes check
    head = response.content[:12]
    if head.startswith(b'GIF8'):
        return '.gif'
    if head.startswith(b'\x89PNG'):
        if b'acTL' in response.content[:1000]:
            return '.apng'
        return '.png'
    if b'RIFF' in head and b'WEBP' in head:
        return '.webp'
    
    return '.jpg'

def pad_animated_image(img_path, output_gif_path=None):
    """Resizes and pads an animated GIF or WebP frame-by-frame into a perfectly fitting GIF."""
    try:
        target_path = output_gif_path if output_gif_path else img_path
        with Image.open(img_path) as im:
            monitor_ratio = MONITOR_WIDTH / MONITOR_HEIGHT
            img_w, img_h = im.size
            img_ratio = img_w / img_h

            if img_ratio > monitor_ratio:
                new_w = MONITOR_WIDTH
                new_h = int(MONITOR_WIDTH / img_ratio)
            else:
                new_h = MONITOR_HEIGHT
                new_w = int(MONITOR_HEIGHT * img_ratio)

            paste_x = (MONITOR_WIDTH - new_w) // 2
            paste_y = (MONITOR_HEIGHT - new_h) // 2

            loop = im.info.get('loop', 0)
            padded_frames = []
            durations = []

            for frame in ImageSequence.Iterator(im):
                durations.append(frame.info.get('duration', 100))
                
                # Convert frame to RGBA to properly resize and overlay
                resized_frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
                bg = Image.new("RGBA", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0, 255))
                bg.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                # Quantize frame back to Palette mode for optimal GIF encoding compatibility
                padded_frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))

            if padded_frames:
                # FIX: Call .save() on the FIRST frame object, passing the rest via append_images
                padded_frames[0].save(
                    target_path,
                    save_all=True,
                    append_images=padded_frames[1:],
                    optimize=True,
                    duration=durations,
                    loop=loop
                )
                print(f"Animated asset successfully converted and padded to fit display layout.")
                return True
    except Exception as e:
        print(f"Failed to pad animated file: {e}")
    return False

def convert_apng_to_padded_gif(apng_path, gif_path):
    """Converts an APNG to a standard padded GIF in one pass using pure Python."""
    try:
        im = APNG.open(apng_path)
        frames = []
        
        with open("temp_size.png", "wb") as f:
            im.frames.save(f)
        with Image.open("temp_size.png") as first_img:
            img_w, img_h = first_img.size
        if os.path.exists("temp_size.png"):
            os.remove("temp_size.png")

        monitor_ratio = MONITOR_WIDTH / MONITOR_HEIGHT
        img_ratio = img_w / img_h

        if img_ratio > monitor_ratio:
            new_w = MONITOR_WIDTH
            new_h = int(MONITOR_WIDTH / img_ratio)
        else:
            new_h = MONITOR_HEIGHT
            new_w = int(MONITOR_HEIGHT * img_ratio)

        paste_x = (MONITOR_WIDTH - new_w) // 2
        paste_y = (MONITOR_HEIGHT - new_h) // 2

        for png_frame, control in im.frames:
            with open("temp_frame.png", "wb") as f:
                png_frame.save(f)
            
            frame_img = Image.open("temp_frame.png")
            resized_frame = frame_img.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
            
            bg = Image.new("RGBA", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0, 255))
            bg.paste(resized_frame, (paste_x, paste_y), resized_frame)
            frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))
            
        if frames:
            frames.save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=[c.delay for _, c in im.frames],
                loop=0
            )
            
        if os.path.exists("temp_frame.png"):
            os.remove("temp_frame.png")
        return True
    except Exception as e:
        print(f"APNG to padded GIF conversion failed: {e}")
        if os.path.exists("temp_frame.png"):
            os.remove("temp_frame.png")
        return False

def pad_static_image(image_path):
    """Pads a static image (JPG/PNG/Static WebP) with black bars to match screen proportions."""
    try:
        with Image.open(image_path) as img:
            img_ratio = img.width / img.height
            monitor_ratio = MONITOR_WIDTH / MONITOR_HEIGHT
            
            if img_ratio > monitor_ratio:
                new_w = MONITOR_WIDTH
                new_h = int(MONITOR_WIDTH / img_ratio)
            else:
                new_h = MONITOR_HEIGHT
                new_w = int(MONITOR_HEIGHT * img_ratio)
                
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            background = Image.new("RGB", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0))
            
            paste_x = (MONITOR_WIDTH - new_w) // 2
            paste_y = (MONITOR_HEIGHT - new_h) // 2
            background.paste(resized_img, (paste_x, paste_y))
            background.save(image_path, "JPEG")
            print("Static image successfully padded to fit screen boundaries.")
    except Exception as e:
        print(f"Failed to pad static image: {e}")

def download_image(url):
    """Downloads the file and enforces uniform padding sizing rules across all formats."""
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            ext = detect_extension(response)
            base_filename = f"wallpaper_{int(time.time())}"
            save_path = os.path.join(DOWNLOAD_DIR, base_filename + ext)
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            # Context branch routing for structural conversion processing
            if ext == '.apng':
                print("APNG detected. Converting to padded GIF format...")
                gif_path = os.path.join(DOWNLOAD_DIR, base_filename + ".gif")
                if convert_apng_to_padded_gif(save_path, gif_path):
                    os.remove(save_path)
                    return gif_path
                return save_path

            elif ext == '.gif':
                print("GIF detected. Scaling animation canvas layout data...")
                pad_animated_image(save_path)
                return save_path

            elif ext == '.webp':
                print("WebP file detected. Checking animation markers...")
                # Inspect file to determine if WebP is animated
                is_animated = False
                try:
                    with Image.open(save_path) as check_img:
                        is_animated = getattr(check_img, "is_animated", False)
                except Exception:
                    pass

                if is_animated:
                    print("Animated WebP found. Rewriting canvas sequence to padded GIF...")
                    gif_path = os.path.join(DOWNLOAD_DIR, base_filename + ".gif")
                    if pad_animated_image(save_path, gif_path):
                        os.remove(save_path)
                        return gif_path
                    return save_path
                else:
                    print("Static WebP found. Applying standard margin layout constraints...")
                    pad_static_image(save_path)
                    return save_path

            else:
                print("Static graphic file detected (JPG/PNG). Sizing canvas layout boundaries...")
                pad_static_image(save_path)
                return save_path
                
        print(f"Failed to download. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading: {e}")
    return None

def parse_line(line):
    """Extracts the URL from the log string structure."""
    pattern = r"\[\d+\]\s+changeWallpaper\s+(https?://\S+)"
    match = re.search(pattern, line)
    if match:
        return match.group(1)
    return None

def watch_log_file():
    """Tails the log file continuously for new commands."""
    if not os.path.exists(LOG_FILE_PATH):
        print(f"Waiting for log file to be created at: {LOG_FILE_PATH}")
        while not os.path.exists(LOG_FILE_PATH):
            time.sleep(1)

    print(f"Monitoring log file for fully letterboxed layouts: {LOG_FILE_PATH}")
    
    with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
                
            url = parse_line(line)
            if url:
                print(f"Command detected! Fetching asset: {url}")
                local_asset = download_image(url)
                if local_asset:
                    update_wallpaper_engine(local_asset)

if __name__ == "__main__":
    watch_log_file()