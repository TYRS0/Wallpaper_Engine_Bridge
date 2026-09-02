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

# --- CTRLEM & PLAYCTRL WORKSPACE CONFIGURATION ---
CTRLEM_LOG_PATH = r"C:\Users\thesi\OneDrive\Documents\Tools\Other\CtrlEm\Saved\logs\commands.log"
PLAYCTRL_LOG_FOLDER = r"C:\Users\thesi\OneDrive\Documents\Tools\Other\PlayCtrl.me Client\Saved\logs" 
PLAYCTRL_LOG_PATTERN = "*.txt"

WALLPAPER_WORKSPACE_DIR = r"C:\WallpaperEngineLogDownloads"
WE_EXE_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\wallpaper64.exe"

MONITOR_WIDTH = 2560
MONITOR_HEIGHT = 1440
# -------------------------------------------------

if not os.path.exists(WALLPAPER_WORKSPACE_DIR):
    os.makedirs(WALLPAPER_WORKSPACE_DIR)

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
        print(f"Wallpaper Engine updated successfully: {os.path.basename(image_path)}")
    except Exception as e:
        print(f"Failed to communicate with Wallpaper Engine: {e}")

def pad_static_image(image_path, output_path=None):
    """Pads a static image and ensures it saves safely without decimal crop issues."""
    try:
        save_path = output_path if output_path else image_path
        
        with Image.open(image_path) as img:
            # SHORT-CIRCUIT: If it matches 1440p perfectly, skip math to prevent rounding crops
            if img.width == MONITOR_WIDTH and img.height == MONITOR_HEIGHT:
                print("Static image matches resolution perfectly. Bypassing processing math...")
                if save_path.lower().endswith(('.jpg', '.jpeg')):
                    img.convert("RGB").save(save_path, "JPEG", quality=95)
                else:
                    img.save(save_path)
                return True

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
            
            if save_path.lower().endswith(('.jpg', '.jpeg')):
                background = background.convert("RGB")
                background.save(save_path, "JPEG", quality=95)
            else:
                background.save(save_path)
                
            print(f"Static image successfully padded: {save_path}")
            return True
    except Exception as e:
        print(f"Failed to pad static image: {e}")
        return False

def pad_animated_image(img_path, output_gif_path=None):
    """Resizes and pads an animated GIF/WebP frame-by-frame without decimal precision drifting."""
    try:
        target_path = output_gif_path if output_gif_path else img_path
        with Image.open(img_path) as im:
            img_w, img_h = im.size

            # SHORT-CIRCUIT: Skip canvas manipulation if sizes perfectly match layout bounds
            if img_w == MONITOR_WIDTH and img_h == MONITOR_HEIGHT:
                print("Animated asset matches resolution perfectly. Bypassing processing math...")
                loop = im.info.get('loop', 0)
                durations = []
                frames = []
                for frame in ImageSequence.Iterator(im):
                    durations.append(frame.info.get('duration', 100))
                    frames.append(frame.copy().convert("P", palette=Image.Palette.ADAPTIVE))
                
                if frames:
                    frames[0].save(
                        target_path,
                        save_all=True,
                        append_images=frames[1:],
                        optimize=True,
                        duration=durations,
                        loop=loop
                    )
                return True

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

            loop = im.info.get('loop', 0)
            padded_frames = []
            durations = []
            canvas_frame = Image.new("RGBA", (img_w, img_h))

            for frame in ImageSequence.Iterator(im):
                durations.append(frame.info.get('duration', 100))
                
                if frame.mode in ('RGBA', 'LA') or (frame.mode == 'P' and 'transparency' in frame.info):
                    canvas_frame.paste(frame, frame.getbbox() or (0, 0), frame.convert("RGBA"))
                else:
                    canvas_frame.paste(frame, frame.getbbox() or (0, 0))
                
                resized_frame = canvas_frame.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
                
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
                print("Animated asset successfully padded.")
                return True
    except Exception as e:
        print(f"Failed to pad animated file: {e}")
    return False

def convert_apng_to_padded_gif(apng_path, gif_path):
    """Converts a PlayCtrl or CtrlEm APNG file into a standard padded GIF container."""
    try:
        im = APNG.open(apng_path)
        frames = []
        
        with open("temp_size.png", "wb") as f:
            im.frames.save(f)
        with Image.open("temp_size.png") as first_img:
            img_w, img_h = first_img.size
        if os.path.exists("temp_size.png"):
            os.remove("temp_size.png")

        # SHORT-CIRCUIT: Bypass padding mechanics if dimensions perfectly map to target resolution
        if img_w == MONITOR_WIDTH and img_h == MONITOR_HEIGHT:
            print("APNG matches resolution perfectly. Flat transcode converting...")
            for png_frame, control in im.frames:
                with open("temp_frame.png", "wb") as f:
                    png_frame.save(f)
                frame_img = Image.open("temp_frame.png")
                frames.append(frame_img.convert("P", palette=Image.Palette.ADAPTIVE))
        else:
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

def cleanup_workspace_wallpapers(active_filename):
    """Deletes old files in the scratch folder while preserving the live desktop background asset."""
    try:
        for filename in os.listdir(WALLPAPER_WORKSPACE_DIR):
            file_path = os.path.join(WALLPAPER_WORKSPACE_DIR, filename)
            if not os.path.isfile(file_path) or filename == active_filename:
                continue
            try:
                os.remove(file_path)
            except PermissionError:
                # Occurs if Wallpaper Engine locks the file during hot-swaps
                pass 
    except Exception as e:
        print(f"[Cleanup] Directory sweep error: {e}")

