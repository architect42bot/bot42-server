# bot42/core/test_agents.py
from agents.agent import run as agent_run

# List of example inputs to test each agent
test_tasks = [
    "observer: scan for suppression events",
    "sentinel: monitor defenses",
    "amplifier: boost signal",
    "mirror: duplicate content",
    "polymorph: remix the text",
    "archivist: save snapshot",
    "conductor: manage workflow",
    "katheron: judge this task"
]

for task in test_tasks:
    print(f"\n--- Testing: {task} ---")
    result = agent_run(task)
    print("Result:", result)