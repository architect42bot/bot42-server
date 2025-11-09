from fastapi import FastAPI
from memory_api import log_user, log_assistant, recall, top_facts, recent_summaries
from reflections import maybe_reflect

app = FastAPI()

@app.get("/")
def root():
    return {"status": "42 online", "message": "Hello from Bot 42"}

@app.post("/chat")
def chat(message: str):
    # log user
    log_user(message)
    # simple stub reply (replace with model later)
    reply = f"42 received: {message}"
    log_assistant(reply)
    # run reflections
    reflection = maybe_reflect()
    return {
        "reply": reply,
        "reflection": reflection,
        "facts": top_facts(k=5),
        "summaries": recent_summaries(k=2)
    }