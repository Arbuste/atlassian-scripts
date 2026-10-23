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
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\output remove.csv'
entryPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\entryGiveBack.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Object","Category","Event","Detail","Additional detail"])
    
    with open(entryPath, 'w', newline='', encoding='utf-8') as output:
        woutput = csv.writer(output, delimiter=',',quotechar='"')
        woutput.writerow(["Project Key","Permission Scheme ID","Permission Scheme Name","Removed permissions"])
        
        def check(dict, key):
            res = False
            if key in dict:
                if dict[key]:
                    res = True
            return res

        def getDC(url,headers={}):
            headers['Authorization'] = f"Bearer {bearer_token}"
            return requests.get(DCBaseUrl + url, headers=headers).json()
        
        def putDC(url,body,headers={}):
            headers['Authorization'] = f"Bearer {bearer_token}"
            headers['Content-type'] = 'application/json'
            return requests.put(DCBaseUrl + url, headers=headers,json=body)
        
        projects = getDC('/rest/api/2/project')
        serviceProjects = [d for d in projects if d['projectTypeKey'] == 'service_desk']
        writer.writerow(['Project','Info','Service Desk Project List',str(serviceProjects)])
        doneSchemes = []
        for project in serviceProjects:
            scheme = getDC('/rest/api/2/project/' + project['id'] + '/permissionscheme')
            schemeId = scheme['id']
            schemeName = scheme['name']
            if not schemeId in doneSchemes:
                writer.writerow(['Permission Scheme','Info','Managing Permission Scheme','Scheme Id : ' + str(schemeId),'Project Key : ' + project['key']])
                permissions = getDC('/rest/api/2/permissionscheme/' + str(schemeId) + '/permission')['permissions']
                writer.writerow(['Permission Scheme','Info','Old Permissions','Scheme Id : ' + str(schemeId),json.dumps(permissions)])
                newPermissions = []
                for perm in permissions:
                    if not perm['permission'] in ['CREATE_ATTACHMENTS','CREATE_ISSUES','EDIT_ISSUES','TRANSITION_ISSUES','ADD_COMMENTS']:
                        if check(perm['holder'],'parameter'):
                            newPermissions.append({'holder': { "type": perm['holder']['type'], "parameter": perm['holder']['parameter'] }, 'permission': perm['permission']})
                        else:
                            newPermissions.append({'holder': { "type": perm['holder']['type'] }, 'permission': perm['permission']})
                writer.writerow(['Permission Scheme','Info','New Permissions','Scheme Id : ' + str(schemeId),json.dumps(newPermissions)])
                lostPermissions = [perm for perm in permissions if perm['permission'] in ['CREATE_ATTACHMENTS','CREATE_ISSUES','EDIT_ISSUES','TRANSITION_ISSUES','ADD_COMMENTS']]
                writer.writerow(['Permission Scheme','Info','Lost Permissions','Scheme Id : ' + str(schemeId),json.dumps(lostPermissions)])
                changeRequest = putDC('/rest/api/2/permissionscheme/' + str(schemeId),{"name": schemeName, "description": scheme['description'], "permissions": newPermissions})
                if changeRequest.status_code == 200:
                    writer.writerow(['Permission Scheme','Info','Permission Scheme Successfully Edited','Scheme Id : ' + str(schemeId)])
                    for perm in lostPermissions:
                        if check(perm['holder'],'parameter'):
                            woutput.writerow([project['key'],str(schemeId),schemeName,json.dumps({ "holder":{ "type": perm['holder']['type'], "parameter": perm['holder']['parameter'] },"permission": perm['permission']})])
                        else:
                            woutput.writerow([project['key'],str(schemeId),schemeName,json.dumps({'holder': { "type": perm['holder']['type'] }, 'permission': perm['permission']})])
                    doneSchemes.append(schemeId)
                else:
                    writer.writerow(['Permission Scheme','Error Code ' + str(changeRequest.status_code),'Permission Scheme Edition Failed','Scheme Id : ' + str(schemeId),json.dumps(changeRequest.json())])
            
                