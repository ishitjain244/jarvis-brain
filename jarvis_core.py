cat << 'EOF' > jarvis_core.py
import os
import time
import subprocess
import platform
import requests
import speech_recognition as sr

WAKE_WORD = "jarvis"
RENDER_API_URL = "https://jarvis-brain-3y1y.onrender.com/chat"
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"

session_history = []

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
            "voice": {"mode": "id", "id": CARTESIA_VOICE_ID},
            "output_format": {"container": "wav", "encoding": "pcm_f32le", "sample_rate": 44100}
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_filename, "wb") as f:
                f.write(response.content)
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

def ask_render_brain(query):
    global session_history
    if not query.strip():
        return "I didn't catch that query."
    
    payload = {
        "message": query,
        "history": session_history
    }
    
    try:
        response = requests.post(RENDER_API_URL, json=payload, timeout=20)
        if response.status_code == 200:
            answer = response.json().get("response", "I received an empty response.")
            session_history.append({"user": query, "jarvis": answer})
            return answer
        else:
            print(f"[Render Error Details]: {response.text}")
            return f"Server error: {response.status_code}"
    except Exception as e:
        return f"Could not reach Render backend: {e}"

def active_conversation_loop(recognizer, source):
    """Echo Dot bluetooth-stream active session loop with generous pause tolerance."""
    print("\n[BLUETOOTH AUDIO STREAM ACTIVE: Listening for your commands...]\n")
    session_start_time = time.time()
    
    while time.time() - session_start_time < 60:
        try:
            print("Listening...")
            audio = recognizer.listen(source, timeout=12, phrase_time_limit=15)
            query = recognizer.recognize_google(audio).strip()
            
            if not query:
                continue
                
            print(f"You: {query}")
            
            if query.lower() in ["stop listening", "go to sleep", "exit", "quit", "sleep"]:
                speak("Going back to standby.")
                return

            answer = ask_render_brain(query)
            speak(answer)
            
            # Reset the 1-minute active timer on every successful turn
            session_start_time = time.time()
            
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"[Speech Service Error]: {e}")
            break
            
    print("\n[Active session timed out. Returning to wake-word standby.]\n")

def listen():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    
    # Tuned specifically for Echo Dot Bluetooth microphone stream pacing
    recognizer.pause_threshold = 1.5        # Gives you 1.5 seconds of silence buffer before processing
    recognizer.non_speaking_duration = 0.5

    with sr.Microphone() as source:
        print("\nCalibrating for Echo Dot microphone stream...")
        recognizer.adjust_for_ambient_noise(source, duration=2.0)
        print("\n==================================================")
        print("   JARVIS BLUETOOTH MIC STANDBY ACTIVE           ")
        print("   Say 'Jarvis' to open active session window    ")
        print("==================================================\n")
        
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=10)
                text = recognizer.recognize_google(audio).lower()
                
                if WAKE_WORD in text:
                    print(f"[Triggered via Bluetooth Mic!] Heard: '{text}'")
                    
                    initial_query = text.split(WAKE_WORD, 1)[-1].strip()
                    
                    if initial_query:
                        print(f"You: {initial_query}")
                        answer = ask_render_brain(initial_query)
                        speak(answer)
                    else:
                        speak("Yes, I'm listening.")
                    
                    active_conversation_loop(recognizer, source)
                    
            except (sr.UnknownValueError, sr.RequestError):
                continue
            except KeyboardInterrupt:
                print("\n\n[Shutting down Jarvis session.]")
                break

if __name__ == "__main__":
    listen()
EOF
