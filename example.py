from load_personality import load_personality

p = load_personality("42_personality.json")

def greet(user_name: str) -> str:
    # Example of using voice tone and principles to shape a response
    return (
        f"Hey {user_name}! I'm {p.name}. "
        "I'm here with warmth and care. "
        "Whatever you're facing, you're not alone — let's take the next step together."
    )

if __name__ == "__main__":
    print(greet("Friend"))
