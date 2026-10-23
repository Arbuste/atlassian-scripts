import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
dc_environment = get_environment("open_groupe_prod", "data_center")

import requests
import csvbaseUrl = dc_environment["confluence_base_url"]
token = dc_environment["confluence_pat"]
headers = {'Authorization':'Bearer ' + token}

accessGroups = ['confluence-administrators','g_confluence_clients','g_confluence_collaborateurs','o_confluence_clients','o_confluence_users']

def scroll(query):
    nextPage = query
    result = []
    while True:
        req = requests.get(baseUrl + nextPage,headers=headers)
        if req is not None:
            response = req.json()
            if 'results' in response:
                result.extend(response['results'])
            if '_links' in response:
                if 'next' in response['_links']:
                    nextPage = response['_links']['next']
                else:
                    break
            else:
                break
    return result

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Open\Users.csv', mode='w', newline='', encoding='utf-8') as outFile:
    writer = csv.writer(outFile, delimiter=',', quotechar='"')
    writer.writerow(['Username','Userkey','Display Name'])
    
    licensedUsers = []
    for accessGroup in accessGroups:
        licensedUsers.extend(scroll('/rest/api/group/' + accessGroup + '/member?expand=status'))
        print(str(len(licensedUsers)))
    
    print(str(len(licensedUsers)))
    licensedUsers = list({licensedUser['username']: licensedUser for licensedUser in licensedUsers if licensedUser['status'] == 'current' and licensedUser['username']}.values())
    print(len(licensedUsers))
    for user in licensedUsers:
        userReq = requests.get(baseUrl + '/rest/mobile/1.0/profile/' + user['username'],headers=headers)
        if userReq is not None:
            if userReq.status_code == 200:
                userResp = userReq.json()
                writer.writerow([user['username'],user['userKey'],userResp['email']])
            else:
                writer.writerow([user['username'],user['userKey'],str(userReq.status_code)])
