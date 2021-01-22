SELECT macToName.Name, WifiInfo.hostname, WifiInfo.MacAddress, WifiInfo.last_seen 
FROM `WifiInfo` 
LEFT JOIN macToName
on macToName.MacAddress = WifiInfo.MacAddress
WHERE WifiInfo.last_seen > CURRENT_TIMESTAMP - INTERVAL 3 MINUTE 
AND WifiInfo.Relevant = 1