# The purpose of this program is to run different actions based on who is detected
# Written by Derek Franz
# Started 12/24/20

import json, time, os
from logging import error
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

        # Contains all the sql that failed to run so it can try and be run again and catch the system up
        self.failed_sql = []

    def create_people_to_notice(self):
        try:
            priority = df.runSql("SELECT PriorityLevel FROM personDetectionPriority WHERE ID = 1")[0][0]
        except Exception as e:
            print('Failed to get new priority going to try and conintue with old priorty')
            writeError(f'Unable to get new priority {str(e)}')
            return

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
                    person.textNums.append(HOME_ALONE_NUM)
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
        try:
            results = df.runSql(sql)        
            if priority == "Home Alone" or priority == "Outside Detection":
            #print(f'Since priorty is {priority} we will use the normnal actions too')
                sql = "SELECT Name, email, textNum, callNum, specialAction FROM peopleToNotice WHERE active = 1 and PriorityLevel = 'Normal'"
                results = df.runSql(sql)
        except Exception as e:
            print('Failed to get info on new priority. Going to keep the old prioty')
            writeError(f'Failed to get info on new priority. Going to keep the old prioty {str(e)}')
            return

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
        try:
            results = runSql(sql)
        except Exception as e:
            print('Problem getting known people')
            print('Going to keep the people we know and try to continue')
            return

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
    
    # Try and make up for the errors if not possible just ignore and wait 
    def make_up_errors(self):
        for sql in self.failed_sql:
            try:
                df.runSql(sql)
                self.failed_sql.remove(sql)
            except Exception as e:
                continue

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
                        self.writeError(f'From line 220 {e}')

            currentPerson.name = name
            # Go through the known peoples list to find dict of relivent person
            for person in self.known_people:
                if person.name == name:
                    currentPerson = person
                    currentPerson.last_seen = last_seen
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
        try:
            df.delete_old_voicemails()
        except Exception as e:
            self.writeError(f'There was a problem accessing freePBX {str(e)}')
        
        if self.first_run == True:
            sql = "DELETE FROM PeopleHere"
            try:
                df.runSql(sql)
            except Exception as e:
                error_msg = f'Failed to clear the people here.  Going to return and try again {e}'
                print(error_msg)
                writeError(error_msg)
                return

        needs_update = False


        # This is used to ensure that the people here table is only updated if everyone 
        temp_people_here = []

        for person in people_found:  
            #If someone has just arrived
            if person not in self.people_here:
                needs_update = True
                resident = 0
                if person.Resident == True:
                    resident = 1
                try:
                    sql = f"INSERT INTO PeopleHere (Name, hostname, MacAddress, Resident) VALUES ('{person.name}', '{person.hosts[0]}', '{person.macs[0]}', {resident})"
                    df.runSql(sql)
                except Exception as e:
                    error_msg = f'Failed to update people here table.  Website will be incorrect after this point {e}'
                    print(error_msg)
                    writeError(error_msg)
                    self.failed_sql.append(sql)

                #print(sql)
                if person.notify_desk_phone == True and self.first_run == False:
                    try:
                        sql = f"INSERT INTO `ProcessToRun` (`Command`, `Server`, `args`) VALUES ('personArrival', 'server', '{person.name}');"
                        df.runSql(sql)
                    except Exception as e:
                        error_msg = f'Failed to notify desk phone, going to continue {e}'
                        print(error_msg)
                        writeError(error_msg)
                        self.failed_sql.append(sql)


                if self.first_run == False:
                    self.runActions(person)
                    try:
                        sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person.name}','Arrived')"
                        df.runSql(sql)
                    except Exception as e:
                        error_msg = f'Failed to log arrival.  Going to continue {e}'
                        print(error_msg)
                        writeError(error_msg)
                        self.failed_sql(sql)
                        
                self.people_here.append(person)
                print(person.name)
            else:
                try:
                    sql = f"UPDATE `PeopleHere` SET Last_Updated = CURRENT_TIMESTAMP WHERE Name = '{person.name}' "
                    df.runSql(sql)
                except Exception as e:
                    error_msg = f'Failed to access database. Going to continue and not try and make up this action {e}'
                    print(error_msg)
                    writeError(error_msg)
                    
        for person in self.people_here:
            # If someone just left
            if person not in people_found:
                needs_update = True
                try:
                    sql = f"DELETE FROM PeopleHere WHERE Name = '{person.name}'"
                    df.runSql(sql)
                except Exception as e:
                    error_msg = f'Failed to remove person from people here table.  Going to continue and try to make up this action {e}'
                    print(error_msg)
                    writeError(error_msg)
                    self.failed_sql(sql)
                try:
                    sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person.name}','Left')"
                    df.runSql(sql)
                except Exception as e:
                    error_msg = f'Failed to log person leaving. Going to continue and try and update later'
                    print(error_msg)
                    writeError(error_msg)
                    self.failed_sql(sql)

                print(person.name+' left')
                try:
                    self.people_here.remove(person)
                except Exception as e:
                    print('Failed to remove a person')
                    self.writeError(f'Failed to remove this person {e}')

        self.first_run = False
        if needs_update == True:
            try:
                sql = f"INSERT INTO ProcessToRun (Command, Server) VALUES ('Presence_Phone','server')"
                df.runSql(sql)
            except Exception as e:
                error_msg = f'Failed to request update to desk phone.  Going to continue anyway {e}'
                print(error_msg)
                writeError(error_msg)
                self.failed_sql.append(sql)
    
    # Run actions on the person dict
    #@param person: The person dict that contains the actions to be performed
    # Actions list 
    # Email
    # Text
    # Call
    # Lights stuff 
    def runActions(self,person):
        if person.active == False:
            return
        for email in person.emails:
            to = email
            emailFrom = 'derekfran55@gmail.com'
            subject = person.name+" detected"
            body = person.name+' detected on '+person.last_seen.strftime("%A, %B %d, at %I:%M %p")
            status = df.sendEmail(to,emailFrom,subject,str(body))
            if status == False:
                error_msg = f'Failed to send email. Going to skip this action'
                print(error_msg)
                writeError(error_msg)

        for text in person.textNums:
            print('Going to send text')
            body = person.name+' detected on '+person.last_seen.strftime("%A, %B %d, at %I:%M %p")
            status = df.sendText(text,body)
            if status == False:
                error_msg = 'failed to send text. Not going to try and make this action up'
                print(error_msg)
                writeError(error_msg)
            #print(f"{person.textNums} is getting a text")
            #print(person)
        
        for num in person.callNums:
            try:
                personDetectedCall.call(num,person.name,str(person.last_seen.strftime("%A, %B %d, at %I:%M %p")).replace(' ','+'))
            except Exception as e:
                error_msg = f'Failed to make call.  Not going to make up'
                print(error_msg)
                writeError(error_msg)

        for action in person.special_actions:
            if action == 'lights':
                sucess = self.turnLights()
                if sucess == True:
                    self.logAction(person.name, action)

    def turnLights(self):
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

        try:
            response = get(url,headers=headers,verify=False)
        except Exception as e:
            error_msg = f'Failed to get light info. Going to continue {e}'
            print(error_msg)
            writeError(error_msg)
            return False
            
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
            try:
                response = post(url,headers=headers,json=service_data,verify=False)
            except Exception as e:
                print('Faile to change light 2')
                writeError(f'Failed to change light 2 {str(e)}')
                return False

            return True

        # Otherwise its between 
        # sql = "UPDATE homeAutomation SET State = 1 WHERE groupName = 'Living_Room'"
        # df.runSql(sql)

        url = "https://derekfranz.ddns.net:8542/api/services/light/turn_on"
        for each in devices_to_switch:
            service_data = {"entity_id":f'light.{each}'}
            try:
                response = post(url,headers=headers,json=service_data,verify=False)
            except Exception as e:
                error_msg = f'Failed to change living room lights {e}'
                print(error_msg)
                writeError(error_msg)
                return False
        return True

    def logAction(self,name, action):
        sql = f"INSERT INTO PersonActionLog (Person,Action) VALUES ('{name}', '{action}')"
        try:
            df.runSql(sql)
        except Exception as e:
            error_msg = f'Failed to log error {e}'
            print(error_msg)
            writeError(error_msg)    

    
    def writeError(self, e):
        print(f'Error occured at {datetime.datetime.now()} {str(e)}')
        f = open(ERROR_FILE,'a')
        f.write(f'Error occured at {datetime.datetime.now()} {str(e)}'+'\n')
        f.close()

def writeError(e):
        print(f'Error occured at {datetime.datetime.now()} {str(e)}')
        f = open(ERROR_FILE,'a')
        f.write(f'Error occured at {datetime.datetime.now()} {str(e)}'+'\n')
        f.close()

def main():
    # p = PresenceDetection()
    # p.findAllKnownPeople()
    # p.create_people_to_notice()
    # p.findPeopleHere()
    p = PresenceDetection()
    while True:
        try:
            #findAllKnownPeople()
            #createPeopleToNotice()
                p.make_up_errors()
                p.findAllKnownPeople()
                p.create_people_to_notice()
                p.findPeopleHere()
                time.sleep(1)
        except Exception as e:
            time.sleep(1)
            print(f'Error in main {e}')
            writeError(f'error occured in main {e}')
            

if __name__ == '__main__':
    main()