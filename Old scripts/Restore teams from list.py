import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys")

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
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Delete teams\output restore teams.csv'

entryPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Delete teams\Teams à réactiver.csv'

#Identifiants pour interroger l'instance Cloud
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(entryPath,'r',newline='',encoding='utf-8') as source:
    with open(logPath, 'w', newline='', encoding='utf-8') as log:
        teams = csv.DictReader(source,delimiter=',',quotechar='"')
        writer = csv.writer(log, delimiter=',',quotechar='"')
        writer.writerow(["Object","Category","Event","Detail","Additional detail"])
        
        def check(dict, key):
                res = False
                if key in dict:
                    if dict[key]:
                        res = True
                return res

        def getCloud(url,headers={}):
            req = requests.get(url, auth=basic, headers=headers)
            resp = {"reqStatusCode": req.status_code}
            if math.floor(req.status_code/100) == 2:
                resp['isReqSuccess'] = True
            else:
                resp['isReqSuccess'] = False
            if 'Content-Type' in req.headers:
                if 'application/json' in req.headers.get('Content-Type'):
                    resp |= req.json()
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
                    resp |= req.json()
            return resp
        
        def deleteCloud(url,headers={}):
            req = requests.delete(url, auth=basic, headers=headers)
            resp = {"reqStatusCode": req.status_code}
            if math.floor(req.status_code/100) == 2:
                resp['isReqSuccess'] = True
            else:
                resp['isReqSuccess'] = False
            if 'Content-Type' in req.headers:
                if 'application/json' in req.headers.get('Content-Type'):
                    resp |= req.json()
            return resp

        def check(dict, key):
            res = False
            if key in dict:
                if dict[key]:
                    res = True
            return res
        
        for team in teams:
            writer.writerow(['Team','Info','Starting restoration',team['ID']])
            
            resp = postCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/" + team['ID'] + '/restore')
            if resp['isReqSuccess']:
                
                writer.writerow(['Team','Info','Team restored','Team: ' + str(team['ID']),str(resp)])
            else:
                writer.writerow(['Users','Error','Error while restoring team', 'Team: ' + str(team['ID']),str(resp)])
            time.sleep(1)

