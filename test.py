from os import name
import unittest
from personDetection import PresenceDetection
from Person import Person

class TestPresenceDetection(unittest.TestCase):

    def test_derek_arrival(self):
        p = PresenceDetection()
        derek = Person('Derek')
        p.findPeopleHere()
        p.people_here.remove(derek)
        
        


if __name__ == '__main__':
    unittest.main()