from livekit.agents import function_tool
import asyncio
import logging
from src.tools.automation_impl import System

logger = logging.getLogger(__name__)

@function_tool()
async def system_control_tool(command: str) -> str:
    """
    Controls system volume (mute, unmute, volume up, volume down).
    
    Use this tool for exact commands: "mute", "unmute", "volume up", "volume down".
    """
    try:
        success = await asyncio.to_thread(System, command)
        if success:
            return f"✅ System command '{command}' executed."
        else:
            return f"❌ Failed to execute system command '{command}'."
    except Exception as e:
        return f"❌ Error: {e}"
