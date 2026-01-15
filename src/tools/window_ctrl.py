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

import webbrowser

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
async def open_app(app_title: str, force_new: bool = False) -> str:
    """
    Opens a desktop app using realistic keyboard interaction (Win -> Type -> Enter).
    Mimics a human user searching for the app.

    Args:
        app_title: Name of the app to open (e.g., "Notepad", "Chrome").
        force_new: Set to True ONLY if the user explicitly asks to open a NEW instance or confirms to open again.

    Example prompts:
    - "Notepad खोलो" -> force_new=False
    - "Chrome open करो" -> force_new=False
    - "Open another Notepad" -> force_new=True
    - "Haan, naya kholo" (Yes, open new) -> force_new=True
    """
    import pyautogui
    
    app_title_l = app_title.lower().strip()
    
    # Clean up title for better typing accuracy
    best_match, score = process.extractOne(app_title_l, APP_MAPPINGS.keys())
    if score > 80:
        search_term = best_match # Use known good name
    else:
        search_term = app_title # Use user input if no match
        
    # Check if already running (to prevent accidental double-opens)
    # Exception: "Settings" is a UWP app and handles single-instance natively. 
    # Checking for it causes false positives due to background processes.
    if gw and not force_new and search_term.lower() != "settings":
        try:
            # Fuzzy Match against ALL open windows
            all_titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
            match_title, match_score = process.extractOne(search_term, all_titles)
            
            # Check 1: Direct Substring Match (Most Reliable)
            # SPECIAL CASE: Antigravity (Input might be "Antigravity Agent")
            check_term = search_term.lower()
            if "antigravity" in check_term:
                check_term = "antigravity" # Force simplest term
                
            for t in all_titles:
                if check_term in t.lower():
                     logger.info(f"✅ Found existing window via SUBSTRING: '{t}'")
                     return f"⚠️ I found an open window named '{t}'. ASK THE USER: '{t} is already open. Do you want to open a new instance?'"

            # Check 2: High Confidence Fuzzy Match (Backup)
            if match_score > 80: 
                logger.info(f"ℹ️ '{search_term}' matches '{match_title}' ({match_score}%). Asking confirmation.")
                return f"⚠️ '{search_term}' matches '{match_title}'. ASK THE USER: '{match_title} is already open. Do you want to open a new instance?'"
        except Exception as e:
            logger.warning(f"Could not check existing windows: {e}")

    logger.info(f"⌨️  Human-Mode: Opening '{search_term}' via keyboard...")
    
    try:
        # Step 1: Open Start Menu
        pyautogui.press('win')
        await asyncio.sleep(0.5) # Wait for UI animation
        
        # Step 2: Type the app name slowly (Human-like)
        pyautogui.write(search_term, interval=0.1) 
        await asyncio.sleep(0.8) # Wait for search results
        
        # Step 3: Launch
        pyautogui.press('enter')
        
        # Step 4: Fast Return (User requested speed)
        await asyncio.sleep(0.5) 
        return f"✅ Command sent: Opening '{search_term}'..."
            
    except Exception as e:
        logger.error(f"❌ Keyboard simulation failed: {e}")
        return f"❌ Failed to open '{app_title}'. Error: {e}"

@function_tool()
async def close_app(window_title: str) -> str:
    """
    Closes an application by finding it and sending a close signal.
    Mimics human behavior but ensures the app actually closes.

    Example prompts:
    - "Notepad बंद करो"
    - "Close VLC"
    """
    import pyautogui
    
    logger.info(f"⌨️  Human-Mode: Closing '{window_title}'...")
    
    search_term = window_title.lower().strip()
    
    # Specific handling for common apps
    if search_term == "youtube":
        has_youtube = any("youtube" in w.title.lower() for w in gw.getAllWindows() if w.title)
        if not has_youtube:
            search_term = "chrome" 
    
    # NEW: Handle "Search", "Google", "Browser" requests
    if search_term in ["search", "google", "browser", "internet"]:
        search_term = "chrome"

    if search_term in ["code", "vs code", "vscode"]:
        search_term = "visual studio code"
    elif search_term == "notepad":
         pass

    if not gw:
        return "❌ pygetwindow not available to find window."

    # Strategy 1: Find ANY visible window containing the search term
    target_window = None
    try:
        all_windows = gw.getAllWindows()
        for w in all_windows:
            if search_term in w.title.lower() and getattr(w, 'isVisible', True) and w.title.strip():
                target_window = w
                break # Close the first matching one
    except Exception as e:
        logger.error(f"Error listing windows: {e}")

    # Strategy 1.5: UWP / Special Apps Fallback (Blind Kill)
    # If "Settings" or known UWP apps are requested but not found via title, kill process directly.
    if not target_window:
        if "setting" in search_term: # Catch "Settings", "System Settings"
            logger.info("⚙️ Attempting to close Settings via TaskKill...")
            os.system("taskkill /IM SystemSettings.exe /F")
            await asyncio.sleep(1)
            return "✅ Settings closed (via Force Kill)."
            
        if "calculator" in search_term:
             os.system("taskkill /IM CalculatorApp.exe /F")
             return "✅ Calculator closed."

    if target_window:
        original_title = target_window.title
        target_hwnd = getattr(target_window, '_hWnd', None) # Get Handle (Robust ID)

        try:
            # Attempt 1: Focus and Alt+F4 (Human-like)
            if target_window.isMinimized:
                target_window.restore()
            target_window.activate()
            await asyncio.sleep(0.5)
            pyautogui.hotkey('alt', 'f4')
            
            # VERIFICATION STEP (Crucial)
            await asyncio.sleep(1.0) # Wait for close
            
            # Check if it's actually gone using HWND (Handle) if available, else Title
            all_current_windows = gw.getAllWindows()
            if target_hwnd:
                still_exists = any(getattr(w, '_hWnd', 0) == target_hwnd for w in all_current_windows)
            else:
                still_exists = any(w.title == original_title for w in all_current_windows)

            if not still_exists:
                return f"✅ Verified: '{original_title}' is closed."
            else:
                # Retry: Direct Close
                target_window.close()
                await asyncio.sleep(0.5)
                return f"⚠️ Force Closed '{original_title}'. Please check."

        except Exception as e:
            return f"❌ Failed to close '{target_window.title}': {e}"
    else:
        return f"❌ Could not find any running app matches '{search_term}'."

