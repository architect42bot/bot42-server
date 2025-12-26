from collections import defaultdict
from datetime import date

# in-memory for now (safe for testing)
_daily_usage = defaultdict(lambda: {
    "tokens_in": 0,
    "tokens_out": 0,
    "agent_calls": defaultdict(int),
    "estimated_cost": 0.0,
})

AGENT_COSTS = {
    "grok": 0.01,      # placeholder per call (we refine later)
    "claude": 0.008,
    "openai": 0.002,
    "local": 0.0,
}

def record_usage(agent: str, tokens_in: int, tokens_out: int):
    today = str(date.today())
    entry = _daily_usage[today]

    entry["tokens_in"] += tokens_in
    entry["tokens_out"] += tokens_out
    entry["agent_calls"][agent] += 1
    entry["estimated_cost"] += AGENT_COSTS.get(agent, 0.0)

def get_today_usage():
    today = str(date.today())
    return _daily_usage[today]