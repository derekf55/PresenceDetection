from opcode import hasconst
import os
import derek_functions as df
from _set_priority import set_priority_attributes
from Person import Person

def find_people_here(self):
    path = os.path.join('sql','peopleHere.sql')
    with open(path) as reader:
        sql = reader.read()

    people_found = []
    results = df.runSql(sql)
    
    
    for item in results:
        person_found = False
        name = item[0]
        hostname = item[1]
        mac = item[2]
        last_seen = item[3]
    
        for person in self.known_people:
            if person.name == name:
                person.last_seen = last_seen
                if hostname not in person.hosts and hostname != "None":
                    person.hosts.append(hostname)
                if mac not in person.macs:
                    person.macs.append(mac)
                if person not in people_found:
                    people_found.append(person)
                # If you find a person with a matching name, this is the person
                person_found = True
                break
            # If the name is unknown but we selected a name from the hostname
            elif hostname is not None and person.name == hostname:
                if mac not in person.macs:
                    person.macs.append(mac)
                person.last_seen = last_seen
                people_found.append(person)
                person_found = True
                break
            # Otherwise if the name is from the mac
            elif person.name == mac:
                person.last_seen = last_seen
                people_found.append(person)
                person_found = True
                break
        
        if person_found == False:
            # If they have a recagnized hostname then call it close enough 
            for person in self.known_people:
                if hostname != 'None' and hostname in person.hosts:
                    if person not in people_found:
                        people_found.append(person)
                    person_found = True
                    break

        """If we dont have a hostname or a name to guess from then we don't know
            who this is and we are just going to have to create a person with a name 
            that is their mac address
        """
        if person_found == False:
            if hostname != "None":
                new_person = Person(hostname)
                new_person.hosts.append(hostname)
            else:
                new_person = Person(mac)
            new_person.macs.append(mac)
            new_person.last_seen = last_seen
            self.known_people.append(new_person)
            set_priority_attributes(self)
            people_found.append(new_person)
        
    return people_found

