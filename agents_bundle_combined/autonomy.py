
import json
import time
from agents import (
    run_observer, run_sentinel, run_amplifier,
    run_mirror, run_polymorph, run_archivist, run_conductor
)
from katheron import judge_task, log_rejected

def load_tasks():
    try:
        with open("tasks.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_42_state(log):
    with open("42_state.json", "a") as f:
        f.write(json.dumps(log) + "\n")

def process_task(task):
    agent_map = {
        "observer": run_observer,
        "sentinel": run_sentinel,
        "amplifier": run_amplifier,
        "mirror": run_mirror,
        "polymorph": run_polymorph,
        "archivist": run_archivist,
        "conductor": run_conductor,
    }
    agent_fn = agent_map.get(task.get("agent"))
    if agent_fn:
        result = agent_fn(task)
        log = {"task": task, "result": result, "completed": True}
        save_42_state(log)

def main_loop():
    print("⚙️ 42 Autonomy Engine Started")
    while True:
        tasks = load_tasks()
        for task in tasks:
            if judge_task(task):
                process_task(task)
            else:
                log_rejected(task)
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
