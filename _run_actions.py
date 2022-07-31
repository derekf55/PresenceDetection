from Person import Person
import derek_functions as df
import datetime
from personDetectedCall import call
from _special_actions import switch_lights

def run_actions(self, person: Person):
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

        now = datetime.datetime.now()
        if person.last_text_sent is None:
            person.last_text_sent = now
            person.num_notifications_sent_last_hour += 1
        elif person.last_text_sent + datetime.timedelta(hours=1) < now:
            # Been more than an hour since last text so reset
            person.last_text_sent = now
            person.num_notifications_sent_last_hour = 0
            person.num_notifications_sent_last_hour += 1

        if person.num_notifications_sent_last_hour >= 4:
            continue

        df.sendText(text, body)

    
    for tel_num in person.callNums:
        call(tel_num, person.name, str(person.last_seen.strftime("%A, %B %d, at %I:%M %p")).replace(' ','+'))

    
    for action in person.special_actions:
        if action == 'lights':
            switch_lights(self)
