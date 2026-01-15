try:
    from livekit.plugins import elevenlabs
    print("✅ ElevenLabs Plugin Found")
except ImportError as e:
    print(f"❌ ElevenLabs Missing: {e}")

try:
    from livekit.agents.pipeline import VoicePipelineAgent
    print("✅ VoicePipelineAgent Found")
except ImportError as e:
    print(f"❌ VoicePipelineAgent Missing: {e}")

try:
    from livekit.agents.utils import VoicePipelineAgent as VPA_Utils
    print("✅ VoicePipelineAgent Found in utils")
except:
    pass

try:
    import livekit.agents
    print(f"ℹ️ LiveKit Agents Version: {livekit.agents.__version__}")
except:
    pass
