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
import time
import re
import copy
import math
import sys
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\output read only.csv'
entryPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\entryReadOnly.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]
with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Object","Category","Event","Detail","Additional detail"])
    
    with open(entryPath, 'w', newline='', encoding='utf-8') as output:
        woutput = csv.writer(output, delimiter=',',quotechar='"')
        woutput.writerow(["Project Key","Old Permission Scheme ID","New Permission Scheme Name"])

        def getDC(url,headers={}):
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.get(url, headers=headers)
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
        
        def postDC(url,headers={},json=None):
            headers['Content-Type'] = 'application/json'
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.post(url, headers=headers, json=json)
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
        
        def putDC(url,headers={},json=None):
            headers['Content-Type'] = 'application/json'
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.put(url, headers=headers, json=json)
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
        
        projects = getDC(DCBaseUrl + '/rest/api/2/project')
        if projects['isReqSuccess']:
            
            #Mapping Projects <-> Permissions schemes
            projectPSMapping = []
            for project in projects['values']:
                projectPS = getDC(DCBaseUrl + '/rest/api/2/project/' + project['key'] + '/permissionscheme')
                if projectPS['isReqSuccess']:
                    projectPSMapping.append({"projectKey":project['key'],"psId":str(projectPS['id'])})
                else:
                    writer.writerow(['Project','Error','Unable to fetch permission scheme',str(project),str(projectPS)])
                    exit()

            permissionSchemesReq = getDC(DCBaseUrl + '/rest/api/2/permissionscheme?expand=permissions')
            if permissionSchemesReq['isReqSuccess']:
                #Get only Permission Schemes that are not already read-only
                permissionSchemes = [permissionScheme for permissionScheme in permissionSchemesReq['permissionSchemes'] if not permissionScheme['name'].endswith(' (read-only)')]
                for ps in permissionSchemes:
                    if str(ps['id']) in [mapping['psId'] for mapping in projectPSMapping]: #If the permission scheme is mapped to a project
                        copy = {}
                        
                        #Checks if a read-only version of the permission scheme already exists
                        copyTest = [permissionscheme['id'] for permissionscheme in permissionSchemes if permissionscheme['name'] == ps['name']+ ' (read-only)']
                        if copyTest:
                            copy['isReqSuccess'] = True
                            copy['id'] = copyTest[0]
                        else:
                            #Creates the read-only version of the permission scheme
                            newPermissions = []
                            for perm in ps['permissions']:
                                if perm['permission'] == 'BROWSE_PROJECTS':
                                    if check(perm['holder'],'parameter'):
                                        if perm['holder']['parameter'] != 'zabbix':
                                            newPermissions.append({'holder': { "type": perm['holder']['type'], "parameter": perm['holder']['parameter'] }, 'permission': perm['permission']})
                                    else:
                                        newPermissions.append({'holder': { "type": perm['holder']['type'] }, 'permission': perm['permission']})
                                elif not perm['permission'] in ['CREATE_SLACK_CHANNEL','VIEW_SLACK_TAB','com.k15t.backbone.permission.syncpanelinfo','PRIVATE_CHANNEL']:
                                    newPermissions.append({'holder': {'type':'group','parameter':'peaksys-system-administrators'},'permission':perm['permission']})
                            if 'description' in ps:
                                copy = postDC(DCBaseUrl + '/rest/api/2/permissionscheme',json={"name":ps['name'] + " (read-only)","description":ps['description'],"permissions":newPermissions})
                            else:
                                copy = postDC(DCBaseUrl + '/rest/api/2/permissionscheme',json={"name":ps['name'] + " (read-only)","permissions":newPermissions})
                        if copy['isReqSuccess']:
                            for projectKey in [mapping['projectKey'] for mapping in projectPSMapping if mapping['psId'] == str(ps['id'])]:
                                assign = putDC(DCBaseUrl + '/rest/api/2/project/' + projectKey +'/permissionscheme',json={'id': copy['id']})
                                if assign['isReqSuccess']:
                                    woutput.writerow([projectKey,str(ps['id']),str(copy['id'])])
                                    writer.writerow(['Project','Info','Assignation of read-only copy succeeded',projectKey,str(copy['id'])])
                                else:
                                    writer.writerow(['Project','Error','Assignation of read-only copy failed',projectKey,str(assign)])
                        else:
                            writer.writerow(['Permission Scheme','Error','Creation of read-only copy failed',str(ps['id']) + ' ' + str(ps['name']),str(copy)])
                    else:
                        writer.writerow(['Permission Scheme','Info','Permission scheme not mapped to project',str(ps['id']) + ps['name']])
            else:
                writer.writerow(['Permission Schemes','Error','Unable to fetch permission schemes',str(permissionSchemes)])
        else:
            writer.writerow(['Projects','Error','Unable to fetch projects',str(projects)])