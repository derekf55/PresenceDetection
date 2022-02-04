import datetime, json
import derek_functions as df
from requests import get, post
from utility_functions import writeError, turn_on_light, turn_off_light, get_amient_light_level
from utility_functions import get_state, get_lights_in_room, get_light_status

class Person:

    def __init__(self,name=None,debug=False) -> None:
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
        self.num_notifications_sent_last_hour = 0
        self.last_text_sent = None
        self.light_states = {}
        self.save_light_states()

        if debug == True:
            self.hosts.append('hostname')
            self.macs.append('mac')
            self.last_seen = datetime.datetime.now()
            self.active = True

    def save_light_states(self):
        if self.name == "Derek":
            lights = get_lights_in_room('dereksroom')
            for light in lights:
                state = get_light_status(light)
                self.light_states[light] = state


    def return_light_states(self):
        for light, state in self.light_states.items():
            if state == 'on':
                turn_on_light(light)
            elif state == 'off':
                turn_off_light(light)


    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

