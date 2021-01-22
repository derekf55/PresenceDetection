SELECT WifiInfo.MacAddress, hostname, macToName.Name 
FROM WifiInfo 
JOIN macToName on macToName.MacAddress = WifiInfo.MacAddress 
WHERE WifiInfo.Relevant != 0 
and macToName.isSet = 1