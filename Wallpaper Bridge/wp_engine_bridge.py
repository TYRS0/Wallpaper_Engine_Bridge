import os
import re
import time
import subprocess
import json
import glob
import threading
from PIL import Image, ImageSequence
from apng import APNG

# --- ENGINE TRACKING SCHEMATICS ---
PLAYCTRL_LOG_PATTERN = "*.txt"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
gui_instance = None  

def load_application_config():
    """Hydrates local execution spaces with fail-safe defaults if config is corrupted or empty."""
    default_config = {
        "CTRLEM_LOG_PATH": "",
        "CTRLEM_EXE_PATH": "",
        "PLAYCTRL_LOG_FOLDER": "",
        "PLAYCTRL_EXE_PATH": "",
        "WE_EXE_PATH": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\wallpaper_engine\\wallpaper64.exe",
        "MONITOR_WIDTH": 1920,
        "MONITOR_HEIGHT": 1080,
        "DEBUG_MODE": False,
        "THEME_ACCENT": "#a855f7",
        "THEME_BASE": "#0f0f13",
        "THEME_SURFACE": "#16161d",
        "THEME_ELEVATED": "#1e1e2a",
        "THEME_TEXT": "#f0f0f8"
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                raise json.JSONDecodeError("File blank", "", 0)
            
            loaded_config = json.loads(content)
            for key, val in default_config.items():
                if key not in loaded_config:
                    loaded_config[key] = val
            return loaded_config
    except (json.JSONDecodeError, FileNotFoundError):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config

# Hot-reload mapping variables globally
config = load_application_config()
CTRLEM_LOG_PATH = config["CTRLEM_LOG_PATH"]
PLAYCTRL_LOG_FOLDER = config["PLAYCTRL_LOG_FOLDER"]
WE_EXE_PATH = config["WE_EXE_PATH"]
MONITOR_WIDTH = int(config.get("MONITOR_WIDTH", 1920))
MONITOR_HEIGHT = int(config.get("MONITOR_HEIGHT", 1080))
DEBUG_MODE = config.get("DEBUG_MODE", False)
CTRLEM_EXE_PATH = config["CTRLEM_EXE_PATH"]
PLAYCTRL_EXE_PATH = config["PLAYCTRL_EXE_PATH"]

WALLPAPER_WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TempDownloads")
if not os.path.exists(WALLPAPER_WORKSPACE_DIR):
    os.makedirs(WALLPAPER_WORKSPACE_DIR)

def format_log_entry(text, is_debug, source_app, source_group):
    """Isolates the string layout rendering logic from multi-thread I/O contexts."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if not is_debug and source_app and source_group:
        return f"[{timestamp}] changed by {source_group} {{{source_app}}}"
    elif DEBUG_MODE or is_debug:
        prefix = f"[{source_app}] " if source_app else ""
        return f"[{timestamp}] {prefix}{text}"
    return None

def log_message(text, is_debug=True, source_app=None, source_group=None):
    """Routes runtime summary messages directly down onto active GUI consoles."""
    global gui_instance
    formatted_msg = format_log_entry(text, is_debug, source_app, source_group)
    
    if formatted_msg:
        print(formatted_msg)
        if gui_instance is not None:
            try:
                # Passes the is_debug_message boolean flag to route logs to the right textbox
                gui_instance.write_to_console(formatted_msg + "\n", is_debug_message=is_debug)
            except Exception:
                pass

def get_windows_startup_info():
    """Generates shell flags to explicitly block window flickering on desktop hosts."""
    if os.name == 'nt' and not DEBUG_MODE:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    return None

def update_wallpaper_engine(image_path):
    """Tells Wallpaper Engine to immediately apply the file via CLI."""
    if not os.path.exists(WE_EXE_PATH):
        log_message(f"Error: wallpaper64.exe missing at {WE_EXE_PATH}", is_debug=True)
        return

    time.sleep(0.2)
    command = [WE_EXE_PATH, "-control", "openWallpaper", "-file", image_path]
    try:
        subprocess.run(
            command, check=True, capture_output=True, 
            startupinfo=get_windows_startup_info()
        )
        log_message("Wallpaper Engine canvas updated.", is_debug=True)
    except Exception as e:
        log_message(f"Failed to communicate with Wallpaper Engine: {e}", is_debug=True)

def calculate_padded_dimensions(width, height):
    """Calculates scaling profiles to perfectly preserve physical aspect limits."""
    img_ratio = width / height
    monitor_ratio = MONITOR_WIDTH / MONITOR_HEIGHT
    
    if img_ratio > monitor_ratio:
        new_w = MONITOR_WIDTH
        new_h = int(MONITOR_WIDTH / img_ratio)
    else:
        new_h = MONITOR_HEIGHT
        new_w = int(MONITOR_HEIGHT * img_ratio)
        
    paste_x = (MONITOR_WIDTH - new_w) // 2
    paste_y = (MONITOR_HEIGHT - new_h) // 2
    return new_w, new_h, paste_x, paste_y

def pad_static_image(image_path, output_path=None):
    """Pads a static image and ensures it saves safely without dimensional precision drifting."""
    try:
        save_path = output_path if output_path else image_path
        with Image.open(image_path) as img:
            if img.width == MONITOR_WIDTH and img.height == MONITOR_HEIGHT:
                log_message("Static resolution matches. Bypassing scaling.", is_debug=True)
                img.convert("RGB").save(save_path, "JPEG", quality=95) if save_path.lower().endswith(('.jpg', '.jpeg')) else img.save(save_path)
                return True

            new_w, new_h, paste_x, paste_y = calculate_padded_dimensions(img.width, img.height)
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            background = Image.new("RGB", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0))
            background.paste(resized_img, (paste_x, paste_y))
            
            if save_path.lower().endswith(('.jpg', '.jpeg')):
                background.convert("RGB").save(save_path, "JPEG", quality=95)
            else:
                background.save(save_path)
            return True
    except Exception as e:
        log_message(f"Failed to pad static image: {e}", is_debug=True)
        return False

def pad_animated_image(img_path, output_gif_path=None):
    """Resizes and pads an animated GIF/WebP frame-by-frame without canvas bleed bugs."""
    try:
        target_path = output_gif_path if output_gif_path else img_path
        with Image.open(img_path) as im:
            if im.size == (MONITOR_WIDTH, MONITOR_HEIGHT):
                log_message("Animation resolution matches. Bypassing processing.", is_debug=True)
                frames = [f.copy().convert("P", palette=Image.Palette.ADAPTIVE) for f in ImageSequence.Iterator(im)]
                if frames:
                    frames[0].save(target_path, save_all=True, append_images=frames[1:], optimize=True, loop=im.info.get('loop', 0))
                return True

            new_w, new_h, px, py = calculate_padded_dimensions(im.width, im.height)
            padded_frames, durations = [], []
            canvas_frame = Image.new("RGBA", im.size)

            for frame in ImageSequence.Iterator(im):
                durations.append(frame.info.get('duration', 100))
                mask = frame.convert("RGBA") if frame.mode in ('RGBA', 'LA') or (frame.mode == 'P' and 'transparency' in frame.info) else None
                canvas_frame.paste(frame, frame.getbbox() or (0, 0), mask)
                
                resized = canvas_frame.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
                bg = Image.new("RGBA", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0, 255))
                bg.paste(resized, (px, py), resized)
                padded_frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))

            if padded_frames:
                padded_frames[0].save(target_path, save_all=True, append_images=padded_frames[1:], optimize=True, duration=durations, loop=im.info.get('loop', 0))
                return True
    except Exception as e:
        log_message(f"Failed to pad animated file: {e}", is_debug=True)
    return False

def convert_apng_to_padded_gif(apng_path, gif_path):
    """Converts an APNG file into a standard padded GIF container."""
    try:
        im = APNG.open(apng_path)
        frames = []
        
        im.frames[0][0].save("temp_size.png")
        with Image.open("temp_size.png") as first_img:
            img_w, img_h = first_img.size
        if os.path.exists("temp_size.png"):
            os.remove("temp_size.png")

        if img_w == MONITOR_WIDTH and img_h == MONITOR_HEIGHT:
            for png_frame, _ in im.frames:
                png_frame.save("temp_frame.png")
                frames.append(Image.open("temp_frame.png").convert("P", palette=Image.Palette.ADAPTIVE))
        else:
            nw, nh, px, py = calculate_padded_dimensions(img_w, img_h)
            for png_frame, _ in im.frames:
                png_frame.save("temp_frame.png")
                resized = Image.open("temp_frame.png").resize((nw, nh), Image.Resampling.LANCZOS).convert("RGBA")
                bg = Image.new("RGBA", (MONITOR_WIDTH, MONITOR_HEIGHT), (0, 0, 0, 255))
                bg.paste(resized, (px, py), resized)
                frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))
            
        if frames:
            frames[0].save(gif_path, save_all=True, append_images=frames[1:], optimize=True, duration=[c.delay for _, c in im.frames], loop=0)
        if os.path.exists("temp_frame.png"):
            os.remove("temp_frame.png")
        return True
    except Exception as e:
        log_message(f"APNG conversion failed: {e}", is_debug=True)
        if os.path.exists("temp_frame.png"):
            os.remove("temp_frame.png")
        return False

def get_clean_extension(url):
    """Parses raw text strings to identify incoming formatting types."""
    url_split = url.split('?')
    clean_url = url_split[0].lower() if url_split else url.lower()
    for ext in ['.webp', '.gif', '.apng', '.webm', '.mp4']:
        if clean_url.endswith(ext):
            return ext
    return '.png'

def verify_image_integrity(save_path):
    """Performs a lightweight structure check on files to discard broken items."""
    try:
        with Image.open(save_path) as verify_img:
            verify_img.verify()
        return True
    except Exception:
        return False

def download_and_route_asset(url, source_app, source_group):
    """Downloads files via curl and handles asset routing based on format styles."""
    try:
        ext = get_clean_extension(url)
        base_filename = f"wallpaper_{int(time.time())}"
        save_path = os.path.join(WALLPAPER_WORKSPACE_DIR, base_filename + ext)
        
        curl_command = f'curl -s -L --max-time 25 -A "Mozilla/5.0" "{url}" -o "{save_path}"'
        subprocess.run(curl_command, shell=True, check=True, capture_output=True, startupinfo=get_windows_startup_info())
        
        if not os.path.exists(save_path) or os.path.getsize(save_path) < 1000:
            if os.path.exists(save_path): os.remove(save_path)
            return

        if ext not in ['.webm', '.mp4'] and not verify_image_integrity(save_path):
            log_message(f"Corrupted download from {source_app}.", is_debug=True, source_app=source_app)
            if os.path.exists(save_path): os.remove(save_path)
            return

        log_message(None, is_debug=False, source_app=source_app, source_group=source_group)

        if ext in ['.webm', '.mp4']:
            cleanup_workspace_wallpapers(base_filename + ext)
            update_wallpaper_engine(save_path)
            return

        if ext == '.apng':
            gif_path = os.path.join(WALLPAPER_WORKSPACE_DIR, base_filename + ".gif")
            if convert_apng_to_padded_gif(save_path, gif_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(base_filename + ".gif")
                update_wallpaper_engine(gif_path)
            return

        is_animated = False
        with Image.open(save_path) as test_img:
            if getattr(test_img, "is_animated", False) and test_img.n_frames > 1:
                is_animated = True

        if is_animated:
            gif_path = os.path.join(WALLPAPER_WORKSPACE_DIR, base_filename + ".gif")
            if pad_animated_image(save_path, gif_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(base_filename + ".gif")
                update_wallpaper_engine(gif_path)
        else:
            jpg_path = os.path.join(WALLPAPER_WORKSPACE_DIR, base_filename + ".jpg")
            if pad_static_image(save_path, output_path=jpg_path):
                if os.path.exists(save_path): os.remove(save_path)
                cleanup_workspace_wallpapers(base_filename + ".jpg")
                update_wallpaper_engine(jpg_path)
    except Exception as e:
        log_message(f"Processing error: {e}", is_debug=True, source_app=source_app)

def cleanup_workspace_wallpapers(active_filename):
    """Sweeps directory structures clean of stale wallpaper fragments."""
    try:
        for filename in os.listdir(WALLPAPER_WORKSPACE_DIR):
            file_path = os.path.join(WALLPAPER_WORKSPACE_DIR, filename)
            if os.path.isfile(file_path) and filename != active_filename:
                try:
                    os.remove(file_path)
                except PermissionError:
                    pass
    except Exception as e:
        log_message(f"Cleanup error: {e}", is_debug=True)

def process_ctrlem_log_line(line):
    """Filters and decodes incoming command string elements from CtrlEm logs."""
    if "changewallpaper" in line.lower():
        url_match = re.search(r'(https?://\S+)', line)
        if not url_match:
            return

        url = url_match.group(1)
        if "sent by api" in line.lower():
            log_message(f"API command: {url}", is_debug=True, source_app="CtrlEm")
            download_and_route_asset(url, source_app="CtrlEm", source_group="API")
            return
            
        group_match = re.search(r'\(sent by .*?\(Group:\s*(.*?)\)\)', line, re.IGNORECASE)
        group_name = group_match.group(1).strip() if group_match else "Unknown Profile"
        log_message(f"Command localized: {group_name} -> {url}", is_debug=True, source_app="CtrlEm")
        download_and_route_asset(url, source_app="CtrlEm", source_group=group_name)

def get_latest_playctrl_daily_file():
    """Identifies the newest dynamic tracking file inside the PlayCtrl logging target folder."""
    files = glob.glob(os.path.join(PLAYCTRL_LOG_FOLDER, PLAYCTRL_LOG_PATTERN))
    return max(files, key=os.path.getmtime) if files else None

def parse_buffered_playctrl_json(buffer, fallback_group):
    """Validates multi-line payload text and hands valid configurations down to loaders."""
    try:
        payload = json.loads(buffer)
        if "url" in payload:
            group_name = str(payload.get("group", fallback_group)).strip()
            if not group_name:
                group_name = "Unknown Profile"
            log_message(f"Extracted json target: {payload['url']}", is_debug=True, source_app="PlayCtrl")
            download_and_route_asset(payload["url"], source_app="PlayCtrl.me", source_group=group_name)
    except Exception:
        pass

def monitor_playctrl_daily_json_streams():
    """Asynchronously parses incoming multi-line JSON blocks out of PlayCtrl client outputs."""
    log_message(f"Watching PlayCtrl directory: {PLAYCTRL_LOG_FOLDER}", is_debug=True, source_app="PlayCtrl")
    current_file, f, json_buffer, inside_json, current_group = None, None, "", False, "Unknown Profile"

    while True:
        latest_file = get_latest_playctrl_daily_file()
        if latest_file and latest_file != current_file:
            if f: f.close()
            current_file = latest_file
            f = open(current_file, "r", encoding="utf-8", errors="ignore")
            f.seek(0, os.SEEK_END)
            json_buffer, inside_json = "", False

        if not f:
            time.sleep(5)
            continue

        line = f.readline()
        if not line:
            time.sleep(1)
            continue

        stripped = line.strip()
        if stripped.startswith("----") and "type=set_wallpaper" in stripped:
            inside_json = True
            json_buffer = ""
            group_match = re.search(r'group=["\'](.*?)["\']', stripped)
            current_group = group_match.group(1).strip() if group_match else "Unknown Profile"
            continue

        if inside_json:
            json_buffer += line
            if stripped == "}":
                parse_buffered_playctrl_json(json_buffer, current_group)
                inside_json = False

def monitor_ctrlem_command_stream():
    """Asynchronously tails the static CtrlEm commands.log file structure."""
    log_message(f"Watching CtrlEm log: {CTRLEM_LOG_PATH}", is_debug=True, source_app="CtrlEm")
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
        time.sleep(5)