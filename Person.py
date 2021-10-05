class Person:

    def __init__(self,name=None) -> None:
        self.name = name
        self.textNums = []
        self.callNums = []
        self.hosts = []
        self.macs = []
        self.special_actions = []
        self.Resident = False
        self.notify_desk_phone = False
        self.active = False
        self.emails = []
        self.last_seen = None
        self.speak_to_google = []

