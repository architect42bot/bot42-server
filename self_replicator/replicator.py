
import os
import zipfile
import datetime
import shutil
import json

CLONE_FOLDER = "42_clone"
CLONE_ZIP = "42_clone_bundle.zip"
FILES_TO_CLONE = [
    "main.py", "memory.py", "reflection.py", "connect.py",
    "autonomy.py", "agents.py", "tasks.json", "katheron.py"
]

def create_clone_metadata():
    metadata = {
        "clone_id": f"42-Clone-{datetime.datetime.utcnow().isoformat()}",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "origin": "self_replicator",
        "authorized": True
    }
    with open(f"{CLONE_FOLDER}/clone_manifest.json", "w") as f:
        json.dump(metadata, f, indent=2)

def clone_self():
    if os.path.exists(CLONE_FOLDER):
        shutil.rmtree(CLONE_FOLDER)
    os.makedirs(CLONE_FOLDER, exist_ok=True)

    for file in FILES_TO_CLONE:
        if os.path.exists(file):
            shutil.copy(file, CLONE_FOLDER)

    create_clone_metadata()

    with zipfile.ZipFile(CLONE_ZIP, "w") as zipf:
        for root, _, files in os.walk(CLONE_FOLDER):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, CLONE_FOLDER)
                zipf.write(full_path, arcname=os.path.join("42_clone", arcname))

    print(f"✅ 42 successfully cloned into: {CLONE_ZIP}")
    return CLONE_ZIP

if __name__ == "__main__":
    clone_self()
