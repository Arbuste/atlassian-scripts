import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("open_groupe_sandbox")

import requests
from requests.auth import HTTPBasicAuthbaseUrl = cloud_environment["org_base_url"]
orgId = cloud_environment["org_id"]
login = cloud_environment["username"]
password = cloud_environment["user_token"]
cursor1 = ''
cursor2 = ''


while True:
    teams1Req = requests.get(baseUrl + '/public/teams/v1/org/'+ orgId +'/teams' + cursor,auth=HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"]), params={
                'cursor': cursor1
                })

    assert teams1Req.status_code == 200
    teams1 = teams1Req.json()
    
    for team1 in teams1:
        while True:
            teams2Req = requests.get(baseUrl + '/public/teams/v1/org/'+ orgId +'/teams' + cursor,auth=HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"]), params={
                    'cursor': cursor2
                    })

            assert teams2Req.status_code == 200
            teams2 = teams2Req.json()
            
            for team2 in teams2:
                if team2['displayName'] == team1['displayName'] && team2['teamId'] != team1['teamId']:
                    console.log(team2['displayName'] + ' ' + team1['displayName'] + ' ' + team2['teamId'] + ' ' + team1['teamId'])
                    cursor2 = null
                    break
        
        if teams2.cursor != null:
            cursor2 = teams2.cursor
        else
            break
    if teams1.cursor != null:
        cursor1 = teams1.cursor
    else
        break
            
