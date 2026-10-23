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
logPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Teams à supprimer - output.csv'

#Identifiants pour interroger l'instance Cloud
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Object","Category","Event","Detail","Additional detail"])

    def getCloud(url):
        req = requests.get(url,auth=basic)
        return req.json()
    
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
    
    #Set Sites environment variables
    env = []
    for url in cloudBaseUrls:
        env.append({"baseUrl": url, "cloudId": getCloud(url + '/_edge/tenant_info')['cloudId'] })
        
    #Teams
    teams = []
    cursor = 'X'
    pace = 300
    while cursor:
        if cursor != 'X':
            cloudTeamsReq = getCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/?cursor=" + str(cursor) + '&size=' + str(pace))
        else:
            cloudTeamsReq = getCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/?size=" + str(pace))
        if cloudTeamsReq['isReqSuccess']:
            teams = teams + cloudTeamsReq['entities']
            cursor = cloudTeamsReq['cursor']
        else:
            writer.writerow(["Teams","Error","Unable to fetch all teams",str(cloudTeamsReq)])
            sys.exit()
    
    saveTeams = copy.deepcopy(teams)
    
    for site in env:
        #Operations
        #Integrations
        integrations = getCloud(cloud_environment["org_base_url"] + "/jsm/ops/api/" + site['cloudId'] + '/v1/integrations')
        if integrations['isReqSuccess']:
           if check(integrations,'values'):
               integratedTeams = [inte['teamId'] for inte in integrations['values'] if 'teamId' in inte]
               teams = [team for team in teams if team['teamId'] not in integratedTeams]
        elif integrations['reqStatusCode'] != 404:
            writer.writerow(["Integrations","Error","Unable to fetch integrations",str(integrations)])
            sys.exit()
               
        #Alerts
        alerts = getCloud(cloud_environment["org_base_url"] + "/jsm/ops/api/" + site['cloudId'] + '/v1/alerts')
        if alerts:
           if check(alerts,'values'):
               alertedTeams = [responder['id'] for value in alerts['values'] if 'responders' in value for responder in value['responders'] if responder['type'] == 'team']
               if alertedTeams:
                   teams = [team for team in teams if team['teamId'] not in alertedTeams]
        else:
            writer.writerow(["Alerts","Error","Unable to fetch alerts",str(alerts)])
            sys.exit()
        
        #Schedule
        schedules = getCloud(cloud_environment["org_base_url"] + "/jsm/ops/api/" + site['cloudId'] + '/v1/schedules')
        if schedules:
           if check(schedules,'values'):
               scheduledTeams = [schedule['teamId'] for schedule in schedules['values'] if 'teamId' in schedule]
               teams = [team for team in teams if team['teamId'] not in scheduledTeams]
        else:
            writer.writerow(["Schedules","Error","Unable to fetch schedules",str(schedules)])
            sys.exit()
        
        #Syncs
        syncs = getCloud(cloud_environment["org_base_url"] + "/jsm/ops/api/" + site['cloudId'] + '/v1/syncs')
        if syncs:
           if check(syncs,'values'):
               syncedTeams = [sync['teamId'] for sync in syncs['values'] if 'teamId' in sync]
               teams = [team for team in teams if team['teamId'] not in syncedTeams]
        else:
            writer.writerow(["Syncs","Error","Unable to fetch syncs",str(syncs)])
            sys.exit()
             
        #Goals & Projects : pas d'API mais j'ai vérifié y'a rien
        
        #Policies
        
        #Issues
        teamList = []
        issueReq = getCloud(site['baseUrl'] + '/rest/api/2/search?jql=Team%20is%20not%20null&maxResults=100')
        if issueReq['isReqSuccess']:
            while check(issueReq,'issues'):
                issueTeams = [issue['fields']['customfield_10001']['id'] for issue in issueReq['issues'] if 'fields' in issue and 'customfield_10001' in issue['fields'] and 'id' in issue['fields']['customfield_10001'] and issue['fields']['customfield_10001']['id'] not in teamList]
                newTeamList = teamList + issueTeams
                if (newTeamList == teamList):
                    break
                else:
                    teamList = newTeamList
                issueReq = getCloud(site['baseUrl'] + '/rest/api/2/search?jql=Team%20is%20not%20null%20and%20Team%20not%20in%20('+','.join(teamList)+')%20&maxResults=100')
                if not issueReq['isReqSuccess']:
                    writer.writerow(["Issues","Error","Unable to fetch issues",str(issueReq)])
                    sys.exit()
        else:
            writer.writerow(["Issues","Error","Unable to fetch issues",str(issueReq)])
            sys.exit()
        
        teams = [team for team in teams if team['teamId'] not in teamList]
    
    writer.writerow(['Nb of teams initially:',str(len(saveTeams))])
    writer.writerow(['Nb of teams to delete:',str(len(teams))])
    writer.writerow(['Action','Team ID','Team Name'])
    
    for team in [team for team in saveTeams if team['teamId'] not in [team['teamId'] for team in teams]]:
        writer.writerow(['Keep',str(team['teamId']),str(team['displayName'])])
    
    writer.writerow(['Team ID','Team name','List of users'])
    for team in teams:
#         resp = deleteCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/" + team['teamId'])
        resp = postCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/" + team['teamId'] + '/members',json={"first":40})
        if resp['isReqSuccess']:
            users=resp['results']
#             while resp['pageInfo']['hasNextPage']:
#                 resp = postCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/" + team['teamId'] + '/members',json={"first":40,"after":resp['pageInfo']['endCursor']})
#                 if resp['isReqSuccess']:
#                     users += resp['results']
#                 else:
#                     users +=

            for user in users:
                displayNameReq = getCloud(cloud_environment["jira_base_url"] + "/rest/api/3/user?accountId=" + user['accountId'])
                if displayNameReq['isReqSuccess']:
                    user['displayName'] = displayNameReq['displayName']
                else:
                    writer.writerow(['User display name','Problem','Error while trying to fetch user\'s display name','Team: ' + str(team['teamId']) + ' ' + str(team['displayName']) + ', User: ' + str(user),str(displayNameReq)])
            writer.writerow([str(team['teamId']),str(team['displayName']), str(users)])
            
#             respRemove = postCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/" + team['teamId'] + '/members/remove',json={"members":users})
#             if respRemove['isReqSuccess']:
#                 time.sleep(0.5)
#                 respDelete = deleteCloud(cloud_environment["jira_base_url"] + "/gateway/api/public/teams/v1/org/" + cloud_environment["org_id"] + "/teams/" + team['teamId'])   
#                 if respDelete['isReqSuccess']:
#                     writer.writerow(['Delete','Success','Team deleted','Team: ' + str(team['teamId']) + ' ' + str(team['displayName'])])
#                 else:
#                     writer.writerow(['Delete','Error','Team not deleted','Team: ' + str(team['teamId']) + ' ' + str(team['displayName']),str(respDelete)])
#             else:
#                 writer.writerow(['Users','Error','Error while removing users','Team: ' + str(team['teamId']) + ' ' + str(team['displayName'])])
#                 continue
        else:
            writer.writerow(['Users','Error','Error while trying to fetch users', 'Team: ' + str(team['teamId']) + ' ' + str(team['displayName']),str(resp)])
        time.sleep(1)