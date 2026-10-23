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

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Différentiel comptes 20241209\Comptes a desuspendre.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Différentiel comptes 20241209\Comptes a desuspendre - returns.csv', mode='w', newline='') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    #Header
    header = next(reader)
    header.append('Deactivate response')
    header.append('Restore respone')
    writer.writerow(header)apiKey = cloud_environment["org_token"]
orgId = cloud_environment["org_id"]
baseUrl = cloud_environment["org_base_url"]

    cnt = 0

    for user in reader:
        print('Dealing with user ' + user[0])
        restoreUrl = baseUrl + '/admin/v1/orgs/' + orgId + '/directory/users/' + user[0] + '/restore-access'
        deactivateUrl = baseUrl + '/users/' + user[0] + '/manage/lifecycle/disable'
        
        reqDeactivate = requests.post(deactivateUrl,headers={ 'Authorization': 'Bearer ' + apiKey, 'Content-type': 'application/json' })
        if reqDeactivate.status_code != 204:
            print('DEACTIVATE NOT OK: ' + str(reqDeactivate.status_code) + ' - ' + str(reqDeactivate.json()))
            user.append(str(reqDeactivate.status_code) + ' - ' + str(reqDeactivate.json()))
        else:
            print('DEACTIVATE OK')
            user.append('204')
            reqRestore = requests.post(restoreUrl,headers={ 'Authorization': 'Bearer ' + apiKey })
            if reqRestore.status_code != 200:
                print('RESTORE NOT OK: ' + str(reqRestore.status_code) + ' - ' + str(reqRestore.json()))
                user.append(str(reqRestore.status_code) + ' - ' + str(reqRestore.json()))
            else:
                print('RESTORE OK')
                user.append('200')

        writer.writerow(user)
        cnt+=1
        if cnt % 100 == 0:
            print('Account n° ' + str(cnt) + ' done')
        time.sleep(0.2)
