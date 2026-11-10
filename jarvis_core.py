import os
import json
import subprocess
import platform
import speech_recognition as sr
from groq import Groq
from cartesia import Cartesia

# ---------------------------------------------------------
# CONFIGURATION & INITIALIZATION
# ---------------------------------------------------------
WAKE_WORD = "jarvis"
MEMORY_FILE = "memory.json"
CARTESIA_VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b" # Default Cartesia Voice ID

# Initialize API Clients
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
cartesia_client = Cartesia(api_key=os.environ.get("CARTESIA_API_KEY"))

# ---------------------------------------------------------
# MEMORY SYSTEM
# ---------------------------------------------------------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(user_input, assistant_response):
    memory = load_memory()
    memory.append({"user": user_input, "jarvis": assistant_response})
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

# ---------------------------------------------------------
# TEXT-TO-SPEECH (CARTESIA) & AUDIO PLAYBACK
# ---------------------------------------------------------
def speak(text):
    print(f"Jarvis: {text}")
    output_filename = "response.wav"
    
    try:
        # Generate speech using Cartesia API
        audio = cartesia_client.tts.generate(
            model_id="sonic-latest",
            transcript=text,
            voice=CARTESIA_VOICE_ID,
            output_format={
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100
            }
        )
        audio.write_to_file(output_filename)
        
        # Play audio based on OS environment (handles Termux / Linux / Windows)
        if "ANDROID_ARGUMENT" in os.environ or os.path.exists("/data/data/com.termux"):
            # Termux environment playback via mpv or termux-media-player
            subprocess.run(["mpv", "--really-quiet", output_filename], stderr=subprocess.DEVNULL)
        elif platform.system() == "Windows":
            import winsound
            winsound.PlaySound(output_filename, winsound.SND_FILENAME)
        else:
            # Standard Linux / macOS playback
            subprocess.run(["aplay", output_filename], stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"[Speech Error]: {e}")

# ---------------------------------------------------------
# BRAIN (GROQ REASONING)
# ---------------------------------------------------------
def process_query(user_text):
    memory = load_memory()
    
    # Formulate prompt with conversation history context
    messages = [
        {"role": "system", "content": "You are Jarvis, a concise, helpful, and highly intelligent local AI assistant."}
    ]
    
    # Add last 5 interactions from history
    for item in memory[-5:]:
        messages.append({"role": "user", "content": item["user"]})
        messages.append({"role": "assistant", "content": item["jarvis"]})
        
    messages.append({"role": "user", "content": user_text})

    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.6,
        max_tokens=200
    )
    
    response = completion.choices[0].message.content
    save_memory(user_text, response)
    return response

# ---------------------------------------------------------
# SENSES (STT & WAKE WORD LISTENER)
# ---------------------------------------------------------
def listen():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        print("\n[Listening in background... Say 'Jarvis' to activate]")
        
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=5)
                text = recognizer.recognize_google(audio).lower()
                
                # Zero-listening condition: Ignore everything unless wake word is present
                if WAKE_WORD in text:
                    print(f"\n[Wake word detected! Raw audio text: '{text}']")
                    
                    # Extract query following the wake word
                    query = text.split(WAKE_WORD, 1)[-1].strip()
                    
                    if not query:
                        speak("Yes?")
                        # Capture active query if user paused after saying "Jarvis"
                        audio_query = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        query = recognizer.recognize_google(audio_query)
                    
                    print(f"User: {query}")
                    response = process_query(query)
                    speak(response)
                    
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[Speech Service Error]: {e}")
                continue
            except KeyboardInterrupt:
                print("\n[Shutting down Jarvis.]")
                break

if __name__ == "__main__":
    listen()
