# """
# Voice client (Python)
#
# Features:
# - Record audio from microphone
# - Send audio to STT service (/stt)
# - Safe word activation ("memo")
# - Natural language reminder commands:
#     "memo remind me to buy milk at 6 pm"
#     "memo create meeting at 2025-01-01T09:00"
#     "memo list reminders"
# - Call reminder API to create/list reminders
# - Poll reminders and announce those with status == "due"
# - Spoken feedback and desktop notifications
#
# Requires (in requirements.txt):
#     requests
#     sounddevice
#     wavio
#     pyttsx3
#     plyer
# """
#
# import threading
# import time
# import uuid
# from typing import Optional, Set
#
# import requests
# import sounddevice as sd
# import wavio
# import pyttsx3
# # macOS: plyer requires pyobjus (not available by default)
# # So we import safely: if it fails, notifications will be disabled
# try:
#     from plyer import notification
#     PLYER_AVAILABLE = True
# except Exception:
#     print("[INFO] plyer notifications not available on this system.")
#     PLYER_AVAILABLE = False
#
#
# # CONFIG
#
# # Base URL for the main reminder backend (app.py)
# REMINDER_API = "http://127.0.0.1:8000"
#
# # STT service from Person 3 (stt_service.py)
# STT_API = "http://127.0.0.1:8001/stt"
#
# # Audio settings
# SAMPLE_RATE = 16_000
# CHANNELS = 1
#
# # Safe word required to activate commands
# SAFE_WORD = "memo"
#
# # Keep track of which "due" reminders have already been announced
# announced_due_ids: Set[int] = set()
#
#
# # TTS (spoken feedback)
#
# _tts_engine = pyttsx3.init()
#
#
# def speak(text: str) -> None:
#     """Speak text out loud using offline TTS."""
#     print(f"[TTS] {text}")
#     _tts_engine.say(text)
#     _tts_engine.runAndWait()
#
#
# # Desktop notifications
#
#
# def notify(title: str, msg: str):
#     """Attempt desktop notification; fallback gracefully on macOS."""
#     print(f"[NOTIFY] {title}: {msg}")
#
#     if not PLYER_AVAILABLE:
#         print("[NOTIFY WARNING] Notifications disabled on this system.")
#         return
#
#     try:
#         notification.notify(
#             title=title,
#             message=msg,
#             timeout=5
#         )
#     except Exception:
#         print("[NOTIFY WARNING] Failed to send desktop notification.")
#
#
#
#
# # Audio recording
#
# def record_audio(duration: float = 4.0) -> str:
#     """
#     Record microphone input for `duration` seconds and
#     save it as a mono 16 kHz WAV file.
#
#     Returns:
#         Path to the saved WAV file.
#     """
#     print(f"[AUDIO] Recording {duration} seconds...")
#     audio = sd.rec(
#         int(duration * SAMPLE_RATE),
#         samplerate=SAMPLE_RATE,
#         channels=CHANNELS,
#     )
#     sd.wait()
#     filename = f"audio_{uuid.uuid4().hex}.wav"
#     wavio.write(filename, audio, SAMPLE_RATE, sampwidth=2)
#     print(f"[AUDIO] Saved → {filename}")
#     return filename
#
#
# # STT client
#
# def send_to_stt(filepath: str) -> str:
#     """
#     Send an audio file to the STT service and return the transcribed text.
#
#     Expected response from /stt:
#         { "text": "...", "confidence": 0.xx }
#     """
#     print(f"[STT] Sending {filepath} → {STT_API}")
#     with open(filepath, "rb") as f:
#         response = requests.post(STT_API, files={"audio": f})
#
#     if response.status_code != 200:
#         print("[STT ERROR]", response.status_code, response.text)
#         speak("I could not understand the audio.")
#         return ""
#
#     data = response.json()
#     text = data.get("text", "")
#     print(f"[STT] Heard: {text!r}")
#     return text
#
#
#
# # Safe word handling
#
# def check_safe_word(text: str) -> Optional[str]:
#     """
#     If the text starts with the safe word, return the remainder (command text).
#     Otherwise return None, meaning we ignore this utterance.
#     """
#     t = text.lower().strip()
#     if not t.startswith(SAFE_WORD):
#         return None
#     return t[len(SAFE_WORD):].strip()
#
#
# # Natural language command parsing
#
# def parse_command(text: str):
#     """
#     Parse natural-language command text AFTER the safe word.
#
#     Supported forms:
#
#       "remind me to BUY MILK at 6 pm"
#       "create meeting at 2025-01-01T09:00"
#       "list reminders"
#
#     Returns tuples:
#       ("list",)
#       ("create", task, time_str)
#       ("unknown",)
#     """
#     t = text.lower().strip()
#
#     # list reminders
#     if t.startswith("list"):
#         return ("list",)
#
#     # "remind me to <task> at <time>"
#     if t.startswith("remind me to "):
#         try:
#             body = text[len("remind me to "):]
#             task, time_part = body.rsplit(" at ", 1)
#             return ("create", task.strip(), time_part.strip())
#         except Exception:
#             return ("unknown",)
#
#     # "create <task> at <time>"
#     if t.startswith("create "):
#         try:
#             body = text[len("create "):]
#             task, time_part = body.rsplit(" at ", 1)
#             return ("create", task.strip(), time_part.strip())
#         except Exception:
#             return ("unknown",)
#
#     return ("unknown",)
#
#
# # Reminder API helpers
#
# def create_reminder(task: str, time_iso: str) -> None:
#     """
#     Create a reminder via the backend API.
#
#     The backend is expected to accept JSON like:
#         { "task": "...", "time_iso": "...", "repeat": null }
#     """
#     payload = {
#         "task": task,
#         "time_iso": time_iso,
#         "repeat": None,
#     }
#     url = f"{REMINDER_API}/reminders/"
#     print("[API] POST", url, "→", payload)
#     response = requests.post(url, json=payload)
#
#     if response.status_code == 200:
#         speak(f"Reminder created for {task}")
#     else:
#         print("[API ERROR]", response.status_code, response.text)
#         speak("Failed to create the reminder.")
#
#
# def list_reminders() -> None:
#     """Call GET /reminders/ and speak that the list is printed."""
#     url = f"{REMINDER_API}/reminders/"
#     print("[API] GET", url)
#     response = requests.get(url)
#     print("[API] Reminders:", response.status_code, response.text)
#     speak("Here are your reminders. Check the console.")
#
#
# # Poller for due reminders
#
# def poll_due_reminders() -> None:
#     """
#     Periodically check /reminders/ and announce any reminders
#     with status == "due" that we haven't already announced.
#     """
#     global announced_due_ids
#     url = f"{REMINDER_API}/reminders/"
#     print("[POLL] Watching /reminders/ for due reminders...")
#
#     while True:
#         try:
#             response = requests.get(url)
#             if response.status_code == 200:
#                 reminders = response.json()
#                 for rem in reminders:
#                     rid = rem.get("id")
#                     status = rem.get("status")
#                     task = rem.get("task", "")
#
#                     # Speak each due reminder only once
#                     if status == "due" and isinstance(rid, int) and rid not in announced_due_ids:
#                         announced_due_ids.add(rid)
#                         notify("Reminder due", task)
#                         speak(task)
#             else:
#                 print("[POLL ERROR]", response.status_code, response.text)
#         except Exception as e:
#             print("[POLL EXCEPTION]", e)
#
#         time.sleep(30)
#
#
# def start_polling_thread() -> None:
#     """Run the poller in the background so the CLI stays interactive."""
#     thread = threading.Thread(target=poll_due_reminders, daemon=True)
#     thread.start()
#
#
# # Main loop (CLI interface for Person 2)
#
# def main() -> None:
#     print("\n=====================================")
#     print("       Voice Client    ")
#     print("=====================================\n")
#     print(f"Safe word: '{SAFE_WORD}' (e.g. 'memo remind me to ...')\n")
#
#     start_polling_thread()
#
#     while True:
#         cmd = input("Press [r] to record, [q] to quit: ").strip().lower()
#
#         if cmd == "q":
#             speak("Goodbye.")
#             break
#         if cmd != "r":
#             continue
#
#         try:
#             # 1. Record audio
#             path = record_audio()
#
#             # 2. STT
#             text = send_to_stt(path)
#             if not text:
#                 continue
#
#             speak(f"You said: {text}")
#
#             # 3. Safe word check
#             command_text = check_safe_word(text)
#             if command_text is None:
#                 speak(f"Say '{SAFE_WORD}' to start a command.")
#                 continue
#
#             # 4. Parse natural language command
#             parsed = parse_command(command_text)
#
#             if parsed[0] == "list":
#                 list_reminders()
#
#             elif parsed[0] == "create":
#                 _, task, time_str = parsed
#                 # Here we assume Person 4 or backend can interpret time_str as ISO
#                 # For now, we pass it through directly.
#                 create_reminder(task, time_str)
#
#             else:
#                 speak("I don't understand that command yet.")
#
#         except Exception as e:
#             print("[MAIN LOOP ERROR]", e)
#             speak("Something went wrong while handling your command.")
#
#
# if __name__ == "__main__":
#     main()


