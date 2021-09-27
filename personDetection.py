# The purpose of this program is to run different actions based on who is detected
# Written by Derek Franz
# Started 12/24/20

import json, time, os
from datetime import datetime
from twilio import rest
import personDetectedCall
from derek_functions import *
import requests
import derek_functions as df
from requests.api import post, get

# A list of dicts with the name info about them
PEOPLE_TO_NOTICE = []
PEOPLE_TO_NOTICE_FILE = 'peopleToNotice.json'
FIND_PEOPLE_SQL_PATH = os.path.join('sql','peopleHere.sql')

f = open(FIND_PEOPLE_SQL_PATH)
FIND_PEOPLE_SQL = f.read()
f.close()

ERROR_FILE = "error.log"

# List of dicts of people who are currently here
PEOPLE_HERE = []

# Creates a dict with info about each known person
KNOWN_PEOPLE = []

FIRST_RUN = True
CURRENT_PRIORITY = ""

# 8am and 6pm 
END_SWITCHING_LIGHT_HOUR = 8
START_SWITCHING_LIGHT_HOUR = 17
HOME_ALONE_NUM = "+17153471797"

# Creates the information needed to take action for people that are to be observed
# Set the default action to just email me
def __createPeopleToNotice():
    global PEOPLE_TO_NOTICE_FILE
    global PEOPLE_TO_NOTICE

    # Tries to read the JSON file with the info about people to Notice
    try:
        f = open(PEOPLE_TO_NOTICE_FILE)
    except Exception as e:
        print('Failed to open file')
        exit()
    
    # Reads the json file
    try:
        jsonData = json.load(f)
    except Exception as e:
        print('Failed to read json file')
        exit()

    for person in jsonData.keys():
        # Find their dict in the known persons list then update
        for item in KNOWN_PEOPLE:
            if item['Name'] == person:
                # This is the person to edit
                emails = jsonData[person]['emails']
                textNums = jsonData[person]['textNums']
                callNums = jsonData[person]['callNums']
                active = jsonData[person]['active']
                item['emails'] = emails
                item['textNums'] = textNums
                item['callNums'] = callNums
                item['active'] = active
                item['specialActions'] = jsonData[person]['specialActions']
                PEOPLE_TO_NOTICE.append(item)


def createPeopleToNoticeDatabase():
    global PEOPLE_TO_NOTICE
    global KNOWN_PEOPLE
    global CURRENT_PRIORITY
    priority = df.runSql("SELECT PriorityLevel FROM personDetectionPriority WHERE ID = 1")[0][0]
    PEOPLE_TO_NOTICE = []

    #findAllKnownPeople()
    clearActionDetails()

    if priority != CURRENT_PRIORITY:
        print(f'Switching to {priority}')
        
    if priority == "Disabled":
        PEOPLE_TO_NOTICE = []
        #findAllKnownPeople()
        for person in KNOWN_PEOPLE:
            person['active'] = False
        CURRENT_PRIORITY = "Disabled"
        return
    elif priority == "Home Alone":
        PEOPLE_TO_NOTICE = []
        #findAllKnownPeople()
        CURRENT_PRIORITY = "Home Alone"
        for person in KNOWN_PEOPLE:
            if person['Name'] == 'Derek':
                continue
            if HOME_ALONE_NUM not in person['textNums']:
                person['textNums'].append(HOME_ALONE_NUM)
            person['active'] = True
            person['NotifyDeskPhone'] = True
    elif priority == "Outside Detection":
        PEOPLE_TO_NOTICE = []
        #findAllKnownPeople()

        for person in KNOWN_PEOPLE:
            if person['Resident'] == False:
                person['active'] = True
                person['NotifyDeskPhone'] = True
                if HOME_ALONE_NUM not in person['textNums']:
                    person['textNums'].append(HOME_ALONE_NUM)
        
        CURRENT_PRIORITY = "Outside Detection"
        
    PEOPLE_TO_NOTICE = []
    #findAllKnownPeople()
        # for person in KNOWN_PEOPLE:
        #     if HOME_ALONE_NUM in person['textNums']:
        #         person['textNums'].remove(HOME_ALONE_NUM)
    
    CURRENT_PRIORITY = priority
    sql = "SELECT Name, email, textNum, callNum, specialAction FROM peopleToNotice WHERE active = 1 and PriorityLevel = (SELECT PriorityLevel FROM personDetectionPriority WHERE ID = 1)"
    results = df.runSql(sql)
    # Keeps actions from normal and adds new actions
    if priority == "Home Alone" or priority == "Outside Detection":
        #print(f'Since priorty is {priority} we will use the normnal actions too')
        sql = "SELECT Name, email, textNum, callNum, specialAction FROM peopleToNotice WHERE active = 1 and PriorityLevel = 'Normal'"
        results = df.runSql(sql)
    else:
        pass
        #print(f'Since priorty is {priority} we will call it here')
    for entry in results:
        name = entry[0]
        email = entry[1]
        text = entry[2]
        call = entry[3]
        action = entry[4]
        for person in KNOWN_PEOPLE:
            if person['Name'] == name:
                if email is not None and email not in person['emails']:
                    person['emails'].append(email)
                if text is not None and text not in person['textNums']:
                    person['textNums'].append(text)
                if call is not None and call not in person['callNums']:
                    person['callNums'].append(call)
                if action is not None and action not in person['specialActions']:
                    person['specialActions'].append(action)
                person['active'] = True 

    

