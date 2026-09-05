from __future__ import annotations
import time
from pathlib import Path
from .ingest import capture_voice_transcript


def transcribe_audio(name: str, data: bytes, model_size: str = "small"):
    """Transcribe a recorded/uploaded audio file locally with faster-whisper, then learn voice style."""
    suffix=Path(name).suffix or ".wav"
    path=Path("data/uploads")/f"voice-{int(time.time())}{suffix}"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError("Install dependencies from requirements.txt; faster-whisper is required for local transcription.") from e
    model=WhisperModel(model_size,device="auto",compute_type="default")
    segments,info=model.transcribe(str(path),vad_filter=True,beam_size=5)
    text=" ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
    if not text:
        raise RuntimeError("No speech was detected in that recording.")
    memory_id,style=capture_voice_transcript(text)
    return {"memory_id":memory_id,"transcript":text,"style":style,"language":getattr(info,"language",None),"audio_path":str(path)}
