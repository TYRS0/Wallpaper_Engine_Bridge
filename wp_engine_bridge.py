import os
import re
import time
import subprocess
import requests
import json
import glob
import threading
from PIL import Image, ImageSequence
from apng import APNG

# --- CONFIGURATION ---
# 1. Path to your original static log file
LOG_FILE_PATH = r"C:\Users\thesi\OneDrive\Documents\Tools\Other\CtrlEm\Saved\logs\commands.log"
DOWNLOAD_DIR = r"C:\WallpaperEngineLogDownloads"

# 2. Folder containing your daily changing log text files
DAILY_LOG_FOLDER = r"C:\Users\thesi\OneDrive\Documents\Tools\Other\PlayCtrl.me Client\Saved\logs" 
DAILY_LOG_PATTERN = "*.txt"  # Looks for any text file in that directory

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
    """Resizes and pads an animated GIF or WebP frame-by-frame into a perfectly centered GIF."""
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

            # FIX: Maintain a base frame canvas to build consecutive sub-frames onto
            canvas_frame = Image.new("RGBA", (img_w, img_h))

            for frame in ImageSequence.Iterator(im):
                durations.append(frame.info.get('duration', 100))
                
                # Overlay the partial frame on top of our cumulative image canvas 
                # to reconstruct the full uncropped frame layout
                if frame.mode in ('RGBA', 'LA') or (frame.mode == 'P' and 'transparency' in frame.info):
                    canvas_frame.paste(frame, frame.getbbox() or (0, 0), frame.convert("RGBA"))
                else:
                    canvas_frame.paste(frame, frame.getbbox() or (0, 0))
                
                # Resize the fully reconstructed composite canvas frame
                resized_frame = canvas_frame.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
                
                # Place it onto the final black screen background container
                bg = Image.new("RGBA", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0, 255))
                bg.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                padded_frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))

            if padded_frames:
                padded_frames[0].save(
                    target_path,
                    save_all=True,
                    append_images=padded_frames[1:],
                    optimize=True,
                    duration=durations,
                    loop=loop
                )
                print(f"Animated asset successfully reconstructed and centered to fit display layout.")
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

def pad_static_image(image_path, output_path=None):
    """Pads a static image and ensures it saves safely (supports converting webp to jpg)."""
    try:
        # Determine our final saving path destination
        save_path = output_path if output_path else image_path
        
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
            
            # If our destination target requires a JPEG, drop alpha channels cleanly
            if save_path.lower().endswith(('.jpg', '.jpeg')):
                background = background.convert("RGB")
                background.save(save_path, "JPEG", quality=95)
            else:
                background.save(save_path)
                
            print(f"Static image successfully padded and saved to: {save_path}")
            return True
    except Exception as e:
        print(f"Failed to pad static image: {e}")
        return False

def cleanup_old_wallpapers(current_new_filename):
    """
    Deletes all previously downloaded wallpaper files in the download directory
    except for the brand new file that was just created.
    """
    try:
        # Scan the directory for all files
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            
            # Skip folders and absolutely skip our brand new wallpaper file
            if not os.path.isfile(file_path) or filename == current_new_filename:
                continue
                
            try:
                os.remove(file_path)
                print(f"[Cleanup] Removed old cached wallpaper: {filename}")
            except PermissionError:
                # This happens if Wallpaper Engine still has a lingering lock on the immediate previous file
                # It will safely skip it and catch it on the next wallpaper swap round.
                pass
            except Exception as e:
                print(f"[Cleanup] Could not delete {filename}: {e}")
    except Exception as e:
        print(f"[Cleanup] Directory sweep error: {e}")

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
            
            if ext == '.apng':
                print("APNG detected. Converting to padded GIF format...")
                gif_name = base_filename + ".gif"
                gif_path = os.path.join(DOWNLOAD_DIR, gif_name)
                if convert_apng_to_padded_gif(save_path, gif_path):
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    # Trigger cache purger for old files before launching new one
                    cleanup_old_wallpapers(gif_name)
                    update_wallpaper_engine(gif_path)
                    
            elif ext in ['.gif', '.webp']:
                is_animated = False
                try:
                    with Image.open(save_path) as test_img:
                        if getattr(test_img, "is_animated", False) and test_img.n_frames > 1:
                            is_animated = True
                except Exception:
                    pass

                if is_animated:
                    print(f"Animated format ({ext}) detected. Standardizing layout padding...")
                    gif_name = base_filename + ".gif"
                    gif_path = os.path.join(DOWNLOAD_DIR, gif_name)
                    if pad_animated_image(save_path, gif_path):
                        if ext == '.webp' and os.path.exists(save_path):
                            os.remove(save_path)
                        # Trigger cache purger for old files before launching new one
                        cleanup_old_wallpapers(gif_name)
                        update_wallpaper_engine(gif_path)
                else:
                    print(f"Static {ext.upper()} asset detected. Transcoding to padded JPG container...")
                    jpg_name = base_filename + ".jpg"
                    jpg_path = os.path.join(DOWNLOAD_DIR, jpg_name)
                    
                    if pad_static_image(save_path, output_path=jpg_path):
                        if os.path.exists(save_path):
                            os.remove(save_path)
                        # Trigger cache purger for old files before launching new one
                        cleanup_old_wallpapers(jpg_name)
                        update_wallpaper_engine(jpg_path)
            else:
                print("Static asset (JPG/PNG) detected. Executing flat image fit...")
                if pad_static_image(save_path):
                    # Trigger cache purger for old files before launching new one
                    cleanup_old_wallpapers(base_filename + ext)
                    update_wallpaper_engine(save_path)
    except Exception as e:
        print(f"Error handling download and transformation pipeline: {e}")

