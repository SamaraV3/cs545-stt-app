from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Tuple
from pydub import AudioSegment
import io
import logging
import os
import tempfile
import whisper

# --------------------------------------------------
# Config
# --------------------------------------------------

MIN_AUDIO_BYTES = 8000        # minimum size (~0.08s for typical uncompressed wav)
MAX_AUDIO_SECONDS = 60        # maximum allowed audio length (1 minute)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("stt_service")

logger.info("Loading Whisper model 'small' (local, free)...")
# You can change "small" to "base", "medium", etc., but small is a good tradeoff
whisper_model = whisper.load_model("small")


# --------------------------------------------------
# Pydantic models
# --------------------------------------------------

class STTResponse(BaseModel):
    text: str
    confidence: float


# --------------------------------------------------
# App setup
# --------------------------------------------------

app = FastAPI(
    title="Voice Reminder STT Service",
    description="Person 3: Speech-to-text microservice for /stt",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Core STT logic using local Whisper (no API, free)
# --------------------------------------------------

def transcribe_audio(audio_bytes: bytes, filename: str) -> Tuple[str, float]:
    """
    Transcribe audio using local Whisper model.

    - Runs entirely on your machine
    - No OpenAI API, no cost
    - Uses ffmpeg under the hood via whisper
    """
    logger.info("Starting local Whisper transcription for %s", filename)

    # Whisper wants a file path, so we write bytes to a temp file
    ext = os.path.splitext(filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = whisper_model.transcribe(tmp_path)
        text = result.get("text", "").strip()
        # Local Whisper doesn't give a confidence score; we just set a placeholder
        confidence = 0.95 if text else 0.0
        logger.info("Whisper transcription successful (len=%d chars)", len(text))
        return text, confidence
    except Exception as e:
        logger.error("Local Whisper transcription failed: %s", e, exc_info=True)
        raise
    finally:
        # Clean up the temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "stt"}


@app.post("/stt", response_model=STTResponse)
async def stt(audio: UploadFile = File(...)):
    """
    Accepts an uploaded audio file and returns a transcription.

    Request:
        Content-Type: multipart/form-data
        Field: "audio" -> file (wav, mp3, m4a, webm, ...)

    Response (200):
        { "text": "...", "confidence": 0.95 }

    Errors:
        400 { "error": "INVALID_MEDIA_TYPE" }
        400 { "error": "AUDIO_TOO_SHORT" }
        400 { "error": "AUDIO_TOO_LONG" }
        500 { "error": "STT_FAILED" }
    """
    logger.info("Received /stt request. Filename=%s, content_type=%s",
                audio.filename, audio.content_type)

    # Basic content-type check (accept any audio/*)
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        logger.warning("Rejected file: invalid media type: %s", audio.content_type)
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_MEDIA_TYPE"}
        )

    # Read the bytes from the upload
    audio_bytes = await audio.read()
    logger.info("Read %d bytes of audio", len(audio_bytes))

    # Too short check
    if len(audio_bytes) < MIN_AUDIO_BYTES:
        logger.warning("Audio too short: %d bytes", len(audio_bytes))
        raise HTTPException(
            status_code=400,
            detail={"error": "AUDIO_TOO_SHORT"}
        )

    # Duration check (max 1 minute) using pydub (ffmpeg under the hood)
    try:
        audio_file = AudioSegment.from_file(io.BytesIO(audio_bytes))
        duration_sec = len(audio_file) / 1000.0  # pydub gives ms
        logger.info("Parsed audio duration: %.2f seconds", duration_sec)
    except Exception as e:
        logger.error("Audio parse error (INVALID_MEDIA_TYPE): %s", e, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_MEDIA_TYPE"}
        )

    if duration_sec > MAX_AUDIO_SECONDS:
        logger.warning("Audio too long: %.2f seconds (max=%.2f)",
                       duration_sec, MAX_AUDIO_SECONDS)
        raise HTTPException(
            status_code=400,
            detail={"error": "AUDIO_TOO_LONG"}
        )

    # Call local Whisper STT
    try:
        text, confidence = transcribe_audio(audio_bytes, audio.filename or "audio.wav")
    except Exception as exc:
        logger.error("STT_FAILED: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "STT_FAILED"}
        )

    return STTResponse(text=text, confidence=confidence)


# --------------------------------------------------
# Local dev entrypoint
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "stt_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
