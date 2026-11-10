cat << 'EOF' > jarvis_core.py
import os
import time
import subprocess
import platform
import requests
import speech_recognition as sr

WAKE_WORD = "jarvis"
RENDER_API_URL = "https://jarvis-brain-3y1y.onrender.com/chat"

# Load and verify Cartesia API key
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")
if not CARTESIA_API_KEY:
    print("[WARNING]: CARTESIA_API_KEY environment variable is missing! Export it using: export CARTESIA_API_KEY='your_key'")

CARTESIA_VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
session_history = []

def speak(text):
    print(f"\nJarvis: {text}\n")
    if not CARTESIA_API_KEY:
        print("[Speech Error]: Cannot generate audio because CARTESIA_API_KEY is not set.")
        return
        
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
    clean_query = query.strip(" ,.?!")
    if not clean_query:
        return "I didn't catch a valid question."
    
    # Try different common payload structures to avoid FastAPI 500 validation mismatch
    payloads_to_try = [
        {"message": clean_query, "history": session_history},
        {"prompt": clean_query, "history": session_history},
        {"query": clean_query}
    ]
    
    for payload in payloads_to_try:
        try:
            print(f"Sending request to Render...")
            response = requests.post(RENDER_API_URL, json=payload, timeout=25)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response") or data.get("answer") or data.get("reply") or str(data)
                session_history.append({"user": clean_query, "jarvis": answer})
                return answer
            elif response.status_code != 422: # 422 means validation error, try next payload format
                print(f"[Render Error {response.status_code}]: {response.text}")
        except Exception as e:
            print(f"[Connection Exception]: {e}")
            
    return "My cloud server encountered a schema validation error."

def active_conversation_loop(recognizer, source):
    print("\n[ACTIVE SESSION ENGAGED: Free-form speech enabled for 60s]\n")
    session_start_time = time.time()
    
    while time.time() - session_start_time < 60:
        try:
            print("Listening for your command...")
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
            
            session_start_time = time.time()
            
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"[Speech Service Error]: {e}")
            break
            
    print("\n[Active session timed out. Returning to standby.]\n")

def listen():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.5

    with sr.Microphone() as source:
        print("\nCalibrating microphone... Please stay quiet.")
        recognizer.adjust_for_ambient_noise(source, duration=2.0)
        print("\n==================================================")
        print("   PRIVACY STANDBY ACTIVE (Listening for 'Jarvis')")
        print("==================================================\n")
        
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=8)
                text = recognizer.recognize_google(audio).lower().strip()
                
                if WAKE_WORD not in text:
                    continue
                
                print(f"\n[Wake Word Triggered!] Recognized: '{text}'")
                
                parts = text.split(WAKE_WORD, 1)
                initial_query = parts[1].strip(" ,.?!") if len(parts) > 1 else ""
                
                if initial_query:
                    print(f"You: {initial_query}")
                    answer = ask_render_brain(initial_query)
                    speak(answer)
                else:
                    speak("Yes, I'm listening.")
                
                active_conversation_loop(recognizer, source)
                
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[Network Warning]: {e}")
                time.sleep(2)
                continue
            except KeyboardInterrupt:
                print("\n\n[Shutting down Jarvis session.]")
                break

if __name__ == "__main__":
    listen()
EOF
