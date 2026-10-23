import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys_sandbox_migration_07")

import json
import requests
import csv
import time
import re
import copy
import math
import sys
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Boards\Boards without location.csv'

#URL de l'instance DCcloudBaseUrl = cloud_environment["jira_base_url"]
#Identifiants pour interroger l'instance Cloud
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    
    def getCloud(url,headers={}):
        req = requests.get(url, auth=basic, headers=headers)
        resp = {"reqStatusCode": req.status_code}
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        else:
            resp['isReqSuccess'] = False
        if 'Content-Type' in req.headers:
            if 'application/json' in req.headers.get('Content-Type'):
                if isinstance(req.json(),dict):
                    resp |= req.json()
                elif isinstance(req.json(),list):
                    resp["values"] = req.json()        
        return resp

    def postCloud(url,headers={},json=None):
        headers['Content-Type'] = 'application/json'
        req = requests.post(url, auth=basic, headers=headers, json=json)
        resp = {"reqStatusCode": req.status_code}
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        else:
            resp['isReqSuccess'] = False
        if 'Content-Type' in req.headers:
            if 'application/json' in req.headers.get('Content-Type'):
                if isinstance(req.json(),dict):
                    resp |= req.json()
                elif isinstance(req.json(),list):
                    resp["values"] = req.json()   
        return resp

    def putCloud(url,headers={},json=None):
        headers['Content-Type'] = 'application/json'
        req = requests.put(url, auth=basic, headers=headers, json=json)
        resp = {"reqStatusCode": req.status_code}
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        else:
            resp['isReqSuccess'] = False
        if 'Content-Type' in req.headers:
            if 'application/json' in req.headers.get('Content-Type'):
                if isinstance(req.json(),dict):
                    resp |= req.json()
                elif isinstance(req.json(),list):
                    resp["values"] = req.json()   
        return resp

    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res

    startAt = 0
    maxResults = 50
    isLast = False
    boards = []
    while isLast == False:
        boardsReq = getCloud(cloudBaseUrl + '/rest/agile/1.0/board?expand=admins&startAt=' + str(startAt) + '&maxResults=' + str(maxResults))
        if boardsReq['isReqSuccess']:
            boards += boardsReq['values']
            startAt += maxResults
            isLast = boardsReq['isLast']
        else:
            writer.writerow(['Error while getting all boards',str(boardsReq)])
            exit()
    
    writer.writerow(["Board ID","Board Name","Board Type","Admins"])
    for board in boards:
        if not 'location' in board:
            writer.writerow([str(board['id']),board['name'],board['type'],str(board['admins'])])