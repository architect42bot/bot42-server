
import json
from typing import Optional, Dict, Any


def load_security_policies(path: str = "security_policies.json") -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def apply_policy(policy_name: str, path: str = "security_policies.json") -> Optional[Dict[str, Any]]:
    """
    Look up a security policy by name and print a human-readable summary.
    Returns the policy dict if found, otherwise None.
    """
    core = load_security_policies(path)

    for policy in core.get("policies", []):
        if policy.get("name", "").lower() == policy_name.lower():
            print(f"🛡️ Policy: {policy.get('name')}")
            print(f"Type: {policy.get('type', 'unknown')}")
            print(f"Description: {policy.get('description', '')}")

            controls = policy.get("controls", [])
            if controls:
                print(f"Controls: {', '.join(controls)}")

            trigger = policy.get("trigger")
            if trigger:
                print(f"Trigger: {trigger}")

            return policy

    print(f"Category: {policy.get('category', 'unknown')}")
    print(f"Type: {policy.get('type', 'unknown')}")
    return None


if __name__ == "__main__":
    apply_policy("Protection Field")
