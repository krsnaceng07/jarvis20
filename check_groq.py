import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

try:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in .env")
        exit(1)

    client = Groq(api_key=api_key)
    print("⏳ Checking Groq Status...")
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10
    )
    print("✅ STATUS: ONLINE (Quota Available)")
    print(f"Reply: {completion.choices[0].message.content}")

except Exception as e:
    error_str = str(e).lower()
    if "429" in error_str or "rate limit" in error_str:
        print("❌ STATUS: RATE LIMIT EXCEEDED (Quota Over)")
    else:
        print(f"❌ STATUS: ERROR ({e})")
