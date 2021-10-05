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
from Person import Person

# A list of dicts with the name info about them
FIND_PEOPLE_SQL_PATH = os.path.join('sql','peopleHere.sql')

f = open(FIND_PEOPLE_SQL_PATH)
FIND_PEOPLE_SQL = f.read()
f.close()

ERROR_FILE = "error.log"

# 8am and 6pm 
END_SWITCHING_LIGHT_HOUR = 8
START_SWITCHING_LIGHT_HOUR = 17
HOME_ALONE_NUM = "+17153471797"


class PresenceDetection:
    def __init__(self) -> None:
        self.first_run = True
        self.known_people = []
        self.current_priority = ""
        self.people_here = []

    def create_people_to_notice(self):
        priority = df.runSql("SELECT PriorityLevel FROM personDetectionPriority WHERE ID = 1")[0][0]

        if priority != self.current_priority:
            print(f'Switching to {priority}')

        if priority == 'Disabled':
            for person in self.known_people:
                person.active = False
        elif priority == "Home Alone":
            for person in self.known_people:
                if person.name == "Derek":
                    continue
            if HOME_ALONE_NUM not in person.textNums:
                person.append(HOME_ALONE_NUM)
                person.active = True
                person.notify_desk_phone = True
        elif priority == "Outside Detection":
            for person in self.known_people:
                if person.Resident == False:
                    person.active = True
                    person.notify_desk_phone = True
                    if HOME_ALONE_NUM not in person.textNums:
                        person.textNums.append(HOME_ALONE_NUM)
        
        self.current_priority = priority

        sql = "SELECT Name, email, textNum, callNum, specialAction FROM peopleToNotice WHERE active = 1 and PriorityLevel = (SELECT PriorityLevel FROM personDetectionPriority WHERE ID = 1)"
        results = df.runSql(sql)        
        if priority == "Home Alone" or priority == "Outside Detection":
        #print(f'Since priorty is {priority} we will use the normnal actions too')
            sql = "SELECT Name, email, textNum, callNum, specialAction FROM peopleToNotice WHERE active = 1 and PriorityLevel = 'Normal'"
            results = df.runSql(sql)

        for entry in results:
            name = entry[0]
            email = entry[1]
            text = entry[2]
            call = entry[3]
            action = entry[4]
            for person in self.known_people:
                if person.name == name:
                    if email is not None and email not in person.emails:
                        person.emails.append(email)
                    if text is not None and text not in person.textNums:
                        person.textNums.append(text)
                    if call is not None and call not in person.callNums:
                        person.callNums.append(call)
                    if action is not None and action not in person.special_actions:
                        person.special_actions.append(action)
                    person.active = True 

    # Searches db and find the people
    # Should only run once at start of program  
    def findAllKnownPeople(self):
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
            new_person = Person(name)
            new_person.hosts.append(host)
            new_person.macs.append(mac)
            if residenceStatus == 1:
                new_person.Resident = True
                

            # Checks if this is a different device from the same person
            personExists = False
            for person in self.known_people:
                if person.name == name:
                    person.macs.append(mac)
                    person.hosts.append(host)
                    personExists = True
                    break
                
            # Add if it's a new person
            if personExists == False:
                self.known_people.append(new_person)

        # Remove duplicates
        for person in self.known_people:
            person.macs = list(set(person.macs))
            person.hosts =  list(set(person.hosts))
    
    # Pull from db and update the info of who is here
    def findPeopleHere(self):
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
            currentPerson = Person()
            
            # If the person is not mapped in MacToName
            if name == None:
                newNameFound = 0
                # Try and figure out based on hostname
                for person in self.known_people:
                    # If you can guess a name based on hostname
                    #print(person['hosts'])
                    if hostname in person.hosts:
                        name = person.name
                        newNameFound = 1
                    
                if newNameFound == 0:
                    try:
                        name = hostname
                    except Exception as e:
                        writeError(f'From line 220 {e}')

            currentPerson.name = name
            # Go through the known peoples list to find dict of relivent person
            for person in self.known_people:
                if person.name == name:
                    currentPerson = person
                    currentPersonlast_seen = last_seen
                    people_found.append(currentPerson)
            
            # If this is still an unknown person
            if currentPerson not in self.known_people:
                currentPerson.last_seen = last_seen
                currentPerson.hosts.append(hostname)
                currentPerson.macs.append(mac)
                if self.current_priority == 'Outside Detection' or self.current_priority == 'Home Alone':
                    currentPerson.active = True
                    currentPerson.notify_desk_phone = True
                    currentPerson.textNums.append(HOME_ALONE_NUM)
                
                #currentperson.last_seen = last_seen
                self.known_people.append(currentPerson)
                people_found.append(currentPerson)
        df.delete_old_voicemails()
        if self.first_run == True:
            sql = "DELETE FROM PeopleHere"
            df.runSql(sql)

        needs_update = False

        for person in people_found:  
            #If someone has just arrived
            if person not in self.people_here:
                needs_update = True
                resident = 0
                if person.Resident == True:
                    resident = 1
                sql = f"INSERT INTO PeopleHere (Name, hostname, MacAddress, Resident) VALUES ('{person.name}', '{person['hosts'][0]}', '{person['macs'][0]}', {resident})"
                df.runSql(sql)
                #print(sql)
                if person.notify_desk_phone == True and self.first_run == False:
                    print('Going to notify the desk phone')
                    sql = f"INSERT INTO `ProcessToRun` (`Command`, `Server`, `args`) VALUES ('personArrival', 'server', '{person.name}');"
                    df.runSql(sql)
                if self.first_run == False:
                    runActions(person)
                    sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person.name}','Arrived')"
                    df.runSql(sql)
                self.people_here.append(person)
                print(person.name)
            else:
                sql = f"UPDATE `PeopleHere` SET Last_Updated = CURRENT_TIMESTAMP WHERE Name = '{person.name}' "
                df.runSql(sql)
                    
        for person in self.people_here:
            # If someone just left
            if person not in people_found:
                needs_update = True
                sql = f"DELETE FROM PeopleHere WHERE Name = '{person.name}'"
                df.runSql(sql)
                sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person.name}','Left')"
                df.runSql(sql)
                print(person.name+' left')
                try:
                    self.people_here.remove(person)
                except Exception as e:
                    writeError(f'Failed to remove this person {e}')

        self.first_run = False
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
    if person.active == False:
        return
    for email in person.emails:
        to = email
        emailFrom = 'derekfran55@gmail.com'
        subject = person.name+" detected"
        body = person.name+' detected on '+person.last_seen.strftime("%A, %B %d, at %I:%M %p")
        df.sendEmail(to,emailFrom,subject,str(body))

    for text in person.textNums:
        body = person.name+' detected on '+person.last_seen.strftime("%A, %B %d, at %I:%M %p")
        df.sendText(text,body)
        #print(f"{person.textNums} is getting a text")
        #print(person)
    
    for num in person.callNums:
        personDetectedCall.call(num,person.name,str(person.last_seen.strftime("%A, %B %d, at %I:%M %p")).replace(' ','+'))

    for action in person.special_actions:
        if action == 'lights':
            sucess = turnLights()
            if sucess == True:
                logAction(person.name, action)
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