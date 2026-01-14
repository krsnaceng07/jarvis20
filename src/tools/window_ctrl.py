import os
import subprocess
import logging
import sys
import asyncio
from fuzzywuzzy import process
from livekit.agents import function_tool

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Setup encoding and logger
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App command map - UPDATED WITH PROPER PATHS
APP_MAPPINGS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": "chrome.exe",
    "vlc": "vlc.exe",
    "command prompt": "cmd.exe",
    "control panel": "control.exe",
    "settings": "start ms-settings:",
    "paint": "mspaint.exe",
    "vs code": "code.exe",
    "postman": "postman.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "photoshop": "photoshop.exe",
    "spotify": "spotify.exe",
    "whatsapp": "whatsapp.exe",
    "telegram": "telegram.exe",
    "discord": "discord.exe"
}

# -------------------------
# Improved focus utility
# -------------------------
async def focus_window(title_keyword: str) -> bool:
    if not gw:
        logger.warning("⚠ pygetwindow not available")
        return False

    await asyncio.sleep(2.5)  # Increased delay for slow apps
    title_keyword = title_keyword.lower().strip()
    
    # Try multiple times to find the window
    for attempt in range(5):
        try:
            # Method 1: Get windows with title
            windows = gw.getWindowsWithTitle(title_keyword)
            if windows:
                window = windows[0]
                if window.isMinimized:
                    window.restore()
                window.activate()
                logger.info(f"✅ Window focused: {window.title}")
                return True
            
            # Method 2: Check all windows
            for window in gw.getAllWindows():
                if title_keyword in window.title.lower():
                    if window.isMinimized:
                        window.restore()
                    window.activate()
                    logger.info(f"✅ Window focused: {window.title}")
                    return True
                    
            await asyncio.sleep(1)  # Wait before next attempt
        except Exception as e:
            logger.error(f"❌ Focus error: {e}")
            await asyncio.sleep(1)
    
    logger.warning(f"⚠ Could not focus window: {title_keyword}")
    return False

# Index items more efficiently
async def index_items(base_dirs):
    item_index = []
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
        try:
            # Use scandir for speed and avoid deep recursion unless necessary
            with os.scandir(base_dir) as it:
                for entry in it:
                    if entry.is_dir():
                        item_index.append({"name": entry.name, "path": entry.path, "type": "folder"})
                    elif entry.is_file():
                        item_index.append({"name": entry.name, "path": entry.path, "type": "file"})
        except Exception as e:
            logger.error(f"Error scanning {base_dir}: {e}")
    logger.info(f"✅ Indexed {len(item_index)} top-level items.")
    return item_index

async def search_item(query, index, item_type):
    filtered = [item for item in index if item["type"] == item_type]
    choices = [item["name"] for item in filtered]
    if not choices:
        return None
    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' with score {score}")
    if score > 70:
        for item in filtered:
            if item["name"] == best_match:
                return item
    return None

# File/folder actions
async def open_folder(path):
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.call(['xdg-open', path])
        await focus_window(os.path.basename(path))
    except Exception as e:
        logger.error(f"❌ Folder open error: {e}")

async def play_file(path):
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.call(['xdg-open', path])
        await focus_window(os.path.basename(path))
    except Exception as e:
        logger.error(f"❌ File open error: {e}")

async def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ Folder created: {path}"
    except Exception as e:
        return f"❌ Folder creation failed: {e}"

