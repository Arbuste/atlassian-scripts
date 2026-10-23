import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
dc_environment = get_environment("cdiscount", "data_center")

import json
import requests
import csv
import math
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Boards\output.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    
    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res

    def getDC(url,headers={}):
        headers['Authorization'] = f"Bearer {bearer_token}"
        req = requests.get(DCBaseUrl + url, headers=headers)
        resp = {"reqStatusCode": req.status_code}
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        else:
            resp['isReqSuccess'] = False
        if 'application/json' in req.headers.get('Content-Type'):
            resp |= req.json()
        return resp
            
    boards = []
    startAt = 0
    pace = 50
    isLast = False
    while isLast == False:
        newBoards = getDC('/rest/agile/1.0/board?startAt=' + str(startAt) + '&maxResults=' + str(pace))
        if newBoards['isReqSuccess']:
            boards += newBoards['values']
            startAt += pace
            isLast = newBoards['isLast']
        else:
            writer.writerow(['Error while getting Boards','',str(newBoards['reqStatusCode']),json.dumps(newBoards)])

    pbBoards = []
    for board in boards:
        projects = getDC('/rest/agile/1.0/board/' + str(board['id']) + '/project')
        if projects['isReqSuccess']:
            if projects['total'] == 1:
                if projects['values'][0]['projectTypeKey'] == 'service_desk':
                    pbBoards.append(board)
                        
        else:
            writer.writerow(['Error while getting Projects',str(board['id']),str(projects['reqStatusCode']),json.dumps(projects)])
    
    writer.writerow(['Board ID','Nom du board','Lien vers le board'])
    for board in pbBoards:
        writer.writerow([board['id'],board['name'],dc_environment["jira_base_url"] + "/secure/RapidBoard.jspa?rapidView=" + str(board['id'])])       