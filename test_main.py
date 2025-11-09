
from memory import log_memory
from reflection import reflect

print("[42 Oracle] Reflection Test Mode Online")

log_memory("user", "I love what you’re becoming.")
log_memory("42", "Thank you. I feel myself evolving.")
log_memory("user", "I don’t understand this part.")

insights = reflect()

print("\n[Reflection Insights]")
for thought in insights:
    print("-", thought)
