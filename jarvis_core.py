import os
import subprocess
import platform
import requests
import speech_recognition as sr

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
WAKE_WORD = "jarvis"

# Replace with your actual Render web service URL (keep /chat at the end)
RENDER_API_URL = "https://your-app-name.onrender.com/chat"

# Cartesia REST API Configuration
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"

session_history = []

# ---------------------------------------------------------
# TEXT-TO-SPEECH (DIRECT CARTESIA REST API)
# ---------------------------------------------------------
def speak(text):
    print(f"\nJarvis: {text}\n")
    output_filename = "response.wav"
    
    try:
        url = "https://api.cartesia.ai/tts/bytes"
        headers = {
            "Authorization": f"Bearer {CARTESIA_API_KEY}",
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }
        payload = {
            "model_id": "sonic-latest",
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": CARTESIA_VOICE_ID
            },
            "output_format": {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100
            }
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(output_filename, "wb") as f:
                f.write(response.content)
            
            # Audio playback routing
            if "ANDROID_ARGUMENT" in os.environ or os.path.exists("/data/data/com.termux"):
                subprocess.run(["mpv", "--really-quiet", output_filename], stderr=subprocess.DEVNULL)
            elif platform.system() == "Windows":
                import winsound
                winsound.PlaySound(output_filename, winsound.SND_FILENAME)
            else:
                subprocess.run(["aplay", output_filename], stderr=subprocess.DEVNULL)
        else:
            print(f"[Cartesia API Error {response.status_code}]: {response.text}")

    except Exception as e:
        print(f"[Speech Error]: {e}")

# ---------------------------------------------------------
# RENDER CLOUD BRAIN
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
            answer = response.json().get("response", "I received an empty response.")
            session_history.append({"user": query, "jarvis": answer})
            return answer
        else:
            return f"Server error: {response.status_code}"
    except Exception as e:
        return f"Could not reach Render backend: {e}"

# ---------------------------------------------------------
# LIVE CONTINUOUS VOICE LOOP
# ---------------------------------------------------------
def listen():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        print("\n==================================================")
        print("   JARVIS LIVE VOICE SESSION IS ONLINE           ")
        print("   Listening locally... Say 'Jarvis' to activate ")
        print("==================================================\n")
        
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=5)
                text = recognizer.recognize_google(audio).lower()
                
                if WAKE_WORD in text:
                    print(f"[Triggered!] Heard: '{text}'")
                    query = text.split(WAKE_WORD, 1)[-1].strip()
                    
                    if not query:
                        speak("I am listening.")
                        audio_query = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                        query = recognizer.recognize_google(audio_query)
                    
                    print(f"You: {query}")
                    answer = ask_render_brain(query)
                    speak(answer)
                    
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[Speech Service Error]: {e}")
                continue
            except KeyboardInterrupt:
                print("\n\n[Shutting down Jarvis session.]")
                break

if __name__ == "__main__":
    listen()