def clearActionDetails():
     global KNOWN_PEOPLE
     for person in KNOWN_PEOPLE:
         person['specialActions'] = []
         person['active'] = False
         person['emails'] = []
         person['textNums'] = []
         person['callNums'] = []
         person['NotifyDeskPhone'] = False

# Searches db and find the people
# Should only run once at start of program  
def findAllKnownPeople():
    global KNOWN_PEOPLE
    KNOWN_PEOPLE = []
    #KNOWN_PEOPLE = []
    # Reads the sql query for finding the known people
    path = os.path.join('sql','knownPeople.sql')
    f = open(path)
    sql = f.read()
    f.close()
    
    # Get access to database
    results = runSql(sql) 

    for item in results:
        mac = item[0]
        host = item[1]
        name = item[2]
        residenceStatus = item[3]

        # Creates a new person dict 
        d = {}
        d['Name'] = name
        d['hosts'] = []
        d['hosts'].append(host)
        d['macs'] = []
        d['macs'].append(mac)
        d['specialActions'] = []
        d['active'] = False
        d['emails'] = []
        d['textNums'] = []
        d['callNums'] = []
        d['Resident'] = False
        d['NotifyDeskPhone'] = False
        if residenceStatus == 1:
            d['Resident'] = True
        

        # Checks if this is a different device from the same person
        personExists = False
        for person in KNOWN_PEOPLE:
            if person['Name'] == name:
                person['macs'].append(mac)
                person['hosts'].append(host)
                personExists = True
                break
            
        # Add if it's a new person
        if personExists == False:
            KNOWN_PEOPLE.append(d)

    # Remove duplicates
    for person in KNOWN_PEOPLE:
        person['macs'] = list(set(person['macs']))
        person['hosts'] =  list(set(person['hosts']))

    
    

