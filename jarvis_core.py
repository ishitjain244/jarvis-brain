import os
import subprocess
import platform
import requests
import speech_recognition as sr
from cartesia import Cartesia

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
WAKE_WORD = "jarvis"
RENDER_API_URL = "https://your-app-name.onrender.com/chat"  # Replace with your actual Render URL
CARTESIA_VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"

cartesia_client = Cartesia(api_key=os.environ.get("CARTESIA_API_KEY"))

# Local conversation session history for the client to pass along
session_history = []

# ---------------------------------------------------------
# TEXT-TO-SPEECH (CARTESIA)
# ---------------------------------------------------------
def speak(text):
    print(f"Jarvis: {text}")
    output_filename = "response.wav"
    
    try:
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
        
        # Cross-platform playback (Termux / Windows / Linux)
        if "ANDROID_ARGUMENT" in os.environ or os.path.exists("/data/data/com.termux"):
            subprocess.run(["mpv", "--really-quiet", output_filename], stderr=subprocess.DEVNULL)
        elif platform.system() == "Windows":
            import winsound
            winsound.PlaySound(output_filename, winsound.SND_FILENAME)
        else:
            subprocess.run(["aplay", output_filename], stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"[Speech Error]: {e}")

# ---------------------------------------------------------
# TALK TO RENDER BRAIN
# ---------------------------------------------------------
def ask_render_brain(query):
    global session_history
    payload = {
        "message": query,
        "history": session_history
    }
    
    try:
        response = requests.post(RENDER_API_URL, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "I received an empty response.")
            
            # Update local session history log
            session_history.append({"user": query, "jarvis": answer})
            return answer
        else:
            return f"Server error: {response.status_code}"
    except Exception as e:
        return f"Could not reach Render backend: {e}"

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
                
                if WAKE_WORD in text:
                    print(f"\n[Wake word detected!]")
                    query = text.split(WAKE_WORD, 1)[-1].strip()
                    
                    if not query:
                        speak("Yes?")
                        audio_query = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        query = recognizer.recognize_google(audio_query)
                    
                    print(f"User: {query}")
                    answer = ask_render_brain(query)
                    speak(answer)
                    
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[Speech Service Error]: {e}")
                continue
            except KeyboardInterrupt:
                print("\n[Shutting down local Jarvis client.]")
                break

if __name__ == "__main__":
    listen()
