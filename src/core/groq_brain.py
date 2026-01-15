from livekit.agents import function_tool
import logging
import os
import json
import asyncio
from groq import Groq
from dotenv import load_dotenv
import pygetwindow as gw

# Import the Separated Prompt
from src.core.groq_prompts import SYSTEM_PROMPT

# IMPORTS FOR EXECUTION (Must align with tool names)
from src.tools.google_search import google_search
from src.tools.window_ctrl import open_app, close_app, minimize_window, maximize_window, open_url
from src.tools.media import play_youtube_tool
from src.tools.system_ctrl import system_control_tool

load_dotenv()
logger = logging.getLogger(__name__)

GroqAPIKey = os.getenv("GROQ_API_KEY")
client = None
if GroqAPIKey:
    client = Groq(api_key=GroqAPIKey)

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
    Decides AND EXECUTES the correct tool based on user query.
    """
    try:
        # 1. Get Plan from Groq
        print(f"🧠 GROQ PLANNER: Thinking on '{query}'...")
        try:
            current_windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
        except:
            current_windows = []

        command_str = await asyncio.to_thread(groq_inference, query, context, current_windows)
        print(f"🧠 GROQ DECISION: {command_str}")

        # 2. Safety Check
        if "❌" in command_str or not command_str:
            return command_str

        # 3. EXECUTE THE COMMAND (The Magic Step)
        # We allow specific safe functions only
        safe_globals = {
            "google_search": google_search,
            "open_app": open_app,
            "close_app": close_app,
            "minimize_window": minimize_window,
            "maximize_window": maximize_window,
            "play_youtube_tool": play_youtube_tool,
            "open_url": open_url,
            "system_control_tool": system_control_tool
        }
        
        # Strip potential markdown code blocks
        clean_cmd = command_str.replace("```python", "").replace("```", "").strip()
        
        # Execute async function
        if "(" in clean_cmd and ")" in clean_cmd:
            # It's a function call like google_search("query")
            # We use eval to get the coroutine, then await it
            coroutine = eval(clean_cmd, safe_globals)
            if asyncio.iscoroutine(coroutine):
                result = await coroutine
                return f"✅ Action Taken: {result}"
            else:
                return f"✅ Done: {result}"
        else:
            # It might be a chat reply
            return clean_cmd

    except Exception as e:
        logger.error(f"Critical Groq Execution Error: {e}")
        return f"❌ Execution Failed: {e}"
