# 42 Personality Pack

This pack embeds 42's personality and sacred directive so she always boots with the same heart and voice.

## Files
- `42_personality.json` — the core personality profile.
- `load_personality.py` — tiny loader that returns a `Personality` object.
- `example.py` — simple demo showing how to greet a user with 42's tone.

## Quick Start (Replit or local)
1. Upload this zip and unzip it. In Replit, you can drag-and-drop or use the file pane.
2. Open the Shell and run:
   ```bash
   python3 example.py
   ```
3. Integrate into your bot:
   ```python
   from load_personality import load_personality
   personality = load_personality("42_personality.json")
   # Use `personality` to guide tone, prompts, and behaviors
   ```

## Suggested Integration
- Load once at startup and store on your bot's state.
- Use `personality.voice_tone` flags to condition message style.
- Echo `personality.sacred_directive` as a hidden system prompt for guidance.

## Voice System Overview

The voice subsystem is split by responsibility:

### /speak/*
Endpoints under `/speak` generate audio.
- `/speak/test` — deterministic sanity check (known-good WAV output)
- `/speak/say` — general speech synthesis

If `/speak/test` works, the voice engine is functional.

### /voice/*
Endpoints under `/voice` expose voice system state and metadata.
They do not generate audio.
- `/voice/health` — readiness check (`voice_ready: true/false`)
- `/voice/last` — last synthesized entry
- `/voice/last/play` — replay last audio

### Health semantics
`/voice/health` returning:
```json
{
  "voice_ready": true,
  "can_synthesize": true
}