async def rename_item(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return f"✅ Renamed to {new_path}"
    except Exception as e:
        return f"❌ Rename failed: {e}"

async def delete_item(path):
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        return f"🗑️ Deleted: {path}"
    except Exception as e:
        return f"❌ Delete failed: {e}"

# Improved App control
@function_tool()
async def open_app(app_title: str) -> str:
    """
    Opens a desktop app like Notepad, Chrome, VLC, etc.

    Use this tool when the user asks to launch an application on their computer.
    Example prompts:
    - "Notepad खोलो"
    - "Chrome open करो"
    - "VLC media player चलाओ"
    - "Calculator launch करो"
    """
    app_title_l = app_title.lower().strip()
    
    # Find the best match for the app name
    best_match, score = process.extractOne(app_title_l, APP_MAPPINGS.keys())
    
    if score > 70:  # Lowered confidence threshold
        app_command = APP_MAPPINGS[best_match]
        logger.info(f"🔍 Opening app: {best_match} with command: {app_command}")
        
        try:
            # For system commands
            if app_command.startswith('start '):
                os.system(app_command)
            # For executable names (no path)
            elif not os.path.exists(app_command) and not '\\' in app_command and not '/' in app_command:
                subprocess.Popen(app_command, shell=True)
            # For full paths
            else:
                subprocess.Popen(app_command)
            
            # Wait for app to launch
            await asyncio.sleep(2)
            
            # Try to focus the window
            focused = await focus_window(best_match)
            if focused:
                return f"✅ '{best_match}' successfully opened and focused!"
            else:
                return f"⚠ '{best_match}' launched but couldn't focus window."
                
        except Exception as e:
            logger.error(f"❌ App launch failed: {e}")
            return f"❌ Failed to open '{best_match}': {str(e)}"
    else:
        # Try to open anyway using the input name
        try:
            subprocess.Popen(app_title_l, shell=True)
            await asyncio.sleep(2)
            focused = await focus_window(app_title_l)
            if focused:
                return f"✅ '{app_title}' opened successfully!"
            else:
                return f"⚠ '{app_title}' launched but couldn't focus."
        except:
            return f"❌ App '{app_title}' not found in my database."

@function_tool()
async def close_app(window_title: str) -> str:
    """
    Closes the applications window by its title.

    Use this tool when the user wants to close any app or window on their desktop.
    Example prompts:
    - "Notepad बंद करो"
    - "Close VLC"
    - "Chrome की window बंद कर दो"
    - "Calculator को बंद करो"
    """
    if not gw:
        return "❌ Window control not available"

    try:
        windows_closed = 0
        for window in gw.getAllWindows():
            if window_title.lower() in window.title.lower():
                window.close()
                windows_closed += 1
                await asyncio.sleep(0.5)
        
        if windows_closed > 0:
            return f"✅ Closed {windows_closed} window(s) containing '{window_title}'"
        else:
            return f"❌ No windows found with '{window_title}' in title"
    except Exception as e:
        return f"❌ Error closing window: {e}"

# Jarvis command logic
@function_tool()
async def folder_file(command: str) -> str:
    """
    Handles folder and file actions like open, create, rename, or delete based on user command.

    Use this tool when the user wants to manage folders or files using natural language.
    Example prompts:
    - "Projects folder बनाओ"
    - "OldName को NewName में rename करो"
    - "xyz.mp4 delete कर दो"
    - "Music folder खोलो"
    - "Resume.pdf चलाओ"
    """
    user_home = os.path.expanduser("~")
    folders_to_index = [
        "D:/", 
        "C:/Users/Public", 
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Downloads")
    ]
    index = await index_items(folders_to_index)
    command_lower = command.lower()

    if "create folder" in command_lower:
        folder_name = command.replace("create folder", "").strip()
        path = os.path.join("D:/", folder_name)
        return await create_folder(path)

    if "rename" in command_lower:
        parts = command_lower.replace("rename", "").strip().split("to")
        if len(parts) == 2:
            old_name = parts[0].strip()
            new_name = parts[1].strip()
            item = await search_item(old_name, index, "folder")
            if item:
                new_path = os.path.join(os.path.dirname(item["path"]), new_name)
                return await rename_item(item["path"], new_path)
        return "❌ Invalid rename command"

    if "delete" in command_lower:
        item = await search_item(command, index, "folder") or await search_item(command, index, "file")
        if item:
            return await delete_item(item["path"])
        return "❌ Item not found for deletion"

    if "folder" in command_lower or "open folder" in command_lower:
        item = await search_item(command, index, "folder")
        if item:
            await open_folder(item["path"])
            return f"✅ Folder opened: {item['name']}"
        return "❌ Folder not found"

    item = await search_item(command, index, "file")
    if item:
        await play_file(item["path"])
        return f"✅ File opened: {item['name']}"

    return "⚠ No matching item found"
