import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("open_groupe_sandbox_target")

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
logPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Teams à supprimer - output.csv'user = cloud_environment["username"]
token = cloud_environment["user_token"]
orgId = cloud_environment["org_id"]
baseUrl = cloud_environment["org_base_url"]

#Identifiants pour interroger l'instance Cloud
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Object","Category","Event","Detail","Additional detail"])
    
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

    #Teams
    teams = []
    cursor = 'X'
    pace = 300
    while cursor:
        if cursor != 'X':
            cloudTeamsReq = getCloud(baseUrl + '/public/teams/v1/org/' + orgId + '/teams?cursor=' + str(cursor) + '&size=' + str(pace))
        else:
            cloudTeamsReq = getCloud(baseUrl + '/public/teams/v1/org/' + orgId + '/teams?size=' + str(pace))
        if cloudTeamsReq['isReqSuccess']:
            teams = teams + cloudTeamsReq['entities']
            cursor = cloudTeamsReq['cursor']
        else:
            writer.writerow(["Teams","Error","Unable to fetch all teams",str(cloudTeamsReq)])
            sys.exit()
    
    #allTeams = copy.deepcopy(teams)
    
    #siteTeams = [team for team in teams if team['teamId'][:36] in cloudPrefixes]
        
    #writer.writerow(['Nb of teams initially:',str(len(allTeams))])
    #writer.writerow(['Nb of teams to delete:',str(len(siteTeams))])
    #writer.writerow(['Action','Team ID','Team Name'])
    
    #for team in [team for team in allTeams if team['teamId'] not in [team['teamId'] for team in siteTeams]]:
    #    writer.writerow(['Keep',str(team['teamId']),str(team['displayName']),str(team)])

    writer.writerow(['Team ID','Team name','Prefix'])
    dry_run = False
    if not dry_run:
        for team in teams: #siteTeams dans le cas initial ?
            writer.writerow([team['teamId'],team['displayName'],team['teamId'][:36]])
            
            resp = postCloud(baseUrl + '/public/teams/v1/org/' + orgId + '/teams/' + team['teamId'] + '/members',json={"first":40})
            if resp['isReqSuccess']:
                users=resp['results']
                for user in users:
                    displayNameReq = getCloud(baseUrl + '/rest/api/3/user?accountId=' + user['accountId'])
                    if displayNameReq['isReqSuccess']:
                        user['displayName'] = displayNameReq['displayName']
                    else:
                        writer.writerow(['User display name','Problem','Error while trying to fetch user\'s display name','Team: ' + str(team['teamId']) + ', User: ' + str(user),str(displayNameReq)])
                writer.writerow(['Team users','Info','Got users from team',str(team['teamId']), str(users)])
                
                respRemove = postCloud(baseUrl + '/public/teams/v1/org/' + orgId + '/teams/' + team['teamId'] + '/members/remove',json={"members":[{"accountId":user['accountId']} for user in users]})
                if respRemove['isReqSuccess']:
                    writer.writerow(['Users','Info','Users removed from team','Team: ' + str(team['teamId']) + ', Users: ' + str(users)])
                    time.sleep(0.5)
                    respDelete = deleteCloud(baseUrl + '/public/teams/v1/org/' + orgId + '/teams/' + team['teamId'])   
                    if respDelete['isReqSuccess']:
                        writer.writerow(['Team','Info','Team deleted','Team: ' + str(team['teamId'])])
                    else:
                        writer.writerow(['Team','Error','Team not deleted','Team: ' + str(team['teamId']),str(respDelete)])
                else:
                    writer.writerow(['Users','Error','Error while removing users','Team: ' + str(team['teamId'])])
                    continue
            else:
                writer.writerow(['Users','Error','Error while fetching users', 'Team: ' + str(team['teamId']),str(resp)])
            time.sleep(1)