# ==================== NEW LOG TRACKING ENGINE ====================

def process_log_line(line):
    """Only extracts and downloads URLs if the line contains a changeWallpaper command."""
    # Ensure the specific command keyword is present in the log line
    if "changewallpaper" in line.lower():
        url_match = re.search(r'(https?://\S+)', line)
        if url_match:
            url = url_match.group(1)
            print(f"[Original Log] Confirmed changeWallpaper target URL: {url}")
            download_image(url)

def monitor_original_log():
    """Background worker tracking your original commands.log file."""
    print(f"[Thread-Original] Starting watch on: {LOG_FILE_PATH}")
    while True:
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(1)
                        continue
                    process_log_line(line)
        else:
            time.sleep(5)

def get_latest_daily_file():
    """Locates the newest modified text file matching the target pattern."""
    search_path = os.path.join(DAILY_LOG_FOLDER, DAILY_LOG_PATTERN)
    files = glob.glob(search_path)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def monitor_daily_dynamic_logs():
    """Background worker monitoring multi-line JSON log strings from the daily files."""
    print(f"[Thread-Daily] Starting folder scan in: {DAILY_LOG_FOLDER}")
    current_file = None
    f = None
    json_buffer = ""
    inside_json = False

    while True:
        latest_file = get_latest_daily_file()
        
        # If a newer file turns up (new day), switch targets seamlessly
        if latest_file and latest_file != current_file:
            print(f"[Thread-Daily] Hot-swapped active track file to: {latest_file}")
            if f:
                f.close()
            current_file = latest_file
            f = open(current_file, "r", encoding="utf-8", errors="ignore")
            f.seek(0, os.SEEK_END)
            json_buffer = ""
            inside_json = False

        if not f:
            time.sleep(5)
            continue

        line = f.readline()
        if not line:
            time.sleep(1)
            continue

        stripped_line = line.strip()

        # Catch header marker: ---- 2026-08-13 ... type=set_wallpaper ----
        if stripped_line.startswith("----") and "type=set_wallpaper" in stripped_line:
            inside_json = True
            json_buffer = ""
            continue

        if inside_json:
            json_buffer += line
            # Look for closing brace ending the JSON payload block
            if stripped_line == "}":
                try:
                    payload = json.loads(json_buffer)
                    if "url" in payload:
                        print(f"[Daily Log] Extracted JSON URL target: {payload['url']}")
                        download_image(payload["url"])
                except json.JSONDecodeError:
                    print(f"[Thread-Daily] Warning: Failed to parse raw log block text:\n{json_buffer}")
                finally:
                    inside_json = False
                    json_buffer = ""

if __name__ == "__main__":
    # Build two isolated background workers
    original_log_thread = threading.Thread(target=monitor_original_log, daemon=True)
    daily_log_thread = threading.Thread(target=monitor_daily_dynamic_logs, daemon=True)

    # Launch threads into async background execution loops
    original_log_thread.start()
    daily_log_thread.start()

    print("=============================================================")
    print(" Dual Wallpaper Engine Bridge actively tracking logs.")
    print(" Monitoring original file AND daily text log folder.")
    print(" Press Ctrl+C to terminate.")
    print("=============================================================")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down bridge smoothly.")