# Pull from db and update the info of who is here
def findPeopleHere():
    global PEOPLE_HERE
    global KNOWN_PEOPLE
    global FIND_PEOPLE_SQL
    global FIRST_RUN

    # Run sql that determines who is here right now
    people_found = []

    # Get access to database
    results = runSql(FIND_PEOPLE_SQL)

    # If there are no people at the house
    if len(results) < 0:
        print('No one found')
        return
    # for each device that is returned as being currently at the house
    for item in results:
        name = item[0]
        hostname = item[1]
        mac = item[2]
        last_seen = item[3]
        currentPerson = {}
        
        # If the person is not mapped in MacToName
        if name == None:
            newNameFound = 0
            # Try and figure out based on hostname
            for person in KNOWN_PEOPLE:
                # If you can guess a name based on hostname
                #print(person['hosts'])
                if hostname in person['hosts']:
                    name = person['Name']
                    newNameFound = 1
                
            if newNameFound == 0:
                try:
                    name = hostname
                except Exception as e:
                    writeError(f'From line 220 {e}')

        currentPerson['Name'] = name
        # Go through the known peoples list to find dict of relivent person
        for person in KNOWN_PEOPLE:
            if person['Name'] == name:
                currentPerson = person
                currentPerson['last_seen'] = last_seen
                people_found.append(currentPerson)
        
        # If this is still an unknown person
        if currentPerson not in KNOWN_PEOPLE:
            currentPerson['hosts'] = []
            currentPerson['macs'] = []
            currentPerson['last_seen'] = last_seen
            currentPerson['emails'] = []
            currentPerson['textNums'] = []
            currentPerson['specialActions'] = []
            currentPerson['callNums'] = []
            currentPerson['hosts'].append(hostname)
            currentPerson['macs'].append(mac)
            currentPerson['Resident'] = False
            currentPerson['active'] = False
            currentPerson['NotifyDeskPhone'] = False
            if CURRENT_PRIORITY == 'Outside Detection' or CURRENT_PRIORITY == 'Home Alone':
                currentPerson['active'] = True
                currentPerson['NotifyDeskPhone'] = True
                currentPerson['textNums'].append(HOME_ALONE_NUM)
            
            #currentPerson['last_seen'] = last_seen
            KNOWN_PEOPLE.append(currentPerson)
            people_found.append(currentPerson)
       
    if FIRST_RUN == True:
        sql = "DELETE FROM PeopleHere"
        df.runSql(sql)

    needs_update = False

    for person in people_found:  
        #If someone has just arrived
        if person not in PEOPLE_HERE:
            needs_update = True
            resident = 0
            if person['Resident'] == True:
                resident = 1
            sql = f"INSERT INTO PeopleHere (Name, hostname, MacAddress, Resident) VALUES ('{person['Name']}', '{person['hosts'][0]}', '{person['macs'][0]}', {resident})"
            df.runSql(sql)
            #print(sql)
            if person['NotifyDeskPhone'] == True and FIRST_RUN == False:
                print('Going to notify the desk phone')
                sql = f"INSERT INTO `ProcessToRun` (`Command`, `Server`, `args`) VALUES ('personArrival', 'server', '{person['Name']}');"
                df.runSql(sql)
            if FIRST_RUN == False:
                runActions(person)
                sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person['Name']}','Arrived')"
                df.runSql(sql)
            PEOPLE_HERE.append(person)
            print(person['Name'])
        else:
            sql = f"UPDATE `PeopleHere` SET Last_Updated = CURRENT_TIMESTAMP WHERE Name = '{person['Name']}' "
            df.runSql(sql)
                   
    for person in PEOPLE_HERE:
        # If someone just left
        if person not in people_found:
            needs_update = True
            sql = f"DELETE FROM PeopleHere WHERE Name = '{person['Name']}'"
            df.runSql(sql)
            sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person['Name']}','Left')"
            df.runSql(sql)
            print(person['Name']+' left')
            try:
                PEOPLE_HERE.remove(person)
            except Exception as e:
                writeError(f'Failed to remove this person {e}')

    FIRST_RUN = False
    if needs_update == True:
        sql = f"INSERT INTO ProcessToRun (Command, Server) VALUES ('Presence_Phone','server')"
        df.runSql(sql)
    
