import os
import json
import threading
import time
import customtkinter as ctk
import psutil  
from tkinter import filedialog  # 🛠️ ADDED: Native file browser dialogue hooks

# Import all background parsing components directly from your bridge code
import wp_engine_bridge

# Configure theme alignment values to closely mimic the provided screenshot
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  

class WallpaperBridgeGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Wallpaper Engine Bridge Controller")
        self.geometry("750x650")
        
        # Exact hex mapping extracted directly from your UI reference photo
        self.theme_colors = {
            "accent": "#dc322f",
            "base_dark": "#002a35",
            "surface_panel": "#053542",
            "elevated_card": "#05313d"
        }
        
        self.configure(fg_color=self.theme_colors["base_dark"])

        # Split root viewport layout grid: Left Navigation Sidebar vs Right Workspace Pane
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Build structural view panels
        self.create_sidebar_navigation()
        self.create_workspace_viewplanes()
        
        # Hydrate text entry boxes with the active saved JSON tracking parameters
        self.load_settings_into_ui()
        
        # Default view routing initialization
        self.select_tab_pane("console")

        # Kick off the asynchronous process monitoring checker loop
        self.update_program_status_indicators()

    def create_sidebar_navigation(self):
        """Constructs the left navigation rail cleanly mimicking structural specifications."""
        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color=self.theme_colors["surface_panel"], border_width=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.app_title = ctk.CTkLabel(self.sidebar_frame, text="WE Bridge", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff")
        self.app_title.grid(row=0, column=0, padx=20, pady=25)

        self.nav_buttons = {}
        self.base_tabs = [("Console", "console"), ("Settings", "settings"), ("Appearance", "appearance")]
        
        for idx, (label, view_id) in enumerate(self.base_tabs, start=1):
            btn = ctk.CTkButton(
                self.sidebar_frame, text=label, anchor="w", height=40,
                corner_radius=8, fg_color="transparent", text_color="#a0b0b5",
                hover_color=self.theme_colors["elevated_card"], font=ctk.CTkFont(size=13),
                command=lambda v=view_id: self.select_tab_pane(v)
            )
            btn.grid(row=idx, column=0, padx=12, pady=6, sticky="ew")
            self.nav_buttons[view_id] = btn

        self.btn_debug_console = ctk.CTkButton(
            self.sidebar_frame, text="Debug Console", anchor="w", height=40,
            corner_radius=8, fg_color="transparent", text_color="#a0b0b5",
            hover_color=self.theme_colors["elevated_card"], font=ctk.CTkFont(size=13),
            command=lambda: self.select_tab_pane("debug_console")
        )
        self.nav_buttons["debug_console"] = self.btn_debug_console

        self.status_ctrlem = ctk.CTkLabel(self.sidebar_frame, text="● CtrlEm: Scanning...", text_color="#f1c40f", font=ctk.CTkFont(size=11, weight="bold"))
        self.status_ctrlem.grid(row=6, column=0, padx=20, pady=(5, 2), sticky="w")

        self.status_playctrl = ctk.CTkLabel(self.sidebar_frame, text="● PlayCtrl: Scanning...", text_color="#f1c40f", font=ctk.CTkFont(size=11, weight="bold"))
        self.status_playctrl.grid(row=7, column=0, padx=20, pady=(2, 15), sticky="w")

    def check_active_processes(self, c_target, p_target):
        """Hunts through running application logs natively to identify active matches."""
        c_running, p_running = False, False
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                if c_target and proc_name == c_target: c_running = True
                if p_target and proc_name == p_target: p_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return c_running, p_running

    def update_program_status_indicators(self):
        """Refreshes structural labels dynamically based on background process scans."""
        c_exe = os.path.basename(wp_engine_bridge.CTRLEM_EXE_PATH).lower() if wp_engine_bridge.CTRLEM_EXE_PATH else "ctrlem.exe"
        p_exe = os.path.basename(wp_engine_bridge.PLAYCTRL_EXE_PATH).lower() if wp_engine_bridge.PLAYCTRL_EXE_PATH else "playctrl.exe"

        c_running, p_running = self.check_active_processes(c_exe, p_exe)

        self.status_ctrlem.configure(text="● CtrlEm: Active" if c_running else "● CtrlEm: Offline", text_color="#2ecc71" if c_running else "#e74c3c")
        self.status_playctrl.configure(text="● PlayCtrl: Active" if p_running else "● PlayCtrl: Offline", text_color="#2ecc71" if p_running else "#e74c3c")

        self.after(5000, self.update_program_status_indicators)

    def create_workspace_viewplanes(self):
        """Creates the container frames for the different functional sections."""
        self.panes = {}

        # ----------------------------------------------------
        # VIEW PANEL: CONSOLE SCREEN (Clean User Logs Only)
        # ----------------------------------------------------
        console_pane = ctk.CTkFrame(self, fg_color="transparent")
        console_pane.grid_columnconfigure(0, weight=1)
        console_pane.grid_rowconfigure(1, weight=1)

        c_title = ctk.CTkLabel(console_pane, text="SYSTEM LIVE CONSOLE", font=ctk.CTkFont(size=15, weight="bold"))
        c_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.console_output = ctk.CTkTextbox(
            console_pane, fg_color=self.theme_colors["surface_panel"], text_color="#00ff66",
            font=ctk.CTkFont(family="Consolas", size=12), corner_radius=12,
            border_width=1, border_color=self.theme_colors["elevated_card"]
        )
        self.console_output.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.console_output.insert("0.0", "[System Init] Terminal log tracking channel active...\n")
        self.console_output.configure(state="disabled")
        self.panes["console"] = console_pane

        # ----------------------------------------------------
        # VIEW PANEL: DEBUG CONSOLE SCREEN
        # ----------------------------------------------------
        debug_pane = ctk.CTkFrame(self, fg_color="transparent")
        debug_pane.grid_columnconfigure(0, weight=1)
        debug_pane.grid_rowconfigure(1, weight=1)

        d_title = ctk.CTkLabel(debug_pane, text="VERBOSE RUNTIME DEBUG DIAGNOSTICS", font=ctk.CTkFont(size=15, weight="bold"))
        d_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.debug_output = ctk.CTkTextbox(
            debug_pane, fg_color=self.theme_colors["surface_panel"], text_color="#ffcc00",
            font=ctk.CTkFont(family="Consolas", size=12), corner_radius=12,
            border_width=1, border_color=self.theme_colors["elevated_card"]
        )
        self.debug_output.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.debug_output.insert("0.0", "[Debug Init] Background diagnostics stream tracker online...\n")
        self.debug_output.configure(state="disabled")
        self.panes["debug_console"] = debug_pane

        # ----------------------------------------------------
        # VIEW PANEL: SETTINGS CONFIGURATION ENGINE
        # ----------------------------------------------------
        settings_pane = ctk.CTkScrollableFrame(self, fg_color="transparent")
        settings_pane.grid_columnconfigure(0, weight=1)
        
        path_card = ctk.CTkFrame(settings_pane, fg_color=self.theme_colors["surface_panel"], corner_radius=12)
        path_card.pack(fill="x", padx=10, pady=10)
        path_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(path_card, text="LOG & EXECUTABLE PATHS", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=15, pady=10, sticky="w")
        
        # CtrlEm Log Input + Picker Button
        ctk.CTkLabel(path_card, text="CtrlEm Log:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.entry_ctrlem = ctk.CTkEntry(path_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_ctrlem.grid(row=1, column=1, padx=(15, 5), pady=5, sticky="ew")
        self.btn_pick_ctrlem_log = ctk.CTkButton(path_card, text="Browse...", width=80, command=self.browse_ctrlem_log)
        self.btn_pick_ctrlem_log.grid(row=1, column=2, padx=(5, 15), pady=5)

        # CtrlEm Exe Input + Picker Button
        ctk.CTkLabel(path_card, text="CtrlEm Exe Path:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.entry_ctrlem_exe = ctk.CTkEntry(path_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_ctrlem_exe.grid(row=2, column=1, padx=(15, 5), pady=5, sticky="ew")
        self.btn_pick_ctrlem_exe = ctk.CTkButton(path_card, text="Browse...", width=80, command=self.browse_ctrlem_exe)
        self.btn_pick_ctrlem_exe.grid(row=2, column=2, padx=(5, 15), pady=5)
        
        # PlayCtrl Log Folder Input + Picker Button
        ctk.CTkLabel(path_card, text="PlayCtrl Log Folder:").grid(row=3, column=0, padx=15, pady=5, sticky="w")
        self.entry_playctrl = ctk.CTkEntry(path_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_playctrl.grid(row=3, column=1, padx=(15, 5), pady=5, sticky="ew")
        self.btn_pick_playctrl_folder = ctk.CTkButton(path_card, text="Browse...", width=80, command=self.browse_playctrl_folder)
        self.btn_pick_playctrl_folder.grid(row=3, column=2, padx=(5, 15), pady=5)

        # PlayCtrl Exe Input + Picker Button
        ctk.CTkLabel(path_card, text="PlayCtrl Exe Path:").grid(row=4, column=0, padx=15, pady=5, sticky="w")
        self.entry_playctrl_exe = ctk.CTkEntry(path_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_playctrl_exe.grid(row=4, column=1, padx=(15, 5), pady=5, sticky="ew")
        self.btn_pick_playctrl_exe = ctk.CTkButton(path_card, text="Browse...", width=80, command=self.browse_playctrl_exe)
        self.btn_pick_playctrl_exe.grid(row=4, column=2, padx=(5, 15), pady=5)

        # Wallpaper Engine Exe Input + Picker Button
        ctk.CTkLabel(path_card, text="WE Exe Path:").grid(row=5, column=0, padx=15, pady=5, sticky="w")
        self.entry_we_exe = ctk.CTkEntry(path_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_we_exe.grid(row=5, column=1, padx=(15, 5), pady=5, sticky="ew")
        self.btn_pick_we_exe = ctk.CTkButton(path_card, text="Browse...", width=80, command=self.browse_we_exe)
        self.btn_pick_we_exe.grid(row=5, column=2, padx=(5, 15), pady=5)

        # Monitor layout parameters
        hw_card = ctk.CTkFrame(settings_pane, fg_color=self.theme_colors["surface_panel"], corner_radius=12)
        hw_card.pack(fill="x", padx=10, pady=10)
        hw_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hw_card, text="MONITOR SIZE", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        
        ctk.CTkLabel(hw_card, text="Width:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.entry_width = ctk.CTkEntry(hw_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_width.grid(row=1, column=1, padx=15, pady=5, sticky="ew")

        ctk.CTkLabel(hw_card, text="Height:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.entry_height = ctk.CTkEntry(hw_card, fg_color=self.theme_colors["elevated_card"])
        self.entry_height.grid(row=2, column=1, padx=15, pady=5, sticky="ew")

        self.switch_debug = ctk.CTkSwitch(settings_pane, text="Toggle Debug Mode", progress_color=self.theme_colors["accent"])
        self.switch_debug.pack(padx=15, pady=15, anchor="w")

        self.save_btn = ctk.CTkButton(settings_pane, text="Save Configurations Changes", fg_color=self.theme_colors["accent"], hover_color="#bd2623", command=self.save_settings_from_ui)
        self.save_btn.pack(pady=20)

        self.panes["settings"] = settings_pane

        # ----------------------------------------------------
        # VIEW PANEL: APPEARANCE PREVIEW & INTERACTIVE FIELDS
        # ----------------------------------------------------
        appearance_pane = ctk.CTkScrollableFrame(self, fg_color="transparent")
        appearance_pane.grid_columnconfigure(0, weight=1)

        acc_frame = ctk.CTkFrame(appearance_pane, fg_color=self.theme_colors["surface_panel"], corner_radius=12)
        acc_frame.pack(fill="x", padx=10, pady=10)
        acc_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(acc_frame, text="ACCENT COLOR", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=15, pady=(10, 5), sticky="w")
        self.swatch_accent = ctk.CTkFrame(acc_frame, width=35, height=25, corner_radius=4)
        self.swatch_accent.grid(row=1, column=0, padx=15, pady=10)
        ctk.CTkLabel(acc_frame, text="Hex Code:").grid(row=1, column=1, padx=(0, 5), pady=10)
        self.entry_accent = ctk.CTkEntry(acc_frame, fg_color=self.theme_colors["elevated_card"])
        self.entry_accent.grid(row=1, column=2, padx=15, pady=10, sticky="ew")

        bg_frame = ctk.CTkFrame(appearance_pane, fg_color=self.theme_colors["surface_panel"], corner_radius=12)
        bg_frame.pack(fill="x", padx=10, pady=10)
        bg_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(bg_frame, text="BACKGROUNDS", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=15, pady=(10, 5), sticky="w")
        
        self.swatch_base = ctk.CTkFrame(bg_frame, width=35, height=25, corner_radius=4)
        self.swatch_base.grid(row=1, column=0, padx=15, pady=5)
        ctk.CTkLabel(bg_frame, text="Base (Darkest):").grid(row=1, column=1, padx=(0, 5), pady=5, sticky="e")
        self.entry_base = ctk.CTkEntry(bg_frame, fg_color=self.theme_colors["elevated_card"])
        self.entry_base.grid(row=1, column=2, padx=15, pady=5, sticky="ew")

        self.swatch_surface = ctk.CTkFrame(bg_frame, width=35, height=25, corner_radius=4)
        self.swatch_surface.grid(row=2, column=0, padx=15, pady=5)
        ctk.CTkLabel(bg_frame, text="Surface (Sidebar, Panels):").grid(row=2, column=1, padx=(0, 5), pady=5, sticky="e")
        self.entry_surface = ctk.CTkEntry(bg_frame, fg_color=self.theme_colors["elevated_card"])
        self.entry_surface.grid(row=2, column=2, padx=15, pady=5, sticky="ew")

        self.swatch_elevated = ctk.CTkFrame(bg_frame, width=35, height=25, corner_radius=4)
        self.swatch_elevated.grid(row=3, column=0, padx=15, pady=5)
        ctk.CTkLabel(bg_frame, text="Elevated (Cards, Inputs):").grid(row=3, column=1, padx=(0, 5), pady=5, sticky="e")
        self.entry_elevated = ctk.CTkEntry(bg_frame, fg_color=self.theme_colors["elevated_card"])
        self.entry_elevated.grid(row=3, column=2, padx=15, pady=5, sticky="ew")

        txt_frame = ctk.CTkFrame(appearance_pane, fg_color=self.theme_colors["surface_panel"], corner_radius=12)
        txt_frame.pack(fill="x", padx=10, pady=10)
        txt_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(txt_frame, text="TEXT", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=15, pady=(10, 5), sticky="w")
        self.swatch_text = ctk.CTkFrame(txt_frame, width=35, height=25, corner_radius=4)
        self.swatch_text.grid(row=1, column=0, padx=15, pady=10)
        ctk.CTkLabel(txt_frame, text="Primary Color:").grid(row=1, column=1, padx=(0, 5), pady=10)
        self.entry_text = ctk.CTkEntry(txt_frame, fg_color=self.theme_colors["elevated_card"])
        self.entry_text.grid(row=1, column=2, padx=15, pady=10, sticky="ew")

        self.theme_btn = ctk.CTkButton(appearance_pane, text="Apply & Save Theme Changes", fg_color=self.theme_colors["accent"], hover_color="#bd2623", command=self.save_theme_from_ui)
        self.theme_btn.pack(pady=20)

        self.panes["appearance"] = appearance_pane

    def select_tab_pane(self, target_view):
        """Manages structural visibility states and styles tabs on selection."""
        if target_view == "debug_console" and not wp_engine_bridge.DEBUG_MODE:
            target_view = "console"

        for view_id, pane in self.panes.items():
            if view_id == target_view:
                pane.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
                self.nav_buttons[view_id].configure(fg_color=self.theme_colors["accent"], text_color="#ffffff")
            else:
                pane.grid_forget()
                self.nav_buttons[view_id].configure(fg_color="transparent", text_color="#a0b0b5")

    def toggle_debug_navigation_visibility(self, should_show_tab):
        """Dynamically inserts or drops the Debug Console button from the layout wireframes."""
        if should_show_tab:
            self.btn_debug_console.grid(row=4, column=0, padx=12, pady=6, sticky="ew")
        else:
            self.btn_debug_console.grid_forget()

    def write_to_console(self, complete_message_text, is_debug_message=False):
        """Thread-safely routes text strings straight into the correct UI logging component box."""
        if is_debug_message:
            self.after(0, lambda: self._append_text_execution(self.debug_output, complete_message_text))
        else:
            self.after(0, lambda: self._append_text_execution(self.console_output, complete_message_text))
            self.after(0, lambda: self._append_text_execution(self.debug_output, complete_message_text))

    def _append_text_execution(self, textbox_widget, text):
        textbox_widget.configure(state="normal")
        textbox_widget.insert("end", text)
        textbox_widget.see("end")
        textbox_widget.configure(state="disabled")

    def load_settings_into_ui(self):
        """Hydrates GUI entry inputs safely with live config.json variables."""
        try:
            self.entry_ctrlem.insert(0, wp_engine_bridge.CTRLEM_LOG_PATH)
            self.entry_playctrl.insert(0, wp_engine_bridge.PLAYCTRL_LOG_FOLDER)
            self.entry_width.insert(0, str(wp_engine_bridge.MONITOR_WIDTH))
            self.entry_height.insert(0, str(wp_engine_bridge.MONITOR_HEIGHT))
            self.entry_ctrlem_exe.insert(0, wp_engine_bridge.CTRLEM_EXE_PATH)
            self.entry_playctrl_exe.insert(0, wp_engine_bridge.PLAYCTRL_EXE_PATH)
            self.entry_we_exe.insert(0, wp_engine_bridge.WE_EXE_PATH)

            if getattr(wp_engine_bridge, "DEBUG_MODE", False):
                self.switch_debug.select()
                self.toggle_debug_navigation_visibility(should_show_tab=True)
            else:
                self.switch_debug.deselect()
                self.toggle_debug_navigation_visibility(should_show_tab=False)
            
            # FIX: Harmonized the internal dictionary keys to prevent loading drops
            self.theme_colors["accent"] = wp_engine_bridge.config.get("THEME_ACCENT", "#dc322f")
            self.theme_colors["base_dark"] = wp_engine_bridge.config.get("THEME_BASE", "#002a35")
            self.theme_colors["surface_panel"] = wp_engine_bridge.config.get("THEME_SURFACE", "#053542")
            self.theme_colors["elevated_card"] = wp_engine_bridge.config.get("THEME_ELEVATED", "#05313d")
            self.theme_colors["text_primary"] = wp_engine_bridge.config.get("THEME_TEXT", "#ffffff")

            self.entry_accent.insert(0, self.theme_colors["accent"])
            self.entry_base.insert(0, self.theme_colors["base_dark"])
            self.entry_surface.insert(0, self.theme_colors["surface_panel"])
            self.entry_elevated.insert(0, self.theme_colors["elevated_card"])
            self.entry_text.insert(0, self.theme_colors["text_primary"])

            self.update_ui_color_swatches()
            self.apply_theme_colors_to_widgets()
        except Exception as e:
            self.write_to_console(f"[GUI Init Error] Failed to populate configuration views: {e}\n", is_debug_message=True)

    def update_ui_color_swatches(self):
        """Refreshes the thumbnail color block objects visually."""
        self.swatch_accent.configure(fg_color=self.theme_colors["accent"])
        self.swatch_base.configure(fg_color=self.theme_colors["base_dark"])
        self.swatch_surface.configure(fg_color=self.theme_colors["surface_panel"])
        self.swatch_elevated.configure(fg_color=self.theme_colors["elevated_card"])
        self.swatch_text.configure(fg_color=self.theme_colors["text_primary"])

    def browse_ctrlem_log(self):
        """Opens a standard file browser pointing to .log targets."""
        selected_file = filedialog.askopenfilename(filetypes=[("Log Files", "*.log"), ("All Files", "*.*")])
        if selected_file:
            self.entry_ctrlem.delete(0, "end")
            self.entry_ctrlem.insert(0, selected_file)

    def browse_ctrlem_exe(self):
        """Opens a standard file browser targeting application files."""
        selected_file = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")])
        if selected_file:
            self.entry_ctrlem_exe.delete(0, "end")
            self.entry_ctrlem_exe.insert(0, selected_file)

    def browse_playctrl_folder(self):
        """Opens a standard directory tree picker window pane."""
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            self.entry_playctrl.delete(0, "end")
            self.entry_playctrl.insert(0, selected_dir)

    def browse_playctrl_exe(self):
        """Opens a file dialog for the client executable."""
        selected_file = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")])
        if selected_file:
            self.entry_playctrl_exe.delete(0, "end")
            self.entry_playctrl_exe.insert(0, selected_file)

    def browse_we_exe(self):
        """Locates the wallpaper engine rendering engine file."""
        selected_file = filedialog.askopenfilename(filetypes=[("Wallpaper Engine Executable", "wallpaper64.exe;wallpaper.exe"), ("All Files", "*.*")])
        if selected_file:
            self.entry_we_exe.delete(0, "end")
            self.entry_we_exe.insert(0, selected_file)

    def apply_theme_colors_to_widgets(self):
        """Redraws ALL background components, text colors, and frames across every tab interface."""
        # 1. Base Window & Sidebar Framework Elements
        self.configure(fg_color=self.theme_colors["base_dark"])
        self.sidebar_frame.configure(fg_color=self.theme_colors["surface_panel"])
        self.app_title.configure(text_color=self.theme_colors["text_primary"])
        
        # 2. Console Tab Elements (Clean Output Viewer & Hidden Debug Diagnostics Tracker)
        self.console_output.configure(
            fg_color=self.theme_colors["surface_panel"], 
            border_color=self.theme_colors["elevated_card"]
        )
        self.debug_output.configure(
            fg_color=self.theme_colors["surface_panel"], 
            border_color=self.theme_colors["elevated_card"]
        )
        
        # 3. Sidebar Tab Select Navigation Buttons & Active Status Indicators
        for view_id, btn in self.nav_buttons.items():
            btn.configure(hover_color=self.theme_colors["elevated_card"])
            if btn.cget("fg_color") != "transparent":
                btn.configure(fg_color=self.theme_colors["accent"], text_color="#ffffff")
            else:
                # FIX: Forces inactive sidebar text strings to blend with your secondary highlights
                btn.configure(text_color="#a0b0b5")

        # 4. Settings & Appearance Viewplanes (Your optimized loop logic)
        for pane_key in ["settings", "appearance"]:
            if pane_key in self.panes:
                self.panes[pane_key].configure(fg_color=self.theme_colors["base_dark"])
                for widget in self.panes[pane_key].winfo_children():
                    if isinstance(widget, ctk.CTkFrame):
                        widget.configure(fg_color=self.theme_colors["surface_panel"])
                        for sub_w in widget.winfo_children():
                            if isinstance(sub_w, ctk.CTkLabel): 
                                sub_w.configure(text_color=self.theme_colors["text_primary"])
                            elif isinstance(sub_w, ctk.CTkEntry): 
                                sub_w.configure(fg_color=self.theme_colors["elevated_card"], text_color=self.theme_colors["text_primary"])
                            elif isinstance(sub_w, ctk.CTkButton):
                                sub_w.configure(fg_color=self.theme_colors["accent"])
                    elif isinstance(widget, ctk.CTkSwitch):
                        widget.configure(progress_color=self.theme_colors["accent"], text_color=self.theme_colors["text_primary"])
                        
        # 5. Core Operational Action Buttons
        self.save_btn.configure(fg_color=self.theme_colors["accent"])
        self.theme_btn.configure(fg_color=self.theme_colors["accent"])

    def save_theme_from_ui(self):
        """Validates entry fields and saves theme customizations straight back to config.json."""
        try:
            clean_hex = lambda val: val.strip() if val.strip().startswith("#") else f"#{val.strip()}"
            for key, entry in [("accent", self.entry_accent), ("base_dark", self.entry_base),
                               ("surface_panel", self.entry_surface), ("elevated_card", self.entry_elevated),
                               ("text_primary", self.entry_text)]:
                self.theme_colors[key] = clean_hex(entry.get())

            with open(wp_engine_bridge.CONFIG_FILE, "r", encoding="utf-8") as f:
                current_config = json.load(f)

            mapping = {"THEME_ACCENT": "accent", "THEME_BASE": "base_dark", "THEME_SURFACE": "surface_panel", "THEME_ELEVATED": "elevated_card", "THEME_TEXT": "text_primary"}
            for conf_k, local_v in mapping.items():
                current_config[conf_k] = self.theme_colors[local_v]

            with open(wp_engine_bridge.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=4)

            wp_engine_bridge.config = current_config
            self.update_ui_color_swatches()
            self.apply_theme_colors_to_widgets()
            self.write_to_console("[Theme System] Theme settings compiled and applied successfully.\n")
        except Exception as e:
            self.write_to_console(f"[Theme Engine Exception] Failed to update: {e}\n")

    def save_settings_from_ui(self):
        """Commits modified UI entries straight back into local config storage file tracks."""
        try:
            with open(wp_engine_bridge.CONFIG_FILE, "r", encoding="utf-8") as f:
                current_config = json.load(f)

            current_config["CTRLEM_LOG_PATH"] = self.entry_ctrlem.get().strip()
            current_config["PLAYCTRL_LOG_FOLDER"] = self.entry_playctrl.get().strip()
            current_config["MONITOR_WIDTH"] = int(self.entry_width.get().strip())
            current_config["MONITOR_HEIGHT"] = int(self.entry_height.get().strip())
            current_config["DEBUG_MODE"] = bool(self.switch_debug.get())
            current_config["CTRLEM_EXE_PATH"] = self.entry_ctrlem_exe.get().strip()
            current_config["PLAYCTRL_EXE_PATH"] = self.entry_playctrl_exe.get().strip()
            current_config["WE_EXE_PATH"] = self.entry_we_exe.get().strip()
            
            if "WALLPAPER_WORKSPACE_DIR" in current_config:
                del current_config["WALLPAPER_WORKSPACE_DIR"]
            
            with open(wp_engine_bridge.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=4)
                
            self.write_to_console("[System Config] Changes committed into 'config.json' successfully.\n")
            
            wp_engine_bridge.CTRLEM_LOG_PATH = current_config["CTRLEM_LOG_PATH"]
            wp_engine_bridge.PLAYCTRL_LOG_FOLDER = current_config["PLAYCTRL_LOG_FOLDER"]
            wp_engine_bridge.MONITOR_WIDTH = current_config["MONITOR_WIDTH"]
            wp_engine_bridge.MONITOR_HEIGHT = current_config["MONITOR_HEIGHT"]
            wp_engine_bridge.DEBUG_MODE = current_config["DEBUG_MODE"]
            wp_engine_bridge.CTRLEM_EXE_PATH = current_config["CTRLEM_EXE_PATH"]
            wp_engine_bridge.PLAYCTRL_EXE_PATH = current_config["PLAYCTRL_EXE_PATH"]
            wp_engine_bridge.WE_EXE_PATH = current_config["WE_EXE_PATH"]

            self.toggle_debug_navigation_visibility(should_show_tab=wp_engine_bridge.DEBUG_MODE)
            if not wp_engine_bridge.DEBUG_MODE:
                self.select_tab_pane("console")
        except Exception as e:
            self.write_to_console(f"[Configuration Save Error] Failed to export settings: {e}\n", is_debug_message=True)

if __name__ == "__main__":
    app = WallpaperBridgeGUI()
    wp_engine_bridge.gui_instance = app
    
    threading.Thread(target=wp_engine_bridge.monitor_ctrlem_command_stream, daemon=True).start()
    threading.Thread(target=wp_engine_bridge.monitor_playctrl_daily_json_streams, daemon=True).start()

    app.mainloop()
