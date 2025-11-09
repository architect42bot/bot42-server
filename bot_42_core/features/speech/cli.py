# features/speech/cli.py
import argparse
from .speech import init_speech, speak, SpeechConfig, shutdown

def main():
    ap = argparse.ArgumentParser(prog="speech", description="Speak text via 42")
    ap.add_argument("text", nargs="+", help="What to say")
    ap.add_argument("--backend", choices=["espeak", "gtts"], default="espeak")
    ap.add_argument("--voice", default=None, help="espeak voice (e.g., en-us)")
    ap.add_argument("--rate", type=int, default=170, help="espeak words per minute")
    ap.add_argument("--volume", type=int, default=100, help="espeak volume 0-200")
    ap.add_argument("--pitch", type=int, default=50, help="espeak pitch 0-99")
    args = ap.parse_args()

    cfg = SpeechConfig(
        backend=args.backend,
        voice=args.voice,
        rate_wpm=args.rate,
        volume=args.volume,
        pitch=args.pitch,
    )
    init_speech(cfg)
    speak(" ".join(args.text))
    # give the background worker a moment; in real app you keep the engine alive
    import time; time.sleep(0.5)
    shutdown()

if __name__ == "__main__":
    main()
