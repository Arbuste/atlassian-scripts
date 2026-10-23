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

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Open\Users Confluence sans email.csv', mode='r', newline='') as inFile, \
     open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Open\Users Confluence ajout Email.csv', mode='w', newline='', encoding='utf-8') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')
    writer.writerow(['Username','Email address'])
    
    next(reader)
    for user in reader:
        print(str(user[0]))
        userReq = requests.get(baseUrl + '/rest/mobile/1.0/profile/' + user[0],headers=headers)
        if userReq is not None:
            print(str(userReq))
            userResp = userReq.json()
            writer.writerow([userResp['userName'],userResp['email']])

