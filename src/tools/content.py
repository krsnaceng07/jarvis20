from livekit.agents import function_tool
import asyncio
import logging
from src.tools.automation_impl import Content

logger = logging.getLogger(__name__)

@function_tool()
async def generate_content_tool(topic: str) -> str:
    """
    Generates content (essays, letters, code, etc.) and saves it to a file using AI.
    
    Use this tool when the user asks to write or generate content like:
    - "Write an application for sick leave"
    - "Create a python script for calculator"
    - "Write an essay on global warming"
    
    The content will be saved to a text file and opened automatically.
    """
    try:
        result = await asyncio.to_thread(Content, topic)
        return result
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return f"❌ Failed to generate content: {e}"
