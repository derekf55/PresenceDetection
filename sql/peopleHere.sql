SELECT knownpeople.Name, WifiInfo.hostname, WifiInfo.MacAddress, WifiInfo.last_seen FROM WifiInfo

left JOIN knownpeople ON
WifiInfo.MacAddress = knownpeople.macAdd
and WifiInfo.hostname = knownpeople.hostname

WHERE WifiInfo.last_seen > CURRENT_TIMESTAMP - INTERVAL 3 MINUTE
and WifiInfo.Relevant != 0