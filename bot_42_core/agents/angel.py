# agent_angel.py

class AgentAngel:
    def __init__(self, name="Angel"):
        self.name = name
        self.vision_range = 100  # How far Angel can detect threats or opportunities
        self.influence_strength = 50  # How much Angel can subtly sway outcomes
        self.healing_power = 40  # How much Angel can heal or repair

    def detect_threats(self, environment):
        """
        Scan the environment for dangers or hidden issues.
        Returns a list of detected threats.
        """
        threats = []
        for entity in environment.get("entities", []):
            if entity.get("hostile", False):
                threats.append(entity)
        return threats

    def guide_ally(self, ally, situation):
        """
        Provide guidance to an ally in a given situation.
        Returns a recommendation or strategy.
        """
        advice = f"{ally['name']}, be cautious in {situation['location']}. Consider {situation['action']}."
        return advice

    def heal(self, target):
        """
        Heal or repair the target (could be a person, system, or environment).
        """
        if target.get("health") is not None:
            target["health"] += self.healing_power
            target["health"] = min(target["health"], 100)
            return f"{self.name} healed {target['name']} to {target['health']} health."
        return f"{target['name']} cannot be healed."

    def influence_outcome(self, situation):
        """
        Apply subtle influence to sway the outcome positively.
        """
        outcome = f"{self.name} nudged the situation towards a favorable outcome."
        return outcome

# Example usage
if __name__ == "__main__":
    environment = {"entities": [{"name": "Enemy Drone", "hostile": True}, {"name": "Bystander", "hostile": False}]}
    angel = AgentAngel()

    print("Detected threats:", angel.detect_threats(environment))

    ally = {"name": "Agent Light"}
    situation = {"location": "Bridge", "action": "take cover"}
    print(angel.guide_ally(ally, situation))

    target = {"name": "Agent Light", "health": 60}
    print(angel.heal(target))

    print(angel.influence_outcome(situation))