# Run actions on the person dict
#@param person: The person dict that contains the actions to be performed
# Actions list 
# Email
# Text
# Call
# Lights stuff 
def runActions(person):
    if person['active'] == False:
        return
    for email in person['emails']:
        to = email
        emailFrom = 'derekfran55@gmail.com'
        subject = person['Name']+" detected"
        body = person['Name']+' detected on '+person['last_seen'].strftime("%A, %B %d, at %I:%M %p")
        df.sendEmail(to,emailFrom,subject,str(body))

    for text in person['textNums']:
        body = person['Name']+' detected on '+person['last_seen'].strftime("%A, %B %d, at %I:%M %p")
        df.sendText(text,body)
        #print(f"{person['textNums']} is getting a text")
        #print(person)
    
    for num in person['callNums']:
        personDetectedCall.call(num,person['Name'],str(person['last_seen'].strftime("%A, %B %d, at %I:%M %p")).replace(' ','+'))

    for action in person['specialActions']:
        if action == 'lights':
            sucess = turnLights()
            if sucess == True:
                logAction(person['Name'], action)
        if action == 'beastMode':
            beastMode()

def turnLights():
    now = datetime.datetime.now()
    # Ignore between these hours
    if now.hour >= END_SWITCHING_LIGHT_HOUR and now.hour <= START_SWITCHING_LIGHT_HOUR:
        return False

    # Get the status of the lights in the living room
    # sql = "SELECT Appliance, State FROM homeAutomation WHERE groupName = 'Living_Room'"
    # results = df.runSql(sql)

    url = "https://derekfranz.ddns.net:8542/api/states"
    headers = HOME_ASSISTANT_HEADERS
    devices_to_switch = ['light_1','light_2']

    response = get(url,headers=headers,verify=False)
    list_of_json = json.loads(response.text)
    for item in list_of_json:
        domain, name = item['entity_id'].split('.')
        if name in devices_to_switch:
            #service_data = {"entity_id":item['entity_id']}
            state = item['state']
            if state == 'on':
                return False
   

    # Only turn on one light between 9pm and 8 am
    if now.hour >= 21 or now.hour < 8:
        # sql = "UPDATE homeAutomation SET State = 1 WHERE Appliance = 'Light_2'"
        # df.runSql(sql)

        url = "https://derekfranz.ddns.net:8542/api/services/light/turn_on"
        service_data = {"entity_id":'light.light_2'}
        response = post(url,headers=headers,json=service_data,verify=False)

        return True

    # Otherwise its between 
    sql = "UPDATE homeAutomation SET State = 1 WHERE groupName = 'Living_Room'"
    df.runSql(sql)

    url = "https://derekfranz.ddns.net:8542/api/services/light/turn_on"
    for each in devices_to_switch:
        service_data = {"entity_id":f'light.{each}'}
        response = post(url,headers=headers,json=service_data,verify=False)

    return True

def logAction(name, action):
    sql = f"INSERT INTO PersonActionLog (Person,Action) VALUES ('{name}', '{action}')"
    df.runSql(sql)    


def beastMode():
    # Toggle the vibe lights and the regular lights 5 times
    for i in range(0,2):
        sql = "INSERT INTO ProcessToRun (Command, Server) VALUES ('LEDpower','Pi')"
        df.runSql(sql)

        sql = "UPDATE homeAutomation SET State = 1 WHERE groupName = 'Living_Room' "
        df.runSql(sql)

        time.sleep(3)

        sql = "UPDATE homeAutomation SET State = 0 WHERE groupName = 'Living_Room' "
        df.runSql(sql)

        sql = "INSERT INTO ProcessToRun (Command, Server) VALUES ('LEDpower','Pi')"
        df.runSql(sql)

        sql = "INSERT INTO ProcessToRun (Command, Server) VALUES ('Donny','Pi')"
        df.runSql(sql)

        time.sleep(3)
    
def writeError(e):
    print(f'Error occured at {datetime.datetime.now()} {str(e)}')
    f = open(ERROR_FILE,'a')
    f.write(f'Error occured at {datetime.datetime.now()} {str(e)}'+'\n')
    f.close()

def main():
    try:
        #findAllKnownPeople()
        #createPeopleToNotice()
        findAllKnownPeople()
        while True:
            createPeopleToNoticeDatabase()
            findPeopleHere()
            time.sleep(1)
    except Exception as e:
        time.sleep(1)
        print(f'Error in main {e}')
        writeError(f'error occured in main {e}')
        main()

if __name__ == '__main__':
    main()