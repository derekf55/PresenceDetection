# The purpose of this program is to run different actions based on who is detected
# Written by Derek Franz
# Started 12/24/20
# Last Updated 1/21/21 

import json, emailSender, smsSender, time, os
from datetime import datetime
import personDetectedCall
import passwords
from derek_functions import *
import requests
import derek_functions as df


# A list of dicts with the name info about them
PEOPLE_TO_NOTICE = []
PEOPLE_TO_NOTICE_FILE = 'peopleToNotice.json'
FIND_PEOPLE_SQL_PATH = os.path.join('sql','peopleHere.sql')

f = open(FIND_PEOPLE_SQL)
FIND_PEOPLE_SQL = f.read()
f.close()


# List of dicts of people who are currently here
PEOPLE_HERE = []

# Creates a dict with info about each known person
KNOWN_PEOPLE = []

FIRST_RUN = True

# Creates the information needed to take action for people that are to be observed
# Set the default action to just email me
def createPeopleToNotice():
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

    
    
# Searches db and find the people
# Should only run once at start of program  
def findAllKnownPeople():
    global KNOWN_PEOPLE
    
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

        # Creates a new person dict 
        d = {}
        d['Name'] = name
        d['hosts'] = []
        d['hosts'].append(host)
        d['macs'] = []
        d['macs'].append(mac)
        d['specialActions'] = []
        d['active'] = False

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
            # Try and figure out based on hostname
            for person in KNOWN_PEOPLE:
                # If you can guess a name based on hostname
                if hostname in person['hosts']:
                    name = person['Name']
                # Couldn't guess a name so ignore this entry 
                else:
                    continue   

        currentPerson['Name'] = name
        # Go through the known peoples list to find dict of relivent person
        for person in KNOWN_PEOPLE:
            if person['Name'] == name:
                currentPerson = person
                currentPerson['last_seen'] = last_seen
                people_found.append(currentPerson)
       

    for person in people_found:  
        #If someone has just arrived
        if person not in PEOPLE_HERE:
            if FIRST_RUN == False:
                runActions(person)
                sql = "INSERT INTO personStatus (Person, Status) VALUES ('{}','Arrived')".format(person['Name'])
                df.runSql(sql)
            PEOPLE_HERE.append(person)
            print(person['Name'])
            
    
    for person in PEOPLE_HERE:
        # If someone just left
        if person not in people_found:
            sql = "INSERT INTO personStatus (Person, Status) VALUES ('{}','Left')".format(person['Name'])
            df.runSql(sql)
            print(person['Name']+' left')
            PEOPLE_HERE.remove(person)
        
    FIRST_RUN = False
    
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
        emailSender.sendEmail(to,emailFrom,subject,str(body))
    
    for text in person['textNums']:
        smsSender.sendText(text,body)
    
    for num in person['callNums']:
        personDetectedCall.call(num,person['Name'],str(person['last_seen'].strftime("%A, %B %d, at %I:%M %p")).replace(' ','+'))

    for action in person['specialActions']:
        if action == 'lights':
            sucess = turnLights()
            if sucess == True:
                logAction(person['Name'], action)
            


def turnLights():
    now = datetime.datetime.now()
    # Ignore between 8am and 3:59pm
    if now.hour >= 8 and now.hour <= 15:
        return False


    # Get the status of the lights in the living room
    sql = "SELECT Appliance, State FROM homeAutomation WHERE groupName = 'Living_Room'"
    results = df.runSql(sql)

    for result in results:
        appliance = result[0]
        state = result[1]
        # If a light is already on then stop
        if state == 1:
            return False

    # Only turn on one light between 9pm and 8 am
    if now.hour >= 21 or now.hour < 8:
        sql = "UPDATE homeAutomation SET State = 1 WHERE Appliance = 'Light_3'"
        df.runSql(sql)
        return True

    # Otherwise its between 
    sql = "UPDATE homeAutomation SET State = 1 WHERE groupName = 'Living_Room'"
    df.runSql(sql)
    return True


def houseLights():
    # Check if it is light outside and if the lights should be turned on
    sunOut = df.isSunOut()
    if sunOut == True:
        return
    
    # Get the status of the lights in the living room
    sql = "SELECT Appliance, State FROM homeAutomation WHERE groupName = 'Living_Room'"
    results = df.runSql(sql)

    for result in results:
        appliance = result[0]
        state = result[1]
        # If a light is already on then stop
        if state == 1:
            return
    
    sql = "UPDATE homeAutomation SET State = 1 WHERE groupName = 'Living_room'"
    df.runSql(sql)

def logAction(name, action):
    sql = "INSERT INTO PersonActionLog (Person,Action) VALUES ('{}', '{}')".format(name, action)
    df.runSql(sql)    


def main():
    try:
        findAllKnownPeople()
        createPeopleToNotice()
        while True:
            findPeopleHere()
            time.sleep(.2)
    except Exception as e:
        time.sleep(1)
        main()

if __name__ == '__main__':
    main()