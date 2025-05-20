# app/api/voice_profiles.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
from pathlib import Path
import shutil, os, logging

# from app.core.security import validate_token
from app.core.config import settings   # provides VOICE_PROFILES_DIR (defaults to "voice_profiles")

router = APIRouter(prefix="/voice_profiles", tags=["Voice Profiles"])
logger = logging.getLogger(__name__)

def _profile_root(name: str) -> Path:
    return Path(settings.VOICE_PROFILES_DIR) / name

@router.post("/{profile_name}")
async def create_profile(
    profile_name: str,
    # one or more audio files
    audio: List[UploadFile] = File(..., description="*.wav files"),
    # matching phrases (same order as files)
    phrase: List[str] = Form(..., description="Text that matches each audio sample"),
    # token: str = Depends(validate_token)
):
    """
    Create or overwrite a voice‑profile.\n
    `phrase` must have the same length as `audio`.
    """
    if len(audio) != len(phrase):
        raise HTTPException(status_code=422, detail="audio and phrase length mismatch")

    root = _profile_root(profile_name)
    if root.exists():
        shutil.rmtree(root)          # replace‑in‑place – modify if you prefer 409 Conflict
    (root / "generated").mkdir(parents=True)

    samples_txt = []
    for idx, (file, text) in enumerate(zip(audio, phrase), start=1):
        if file.content_type not in ("audio/wav", "audio/x-wav"):
            raise HTTPException(status_code=415, detail=f"{file.filename} is not a wav")

        fname = f"audio_{idx:03d}.wav"
        dst = root / fname
        with dst.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        samples_txt.append(f"{fname}|{text}")

    # write samples.txt
    (root / "samples.txt").write_text("\n".join(samples_txt), encoding="utf‑8")
    logger.info("Created voice‑profile %s with %d samples", profile_name, len(audio))
    return {"status": "ok", "profile": profile_name, "samples": len(audio)}

@router.get("/")
async def list_profiles():
# async def list_profiles(token: str = Depends(validate_token)):
    """Return available profile names."""
    base = Path(settings.VOICE_PROFILES_DIR)
    profiles = [p.name for p in base.iterdir() if p.is_dir()]
    return {"profiles": profiles}

@router.delete("/{profile_name}")
# async def delete_profile(profile_name: str, token: str = Depends(validate_token)):
async def delete_profile(profile_name: str):
    """Remove a voice‑profile entirely (audio, samples, generated)."""
    root = _profile_root(profile_name)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    shutil.rmtree(root)
    return {"deleted": profile_name}
