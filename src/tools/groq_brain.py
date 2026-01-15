from livekit.agents import function_tool
import logging
import os
import json
import asyncio
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GroqAPIKey = os.getenv("GROQ_API_KEY")
client = None
if GroqAPIKey:
    client = Groq(api_key=GroqAPIKey)

SYSTEM_PROMPT = """
You are the "Cortex" (Logic Brain) of Jarvis.
Your Goal: Translate vague, complex, or Nepali user requests into PRECISE Python Function Calls.

**AVAILABLE TOOLS:**
1. `google_search(query)`: For general info (E.g. "Who is PM of Nepal?").
2. `open_app(app_name)`: To open software. (Input: "Chrome khola", "Notepad open").
3. `close_app(app_name)`: To close software. (Input: "Yo banda gara", "Close this").
4. `minimize_window(title)`: Minimize active window. (Input: "Lukaideu", "Minimize").
5. `play_youtube_tool(query)`: Play music/video. (Input: "Gana bajau", "Song sunau").
6. `open_url(url)`: Show visual results. (Input: "Dekhao", "Show me", "Kholi deu").
7. `system_control_tool(command)`: (Input: "Awaj bada", "Ujyalo ghata", "Sutne bela vo").
8. `folder_file(command)`: File operations.

**NEPALI INTENT MAPPING (CRITICAL):**
- **"Bajau", "Sunau", "Laga", "Play":** -> `play_youtube_tool("QUERY")`
  - Example: "Nepali lok dohori bajau" -> `play_youtube_tool("Nepali lok dohori")`
  
- **"Dekhao", "Herne", "Khol", "Open":** -> `open_url("LINK")` or `open_app("APP")`
  - Example: "Search result dekhao" -> `open_url("https://google.com/search?q=...")`
  - Example: "Facebook khola" -> `open_url("https://facebook.com")`

- **"Banda", "Band", "Close", "Hata":** -> `close_app("TARGET")`
  - Example: "Yo banda gara" -> `close_app("active_window")`
  - Example: "Gaana banda gara" -> `close_app("chrome")` (Be smart: Music implies Browser)
  
- **"Khoj", "K ho", "Pata laga", "Search":** -> `google_search("QUERY")` (If text answer wanted) OR `open_url(...)` (If visual wanted).

- **"Chota", "Lukau", "Minimize":** -> `minimize_window("active_window")`

**SYSTEM APP KNOWLEDGE:**
- "Settings" / "Control Panel": -> `close_app("Settings")` (I handle UWP apps specially).
- "Calculator" / "Hisab Kitab": -> `close_app("Calculator")` or `open_app("Calculator")`.

**RULES:**
1. Analyze the *meaning*, not just words. "Malai bore lagyo, gana sunna man cha" -> `play_youtube_tool("Entertaining songs")`.
2. If input is strictly Chat ("K cha khabar", "Timro naam k ho"), Output: "CHAT: [Reply in Nepali]".
3. Return ONLY the function string.

**OUTPUT FORMAT:**
`tool_name("args")`
"""

import pygetwindow as gw

def groq_inference(query: str, context: str = "", active_windows: list = None):
    if not client:
        return "❌ Groq API Key missing."

    window_context = f"Active Windows: {active_windows}" if active_windows else "Active Windows: [Unknown]"
    full_prompt = f"User Request: '{query}'\nVisual Context: {context}\n{window_context}\n\nExecute Action:"

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1, 
            max_tokens=200
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "rate limit" in error_str:
            logger.warning("⚠️ Groq Rate Limit Exceeded.")
            return "❌ Groq Rate Limit Exceeded. Switching to Basic Logic."
        
        logger.error(f"Groq Error: {e}")
        return f"❌ Groq Brain Error: {e}"

@function_tool()
async def ask_groq_planner(query: str, context: str = ""):
    """
    Use this tool when the user's command is VAGUE, in NEPALI, or requires Complex Reasoning.
    Groq will decide the exact tool to run.
    """
    try:
        # Debug log
        print(f"🧠 GROQ PLANNER: Processing '{query}'")
        if not query: return "❌ Query is empty."
        
        # SENSORY INPUT: Capture Window State
        try:
            current_windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
        except:
            current_windows = []

        result = await asyncio.to_thread(groq_inference, query, context, current_windows)
        print(f"🧠 GROQ RESULT: {result}")
        return result
    except Exception as e:
        logger.error(f"Critical Groq Tool Error: {e}")
        return f"❌ Critical Groq Error: {e}"
