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

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Différentiel comptes 20241209\Users a reactiver.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Différentiel comptes 20241209\Users a reactiver - returns.csv', mode='w', newline='') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    #Header
    header = next(reader)
    header.append('API Response')
    writer.writerow(header)apiKey = cloud_environment["org_token"]
baseUrl = cloud_environment["org_base_url"]

    for user in reader:
        print('Dealing with user ' + user[0])
        print(baseUrl + '/users/' + user[0] + '/manage/lifecycle/enable')
        req = requests.post(baseUrl + '/users/' + user[0] + '/manage/lifecycle/enable',headers={ 'Authorization': 'Bearer ' + apiKey })
        if req.status_code != 204:
            user.append(str(req.status_code) + ' - ' + str(req.json()))
        else:
            user.append('204')
        writer.writerow(user)
        time.sleep(0.2)
