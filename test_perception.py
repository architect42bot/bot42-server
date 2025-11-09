
from perception import detect_signals

sample = "Today I saw 11:11 and felt the Machine watching me 🔥"
result = detect_signals(sample)

print("\n[Perception Output]")
for signal in result:
    print("-", signal)
