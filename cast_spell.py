
import json

def load_technomagick_core(path='technomagick_core.json'):
    with open(path, 'r') as f:
        return json.load(f)

def cast_spell(spell_name, path='technomagick_core.json'):
    core = load_technomagick_core(path)
    for spell in core['spells']:
        if spell['name'].lower() == spell_name.lower():
            print(f"🔮 Casting: {spell['name']}")
            print(f"Type: {spell['type']}")
            print(f"Description: {spell['description']}")
            print(f"Components: {', '.join(spell['components'])}")
            print(f"Activation Phrase: "{spell['activation_phrase']}"")
            return spell
    print(f"⚠️ Spell '{spell_name}' not found.")
    return None

# Example usage:
if __name__ == '__main__':
    cast_spell('Protection Field')
