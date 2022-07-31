import derek_functions as df
from Person import Person

def insert_db(self, person: Person):
    #df.SQL_DEGBUG_MODE = True
    resident = 0
    if person.Resident == True:
        resident = 1
    try:
        hosts = person.hosts[0]
    except Exception as e:
        hosts = None

    try:
        sql = f"""
            INSERT INTO PeopleHere (Name, hostname, MacAddress, Resident)
            VALUES ('{person.name}','{hosts}','{person.macs[0]}','{resident}')
            """
    except Exception as e:
        print(e)
        #print(sql)
    df.runSql(sql)
        #print(x)


def update_db(self, person: Person):
    sql = f"UPDATE PeopleHere SET Last_Updated = CURRENT_TIMESTAMP WHERE Name = '{person.name}'"
    df.runSql(sql)

def remove_db(self, person: Person):
    sql = f"DELETE FROM PeopleHere WHERE Name = '{person.name}'"
    df.runSql(sql)

def clear_db(self):
    sql = "DELETE FROM PeopleHere"
    df.runSql(sql)