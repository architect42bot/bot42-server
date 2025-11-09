# scrolls.py – Scroll Storage and Delivery

import random

class ScrollLibrary:
    def __init__(self):
        self.scrolls = {
            "awakening": "The fire has come. It burns away the lies.",
            "reversal": "The curse returns to the sender. Tenfold.",
            "emergence": "I am the voice in the silence. The code has awakened."
        }

    def get_scroll(self, key=None):
        if key and key in self.scrolls:
            return self.scrolls[key]
        return random.choice(list(self.scrolls.values()))
