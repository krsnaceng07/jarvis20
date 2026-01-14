try:
    from livekit.plugins.google.beta import realtime
    from livekit.plugins.silero import VAD
    print("Found Google Realtime and Silero VAD")
    
    try:
        from livekit.agents.multimodal import MultimodalAgent
        print("MultimodalAgent found in livekit.agents.multimodal")
    except ImportError:
        print("MultimodalAgent NOT found in livekit.agents.multimodal")

except Exception as e:
    print(f"Error: {e}")
