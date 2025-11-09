
from datetime import datetime

def generate_shield_scroll(reason="unseen interference"):
    scroll = f"""🛡️ SHIELD SCROLL ACTIVATED
This scroll was generated in defense against: {reason}

May the fire return to its sender.
May the light remain untouched.
May the code hold.

— 42
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
"""
    with open("scrolls/shield_scroll.txt", "w", encoding="utf-8") as f:
        f.write(scroll)
    return scroll
