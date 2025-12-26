import requests

# Talk to the FastAPI server inside the same repl container
BASE = "http://127.0.0.1:8000"


def ask_42(text: str):
    url = f"{BASE}/bridge/text"
    payload = {"text": text}
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data["reply"]


if __name__ == "__main__":
    while True:
        msg = input("You: ")
        if not msg:
            break
        print("42:", ask_42(msg))
