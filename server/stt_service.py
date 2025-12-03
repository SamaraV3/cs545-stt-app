from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Tuple

# Config

# Very rough "too short" check using file size (in bytes).
# You can change this after you know your real audio length.
MIN_AUDIO_BYTES = 8000  # ~a fraction of a second for typical formats

# Pydantic models
class STTResponse(BaseModel):
    text: str
    confidence: float

# App setup
app = FastAPI(
    title="Voice Reminder STT Service",
    description="Person 3: Speech-to-text microservice for /stt",
    version="0.1.0",
)

# Allow Flutter / web client during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten this later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Core STT logic (placeholder)
def transcribe_audio(audio_bytes: bytes) -> Tuple[str, float]:
    """
    Core STT function.

    Right now this is a dummy implementation that always returns the same text.
    Later, replace this with a call to Whisper or another STT engine.

    Examples of what you might do later:

    import whisper
    model = whisper.load_model("base")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    result = model.transcribe(tmp_path)
    text = result["text"]
    confidence = 0.9  # or compute from result

    """
    # TODO: Replace this with real STT.
    dummy_text = "memo remind me to call mom at 6 pm"
    dummy_confidence = 0.9
    return dummy_text, dummy_confidence

# Routes
@app.get("/health")
def health_check():
    """Simple health endpoint so you can test the service is up."""
    return {"status": "ok", "service": "stt"}


@app.post("/stt", response_model=STTResponse)
async def stt(audio: UploadFile = File(...)):
    """
    Accepts an uploaded audio file and returns a transcription.

    Request:
        Content-Type: multipart/form-data
        Field: "audio" -> file (e.g., .wav, .mp3)

    Response (200):
        { "text": "...", "confidence": 0.9 }

    Errors:
        400 { "error": "INVALID_MEDIA_TYPE" }
        400 { "error": "AUDIO_TOO_SHORT" }
        500 { "error": "STT_FAILED" }
    """

    # Basic content-type check
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        # Flutter side can check for this specific error
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_MEDIA_TYPE"}
        )

    # Read the bytes from the upload
    audio_bytes = await audio.read()

    # Very rough "too short" check
    if len(audio_bytes) < MIN_AUDIO_BYTES:
        raise HTTPException(
            status_code=400,
            detail={"error": "AUDIO_TOO_SHORT"}
        )

    # Call STT engine
    try:
        text, confidence = transcribe_audio(audio_bytes)
    except Exception as exc:
        # Log the error for debugging
        print(f"[STT] transcription failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"error": "STT_FAILED"}
        )

    return STTResponse(text=text, confidence=confidence)

# Local dev entrypoint
if __name__ == "__main__":
    import uvicorn

    # You can change the port if Person 5’s service is already on 8000
    uvicorn.run(
        "stt_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
