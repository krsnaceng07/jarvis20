import os
import asyncio
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation, silero

# Import your custom modules
from src.core.prompts import get_system_prompts
from src.tools.google_search import google_search, get_current_datetime
from src.tools.weather import get_weather
from src.tools.window_ctrl import open_app, close_app, folder_file
from src.tools.file_opener import Play_file
from src.tools.inputs import (
    move_cursor_tool, mouse_click_tool, scroll_cursor_tool, 
    type_text_tool, press_key_tool, swipe_gesture_tool, 
    press_hotkey_tool, control_volume_tool
)
from src.tools.content import generate_content_tool
from src.tools.media import play_youtube_tool, search_youtube_tool
from src.tools.system_ctrl import system_control_tool
from src.memory.loop import MemoryExtractor

load_dotenv()


class Assistant(Agent):
    def __init__(self, chat_ctx, instructions) -> None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        super().__init__(chat_ctx = chat_ctx,
                        instructions=instructions,
                        llm=google.beta.realtime.RealtimeModel(
                            model=model_name,
                            voice="Charon"
                        ),
                        tools=[
                                google_search,
                                get_current_datetime,
                                get_weather,
                                open_app,
                                close_app,
                                folder_file,
                                Play_file,
                                move_cursor_tool,
                                mouse_click_tool,
                                scroll_cursor_tool,
                                type_text_tool,
                                press_key_tool,
                                press_hotkey_tool,
                                control_volume_tool,
                                swipe_gesture_tool,
                                generate_content_tool,
                                play_youtube_tool,
                                search_youtube_tool,
                                system_control_tool]
                                )

async def entrypoint(ctx: agents.JobContext):
    # Initialize session with optimized turn detection
    session = AgentSession(
        preemptive_generation=True,
        turn_detection=silero.VAD.load(
            min_silence_duration=0.5, # Reduced for faster response
        )
    )
    
    # Load system prompts asynchronously
    instructions_prompt, reply_prompts = await get_system_prompts()
    
    # getting the current memory chat
    current_ctx = session.history.items
    
    # Start the agent with Silero VAD for much faster speech detection (instant feel)
    await session.start(
        room=ctx.room,
        agent=Assistant(chat_ctx=current_ctx, instructions=instructions_prompt),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )
    
    # Generate initial greeting
    await session.generate_reply(
        instructions=reply_prompts
    )
    
    # Run memory loop in background so it doesn't block turn-taking
    conv_ctx = MemoryExtractor()
    asyncio.create_task(conv_ctx.run(current_ctx))
    
    # Keep the entrypoint alive by waiting for the participant to connect/disconnect
    # or simply waiting on the room connection state properly.
    # Since we are in an agent session, we can just wait for the room to disconnect.
    # We use a signal from the room object if available, or just wait indefinitely
    # until the process is killed.
    
    # Simple keep-alive that works in both console (Mock room) and production
    try:
        await ctx.wait_for_participant()
    except Exception:
        # Fallback if wait_for_participant isn't implemented in Mock or needed
        pass

    while True:
        await asyncio.sleep(1)
    


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
