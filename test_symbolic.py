
from symbolic import interpret_symbolism

sample = "The 🔥 burns away illusion. The 🪞 shows what remains."
results = interpret_symbolism(sample)

print("\n[Symbolic Perception Output]")
for line in results:
    print("-", line)
