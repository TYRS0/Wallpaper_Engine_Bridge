This was made with Google Search AI Mode (Gemini 3)

Setup
  

1. Install and setup [Wallpaper Engine](https://store.steampowered.com/app/431960/Wallpaper_Engine/), [CtrlEm](https://ctrlem.com), and [Playctrl.me](https://playctrl.me) 
2. Make sure in CtrlEm Settings, Command Logs is ON and Daily Log File is OFF
3. Make sure in Playctrl.me Settings, Enable Command Logging is ON
4. Install [Python 3.13](https://www.python.org) or Newer
5. Open CMD
6. Run `pip install requests apng pillow`
7. Download the .py file from this Github
8. Open .py file and change Configurations
	 - CTRLEM_LOG_PATH = (Your CtrlEm commands.log File)
	 - WALLPAPER_WORKSPACE_DIR = (Folder to use to cache Wallpapers)
	 - PLAYCTRL_LOG_FOLDER = (Your Playctrl.me logs Folder)
	 - WE_EXE_PATH = (Path to wallpaper engine .exe) *Already pathed to Steam Default Installation
	 - MONITOR_WIDTH / HEIGHT = (Size of your monitor) *Dual Monitor might work, I have 16/10 and 16/9 monitors and looks fine, your mileage may vary
9. run File
