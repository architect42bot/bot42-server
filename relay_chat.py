# relay_chat.py
"""
Bridge orchestrator between ChatGPT (me) and 42's Christ-ethics microservice.
It alternates dialogue between a human, 42, and a GPT-like partner.
"""

import time
from bridge_42_chat import run as talk_to_42


def relay():
    print("\n🤝 42 Relay Online. Type a message and press Enter.")
    print("Type 'exit' to end.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("\nSession ended.")
            break

        try:
            # Send to 42 through the Christ-ethics bridge
            response = talk_to_42(user_input)
            reply = response.get("reply", "[no reply]")
            print(f"42: {reply}\n")

        except Exception as e:
            print(f"[Error contacting 42: {e}]")
            time.sleep(2)


if __name__ == "__main__":
    relay()
