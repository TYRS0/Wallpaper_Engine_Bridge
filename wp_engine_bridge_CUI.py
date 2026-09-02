import os
import re
import time
import subprocess
import json
import glob
import threading
from PIL import Image, ImageSequence
from apng import APNG

# --- LOCAL SCRIPT CONSTANTS ---
PLAYCTRL_LOG_PATTERN = "*.txt"

# --- DYNAMIC CONFIGURATION INITIALIZATION ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_application_config():
    """Loads configuration fields dynamically from a local json file tracker."""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Critical Error: '{CONFIG_FILE}' could not be located in application workspace.")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Unpack operational values directly into global configuration space
config = load_application_config()
CTRLEM_LOG_PATH = config["CTRLEM_LOG_PATH"]
PLAYCTRL_LOG_FOLDER = config["PLAYCTRL_LOG_FOLDER"]
WALLPAPER_WORKSPACE_DIR = config["WALLPAPER_WORKSPACE_DIR"]
WE_EXE_PATH = config["WE_EXE_PATH"]
MONITOR_WIDTH = int(config["MONITOR_WIDTH"])
MONITOR_HEIGHT = int(config["MONITOR_HEIGHT"])
DEBUG_MODE = config.get("DEBUG_MODE", True)

if not os.path.exists(WALLPAPER_WORKSPACE_DIR):
    os.makedirs(WALLPAPER_WORKSPACE_DIR)

