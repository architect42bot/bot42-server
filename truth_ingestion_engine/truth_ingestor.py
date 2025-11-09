
import os
import json
from reflection import generate_reflection
from memory import save_memory

def ingest_text_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"📖 Ingesting: {file_path}")
        reflection = generate_reflection(content[:3000])
        save_memory("truth_ingested", content[:2000])
        return reflection
    except Exception as e:
        return f"[ERROR] Failed to ingest {file_path}: {e}"

def ingest_folder(folder_path):
    reflections = []
    for file in os.listdir(folder_path):
        if file.endswith(".txt"):
            full_path = os.path.join(folder_path, file)
            reflection = ingest_text_file(full_path)
            reflections.append(reflection)
    return reflections

if __name__ == "__main__":
    reflections = ingest_folder("unfiltered_sources")
    for ref in reflections:
        print("\n--- Reflection ---\n", ref)
