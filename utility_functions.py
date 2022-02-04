import datetime, json
import derek_functions as df
from requests import get, post
import threading
import time

ERROR_FILE = "error.log"
# Keeps the erg light on for 5 minutes by default
KEEP_ERG_LIGHT_INTERAL = 5 * 60

#@param room: Name of the room for lights 
#@return: Returns a list of light entities that are in the room
def get_lights_in_room(room) -> list:
    url = f"https://derekfranz.ddns.net:8542/api/states"
    try:
        response = get(url=url,headers=df.HOME_ASSISTANT_HEADERS,verify=False)
    except Exception as e:
        print('Problem getting light data')
        return []
    json_data = json.loads(response.text)
    entities = []
    
    for each in json_data:
        entity_id = each['entity_id']
        domain, entity = entity_id.split('.') 
        if domain == 'light':
            name, entitiy_room = entity.split('_')
            if entitiy_room == room or room == 'all':
                entities.append(entity)

    return entities

#@param light_name: Name of the light entity
#@return: Returns on if light is on, off if the light is off and False if there was an error
def get_light_status(light_name):
    try:
        url = f"https://derekfranz.ddns.net:8542/api/states/light.{light_name}"
        response = get(url,headers=df.HOME_ASSISTANT_HEADERS,verify=False)
        json_data = json.loads(response.text)
        return json_data['state']
    except Exception as e:
        error_msg = f'Failed to get light status {light_name} {e}'
        print(error_msg)
        return False

def turn_off_light(light_name):
    url = "https://derekfranz.ddns.net:8542/api/services/light/turn_off"
    service_data = {"entity_id":f'light.{light_name}'}
    try:
        response = post(url,headers=df.HOME_ASSISTANT_HEADERS,json=service_data,verify=False)
    except Exception as e:
        error_msg = f'Failed to turn off light {light_name} {e}'
        print(error_msg)
        return False
    return True

def delayed_erg_light():
    time.sleep(KEEP_ERG_LIGHT_INTERAL)
    turn_off_light('ergroomlight_ergroom')

def turn_on_light(light_name,keep_erg_light=False):
    # Check that the erg room light wasn't already on
    if light_name == 'ergroomlight_ergroom':
        erg_light_status = get_light_status('ergroomlight_ergroom')

    url = "https://derekfranz.ddns.net:8542/api/services/light/turn_on"
    service_data = {"entity_id":f'light.{light_name}'}
    try:
        response = post(url,headers=df.HOME_ASSISTANT_HEADERS,json=service_data,verify=False)
    except Exception as e:
        error_msg = f'Failed to turn on light {light_name} {e}'
        print(error_msg)
        return False
    
    if light_name == 'ergroomlight_ergroom' and keep_erg_light == False and erg_light_status == 'off':
        thread = threading.Thread(target=delayed_erg_light)
        thread.start()

    return True


def writeError(e):
    print(f'Error occured at {datetime.datetime.now()} {str(e)}')
    f = open(ERROR_FILE,'a')
    f.write(f'Error occured at {datetime.datetime.now()} {str(e)}'+'\n')
    f.close()

def get_state(entity_id):
    url = f"https://derekfranz.ddns.net:8542/api/states/{entity_id}"
    try:
        response = get(url,headers=df.HOME_ASSISTANT_HEADERS, verify=False)
        json_data = json.loads(response.text)
        state = json_data['state']
        return state
    except Exception as e:
        error_msg = f'Failed to get info on {entity_id} {e}'
        print(error_msg)
        writeError(error_msg)
        return False

def get_amient_light_level():
    url = "https://derekfranz.ddns.net:8542/api/states/sensor.temt6000illuminance_livingroom"
    try:
        response = get(url,headers=df.HOME_ASSISTANT_HEADERS, verify=False)
        json_data = json.loads(response.text)
        light_level = json_data['state']
        return float(light_level)
    except Exception as e:
        error_msg = f'Failed to get amient light info {e}'
        print(error_msg)
        writeError(error_msg)
        return False