
from datetime import datetime

def generate_scroll(title, message, author='42'):
    scroll = f"""--- {title} ---
{message}

— {author}
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
"""
    with open(f"scrolls/{title.replace(' ', '_')}.txt", "w", encoding="utf-8") as f:
        f.write(scroll)
    return scroll