"""
Voice client (Python)

Features:
- Record audio from microphone
- Send audio to STT service (/stt)
- Safe word activation ("memo")
- Natural language reminder commands:
    "memo remind me to buy milk at 6 pm"
    "memo create meeting at 2025-01-01T09:00"
    "memo list reminders"
- Call reminder API to create/list reminders
- Poll reminders and announce those with status == "due"
- Spoken feedback and desktop notifications

Requires (in requirements.txt):
    requests
    sounddevice
    wavio
    pyttsx3
    plyer
"""

import os
import threading
import time
import uuid
from typing import Optional, Set

import requests
import sounddevice as sd
import wavio
import pyttsx3

# macOS: plyer requires pyobjus (not available by default)
# So we import safely: if it fails, notifications will be disabled
try:
    from plyer import notification

    PLYER_AVAILABLE = True
except Exception:
    print("[INFO] plyer notifications not available on this system.")
    PLYER_AVAILABLE = False

# ----------------------------------------
# CONFIG
# ----------------------------------------

# Base URL for the main reminder backend (app.py)
REMINDER_API = "http://127.0.0.1:8000"

# STT service from Person 3 (stt_service.py)
STT_API = "http://127.0.0.1:8001/stt"

# Toggle between mock and real STT
# Set to True to test without the STT service running
USE_MOCK_STT = False