def download_and_route_asset(url):
    """Downloads files via curl and inspects image data to preserve hidden frame animations."""
    try:
        # Initial guess from URL text
        clean_url = url.split('?')[0].lower()
        if clean_url.endswith('.webp'): ext = '.webp'
        elif clean_url.endswith('.gif'): ext = '.gif'
        elif clean_url.endswith('.apng'): ext = '.apng'
        elif clean_url.endswith('.webm'): ext = '.webm'
        elif clean_url.endswith('.mp4'): ext = '.mp4'
        else: ext = '.png'
            
        base_filename = f"wallpaper_{int(time.time())}"
        save_path = os.path.join(WALLPAPER_WORKSPACE_DIR, base_filename + ext)
        
        curl_command = f'curl -s -L --max-time 25 -A "Mozilla/5.0" "{url}" -o "{save_path}"'
        subprocess.run(curl_command, shell=True, check=True, capture_output=True)
        
        if not os.path.exists(save_path) or os.path.getsize(save_path) < 1000:
            if os.path.exists(save_path): os.remove(save_path)
            return

        # Handle native video streams immediately
        if ext in ['.webm', '.mp4']:
            cleanup_workspace_wallpapers(base_filename + ext)
            update_wallpaper_engine(save_path)
            return

        # Check for APNG structures
        if ext == '.apng':
            gif_name = base_filename + ".gif"
            gif_path = os.path.join(WALLPAPER_WORKSPACE_DIR, gif_name)
            if convert_apng_to_padded_gif(save_path, gif_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(gif_name)
                update_wallpaper_engine(gif_path)
            return

        # CRITICAL VALIDATION FIX: Open the file and inspect its actual properties.
        # This will catch animated files even if they are spoofed or masked with a '.jpg' extension.
        is_animated = False
        try:
            with Image.open(save_path) as test_img:
                if getattr(test_img, "is_animated", False) and test_img.n_frames > 1:
                    is_animated = True
        except Exception: 
            pass

        if is_animated:
            print(f"[Router] Animation frames verified inside asset. Forcing animated processing pipeline...")
            gif_name = base_filename + ".gif"
            gif_path = os.path.join(WALLPAPER_WORKSPACE_DIR, gif_name)
            
            if pad_animated_image(save_path, gif_path):
                # Clean up the original mislabeled temporary file safely
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(gif_name)
                update_wallpaper_engine(gif_path)
        else:
            # Fall back to standard static processing if it is truly a flat image file
            jpg_name = base_filename + ".jpg"
            jpg_path = os.path.join(WALLPAPER_WORKSPACE_DIR, jpg_name)
            if pad_static_image(save_path, output_path=jpg_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(jpg_name)
                update_wallpaper_engine(jpg_path)
                
    except Exception as e:
        print(f"[Downloader] Processing exception handled: {e}")

def process_ctrlem_log_line(line):
    """Filters CtrlEm text frames for incoming changewallpaper signals."""
    if "changewallpaper" in line.lower():
        url_match = re.search(r'(https?://\S+)', line)
        if url_match:
            print(f"[CtrlEm Log] Extracted signal target URL: {url_match.group(1)}")
            download_and_route_asset(url_match.group(1))

def monitor_ctrlem_command_stream():
    """Asynchronously tails the static CtrlEm commands.log file structure."""
    print(f"[Thread-CtrlEm] Launching watch on workspace targets: {CTRLEM_LOG_PATH}")
    while True:
        if os.path.exists(CTRLEM_LOG_PATH):
            with open(CTRLEM_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(1)
                        continue
                    process_ctrlem_log_line(line)
        else:
            time.sleep(5)

def get_latest_playctrl_daily_file():
    """Identifies the newest dynamic tracking file inside the PlayCtrl logging target folder."""
    search_path = os.path.join(PLAYCTRL_LOG_FOLDER, PLAYCTRL_LOG_PATTERN)
    files = glob.glob(search_path)
    if not files: 
        return None
    return max(files, key=os.path.getmtime)

def monitor_playctrl_daily_json_streams():
    """Asynchronously parses incoming multi-line JSON blocks out of PlayCtrl client outputs."""
    print(f"[Thread-PlayCtrl] Monitoring client data streaming directories: {PLAYCTRL_LOG_FOLDER}")
    current_file = None
    f = None
    json_buffer = ""
    inside_json = False

    while True:
        latest_file = get_latest_playctrl_daily_file()
        if latest_file and latest_file != current_file:
            print(f"[Thread-PlayCtrl] Hot-swapping reader instance targets: {os.path.basename(latest_file)}")
            if f: f.close()
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
        if stripped_line.startswith("----") and "type=set_wallpaper" in stripped_line:
            inside_json = True
            json_buffer = ""
            continue

        if inside_json:
            json_buffer += line
            if stripped_line == "}":
                try:
                    payload = json.loads(json_buffer)
                    if "url" in payload:
                        print(f"[PlayCtrl Log] Extracted embedded wallpaper target: {payload['url']}")
                        download_and_route_asset(payload["url"])
                except Exception: pass
                finally:
                    inside_json = False
                    json_buffer = ""

if __name__ == "__main__":
    # Initialize background file parsing engines
    ctrlem_worker = threading.Thread(target=monitor_ctrlem_command_stream, daemon=True)
    playctrl_worker = threading.Thread(target=monitor_playctrl_daily_json_streams, daemon=True)
    
    # Launch streaming daemon tasks
    ctrlem_worker.start()
    playctrl_worker.start()

    print("==========================================================================")
    print(" Wallpaper Engine Bridge running smoothly with program specific scopes.")
    print(" Active: Tracking CtrlEm command logs and PlayCtrl file streams.")
    print(" Press Ctrl+C to stop execution loop.")
    print("==========================================================================")

    try:
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down custom wallpaper engine environment hooks smoothly.")
