SELECT macToName.Name, WifiInfo.last_seen 
FROM `WifiInfo` 
JOIN macToName ON macToName.MacAddress = WifiInfo.MacAddress 
WHERE WifiInfo.last_seen > CURRENT_TIMESTAMP - INTERVAL 3 MINUTE 
AND WifiInfo.Relevant = 1
GROUP by Name
HAVING MAX(WifiInfo.last_seen)
