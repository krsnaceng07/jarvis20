from livekit.agents import function_tool
import asyncio
import logging
import os
import subprocess
from dotenv import load_dotenv
from groq import Groq
from livekit.agents import function_tool

# Initialize environment and Groq
load_dotenv()
GroqAPIKey = os.getenv("GroqAPIKey")
client = None
if GroqAPIKey:
    client = Groq(api_key=GroqAPIKey)

SystemChatBot = [{"role": "system", "content": f"Hello, I am {os.getenv('Username', 'User')}, a content writer. You have to write content like letters, codes, applications, essays, notes, songs, poems, etc."}]

def Content(topic):
    topic = topic.replace("content", "").strip()
    
    if not client:
        logger.error("Error: Groq API key not found.")
        return "Error: Unable to generate content - API key missing."
        
    try:
        messages = [{"role": "user", "content": f"{topic}"}]
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=SystemChatBot + messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=True,
            stop=None
        )

        answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content
        answer = answer.replace("</s>", "")
        
        # Save to file
        data_dir = "Data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        filepath = os.path.join(data_dir, f"{topic.lower().replace(' ', '_')}.txt")
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(answer)
            
        # Open in Notepad
        subprocess.Popen(['notepad.exe', filepath])
        return f"Content generated and opened in Notepad: {filepath}"
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return f"Error: Unable to generate content - {str(e)}"

@function_tool()
async def generate_content_tool(topic: str) -> str:
    """
    Generates content (essays, letters, code, etc.) and saves it to a file using AI.
    """
    try:
        result = await asyncio.to_thread(Content, topic)
        return result
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return f"❌ Failed to generate content: {e}"
