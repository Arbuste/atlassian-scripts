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

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Extract users post deactivation suspended\comptes a migrer.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Extract users post deactivation suspended\comptes a migrer - returns.csv', mode='w', newline='') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    #Header
    header = next(reader)
    header.append('New email')
    header.append('Change Email Old Response')
    header.append('Change Email Real Response')
    header.append('Deactivate Response')
    writer.writerow(header)apiKey = cloud_environment["org_token"]
orgId = cloud_environment["org_id"]
baseUrl = cloud_environment["org_base_url"]

    cnt = 0

    for user in reader:
        print('Dealing with user ' + user[0])
        setEmailOld = baseUrl + '/users/' + user[0] + '/manage/email'
        setEmailReal = baseUrl + '/users/' + user[2] + '/manage/email'
        disableAccount = baseUrl + '/users/' + user[0] + '/manage/lifecycle/disable'
    
        newEmail = user[1][:user[1].find('@')] + '-old' + user[1][user[1].find('@'):]
        print(newEmail)
        user.append(newEmail)
        
        reqEmailOld = requests.put(setEmailOld,headers={ 'Authorization': 'Bearer ' + apiKey, 'Content-Type': 'application/json' },json={ 'email': newEmail })
        if reqEmailOld.status_code != 204:
            print('CHANGE EMAIL OLD NOT OK: ' + str(reqEmailOld.status_code) + ' - ' + str(reqEmailOld.json()))
            user.append(str(reqEmailOld.status_code) + ' - ' + str(reqEmailOld.json()))
        else:
            print('CHANGE EMAIL OLD OK')
            user.append('204')
            reqEmailReal = requests.put(setEmailReal,headers={ 'Authorization': 'Bearer ' + apiKey, 'Content-Type': 'application/json' },json={ 'email': user[1] })
            if reqEmailReal.status_code != 204:
                print('CHANGE EMAIL REAL NOT OK: ' + str(reqEmailReal.status_code) + ' - ' + str(reqEmailReal.json()))
                user.append(str(reqEmailReal.status_code) + ' - ' + str(reqEmailReal.json()))
            else:
                print('CHANGE EMAIL REAL OK')
                user.append('204')
                reqDeactivate = requests.post(disableAccount,headers={ 'Authorization': 'Bearer ' + apiKey, 'Content-type': 'application/json' })
                if reqDeactivate.status_code != 204:
                    print('DEACTIVATE NOT OK: ' + str(reqDeactivate.status_code) + ' - ' + str(reqDeactivate.json()))
                    user.append(str(reqDeactivate.status_code) + ' - ' + str(reqDeactivate.json()))
                else:
                    print('DEACTIVATE OK')
                    user.append('204')
        writer.writerow(user)
        cnt+=1
        if cnt % 100 == 0:
            print('Account n° ' + str(cnt) + ' done')
        time.sleep(0.2)
        

