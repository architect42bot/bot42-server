import os
import sys

mode = os.environ.get("MODE", "cli")

if mode == "cli":
    os.execvp("python3", ["python3", "main.py"])
elif mode == "api":
    os.execvp("python3", ["python3", "bot42_api_polished/oracle_api.py"])
else:
    print("Unknown MODE. Use cli or api.")
    sys.exit(1)