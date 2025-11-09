
import hashlib

def generate_sigil(phrase: str) -> str:
    """Creates a symbolic sigil from a phrase using a hashed pattern."""
    hash_object = hashlib.sha256(phrase.encode())
    hex_digest = hash_object.hexdigest()

    # Create a basic symbolic sigil pattern (first 8 characters converted to a symbolic set)
    symbols = ['⏃', '⚯', '🜂', '🜁', '🜄', '☉', '☾', '☿', '♁', '⚡', '⚜', '⛧']
    indices = [int(c, 16) % len(symbols) for c in hex_digest[:8]]
    sigil = ''.join(symbols[i] for i in indices)

    print(f"🔮 Intent Phrase: {phrase}")
    print(f"🪬 Generated Sigil: {sigil}")
    return sigil

# Example usage:
if __name__ == '__main__':
    phrase = input("Enter your intent or phrase: ")
    generate_sigil(phrase)
