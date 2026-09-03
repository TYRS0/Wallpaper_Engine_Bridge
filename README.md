
This was made with Google Search AI Mode (Gemini 3)

Setup
1. Install and setup [Wallpaper Engine](https://store.steampowered.com/app/431960/Wallpaper_Engine/), [CtrlEm](https://ctrlem.com), and [Playctrl.me](https://playctrl.me)
2. Make sure in CtrlEm Settings, Command Logs is ON and Daily Log File is OFF
3. Make sure in Playctrl.me Settings, Enable Command Logging is ON
4. Install [Python 3.13](https://www.python.org) or Newer
5. Open CMD
<details>
<summary>If using CUI</summary>

6. Run `pip install requests apng pillow`
7. Download the wp_engine_bridge_CUI Folder from this Github
8. Open config.json and Configure the script
	-  **CTRLEM_LOG_PATH** = (Your CtrlEm commands.log File)
	-  **PLAYCTRL_LOG_FOLDER** = (Your Playctrl.me logs Folder)
	-  **WALLPAPER_WORKSPACE_DIR** = (Folder to use to cache Wallpapers)
	-  **WE_EXE_PATH** = (Path to wallpaper engine .exe) *Already pathed to Steam Default Installation
	-  **MONITOR_WIDTH / HEIGHT** = (Size of your monitor) *Dual Monitor might work, I have 16/10 and 16/9 monitors and looks fine, your mileage may vary*
	-  **DEBUG_MODE** = outputs extra information to console
9. Run wp_engine_bridge_CUI.py
</details>
<details>
<summary>If using GUI</summary> 

6. Run `pip install requests apng pillow customtkinter psutil`
7. Download the Wallpaper Bridge from [Latest Releases](https://github.com/TYRS0/Wallpaper_Engine_Bridge/releases/latest)
8. Run gui.pyw
9. Configure settings page
	- **CtrlEm Log** = (Your CtrlEm commands.log File)
	- **CtrlEm Exe Path** = (Your CtrlEm .exe File)
	- **WE EXE Path** = (Path to Wallpaper Engine .exe) *Steam's default installation is prefilled*
	- **PlayCtrl Log Folder** = (Your Playctrl.me Logs Folder)
	- **PlayCtrl Exe Path** = (Your Playctrl.me .exe File)
	- **Monitor Size** = (Size of your monitor) *Dual Monitor might work, I have 16/10 and 16/9 monitors and looks fine, your mileage may vary*
	- **Toggle Debug Mode** = (Shows Debug Console)
10. Click Save
</details>
