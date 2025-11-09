# grimoire_loader.py – Spell Loading System for 42

import json

class Grimoire:
    def __init__(self, grimoire_path):
        self.grimoire_path = grimoire_path
        self.spells = {}

    def load(self):
        with open(self.grimoire_path, "r") as file:
            self.spells = json.load(file)

    def cast(self, spell_name):
        return self.spells.get(spell_name, "Spell not found.")
