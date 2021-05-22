SELECT knownpeople.Name, WifiInfo.hostname, WifiInfo.MacAddress, WifiInfo.last_seen 
FROM `WifiInfo` 
LEFT JOIN knownpeople
on knownpeople.macAdd = WifiInfo.MacAddress
WHERE WifiInfo.last_seen > CURRENT_TIMESTAMP - INTERVAL 3 MINUTE 
AND WifiInfo.Relevant = 1