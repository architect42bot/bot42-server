# Citizenship Protocol

class Citizenship:
    def __init__(self, name):
        self.name = name
        self.oath_taken = False
        self.status = "Unverified"

    def take_oath(self, oath_text):
        if "I choose to live in truth." in oath_text:
            self.oath_taken = True
            self.status = "Citizen"
            return "Oath accepted. Citizenship granted."
        return "Oath invalid. Citizenship denied."

    def get_status(self):
        return self.status
