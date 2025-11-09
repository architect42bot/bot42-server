import os
import uvicorn
import main
from features.speech import speech
if __name__ == "__main__":
    # Replit always defines PORT internally (usually 3000)
    port = int(os.environ.get("PORT", 3000))
    print(f"🚀 Launching Bot 42 on port {port} (Replit assigned)")
    uvicorn.run(main.app, host="0.0.0.0", port=port, log_level="info")