import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("open_groupe_sandbox")

import requests
import csv
import time

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Extract users post deactivation suspended\Deactivation etape 3c.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Extract users post deactivation suspended\Deactivation etape 3c - returns.csv', mode='w', newline='') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    #Header
    header = next(reader)
    header.append('Deactivate Response')
    writer.writerow(header)apiKey = cloud_environment["org_token"]
orgId = cloud_environment["org_id"]
baseUrl = cloud_environment["org_base_url"]
    
    for user in reader:
        print('Dealing with user ' + user[0])
        disableAccount = baseUrl + '/users/' + user[0] + '/manage/lifecycle/disable'
        reqDeactivate = requests.post(disableAccount,headers={ 'Authorization': 'Bearer ' + apiKey, 'Content-type': 'application/json' })
        if reqDeactivate.status_code != 204:
            print('DEACTIVATE NOT OK: ' + str(reqDeactivate.status_code) + ' - ' + str(reqDeactivate.json()))
            user.append(str(reqDeactivate.status_code) + ' - ' + str(reqDeactivate.json()))
        else:
            print('DEACTIVATE OK')
            user.append('204')
        
        writer.writerow(user)
        time.sleep(0.2)
