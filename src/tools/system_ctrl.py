import logging
import keyboard
import re
import psutil
from livekit.agents import function_tool
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

logger = logging.getLogger(__name__)

@function_tool()
async def get_battery_status() -> str:
    """
    Get accurate Battery %, Charging Status, CPU and RAM usage.
    MUST USE for: "Battery kitna hai", "Charge check", "System stats".
    DO NOT USE VISION for battery checks.
    """
    try:
        battery = psutil.sensors_battery()
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        status = []
        
        # Battery Info
        if battery:
            plugged = "Plugged In ⚡" if battery.power_plugged else "Running on Battery 🔋"
            status.append(f"Battery: {battery.percent}% ({plugged})")
        else:
            status.append("Battery: Desktop (No Battery Detected)")

        # CPU/RAM Info
        status.append(f"CPU Usage: {cpu_percent}%")
        status.append(f"RAM Usage: {memory.percent}%")

        return "\n".join(status)
    except Exception as e:
        return f"❌ Error getting system info: {e}"

def set_absolute_volume(level: int):
    """Sets system volume to a specific percentage (0-100)."""
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Clamp value between 0 and 100
        level = max(0, min(100, level))
        scalar = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return True
    except Exception as e:
        logger.error(f"pycaw error: {e}")
        return False

@function_tool()
async def system_control_tool(command: str) -> str:
    """
    Controls system volume. Supports relative (up/down) and absolute levels.
    
    Examples:
    - "volume up", "volume down", "mute", "unmute"
    - "set volume to 80", "volume 50 percent", "volume 100 karo"
    """
    command = command.lower().strip()
    
    # Check for specific number in command (Absolute Volume)
    # Extracts number like "80" from "volume 80"
    match = re.search(r'\b(\d{1,3})\b', command)
    if match:
        try:
            level = int(match.group(1))
            if set_absolute_volume(level):
                return f"✅ Volume set to {level}%."
        except Exception:
            pass

    try:
        if "mute" in command and "unmute" not in command:
            keyboard.press_and_release("volume mute")
            return "✅ Muted."
        elif "unmute" in command:
            keyboard.press_and_release("volume mute")
            return "✅ Unmuted."
        elif any(x in command for x in ["volume up", "increase", "badha", "tez", "up"]):
             # Fast relative increase
            for _ in range(5):
                keyboard.press_and_release("volume up")
            return "✅ Volume Increased."
        elif any(x in command for x in ["volume down", "decrease", "kam", "slow", "down", "dheere"]):
             # Fast relative decrease
            for _ in range(5):
                keyboard.press_and_release("volume down")
            return "✅ Volume Decreased."
        else:
             # Fallback if no number and no known keyword
             return f"❌ Unknown volume command: {command}"
            
    except Exception as e:
        logger.error(f"System command failed: {e}")
        return f"❌ Error: {e}"