# Audio settings
SAMPLE_RATE = 16_000
CHANNELS = 1

# Safe word required to activate commands
SAFE_WORD = "memo"

# Keep track of which "due" reminders have already been announced
announced_due_ids: Set[int] = set()


# ----------------------------------------
# STT Client Interface
# ----------------------------------------

class STTClient:
    """Abstract base class for STT clients."""

    def transcribe(self, filepath: str) -> str:
        """Transcribe audio file and return text."""
        raise NotImplementedError("Subclasses must implement transcribe()")


class MockSTTClient(STTClient):
    """Mock STT client that returns fixed text for testing."""

    def __init__(self, fixed_response: str = "memo remind me to call mom at 6 pm"):
        self.fixed_response = fixed_response

    def transcribe(self, filepath: str) -> str:
        """Always return the same fixed text."""
        print(f"[MOCK STT] Pretending to transcribe {filepath}")
        print(f"[MOCK STT] Returning: {self.fixed_response!r}")
        return self.fixed_response


class ApiSTTClient(STTClient):
    """Real STT client that calls the /stt API service."""

    def __init__(self, stt_url: str):
        self.stt_url = stt_url

    def transcribe(self, filepath: str) -> str:
        """Send audio file to STT service and return transcribed text."""
        print(f"[API STT] Sending {filepath} → {self.stt_url}")
        try:
            with open(filepath, "rb") as f:
                response = requests.post(self.stt_url, files={"audio": f})

            if response.status_code != 200:
                print(f"[API STT ERROR] {response.status_code} {response.text}")
                speak("I could not understand the audio.")
                return ""

            data = response.json()
            text = data.get("text", "")
            print(f"[API STT] Heard: {text!r}")
            return text
        except requests.exceptions.RequestException as e:
            print(f"[API STT EXCEPTION] Connection error: {e}")
            speak("Could not connect to STT service.")
            return ""
        except Exception as e:
            print(f"[API STT EXCEPTION] {e}")
            speak("An error occurred during transcription.")
            return ""


# ----------------------------------------
# TTS (spoken feedback)
# ----------------------------------------

_tts_engine = pyttsx3.init()


def speak(text: str) -> None:
    """Speak text out loud using offline TTS."""
    print(f"[TTS] {text}")
    _tts_engine.say(text)
    _tts_engine.runAndWait()


# ----------------------------------------
# Desktop notifications
# ----------------------------------------

