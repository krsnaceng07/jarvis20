import os
import asyncio
import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation, silero
from google.genai import types # Required for Vision Payload
from src.vision.screen_capture import ScreenCapture
from livekit.agents import function_tool # Required for vision_tool

# Import your custom modules
from src.core.prompts import get_system_prompts
from src.tools.google_search import google_search, get_current_datetime
from src.tools.weather import get_weather
from src.tools.window_ctrl import open_app, close_app, folder_file, minimize_window, maximize_window, list_open_windows, open_url
from src.tools.window_ctrl import play_file as Play_file 
from src.tools.inputs import (
    move_cursor_tool, mouse_click_tool, scroll_cursor_tool, 
    type_text_tool, press_key_tool, swipe_gesture_tool, 
    press_hotkey_tool, mouse_move_to_coords
)
from src.tools.content import generate_content_tool
from src.tools.media import play_youtube_tool, search_youtube_tool
from src.tools.system_ctrl import system_control_tool, get_battery_status
from src.tools.groq_brain import ask_groq_planner
from src.memory.loop import MemoryExtractor

load_dotenv()

# Vision Manager Implementation
class VisionManager:
    def __init__(self, agent_llm):
        self.llm = agent_llm
        self.capturer = ScreenCapture()
        self.active_task = None
        self.is_active = False

    async def _stream_loop(self, duration: int):
        self.is_active = True
        print(f"👀 Vision Enabled for {duration}s")
        start_time = asyncio.get_event_loop().time()
        
        async for frame_bytes in self.capturer.start_capture(interval=1.0):
            if asyncio.get_event_loop().time() - start_time > duration:
                break
                
            # Inject Frame into Active Session
            sessions = list(self.llm._sessions)
            if sessions:
                session = sessions[0]
                try:
                    # Construct Realtime Input with JPEG Blob
                    realtime_input = types.LiveClientRealtimeInput(
                        media_chunks=[types.Blob(data=frame_bytes, mime_type="image/jpeg")]
                    )
                    # Use private _send_client_event (Hack but necessary for bypass)
                    if hasattr(session, '_send_client_event'):
                        session._send_client_event(realtime_input)
                        print(f"📸 Frame Sent: {len(frame_bytes)} bytes") # DEBUG
                    else:
                        print("⚠️ Cannot send vision frame: method '_send_client_event' not found")
                except Exception as e:
                    print(f"⚠️ Vision Push Error: {e}")
            else:
                print("⚠️ No Active Session for Vision (Sessions list empty)")

        self.is_active = False
        self.capturer.stop_capture()
        print("🙈 Vision Auto-Disabled")

    def enable(self, duration=15):
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
        self.active_task = asyncio.create_task(self._stream_loop(duration))
        return "Vision Enabled"

    def disable(self):
        if self.active_task:
            self.active_task.cancel()
        self.capturer.stop_capture()
        self.is_active = False
        return "Vision Disabled"

# Tool to control Vision
vision_manager = None # Global reference

@function_tool()
async def vision_tool(action: str) -> str:
    """
    Control Jarvis Vision ('Eyes').
    Use this when you need to see the screen (e.g. "read error", "what is this", "check app").
    
    Args:
        action: "on" (active for 15s) or "off"
    """
    global vision_manager
    if not vision_manager:
        return "❌ Vision Manager not initialized."
    
    if action.lower() == "on":
        vision_manager.enable()
        return "✅ Vision Enabled (Eyes Open)"
    else:
        vision_manager.disable()
        return "✅ Vision Disabled"

# Common Tools List
TOOLS = [
    google_search, get_current_datetime, get_weather,
    open_app, close_app, folder_file, 
    move_cursor_tool, mouse_click_tool, scroll_cursor_tool, 
    type_text_tool, press_key_tool, press_hotkey_tool, 
    swipe_gesture_tool, mouse_move_to_coords,
    generate_content_tool, play_youtube_tool, search_youtube_tool,
    system_control_tool, vision_tool, get_battery_status,
    minimize_window, maximize_window, ask_groq_planner, list_open_windows,
    open_url
]

class APIKeyManager:
    def __init__(self):
        self.keys = []
        if os.getenv("GOOGLE_API_KEY"):
            self.keys.append(os.getenv("GOOGLE_API_KEY"))
        i = 1
        while True:
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if key:
                if key not in self.keys:
                    self.keys.append(key)
            elif i > 10:
                break
            i += 1
        self.current_index = 0
        print(f"🔑 Loaded {len(self.keys)} Google API Keys.")

    def get_current_key(self):
        if not self.keys: return None
        return self.keys[self.current_index]

    def rotate_key(self):
        if not self.keys: return False
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"🔄 Switching to API Key Index: {self.current_index + 1}")
        return self.get_current_key()

class NativeAssistant(Agent):
    def __init__(self, chat_ctx, instructions, api_key=None) -> None:
        # Suppress Noisy Logs
        logging.getLogger("groq").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-preview-09-2025")
        
        # Initialize Realtime Model
        self.min_model = google.beta.realtime.RealtimeModel(
            model=model_name,
            voice="Aoede",
            api_key=api_key
        )
        
        # Initialize Vision Manager
        global vision_manager
        vision_manager = VisionManager(self.min_model)
        
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=instructions,
            llm=self.min_model,
            tools=TOOLS
        )

async def entrypoint(ctx: agents.JobContext):
    key_manager = APIKeyManager()
    instructions_prompt, reply_prompts = await get_system_prompts()
    
    while True:
        current_api_key = key_manager.get_current_key()
        if not current_api_key:
            print("❌ No Google API Keys found!")
            break

        print(f"🚀 Starting Native Agent Session (Key Index: {key_manager.current_index+1})")

        try:
            # Tuned VAD to prevent double responses
            vad = silero.VAD.load(
                min_silence_duration=0.6, # Reduced to 0.6 for snappy response
                prefix_padding_duration=0.3, # Reduced to 0.3 for lower latency
                min_speech_duration=0.3,  # Ignore very short noises
                activation_threshold=0.5, # Keep robust noise rejection
            )

            session = AgentSession(
                preemptive_generation=False, # Changed to False: Waits for full command to prevent double-processing
                turn_detection=vad
            )
            current_ctx = session.history.items 

            # Correctly Instantiate NativeAssistant
            agent_instance = NativeAssistant(
                chat_ctx=current_ctx, 
                instructions=instructions_prompt, 
                api_key=current_api_key
            )

            await session.start(
                room=ctx.room,
                agent=agent_instance,
                room_input_options=RoomInputOptions(
                    noise_cancellation=noise_cancellation.BVC()
                ),
            )
            
            # Initial Greeting
            await session.generate_reply(instructions=reply_prompts)
            
            # Memory Loop
            conv_ctx = MemoryExtractor()
            asyncio.create_task(conv_ctx.run(current_ctx))
            
            await ctx.wait_for_participant()
            print("👋 User disconnected.")
            break

        except Exception as e:
            error_str = str(e).lower()
            print(f"💥 Runtime Error: {e}")
            
            # Google Quota Error -> Rotate Key
            if "429" in error_str or "quota" in error_str or "1011" in error_str or "connectionclosed" in error_str:
                print(f"⚠️ Google API Error Detected. Rotating Key...")
                key_manager.rotate_key()
                await asyncio.sleep(0.5)
                continue
            
            raise e

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))