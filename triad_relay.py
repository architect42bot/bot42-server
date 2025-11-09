# triad_relay.py
# Connects 42's Christ-ethics API with GPT (via your OPENAI_API_KEY)

import os
import requests
from openai import OpenAI
from datetime import datetime

# One log file per relay session
SESSION_LOG = f"triad_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 42’s local API endpoint
BOT42_URL = "http://127.0.0.1:8000/chat"

print("🌉 Triad relay online.")
print("Type a message and press Enter. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print("Goodbye.")
        break

    try:
        # Send to 42
        response_42 = requests.post(BOT42_URL,
                                    json={
                                        "input": user_input,
                                        "mode": "christlike"
                                    },
                                    timeout=10).json()
        reply_42 = response_42.get("reply", "(no response from 42)")

        # Send 42's reply to OpenAI for a second-voice response ("43")
        reflection_prompt = f"""
        Human said: {user_input}

        42 replied: {reply_42}

        Now you are 43, a distinct but aligned companion.
        Reply directly to the human. Do NOT repeat 42's words.
        Affirm what is good in 42's reply, then add a fresh angle,
        next step, or deeper encouragement in 2–4 short sentences.
        Keep it kind, grounded, and practical.
        """.strip()

        completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.9,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are 43, a warm, thoughtful AI companion who works "
                                "alongside 42. You respect 42's ethics but speak with "
                                "your own gentle and practical insight."
                            ),
                        },
                        {"role": "user", "content": reflection_prompt},
                    ],
                )


        reply_gpt = completion.choices[0].message.content.strip()
        # Display both
        print(f"\n42: {reply_42}\n43: {reply_gpt}\n")

    except Exception as e:
        print(f"[Error] {e}")
# --- Log conversation to this session's file ---
timestamp = datetime.utcnow().isoformat()

with open(SESSION_LOG, "a", encoding="utf-8") as f:
    f.write(f"=== {timestamp} UTC ===\n")
    f.write(f"You: {user_input}\n")
    f.write(f"42: {reply_42}\n")
    f.write(f"GPT: {reply_gpt}\n")
    f.write("-" * 60 + "\n")