from unittest import result
import derek_functions as df

HOME_ALONE_NUM = "+17153471797"

def get_priority(self):
    sql = "SELECT PriorityLevel FROM `personDetectionPriority` WHERE ID = 1"
    result = df.runSql(sql)[0][0]
    return result

def clear_attributes(self):
    for person in self.known_people:
        person.textNums = []
        person.callNums = []
        person.special_actions = []
        person.notify_desk_phone = False
        person.active = False
        person.emails = []
        person.speak_to_google = []

def set_priority_attributes(self):
    priority = self.priority

    if priority == "Home Alone":
        for person in self.known_people:
            if person.name == 'Derek':
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


    sql = f"""SELECT Name, email, textNum, callNum, specialAction FROM peopleToNotice 
        WHERE active = 1 and PriorityLevel = '{priority}'"""

    try:
        results = df.runSql(sql)
    except Exception as e:
        print('Failed to set the priorities')

    for entry in results:
        name = entry[0]
        email = entry[1]
        text = entry[2]
        call = entry[3]
        action = entry[4]

        for person in self.known_people:
            if person.name == name:
                if email not in person.emails and email is not None:
                    person.emails.append(email)
                if text not in person.textNums and text is not None:
                    person.textNums.append(text)
                if call not in person.callNums and call is not None:
                    person.callNums.append(call)
                if action not in person.special_actions and action is not None:
                    person.special_actions.append(action)

                person.active = True
    
    if priority == "Disabled":
        for person in self.known_people:
            person.active = False
    elif priority == "Party":
        for person in self.known_people:
            if 'lights' in person.special_actions:
                person.special_actions.remove('lights')
            person.notify_desk_phone = False
            person.callNums = []
    

    