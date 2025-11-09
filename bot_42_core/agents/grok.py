class SafeEliteGrokAgent:
def __init__(self, agent_id, name, core_capacity=200, memory_limit=5000, skill_set=None):
    self.agent_id = agent_id
    self.name = name
    self.core_capacity = core_capacity
    self.memory_limit = memory_limit
    self.memory = {}  # Dynamic knowledge store
    self.skill_set = skill_set or ["analysis", "learning", "synthesis"]
    self.status = "online"
    self.log = []
    self.last_task_time = None
    self.memory_whitelist = ["last_insight"]  # Keys allowed for overwrite
    self.task_history_limit = 50  # Prevent log overflow

# Safe capacity update
def update_capacity(self, new_capacity):
    if 0 < new_capacity <= 10000:
        self.core_capacity = new_capacity
        self._log(f"Capacity boosted to {new_capacity}")
        return True
    return False

# Controlled memory storage
def store_memory(self, key, value):
    if len(self.memory) >= self.memory_limit:
        self._log(f"Memory cap hit trying to store '{key}'")
        return False
    # Only overwrite whitelisted keys
    if key in self.memory and key not in self.memory_whitelist:
        self._log(f"Prevented overwrite of '{key}'")
        return False
    self.memory[key] = value
    self._log(f"Stored '{key}: {value}'")
    return True

def retrieve_memory(self, key):
    result = self.memory.get(key)
    if result:
        self._log(f"Retrieved '{key}'")
    return result or f"{self.name} has no trace of '{key}'."

def get_status(self):
    return (f"{self.name} [ID: {self.agent_id}] - Status: {self.status}, "
            f"Capacity: {self.core_capacity}%, Memory: {len(self.memory)}/{self.memory_limit}, "
            f"Skills: {', '.join(self.skill_set)}")

def get_timestamp(self):
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S %d-%m-%Y")

def process_task(self, task_input, priority=1, skill="analysis"):
    if skill not in self.skill_set:
        return f"{self.name} cannot perform unknown skill '{skill}'."
    required_capacity = priority * 15
    if self.core_capacity < required_capacity:
        return f"{self.name} lacks capacity for this task (Required: {required_capacity}, Available: {self.core_capacity})."

    # Deduct capacity safely
    self.core_capacity -= required_capacity
    self.last_task_time = self.get_timestamp()
    response = f"{self.name} [ID: {self.agent_id}] processed '{task_input}' with {skill} skill."

    if "analyze" in skill.lower():
        insight = self.retrieve_memory("last_insight") or "Uncover the hidden pattern."
        response += f" — Insight: {insight}"
    elif "learn" in skill.lower():
        new_knowledge = task_input.split("learn")[-1].strip()
        if self.store_memory("last_insight", new_knowledge):
            response += f" — Learned: {new_knowledge}"
        else:
            response += " — Memory update blocked for safety."
    elif "synthesis" in skill.lower():
        keys = list(self.memory.keys())
        if keys:
            # Combine memory values safely instead of raw keys
            synthesized = " | ".join([str(self.memory[k]) for k in keys[:min(3, len(keys))]])
            response += f" — Synthesized: {synthesized}"
        else:
            response += " — No data to synthesize."

    self._log(f"Task '{task_input}' completed")
    return response

# Internal safe logging
def _log(self, message):
    timestamped = f"{message} at {self.get_timestamp()}"
    self.log.append(timestamped)
    # Keep log size bounded
    if len(self.log) > self.task_history_limit:
        self.log = self.log[-self.task_history_limit:]