# The purpose of this program is to run different actions based on who is detected
# Written by Derek Franz
# Started 12/24/20

import json, time, os
import datetime
import personDetectedCall
import derek_functions as df
from requests.api import post, get, request
from Person import Person
import threading
from utility_functions import writeError, turn_on_light, turn_off_light, get_amient_light_level
from utility_functions import get_state, get_lights_in_room, get_light_status

# A list of dicts with the name info about them
FIND_PEOPLE_SQL_PATH = os.path.join('sql','peopleHere.sql')

f = open(FIND_PEOPLE_SQL_PATH)
FIND_PEOPLE_SQL = f.read()
f.close()

ERROR_FILE = "error.log"

# 8am and 5pm 
END_SWITCHING_LIGHT_HOUR = 8
START_SWITCHING_LIGHT_HOUR = 16
HOME_ALONE_NUM = "+17153471797"


class PresenceDetection:
    def __init__(self,debug=False) -> None:
        self.first_run = True
        self.known_people = []
        self.current_priority = ""
        self.people_here = []
        self.newest_seen = None
        self.database_error = False
        self.lights_out = False
        self.light_level_threshold = 1.0
        df.SQL_DEGBUG_MODE = debug
        # The max number of texts that can be sent about one person within an hour
        self.max_texts_hour = 3

        # Contains all the sql that failed to run so it can try and be run again and catch the system up
        self.failed_sql = []
        

    def clear_atributes(self):
        for person in self.known_people:
            person.textNums = []
            person.callNums = []
            person.special_actions = []
            person.notify_desk_phone = False
            person.active = False
            person.emails = []

    def is_person_here(self,name):
        for person in self.people_here:
            if person.name == name:
                return True
        
        return False

    def create_people_to_notice(self):
        try:
            priority = df.runSql("SELECT PriorityLevel FROM personDetectionPriority WHERE ID = 1")[0][0]
        except Exception as e:
            print('Failed to get new priority going to try and conintue with old priorty')
            writeError(f'Unable to get new priority {str(e)}')
            return

        if priority != self.current_priority:
            print(f'Switching to {priority}')
            self.clear_atributes()
            

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

        if priority != 'Party' and priority != 'Disabled':
            for person in self.known_people:
                if person.Resident == True and 'lights' not in person.special_actions:
                    person.special_actions.append('lights')
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
            results = df.runSql(sql)
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
        self.failed_sql = set(list(self.failed_sql))
        for sql in self.failed_sql:
            try:
                df.runSql(sql)
                self.failed_sql.remove(sql)
            except Exception as e:
                continue

    # @return: Returns a list of Person objects that were created from db info
    def findPeopleHere(self):
        # Run sql that determines who is here right now
        people_found = []

        # Get access to database
        try:
            results = df.runSql(FIND_PEOPLE_SQL)
        except Exception as e:
            error_msg = f'Failed to get people from database.  Going to return and not try to make this up {e}'
            print(error_msg)
            writeError(error_msg)
            self.database_error = True
            return 

        # If there are no people at the house
        if len(results) == 0:
            print('No one found')
            return people_found

        # for each device that is returned as being currently at the house
        for item in results:
            name = item[0]
            hostname = item[1]
            mac = item[2]
            last_seen = item[3]
            currentPerson = Person()

            if self.newest_seen is not None and last_seen < self.newest_seen - datetime.timedelta(minutes=3):
                print('This is old enough to cause a problem')
                exit()

            if self.newest_seen == None or self.newest_seen < last_seen:
                self.newest_seen = last_seen
            
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
                        name = mac
                    except Exception as e:
                        writeError(f'From line 220 {e}')

            currentPerson.name = name
            # Go through the known peoples list to find dict of relivent person
            for person in self.known_people:
                if person.name == name:
                    #print(f'This is where we find {person.name} is {name}')
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

        return people_found


    def update_people_here(self,people_found):

        try:
            df.delete_old_voicemails()
        except Exception as e:
            writeError(f'There was a problem accessing freePBX {str(e)}')
        
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

        # If no one is home turn off all the lights in the house
        # In the short term we will only do this once in case of a bug that would keep the lights off
        # if len(people_found) == 0:
        #     lights = ['light1_livingroom','light2_livingroom','ergroomlight_ergroom']
        #         #df.sendText('+17153471797','Just turned off all the lights in the house')
        #     for light in lights:
        #         turn_off_light(light)

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
                    if person.name == 'Derek' and (self.current_priority != 'Disabled' and self.current_priority != 'Party'):
                        person.return_light_states() 
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
                    error_msg = f'Failed to remove person from people here table.  Going to continue and not try to make up this action {e}'
                    print(error_msg)
                    writeError(error_msg)
                    #self.failed_sql(sql)
                try:
                    sql = f"INSERT INTO personStatus (Person, Status) VALUES ('{person.name}','Left')"
                    df.runSql(sql)
                except Exception as e:
                    error_msg = f'Failed to log person leaving. Going to continue and try and update later'
                    print(error_msg)
                    writeError(error_msg)
                    self.failed_sql(sql)

                # If I've left turn off the lights in my room
                if person.name == 'Derek':
                    derek_room_lights = get_lights_in_room('dereksroom')
                    #print(derek_room_lights)
                    # Save the state of the lights before leaving then turn off
                    person.save_light_states()
                    for light in derek_room_lights:
                        turn_off_light(light)


                print(person.name+' left')
                try:
                    self.people_here.remove(person)
                    if len(self.people_here) == 0:
                        lights = ['light1_livingroom','light2_livingroom','ergroomlight_ergroom']
                        for light in lights:
                            turn_off_light(light)
                except Exception as e:
                    print('Failed to remove a person')
                    writeError(f'Failed to remove this person {e}')
                    exit()
        

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
        
        if person.active is False:
            print(f'{person.name}: {person.active}')
            return

        print('running actions here')

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
            
            now = datetime.datetime.now()
            if person.last_text_sent == None:
                print('No text sent yet going to send now')
                person.last_text_sent = now
                person.num_notifications_sent_last_hour += 1
            elif person.last_text_sent + datetime.timedelta(hours=1) < now:
                # older than an hour can send
                print('Older than an hour going to reset and send ')
                person.last_text_sent = now
                person.num_notifications_sent_last_hour = 0
                person.num_notifications_sent_last_hour += 1
            else:
                # Less than an hour sense last message 
                if person.num_notifications_sent_last_hour >= self.max_texts_hour:
                    print('Sent too many in the last hour')
                    break
                print('Less than an hour but within the range of max texts')
                person.num_notifications_sent_last_hour += 1
            
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

        print('spec action sec')

        for action in person.special_actions:
            print(f'actions here {person.special_actions}')
            if action == 'lights':
                sucess = self.switch_lights()
                if sucess == True:
                    self.logAction(person.name, action)


    def switch_lights(self,now=datetime.datetime.now(),light_level=None,tv_state=None):
        # Check if it's dark and if not return
        # If it is currently lighter than the darkness threshold do nothing
        print('running switch lights')
        if light_level == None:
            light_level = get_amient_light_level()

        
        # If it's light in the living room and the sun is out do nothing
        if (light_level > self.light_level_threshold or light_level == False) and df.isSunOut() == True:
            with open('/home/derek/PresenceDetection/light_log.txt','a') as writer:
                message = f'now:{now}-light_level:{light_level}-tv_state{tv_state}-turning on:Nothing\n'
                writer.write(message)
            return False
        # If it's light in the living room but the sun is down turn on the erg room light for the 5 minutes
        elif (light_level > self.light_level_threshold or light_level is False) and df.isSunOut() == False:
            turn_on_light('ergroomlight_ergroom')
            with open('/home/derek/PresenceDetection/light_log.txt','a') as writer:
                message = f'now:{now}-light_level:{light_level}-tv_state{tv_state}-turning on:ergroomlight_ergroom\n'
                writer.write(message)
            x = light_level == False
            print(f'About to return light level is {light_level} and sun is {df.isSunOut()} and x {x}')
            return True

        # If the sun is down make sure to turn on the erg room light

        print('made it here')

        # Check if all lights are off 
        lights_to_check = ['light1_livingroom','light2_livingroom']
        for light in lights_to_check:
            status = get_light_status(light)
            if status == 'on' or status == False:
                # Light is on or cant determine so do nothing
                return False
        
        # At this point both lights are determined to be off and it's dark
        # Check if TV is playing and if so only turn on erg room light
        entity_id = 'media_player.living_room_tv'
        if tv_state == None:
            tv_state = get_state(entity_id)
            print(f'The new tv state is {tv_state}')
        tv_on_states = ['unknown','playing']
        if tv_state in tv_on_states:
            lights = ['ergroomlight_ergroom']
            turn_on_light('ergroomlight_ergroom')
        else:
            lights = ['ergroomlight_ergroom','light2_livingroom','light1_livingroom']
            # If its not too late then turn on all lights otherwise just light 2
            
            # Don't turn on lights 1 between 9pm and 8 am if same is home
            if (now.hour >= 21 or now.hour < 8) and self.is_person_here('Sam') == False:
                lights.remove('light1_livingroom')
            for light in lights:
                turn_on_light(light)

        
        with open('/home/derek/PresenceDetection/light_log.txt','a') as writer:
            message = f'now:{now}-light_level:{light_level}-tv_state{tv_state}-turning on:{lights}\n'
            writer.write(message)

        return True
        

    def logAction(self,name, action):
        sql = f"INSERT INTO PersonActionLog (Person,Action) VALUES ('{name}', '{action}')"
        try:
            df.runSql(sql)
        except Exception as e:
            error_msg = f'Failed to log error {e}'
            print(error_msg)
            writeError(error_msg)
    


def main():
    # p = PresenceDetection()
    # p.findAllKnownPeople()
    # p.create_people_to_notice()
    # p.findPeopleHere()
    p = PresenceDetection()
    p.findAllKnownPeople()
    while True:
        # try:
            #findAllKnownPeople()
            #createPeopleToNotice()
        p.make_up_errors()
        p.create_people_to_notice()
        people = p.findPeopleHere()
        p.update_people_here(people)
        time.sleep(1)
        # except Exception as e:
        #     time.sleep(1)
        #     print(f'Error in main {e}')
        #     writeError(f'error occured in main {e}')
            

if __name__ == '__main__':
    main()