import os
import derek_functions as df

from Person import Person

def find_known_people():
    path = os.path.join('sql','knownPeople.sql')
    with open(path) as reader:
        sql = reader.read()

    try:
        results = df.runSql(sql)
    except Exception as e:
        print('error getting knownpeople results' )

    known_people = []
    known_names = []

    for item in results:
        mac = item[0]
        host = item[1]
        name = item[2]
        residence_status = item[3]
        if residence_status == 1:
            residence_status = True
        else:
            residence_status = False

        # Checks if the person already exists
        try:
            existing_index = known_names.index(name)
            person = known_people[existing_index]
            person.macs.append(mac)
            if host is not None:
                person.hosts.append(host)
        except ValueError:
            new_person = Person(name)
            new_person.macs.append(mac)
            if host is not None:
                new_person.hosts.append(host)
            new_person.Resident = residence_status
            known_names.append(name)
            known_people.append(new_person)


    return known_people