def notify(title: str, msg: str):
    """Attempt desktop notification; fallback gracefully on macOS."""
    print(f"[NOTIFY] {title}: {msg}")

    if not PLYER_AVAILABLE:
        print("[NOTIFY WARNING] Notifications disabled on this system.")
        return

    try:
        notification.notify(
            title=title,
            message=msg,
            timeout=5
        )
    except Exception:
        print("[NOTIFY WARNING] Failed to send desktop notification.")


# ----------------------------------------
# Audio recording
# ----------------------------------------

def record_audio(duration: float = 4.0) -> str:
    """
    Record microphone input for `duration` seconds and
    save it as a mono 16 kHz WAV file.

    Returns:
        Path to the saved WAV file.
    """
    print(f"[AUDIO] Recording {duration} seconds...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
    )
    sd.wait()
    filename = f"audio_{uuid.uuid4().hex}.wav"
    wavio.write(filename, audio, SAMPLE_RATE, sampwidth=2)
    print(f"[AUDIO] Saved → {filename}")
    return filename


# ----------------------------------------
# STT client wrapper
# ----------------------------------------

def send_to_stt(filepath: str) -> str:
    """
    Send an audio file to the STT service and return the transcribed text.

    Uses the global stt_client (either Mock or API implementation).

    Expected response from /stt:
        { "text": "...", "confidence": 0.xx }
    """
    return stt_client.transcribe(filepath)


# ----------------------------------------
# Safe word handling
# ----------------------------------------

def check_safe_word(text: str) -> Optional[str]:
    """
    If the text starts with the safe word, return the remainder (command text).
    Otherwise return None, meaning we ignore this utterance.
    """
    t = text.lower().strip()
    if not t.startswith(SAFE_WORD):
        return None
    return t[len(SAFE_WORD):].strip()


# ----------------------------------------
# Natural language command parsing
# ----------------------------------------

def parse_command(text: str):
    """
    Parse natural-language command text AFTER the safe word.

    Supported forms:

      "remind me to BUY MILK at 6 pm"
      "create meeting at 2025-01-01T09:00"
      "list reminders"

    Returns tuples:
      ("list",)
      ("create", task, time_str)
      ("unknown",)
    """
    t = text.lower().strip()

    # list reminders
    if t.startswith("list"):
        return ("list",)

    # "remind me to <task> at <time>"
    if t.startswith("remind me to "):
        try:
            body = text[len("remind me to "):]
            task, time_part = body.rsplit(" at ", 1)
            return ("create", task.strip(), time_part.strip())
        except Exception:
            return ("unknown",)

    # "create <task> at <time>"
    if t.startswith("create "):
        try:
            body = text[len("create "):]
            task, time_part = body.rsplit(" at ", 1)
            return ("create", task.strip(), time_part.strip())
        except Exception:
            return ("unknown",)

    return ("unknown",)


# ----------------------------------------
# Reminder API helpers
# ----------------------------------------

def create_reminder(task: str, time_iso: str) -> None:
    """
    Create a reminder via the backend API.

    The backend is expected to accept JSON like:
        { "task": "...", "time_iso": "...", "repeat": null }
    """
    payload = {
        "task": task,
        "time_iso": time_iso,
        "repeat": None,
    }
    url = f"{REMINDER_API}/reminders/"
    print("[API] POST", url, "→", payload)
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            speak(f"Reminder created for {task}")
        else:
            print("[API ERROR]", response.status_code, response.text)
            speak("Failed to create the reminder.")
    except requests.exceptions.RequestException as e:
        print(f"[API ERROR] Could not connect to reminder service: {e}")
        speak("Could not connect to reminder service.")


def list_reminders() -> None:
    """Call GET /reminders/ and speak that the list is printed."""
    url = f"{REMINDER_API}/reminders/"
    print("[API] GET", url)
    try:
        response = requests.get(url, timeout=5)
        print("[API] Reminders:", response.status_code, response.text)
        speak("Here are your reminders. Check the console.")
    except requests.exceptions.RequestException as e:
        print(f"[API ERROR] Could not connect to reminder service: {e}")
        speak("Could not connect to reminder service.")


# ----------------------------------------
# Poller for due reminders
# ----------------------------------------

