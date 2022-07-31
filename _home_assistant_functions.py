from concurrent.futures import thread
from requests import get, post
import derek_functions as df
import json
import time
import threading
import urllib3
urllib3.disable_warnings()

def get_amient_light_level():
    url = "https://derekfranz.ddns.net:8542/api/states/sensor.temt6000illuminance_livingroom"
    response = get(url,headers=df.HOME_ASSISTANT_HEADERS, verify=False)
    json_data = json.loads(response.text)
    light_level = json_data['state']
    return float(light_level)

def delayed_erg_light():
    time.sleep(5*60)
    turn_off_light('ergroomlight_ergroom')

def turn_on_light(light_name):
    url = "https://derekfranz.ddns.net:8542/api/services/light/turn_on"
    service_data = {"entity_id":f'light.{light_name}'}
    if light_name == 'ergroomlight_ergroom':
        try:
            url2 = f"https://derekfranz.ddns.net:8542/api/states/light.{light_name}"
            resposnse = get(url=url2, headers=df.HOME_ASSISTANT_HEADERS, verify=False)
            json_data = json.loads(resposnse.text)
            state = json_data['state']
            if state != 'off':
                return
        except Exception as e:
            print('Cant check the erg room so ignore')
    
        t = threading.Thread(target=delayed_erg_light)
        t.start()
        

    post(url, headers=df.HOME_ASSISTANT_HEADERS, json=service_data, verify=False)

def turn_off_light(light_name):
    url = "https://derekfranz.ddns.net:8542/api/services/light/turn_off"
    service_data = {"entity_id":f'light.{light_name}'}
    post(url, headers=df.HOME_ASSISTANT_HEADERS, json=service_data, verify=False)


get_amient_light_level()