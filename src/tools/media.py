from livekit.agents import function_tool
import asyncio
import logging
import webbrowser
import pywhatkit

logger = logging.getLogger(__name__)

# Helper functions moved from automation_impl.py
def YouTubeSearch(topic):
    url = f"https://www.youtube.com/results?search_query={topic}"
    webbrowser.open(url)
    return True

def PlayYoutube(query):
    try:
        pywhatkit.playonyt(query)
        return True
    except Exception as e:
        logger.error(f"Error playing YouTube video: {e}")
        return False

@function_tool()
async def play_youtube_tool(query: str) -> str:
    """
    Plays a video on YouTube based on the search query.
    
    Use this tool when the user says:
    - "Play Despacito on YouTube"
    - "YouTube par Arijit Singh ke gaane chalao"
    - "Play funny cats video"
    """
    try:
        success = await asyncio.to_thread(PlayYoutube, query)
        if success:
            return f"✅ Playing '{query}' on YouTube."
        else:
            return "❌ Failed to play YouTube video."
    except Exception as e:
        return f"❌ Error: {e}"

@function_tool()
async def search_youtube_tool(query: str) -> str:
    """
    Searches for a topic on YouTube and opens the results page.
    """
    try:
        success = await asyncio.to_thread(YouTubeSearch, query)
        if success:
            return f"✅ Opened YouTube search for '{query}'"
        else:
            return "❌ Failed to search YouTube."
    except Exception as e:
        return f"❌ Error: {e}"