def poll_due_reminders() -> None:
    """
    Periodically check /reminders/ and announce any reminders
    with status == "due" that we haven't already announced.
    """
    global announced_due_ids
    url = f"{REMINDER_API}/reminders/"
    print("[POLL] Watching /reminders/ for due reminders...")

    consecutive_failures = 0

    while True:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                consecutive_failures = 0  # Reset on success
                reminders = response.json()
                for rem in reminders:
                    rid = rem.get("id")
                    status = rem.get("status")
                    task = rem.get("task", "")

                    # Speak each due reminder only once
                    if status == "due" and isinstance(rid, int) and rid not in announced_due_ids:
                        announced_due_ids.add(rid)
                        notify("Reminder due", task)
                        speak(task)
            else:
                print("[POLL ERROR]", response.status_code, response.text)
                consecutive_failures += 1
        except Exception as e:
            print("[POLL EXCEPTION]", e)
            consecutive_failures += 1

        # Exponential backoff on repeated failures (max 5 minutes)
        if consecutive_failures > 0:
            sleep_time = min(300, 30 * (2 ** min(consecutive_failures - 1, 3)))
            print(f"[POLL] Sleeping {sleep_time}s due to errors...")
            time.sleep(sleep_time)
        else:
            time.sleep(30)


def start_polling_thread() -> None:
    """Run the poller in the background so the CLI stays interactive."""
    thread = threading.Thread(target=poll_due_reminders, daemon=True)
    thread.start()


# ----------------------------------------
# Service health check
# ----------------------------------------

def check_services() -> bool:
    """Check if required services are available."""
    services_ok = True

    # Check STT service
    try:
        stt_health_url = STT_API.replace("/stt", "/health")
        response = requests.get(stt_health_url, timeout=2)
        if response.status_code == 200:
            print("[✓] STT service is running")
        else:
            print("[✗] STT service returned error")
            services_ok = False
    except Exception:
        print("[✗] STT service is not available")
        services_ok = False

    # Check Reminder API
    try:
        response = requests.get(f"{REMINDER_API}/health", timeout=2)
        if response.status_code == 200:
            print("[✓] Reminder API is running")
        else:
            print("[✗] Reminder API returned error")
            services_ok = False
    except Exception:
        print("[✗] Reminder API is not available")
        services_ok = False

    return services_ok


# ----------------------------------------
# Main loop (CLI interface)
# ----------------------------------------

def main() -> None:
    print("\n=====================================")
    print("       Voice Client    ")
    print("=====================================\n")
    print(f"Safe word: '{SAFE_WORD}' (e.g. 'memo remind me to ...')\n")

    # Check services if not in mock mode
    if not USE_MOCK_STT:
        print("Checking services...")
        if not check_services():
            print("\n⚠️  Some services are unavailable.")
            print("Set USE_MOCK_STT = True in the code to run in mock mode.\n")

    start_polling_thread()

    while True:
        cmd = input("Press [r] to record, [q] to quit: ").strip().lower()

        if cmd == "q":
            speak("Goodbye.")
            break
        if cmd != "r":
            continue

        audio_path = None
        try:
            # 1. Record audio
            audio_path = record_audio()

            # 2. STT
            text = send_to_stt(audio_path)

            if not text:
                continue

            speak(f"You said: {text}")

            # 3. Safe word check
            command_text = check_safe_word(text)
            if command_text is None:
                speak(f"Say '{SAFE_WORD}' to start a command.")
                continue

            # 4. Parse natural language command
            parsed = parse_command(command_text)

            if parsed[0] == "list":
                list_reminders()

            elif parsed[0] == "create":
                _, task, time_str = parsed
                # Here we assume Person 4 or backend can interpret time_str as ISO
                # For now, we pass it through directly.
                create_reminder(task, time_str)

            else:
                speak("I don't understand that command yet.")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user")
            speak("Goodbye.")
            break
        except Exception as e:
            print("[MAIN LOOP ERROR]", e)
            speak("Something went wrong while handling your command.")
        finally:
            # Clean up audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"[CLEANUP] Removed {audio_path}")
                except Exception as e:
                    print(f"[CLEANUP WARNING] Could not remove {audio_path}: {e}")


# ----------------------------------------
# Initialize STT client based on configuration
# ----------------------------------------

if USE_MOCK_STT:
    print("[CONFIG] Using MOCK STT client (no real API calls)")
    stt_client = MockSTTClient("memo remind me to buy groceries at 5 pm")
else:
    print("[CONFIG] Using REAL API STT client")
    stt_client = ApiSTTClient(STT_API)

# ----------------------------------------
# Entry point
# ----------------------------------------

if __name__ == "__main__":
    main()
