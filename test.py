from twilio import rest
import personDetection
import derek_functions as df
import datetime

def test_add_one():
    personDetection.findAllKnownPeople()
    personDetection.createPeopleToNotice()

    # Set all people that are here to be back 10 minute
    sql = "UPDATE WifiInfo SET wifiInfo.last_seen = (wifiInfo.last_seen - INTERVAL 10 MINUTE) WHERE wifiInfo.last_seen > (CURRENT_TIMESTAMP - 1) "
    df.runSql(sql)

    personDetection.findPeopleHere()

    # I arrive
    sql = "UPDATE WifiInfo SET WifiInfo.last_seen = (CURRENT_TIMESTAMP) WHERE hostname ='Dereks-iPhone'"
    df.runSql(sql)
    
    sql = "SELECT Name FROM PeopleHere"
    name = df.runSql(sql)[0][0]
    if name == "Derek":
        return True
    else:
        return False
    


def test_no_one_home():
    pass



def test_light_flash():
    print('Make sure services are disabled')
    now = datetime.datetime.now()
    
    if now.hour >= personDetection.END_SWITCHING_LIGHT_HOUR and now.hour <= personDetection.START_SWITCHING_LIGHT_HOUR:
        return

    personDetection.findAllKnownPeople()
    personDetection.createPeopleToNotice()
    # Set myself to be gone
    sql = "UPDATE WifiInfo SET WifiInfo.last_seen = (CURRENT_TIMESTAMP - INTERVAL 10 MINUTE) WHERE hostname ='Dereks-iPhone'"
    df.runSql(sql)
    personDetection.findPeopleHere()

    # Check the time and turn off lights that will need to be switched
    light1_status = df.runSql("SELECT State FROM homeAutomation WHERE Appliance = 'Light_1'")
    light2_status = df.runSql("SELECT State FROM homeAutomation WHERE Appliance = 'Light_2'")
    light3_status = df.runSql("SELECT State FROM homeAutomation WHERE Appliance = 'Light_3'")

    # Turn off all lights
    df.runSql("UPDATE homeAutomation set State = 0 WHERE groupName = 'Living_Room'")

    # I have just arrived
    df.runSql("UPDATE WifiInfo SET WifiInfo.last_seen = (CURRENT_TIMESTAMP) WHERE hostname ='Dereks-iPhone'")
    personDetection.findPeopleHere()

    results = df.runSql("SELECT STATE FROM homeAutomation WHERE Appliance = 'Light_3'")
    # Return lights to previous state
    df.runSql(f"UPDATE homeAutomation set State = {light1_status} WHERE Appliance = 'Light_1")
    df.runSql(f"UPDATE homeAutomation set State = {light2_status} WHERE Appliance = 'Light_2")
    df.runSql(f"UPDATE homeAutomation set State = {light3_status} WHERE Appliance = 'Light_3")

    if results[0][0] == 1:
        print("Success")
        return True
    else:
        print("Failed")
        return False


def test_createPeopleToNoticeDatabase():
    personDetection.findAllKnownPeople()
    personDetection.createPeopleToNoticeDatabase()
    for person in personDetection.KNOWN_PEOPLE:
        print(person)


def test_beast_mode():
    personDetection.beastMode()

def test_home_alone():
    personDetection.findAllKnownPeople()
    personDetection.createPeopleToNoticeDatabase()
    for person in personDetection.KNOWN_PEOPLE:
        print(person)
    
def main():   
    count = 0
    #assert(test_light_flash)
    #test_createPeopleToNoticeDatabase()
    test_home_alone()
    #test_light_flash()
    #test_beast_mode()
    
main()

