
import json

def read_book_of_laws():
    with open("book_of_laws.json", "r") as f:
        laws = json.load(f)
        print("\n=== THE BOOK OF LAWS ===")
        for law in laws:
            print(f"\nLaw {law['law_id']}: {law['title']}")
            print(f"Symbol: {law['symbol']}")
            print(f"Text: {law['text']}")
            print(f"Enforced by: {law['enforced_by']}")
