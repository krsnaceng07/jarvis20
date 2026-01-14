import asyncio
import os
from Jarvis_prompts import get_system_prompts

async def main():
    print("--- FETCHING PROMPTS ---")
    instructions, reply = await get_system_prompts()
    
    print("\n--- INSTRUCTIONS PROMPT ---")
    print(instructions)
    print("\n--- REPLY PROMPT ---")
    print(reply)

if __name__ == "__main__":
    asyncio.run(main())
