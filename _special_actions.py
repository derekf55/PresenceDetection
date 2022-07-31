from _home_assistant_functions import get_amient_light_level, turn_on_light
import datetime


LIGHT_LEVEL_THRESHOLD = 1.0
START_DISABLING_LIGHT_1_HOUR = 16
END_DISABLING_LIGHT_1_HOUR = 8

def switch_lights(self):
    try:
        light_level = get_amient_light_level()
    except Exception as e:
        print('Failed to get the light level')

    if light_level < LIGHT_LEVEL_THRESHOLD:
        print('Turn on all lights')
        lights = ['ergroomlight_ergroom','light2_livingroom','light1_livingroom']
    else:
        lights = ['ergroomlight_ergroom']
    
    now = datetime.datetime.now()
    if ((now.hour > START_DISABLING_LIGHT_1_HOUR or now.hour < END_DISABLING_LIGHT_1_HOUR)
        and 'Sam' in self.people_here):
        print('disable light 1')
        lights.remove('light1_livingroom')

    for light in lights:
        try:
            turn_on_light(light)
        except Exception as e:
            print(f'Problem turning on light {light}')
    