@function_tool()
async def minimize_window(window_title: str) -> str:
    """
    Minimizes a specific window.
    Example: "Minimize VS Code", "Hide Chrome", "Minimize Antigravity"
    """
    print(f"🔧 TOOL: minimize_window called for '{window_title}'") # Debug
    
    if not gw: return "❌ pygetwindow not available."
    
    search_term = window_title.lower().strip()
    
    try:
        # 1. Get all visible windows
        all_windows = [w for w in gw.getAllWindows() if w.title and w.isVisible]
        if not all_windows:
            return "❌ No visible windows found."

        # 2. Try Exact/Substring Match
        for w in all_windows:
            if search_term in w.title.lower():
                if not w.isMinimized:
                    w.minimize()
                    print(f"✅ Minimized (Exact): {w.title}")
                    return f"✅ Minimized '{w.title}'."
                return f"ℹ️ '{w.title}' is already minimized."

        # 3. Try Fuzzy Match (Best Guess)
        titles = [w.title for w in all_windows]
        best_match_title, score = process.extractOne(window_title, titles)
        
        if score > 70:
            for w in all_windows:
                if w.title == best_match_title:
                    w.minimize()
                    print(f"✅ Minimized (Fuzzy {score}%): {w.title}")
                    return f"✅ Minimized '{w.title}' (Match: {score}%)."

        return f"❌ Could not find window '{window_title}'. Open: {', '.join(titles[:5])}..."
    except Exception as e:
        return f"❌ Error minimizing: {e}"

@function_tool()
async def maximize_window(window_title: str) -> str:
    """
    Maximizes/Restores a specific window.
    Example: "Maximize Notepad", "Bring Chrome back"
    """
    if not gw: return "❌ pygetwindow not available."
    
    search_term = window_title.lower().strip()
    if search_term in ["code", "vs code", "vscode"]: search_term = "visual studio code"
    
    try:
        # Strategy 1: Direct Match
        windows = gw.getWindowsWithTitle(search_term)
        
        # Strategy 2: Manual Case-Insensitive Search
        if not windows:
            all_wins = gw.getAllWindows()
            for w in all_wins:
                if search_term in w.title.lower() and w.title.strip():
                    windows = [w]
                    break

        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.maximize()
            w.activate()
            return f"✅ Maximized '{w.title}'."
        return f"❌ Could not find window '{window_title}' to maximize."
    except Exception as e:
        return f"❌ Error maximizing: {e}"

@function_tool()
async def list_open_windows() -> str:
    """
    Lists all currently visible open windows.
    Use this BEFORE trying to minimize/maximize if you are unsure of the exact window title.
    """
    if not gw: return "❌ pygetwindow not available."
    try:
        # Strict Filtering: Must have title, be visible, and have non-zero area (avoids 1x1 background processes)
        windows = []
        for w in gw.getAllWindows():
            if w.title and w.isVisible and w.width > 30 and w.height > 30:
                 # Exclude common ghost windows
                if w.title.strip() not in ["Program Manager", "Settings", "Default IME", "MSCTFIME UI"]:
                    windows.append(w.title)
        
        return f"Open Windows: {', '.join(windows)}"
    except Exception as e:
        return f"❌ Error listing windows: {e}"

@function_tool()
async def open_url(url: str) -> str:
    """
    Opens a URL in the default web browser.
    Useful when user says "Show search results", "Open Google", or "Open YouTube link".
    """
    try:
        webbrowser.open(url)
        return f"✅ Opened URL: {url}"
    except Exception as e:
        return f"❌ Failed to open URL: {e}"

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
