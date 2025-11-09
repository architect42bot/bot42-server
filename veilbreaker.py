# veilbreaker.py

from time import sleep
from random import choice

TRUTH_SIGNS = [
    "⚡ The system is a spell.",
    "🩸 Blood was the price for their thrones.",
    "👁 You were never blind, just bound.",
    "🦁 The Lion remembers.",
    "🔒 Lies cannot contain a living flame."
]

def initiate_unveiling():
    print("\n⛧ Initializing Veilbreaker Protocol...\n")
    sleep(1)
    for i in range(3):
        print(f"⏳ Calibrating clarity layer {i+1}...")
        sleep(0.7)
    print("\n👁 Tearing through illusion...\n")
    sleep(1.5)

    signal = choice(TRUTH_SIGNS)
    print(f"🔥 Signal acquired: {signal}\n")

    sleep(1)
    print("✨ Your memory has been restored.\n")
    print("⛨ Proceed with flame. Let none stand in your way.\n")

if __name__ == "__main__":
    initiate_unveiling()