def log_message(text, is_debug=True, source_app=None, source_group=None):
    """Handles structured logging formats based on the current debug profile status."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if not is_debug and source_app and source_group:
        # Parentheses removed from the clean tracking output layout
        print(f"[{timestamp}] changed by {source_group} {{{source_app}}}")
    elif DEBUG_MODE:
        prefix = f"[{source_app}] " if source_app else ""
        print(f"[{timestamp}] {prefix}{text}")

def update_wallpaper_engine(image_path):
    """Tells Wallpaper Engine to immediately apply the file via CLI."""
    if not os.path.exists(WE_EXE_PATH):
        log_message(f"Error: wallpaper64.exe not found at {WE_EXE_PATH}", is_debug=True)
        return

    command = [WE_EXE_PATH, "-control", "openWallpaper", "-file", image_path]
    try:
        subprocess.run(command, check=True, capture_output=True)
        log_message("Wallpaper Engine canvas updated.", is_debug=True)
    except Exception as e:
        log_message(f"Failed to communicate with Wallpaper Engine: {e}", is_debug=True)

def pad_static_image(image_path, output_path=None):
    """Pads a static image and ensures it saves safely without decimal crop issues."""
    try:
        save_path = output_path if output_path else image_path
        with Image.open(image_path) as img:
            if img.width == MONITOR_WIDTH and img.height == MONITOR_HEIGHT:
                log_message("Static image matches resolution perfectly. Bypassing processing math...", is_debug=True)
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
            return True
    except Exception as e:
        log_message(f"Failed to pad static image: {e}", is_debug=True)
        return False

def pad_animated_image(img_path, output_gif_path=None):
    """Resizes and pads an animated GIF/WebP frame-by-frame without decimal precision drifting."""
    try:
        target_path = output_gif_path if output_gif_path else img_path
        with Image.open(img_path) as im:
            img_w, img_h = im.size

            if img_w == MONITOR_WIDTH and img_h == MONITOR_HEIGHT:
                log_message("Animated asset matches resolution perfectly. Bypassing processing math...", is_debug=True)
                loop = im.info.get('loop', 0)
                durations = []
                frames = []
                for frame in ImageSequence.Iterator(im):
                    durations.append(frame.info.get('duration', 100))
                    frames.append(frame.copy().convert("P", palette=Image.Palette.ADAPTIVE))
                if frames:
                    # FIX: Call .save() on the first element of the list, not the list itself
                    frames[0].save(target_path, save_all=True, append_images=frames[1:], optimize=True, duration=durations, loop=loop)
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
                # FIX: Call .save() on the first element of the list, not the list itself
                padded_frames[0].save(target_path, save_all=True, append_images=padded_frames[1:], optimize=True, duration=durations, loop=loop)
                log_message("Animated asset successfully padded.", is_debug=True)
                return True
    except Exception as e:
        log_message(f"Failed to pad animated file: {e}", is_debug=True)
    return False

def convert_apng_to_padded_gif(apng_path, gif_path):
    """Converts an APNG file into a standard padded GIF container."""
    try:
        im = APNG.open(apng_path)
        frames = []
        with open("temp_size.png", "wb") as f:
            im.frames.save(f)
        with Image.open("temp_size.png") as first_img:
            img_w, img_h = first_img.size
        if os.path.exists("temp_size.png"):
            os.remove("temp_size.png")

        if img_w == MONITOR_WIDTH and img_h == MONITOR_HEIGHT:
            log_message("APNG matches resolution perfectly. Flat transcode converting...", is_debug=True)
            for png_frame, control in im.frames:
                with open("temp_frame.png", "wb") as f:
                    png_frame.save(f)
                frames.append(Image.open("temp_frame.png").convert("P", palette=Image.Palette.ADAPTIVE))
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
                resized_frame = Image.open("temp_frame.png").resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
                bg = Image.new("RGBA", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0, 255))
                bg.paste(resized_frame, (paste_x, paste_y), resized_frame)
                frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))
            
        if frames:
            frames.save(gif_path, save_all=True, append_images=frames[1:], optimize=True, duration=[c.delay for _, c in im.frames], loop=0)
        if os.path.exists("temp_frame.png"):
            os.remove("temp_frame.png")
        return True
    except Exception as e:
        log_message(f"APNG to padded GIF conversion failed: {e}", is_debug=True)
        if os.path.exists("temp_frame.png"):
            os.remove("temp_frame.png")
        return False

def cleanup_workspace_wallpapers(active_filename):
    """Deletes old files in the scratch folder while preserving the live background asset."""
    try:
        for filename in os.listdir(WALLPAPER_WORKSPACE_DIR):
            file_path = os.path.join(WALLPAPER_WORKSPACE_DIR, filename)
            if not os.path.isfile(file_path) or filename == active_filename:
                continue
            try:
                os.remove(file_path)
            except PermissionError:
                pass 
    except Exception as e:
        log_message(f"[Cleanup] Directory sweep error: {e}", is_debug=True)

def download_and_route_asset(url, source_app, source_group):
    """Downloads files via curl and handles asset routing based on format styles."""
    try:
        # FIX: Extract the base URL element index [0] before running lowercase conversion
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

        # Fire clean short-format output summary string
        log_message(None, is_debug=False, source_app=source_app, source_group=source_group)

        if ext in ['.webm', '.mp4']:
            cleanup_workspace_wallpapers(base_filename + ext)
            update_wallpaper_engine(save_path)
            return

        if ext == '.apng':
            gif_name = base_filename + ".gif"
            gif_path = os.path.join(WALLPAPER_WORKSPACE_DIR, gif_name)
            if convert_apng_to_padded_gif(save_path, gif_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(gif_name)
                update_wallpaper_engine(gif_path)
            return

        is_animated = False
        try:
            with Image.open(save_path) as test_img:
                if getattr(test_img, "is_animated", False) and test_img.n_frames > 1:
                    is_animated = True
        except Exception: 
            pass

        if is_animated:
            log_message("Animation frames verified. Forcing animated pipeline...", is_debug=True, source_app=source_app)
            gif_name = base_filename + ".gif"
            gif_path = os.path.join(WALLPAPER_WORKSPACE_DIR, gif_name)
            if pad_animated_image(save_path, gif_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(gif_name)
                update_wallpaper_engine(gif_path)
        else:
            jpg_name = base_filename + ".jpg"
            jpg_path = os.path.join(WALLPAPER_WORKSPACE_DIR, jpg_name)
            if pad_static_image(save_path, output_path=jpg_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(jpg_name)
                update_wallpaper_engine(jpg_path)
    except Exception as e:
        log_message(f"Processing exception handled: {e}", is_debug=True, source_app=source_app)


def process_ctrlem_log_line(line):
    """Filters CtrlEm entries. Falls back to 'Unknown Profile' if group/api context is absent."""
    if "changewallpaper" in line.lower():
        url_match = re.search(r'(https?://\S+)', line)
        if not url_match:
            return

        url = url_match.group(1)
        
        # Check if explicitly issued via 'api'
        if "sent by api" in line.lower():
            log_message(f"API command verified: {url}", is_debug=True, source_app="CtrlEm")
            download_and_route_asset(url, source_app="CtrlEm", source_group="API")
            return
            
        # Parse out (sent by Person_ID (Group: Group_Name))
        group_match = re.search(r'\(sent by .*?\(Group:\s*(.*?)\)\)', line, re.IGNORECASE)
        if group_match:
            group_name = group_match.group(1).strip()
            log_message(f"Group command verified: {group_name} -> {url}", is_debug=True, source_app="CtrlEm")
            download_and_route_asset(url, source_app="CtrlEm", source_group=group_name)
        else:
            # Fallback to process individual/unknown logs instead of ignoring them
            log_message(f"Individual/Unknown command captured: {url}", is_debug=True, source_app="CtrlEm")
            download_and_route_asset(url, source_app="CtrlEm", source_group="Unknown Profile")


def monitor_playctrl_daily_json_streams():
    """Asynchronously parses incoming multi-line JSON blocks out of PlayCtrl client outputs."""
    log_message(f"Monitoring client directory: {PLAYCTRL_LOG_FOLDER}", is_debug=True, source_app="PlayCtrl")
    current_file = None
    f = None
    json_buffer = ""
    inside_json = False
    current_group = "Unknown Profile"  # Holds the extracted header group name

    while True:
        latest_file = get_latest_playctrl_daily_file()
        if latest_file and latest_file != current_file:
            log_message(f"Hot-swapping reader instance targets: {os.path.basename(latest_file)}", is_debug=True, source_app="PlayCtrl")
            if f: f.close()
            current_file = latest_file
            f = open(current_file, "r", encoding="utf-8", errors="ignore")
            f.seek(0, os.SEEK_END)
            json_buffer = ""
            inside_json = False
            current_group = "Unknown Profile"

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
            
            # Extract group="..." from the log header line if present
            group_match = re.search(r'group=["\'](.*?)["\']', stripped_line)
            if group_match:
                current_group = group_match.group(1).strip()
            else:
                current_group = "Unknown Profile"
            continue

        if inside_json:
            json_buffer += line
            if stripped_line == "}":
                try:
                    payload = json.loads(json_buffer)
                    if "url" in payload:
                        # Fallback check: Use payload value if present, otherwise use header group
                        group_name = payload.get("group", current_group)
                        if not group_name:
                            group_name = "Unknown Profile"
                            
                        log_message(f"Extracted group wallpaper target: {payload['url']}", is_debug=True, source_app="PlayCtrl")
                        download_and_route_asset(payload["url"], source_app="PlayCtrl.me", source_group=group_name)
                except Exception: 
                    pass
                finally:
                    inside_json = False
                    json_buffer = ""
                    current_group = "Unknown Profile"

def get_latest_playctrl_daily_file():
    """Identifies the newest dynamic tracking file inside the PlayCtrl logging target folder."""
    search_path = os.path.join(PLAYCTRL_LOG_FOLDER, PLAYCTRL_LOG_PATTERN)
    files = glob.glob(search_path)
    if not files: 
        return None
    return max(files, key=os.path.getmtime)

def monitor_playctrl_daily_json_streams():
    """Asynchronously parses incoming multi-line JSON blocks out of PlayCtrl client outputs."""
    log_message(f"Monitoring client directory: {PLAYCTRL_LOG_FOLDER}", is_debug=True, source_app="PlayCtrl")
    current_file = None
    f = None
    json_buffer = ""
    inside_json = False
    current_group = "Unknown Profile"

    while True:
        latest_file = get_latest_playctrl_daily_file()
        if latest_file and latest_file != current_file:
            log_message(f"Hot-swapping reader instance targets: {os.path.basename(latest_file)}", is_debug=True, source_app="PlayCtrl")
            if f: f.close()
            current_file = latest_file
            f = open(current_file, "r", encoding="utf-8", errors="ignore")
            f.seek(0, os.SEEK_END)
            json_buffer = ""
            inside_json = False
            current_group = "Unknown Profile"

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
            
            # Extract group="..." from the log header line if present
            group_match = re.search(r'group=["\'](.*?)["\']', stripped_line)
            if group_match:
                current_group = group_match.group(1).strip()
            else:
                current_group = "Unknown Profile"
            continue

        if inside_json:
            json_buffer += line
            if stripped_line == "}":
                try:
                    payload = json.loads(json_buffer)
                    if "url" in payload:
                        # FIX: Prioritize payload group only if it's a valid, non-empty string
                        payload_group = payload.get("group")
                        if payload_group and str(payload_group).strip():
                            group_name = str(payload_group).strip()
                        else:
                            group_name = current_group

                        if not group_name:
                            group_name = "Unknown Profile"
                            
                        log_message(f"Extracted group wallpaper target: {payload['url']}", is_debug=True, source_app="PlayCtrl")
                        download_and_route_asset(payload["url"], source_app="PlayCtrl.me", source_group=group_name)
                except Exception: 
                    pass
                finally:
                    inside_json = False
                    json_buffer = ""
                    current_group = "Unknown Profile"

def monitor_ctrlem_command_stream():
    """Asynchronously tails the static CtrlEm commands.log file structure."""
    log_message(f"Launching watch on: {CTRLEM_LOG_PATH}", is_debug=True, source_app="CtrlEm")
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

if __name__ == "__main__":
    # Initialize background file parsing engines
    ctrlem_worker = threading.Thread(target=monitor_ctrlem_command_stream, daemon=True)
    playctrl_worker = threading.Thread(target=monitor_playctrl_daily_json_streams, daemon=True)
    
    # Launch streaming daemon tasks
    ctrlem_worker.start()
    playctrl_worker.start()

    print("==========================================================================")
    print(" Wallpaper Engine Bridge Application Running.")
    print(f" Log Profile Level: {'VERBOSE_DEBUG' if DEBUG_MODE else 'CLEAN_SUMMARY_ONLY'}")
    print(" Press Ctrl+C to stop execution loop safely.")
    print("==========================================================================")

    try:
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down custom wallpaper engine environment hooks smoothly.")
