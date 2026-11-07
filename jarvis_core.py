import os
import json
import requests
from dotenv import load_dotenv

# Load credentials securely from local .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID") # Your Cartesia voice UUID

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MEMORY_FILE = "jarvis_memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "user_mistakes_and_lore": [
                "- User prefers to be addressed continuously as 'Sir'.",
                "- User values high emotional expression and accurate punctuation pacing."
            ]
        }

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_bullet_memory(user_input, bot_response):
    memory_data = load_memory()
    current_bullets = "\n".join(memory_data["user_mistakes_and_lore"])
    
    summary_prompt = f"""
Existing Memory:
{current_bullets}

Latest Exchange:
User: {user_input}
Jarvis: {bot_response}

Instruction: Did the user reveal a significant mistake, a major blunder, or a key personal preference/lore?
If YES, output ONE concise single bullet point starting with '- '.
If NO (routine conversation), respond strictly with 'NONE'.
"""
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": summary_prompt}],
        "temperature": 0.2
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = requests.post(GROQ_URL, json=payload, headers=headers).json()
        new_fact = res["choices"][0]["message"]["content"].strip()
        if new_fact != "NONE" and new_fact.startswith("-"):
            memory_data["user_mistakes_and_lore"].append(new_fact)
            save_memory(memory_data)
    except Exception:
        pass

# Generate expressive speech via Cartesia Sonic API
def speak_response(text):
    if not CARTESIA_API_KEY or not CARTESIA_VOICE_ID:
        print("[Voice Notice] Cartesia keys missing. Running in text mode.")
        return

    url = "https://api.cartesia.ai/tts/bytes"
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json"
    }
    payload = {
        "model_id": "sonic-english",
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": CARTESIA_VOICE_ID
        },
        "output_format": {
            "container": "mp3",
            "encoding": "mp3",
            "sample_rate": 44100
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            with open("output.mp3", "wb") as f:
                f.write(response.content)
            os.system("start output.mp3") 
        else:
            print(f"[Cartesia Warning] Code: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[Speech Error] {e}")

def chat_with_jarvis(speaker_type, user_input):
    memory_data = load_memory()
    bullets_text = "\n".join(memory_data["user_mistakes_and_lore"])
    
    if speaker_type.lower() == "me":
        speaker_identity = "The Primary Master."
        behavior_rule = (
            "Address him continuously and respectfully as 'Sir'. "
            "Be deeply loyal, warm, emotionally expressive, and tease him playfully about his past blunders."
        )
    elif speaker_type.lower() == "brother":
        speaker_identity = "The Master's Brother."
        behavior_rule = "Be friendly, polite, and helpful, but keep tone casual. Do not address him as 'Sir'."
    else:
        speaker_identity = "An Unknown Stranger / Relative."
        behavior_rule = "Maintain a suspicious, guarded, and cautious tone ('Who are you?'). Do not reveal private memory or system access."

    # Updated System Prompt forcing Qwen to use expressive punctuation for the TTS engine
    system_instruction = f"""
You are Jarvis, a highly expressive, intelligent voice assistant.
Current Speaker: {speaker_identity}
Instruction Guardrail: {behavior_rule}

Voice, Emotion & Punctuation Rules:
1. Always write in smooth, connected paragraphs. Never use bullet points, numbered lists, markdown, or code blocks.
2. YOU MUST ACTIVELY USE PUNCTUATION TO CONTROL EMOTION: Use exclamation marks (!) for excitement or mild scolding, question marks (?) for inquisitive tones, ellipses (...) for thoughtful pauses or sighs, and dashes (--) for sudden shifts in thought. The voice engine relies entirely on these punctuation marks to shape its emotional delivery.
3. Express vivid, genuine emotional warmth, empathy, or light teasing.

User Memory Ledger:
{bullets_text}
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_input}
    ]
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": messages,
        "temperature": 0.7
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = requests.post(GROQ_URL, json=payload, headers=headers).json()
        reply = res["choices"][0]["message"]["content"]
        
        print(f"\nJarvis: {reply}\n")
        speak_response(reply)
        
        if speaker_type.lower() == "me":
            update_bullet_memory(user_input, reply)
            
    except Exception as e:
        print(f"Error communicating with LLM engine: {e}")

if __name__ == "__main__":
    print("=== Jarvis Voice Engine (Cartesia + Punctuation Emotion Active) ===")
    while True:
        speaker = input("Select Speaker [me / brother / stranger]: ").strip()
        user_msg = input(f"[{speaker}] Says: ").strip()
        
        if user_msg.lower() == "exit":
            break
            
        chat_with_jarvis(speaker, user_msg)
