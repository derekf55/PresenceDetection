from _find_people_here import find_people_here
from _find_known_people import find_known_people
from _set_priority import get_priority, set_priority_attributes, clear_attributes
from _update_db import insert_db, update_db, remove_db, clear_db
from _run_actions import run_actions
import time
from _home_assistant_functions import turn_off_light
import derek_functions as df


class PresenceDetection:
    def __init__(self) -> None:
        self.first_run = True
        self.known_people = find_known_people()
        clear_attributes(self)
        self.priority = get_priority(self)
        print(self.priority)
        set_priority_attributes(self)
        self.people_here = find_people_here(self)
        print(self.people_here)
        clear_db(self)
        for person in self.people_here:
            insert_db(self, person)
        #self.known_people[5].print_data()

    def main(self):
        try:
            current_priority = get_priority(self)
            if self.priority != current_priority:
                print(f'Setting priority to {current_priority} from {self.priority}')
                clear_attributes(self)
                self.priority = current_priority
                set_priority_attributes(self)
        except Exception as e:
            # If there is a problem gettting the priority then just continue
            print('Problem finding priority')
            pass
            
        try:
            people_found = find_people_here(self)
        except Exception as e:
            # If there is a problem finding the people here don't continue
            print('Problem finding people here')
            return

        for person in people_found:
            try:
                if person not in self.people_here:
                    print(f'{person} arrived')
                    run_actions(self, person)
                    person.return_light_states()
                    self.people_here.append(person)
                    insert_db(self, person)
                    sql = f"INSERT INTO `personStatus` (`Person`, `Status`, `Timestamp`) VALUES ('{person.name}', 'Arrived', current_timestamp());"
                    df.runSql(sql)
                else:
                    update_db(self, person)
            except Exception as e:
                # IF there is a problem with a persons arrival
                print(f"Problem with {person.name}'s arrival")
                print(e)
                return

                
        
        for person in self.people_here:
            try:
                if person not in people_found:
                    print(f'{person} left')
                    self.people_here.remove(person)
                    person.save_light_states()
                    for light in person.light_states.keys():
                        turn_off_light(light)
                    remove_db(self, person)
                    sql = f"INSERT INTO `personStatus` (`Person`, `Status`, `Timestamp`) VALUES ('{person.name}', 'Left', current_timestamp());"
                    df.runSql(sql)
                    if len(self.people_here) == 0:
                        print('Everyone left')
            except Exception as e:
                # IF there is a problem when someone leaves
                print(f"Problem with {person.name} leaving")
                print(e)
                return

                          


if __name__ == '__main__':
    p = PresenceDetection()
    while True:
        p.main()
        time.sleep(1)
