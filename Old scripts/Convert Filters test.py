import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys_sandbox_migration_11")
dc_environment = get_environment("cdiscount", "data_center")

import json
import requests
import csv
import re
import copy
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Convert Filters\output.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]
#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]

#URL de l'instance Cloud ciblecloudBaseUrl = cloud_environment["jira_base_url"]
#Identifiants pour interroger l'instance Cloud
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Object","Category","Event","Detail","Additional detail"])
        
    def getDC(url,headers={}):
        headers['Authorization'] = f"Bearer {bearer_token}"
        return requests.get(DCBaseUrl + url, headers=headers).json()

    def getCloud(url):
        return requests.get(cloudBaseUrl + url,auth=basic).json()

    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res

    def generateId(id):
        return str(id) + '1'
    
    #Chargement des éléments
    #Fields
    dcFields = getDC('/rest/api/2/field')
    cloudFields = getCloud('/rest/api/2/field')
    
    #Teams
    dcTeams = []
    cloudTeams = []
    startAt = 1
    pace = 100
    size = pace
    while size == pace:
        dcTeamsReq = getDC('/rest/teams-api/1.0/team?page=' + str(startAt) + '&size=' + str(pace))
        if dcTeamsReq:
            dcTeams = dcTeams + dcTeamsReq
            startAt = startAt + 1
            size = len(dcTeamsReq)
        else:
            break
    cursor = 'X'
    pace = 300
    while cursor:
        if cursor != 'X':
            cloudTeamsReq = getCloud('/gateway/api/public/teams/v1/org/a631b804-8d8b-1233-68c2-c604c1264165/teams?cursor=' + str(cursor) + '&size=' + str(pace))
        else:
            cloudTeamsReq = getCloud('/gateway/api/public/teams/v1/org/a631b804-8d8b-1233-68c2-c604c1264165/teams?size=' + str(pace))
        if cloudTeamsReq:
            cloudTeams = cloudTeams + cloudTeamsReq['entities']
            cursor = cloudTeamsReq['cursor']
        else:
            break
    
    #Object types & assets
        
    workspaceId = getCloud('/rest/servicedeskapi/assets/workspace')['values'][0]['workspaceId']

    #Assets 
    dcAssets = []
    page = 1
    pace = 10000
    cnt = 0
    limit = pace
    while cnt < limit:
        dcAssetsReq = getDC('/rest/assets/1.0/aql/objects?includeAttributes=false&page=' + str(page) + '&resultPerPage=' + str(pace))
        if dcAssetsReq:
            dcAssets = dcAssets + dcAssetsReq['objectEntries']
            page = page + 1
            cnt = dcAssetsReq['toIndex']
            limit = dcAssetsReq['totalFilterCount']
        else:
            break
            
    cloudAssets = []
    startAt = 1
    pace = 10000
    isLast = False
    while not isLast:
        cloudAssetsReq = requests.post(cloud_environment["org_base_url"] + "/jsm/assets/workspace/" + workspaceId + '/v1/object/aql?includeAttributes=false&startAt=' + str(startAt) + '&maxResults=' + str(pace),json={"qlQuery":""},auth=basic).json()
        if cloudAssetsReq:
            cloudAssets = cloudAssets + cloudAssetsReq['values']
            startAt = startAt + pace
            isLast = cloudAssetsReq['isLast']
        else:
            break
    
    #Asset fields on DC
    dcAssetFieldsReq = getDC('/rest/api/2/customFields?types=com.riadalabs.jira.plugins.insight:rlabs-customfield-default-object&types=com.riadalabs.jira.plugins.insight:rlabs-customfield-object-reference&types=com.riadalabs.jira.plugins.insight:rlabs-customfield-object-reference-multi&types=com.riadalabs.jira.plugins.insight:rlabs-customfield-object-readonly')['values']
    dcAssetFields = []
    dcAssetClauses = []

    for assetField in dcAssetFieldsReq:
        improvedFields = list(filter(lambda field: field['id'] == assetField['id'], dcFields))
        if improvedFields:
            improvedField = improvedFields[0]
            if check(improvedField,'clauseNames'):
                dcAssetClauses = dcAssetClauses + improvedField['clauseNames']
            else:
                dcAssetClauses.append(improvedField['name'])
            dcAssetFields.append(improvedField['id'])
            dcAssetFields.append(improvedField['name'])
        else:
            writer.writerow(['Asset Fields','Error','Couldn\'t find the field ID in DC',assetField['id']])

#     #Boards
#     dcBoards = []
#     cloudBoards = []
#     isLast = False
#     startAt = 0
#     pace = 50
#     while isLast == False:
#         dcBoardsReq = getDC('/rest/agile/1.0/board?startAt='+str(startAt)+'&maxResults='+str(pace))
#         if dcBoardsReq:
#             dcBoards = dcBoards + dcBoardsReq['values']
#             startAt = startAt + pace
#             isLast = dcBoardsReq['isLast']
#         else:
#             break
#     isLast = False
#     startAt = 0
#     pace = 50
#     while isLast == False:
#         cloudBoardsReq = getCloud('/rest/agile/1.0/board?includePrivate=true&startAt='+str(startAt)+'&maxResults='+str(pace))
#         if cloudBoardsReq:
#             cloudBoards = cloudBoards + cloudBoardsReq['values']
#             startAt = startAt + pace
#             isLast = cloudBoardsReq['isLast']
#         else:
#             break

    currentRule = ''
    currentComponent = ''

    def mapFieldFromId(id):
        if id in ['initiator','parent']:
            return id
        dcFieldsReq = list(filter(lambda field: field['id'] == id, dcFields))
        if dcFieldsReq:
            dcField = dcFieldsReq[0]
            if dcField['id'] in ['components','fixVersions','duedate','description','summary','resolution','status']:
                return dcField['id']
            elif dcField['id'] == 'customfield_10002':
                dcField['name'] = 'Request Type'
            elif dcField['id'] == 'customfield_11200':
                dcField['name'] = 'Story points'
            elif dcField['id'] == 'customfield_14300':
                dcField['name'] = 'Flagged'
            cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'], cloudFields))
            if cloudFieldsReq:
                if len(cloudFieldsReq) > 1:
                    writer.writerow(['Field','Problem','More than one match in Cloud',str(id)])
                return cloudFieldsReq[0]['id']
            else:
                writer.writerow(['Field','Info','No direct match in Cloud, checking the clauses...',str(id)])
                for clauseName in dcField['clauseNames']:
                    cloudFieldsReq = list(filter(lambda field: field['name'] == clauseName, cloudFields)) 
                    if cloudFieldsReq:
                        if len(cloudFieldsReq) > 1:
                            writer.writerow(['Field','Problem','More than one match in Cloud',str(id)])
                        return cloudFieldsReq[0]['id']
                writer.writerow(['Field','Error','No match in Cloud, even after clauses',str(id)])
                return id
        else:
            writer.writerow(['Field','Error','Field not found in DC',str(id)])
            return id

    def mapTeam(id):
        dcTeamsReq = list(filter(lambda team: team['id'] == int(id), dcTeams))
        if dcTeamsReq:
            dcTeam = dcTeamsReq[0]
            cloudTeamsReq = list(filter(lambda team: team['displayName'].lower() == dcTeam['title'].lower(), cloudTeams))
            if cloudTeamsReq:
                if len(cloudTeamsReq) > 1:
                    writer.writerow(['Team','Problem','More than one match in Cloud',str(id)])
                return cloudTeamsReq[0]['teamId']
            else:
                writer.writerow(['Team','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow(['Team','Error','Team not found in DC',str(id)])
            return id

    def mapAsset(key,jql=False):
        dcAssetsReq = list(filter(lambda obj: obj['objectKey'] == key, dcAssets))
        if dcAssetsReq:
            dcAsset = dcAssetsReq[0]
            cloudAssetsReq = list(filter(lambda obj: obj['name'] == dcAsset['name'] and obj['objectType']['name'] == dcAsset['objectType']['name'], cloudAssets))
            if cloudAssetsReq:
                if len(cloudAssetsReq) > 1:
                    writer.writerow(['Asset','Problem','More than one match in Cloud',str(key)])
                return cloudAssetsReq[0]['objectKey']
            else:
                writer.writerow(['Asset','Error','No match in Cloud',str(key)])
                return key
        else:
            writer.writerow(['Asset','Error','Asset not found in DC',str(key)])
            return key        

    def manageJql(query):
        if 'issuefunction' in query.lower():
            writer.writerow(['JQL','Problem','Contains Scriptrunner function',query])

        writer.writerow(['JQL','Info','Query: Before',query])
        
        #Special field Customer Request Type
        newQuery = re.sub('''customer request type''','Request type',query,flags=re.I)
        
        #Teams
        teamRegex = '''(?=("?'?(?:team|cf\[10001\])"?'?\s*(?:!?=| (?:not )?in )\s*\(?((?:\s*"?'?\d+"?'?\s*,?)+)\)?))'''
        teamClauses = []
        for d in re.findall(teamRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                teamId = ''.join(filter(lambda str: str.isdigit(), l[1][i]))
                if teamId:
                    newClause = newClause.replace(teamId,str(mapTeam(teamId)))
                i = i+1
            teamClauses.append((d[0],newClause))
        for clause in teamClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        
        #Assets
        #Clause classique type "Owner Team" in (TEAM-124,TEAM-125), rarement présente
        assetClause = '|'.join([re.escape(d) for d in dcAssetClauses])
        assetClauses = []
        regexs = []
        assetRegexs = []

        #Regex pour le format in (TEAM-123,TEAM-456) ou in (TEAM-123), à faire en premier pour exclure le cas 2 qui va être transformé en cas 1
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*((?: not)? in )\s*\(((?!\s*".*?"\s*,?)[^)]+)\))''')

        #Regex pour le format in ("C-logistics [Peaksys] (CUST-53)", "Prout (Team-123)") ou in ("C-logistics [Peaksys] (CUST-53)") ou in ("TEAM-453")
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*((?: not)? in )\s*\(((?:\s*".*?"\s*,?)+)\))''') #Obligé de faire comme ça pour gérer les parenthèses

        #Regex pour le format = TEAM-123
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*(!?=)\s*((?!".*?(?<!\\\)")[^ ]+))''')
            
        #Regex pour le format = "C-logistics [Peaksys] (CUST-53)"
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*(!?=)\s*(".*?(?<!\\\)"))''')

        for assetRegex in assetRegexs:
            resa = re.findall(assetRegex,newQuery,flags=re.I)
            if resa:
                for res in resa:
                    regexs.append(res)

        for d in regexs:
            print(str(d))
            #Pour chaque clause, d[0] = totalité de la clause, d[1] = champ, d[2] = opérateur, d[3] = liste des refs
            newClause = d[0]
            l=d[3].split(',')
            i=0
            while i < len(l):
                assetKey = re.search('([a-zA-Z0-9]+-\d+)',l[i])
                if assetKey:
                    newAsset = mapAsset(assetKey.group(1))
                    newClause = newClause.replace(l[i],newAsset)
                i = i+1
            assetClauses.append((d[0],newClause))
            
        for clause in assetClauses:
            newQuery = newQuery.replace(clause[0],clause[1])

        #Regex générale
        assetRegexClass = f'''(("?'?(?:{assetClause})"?'?)\s*(!?=|(?: not)? in )\s*(\((?:[a-zA-Z0-9]+-\d+,?)+\)|[a-zA-Z0-9]+-\d+))'''

        newQuery = re.sub(assetRegexClass,r'\2 in aqlFunction("key\3\4")',newQuery)
        
        fieldClauses = []
        for field in dcAssetClauses:
            fieldId = re.search('\d{5}',field)
            if fieldId:
                newField = mapFieldFromId('customfield_' + fieldId[0])
                if newField:
                    fieldClauses.append(('cf[' + fieldId[0] + ']',re.sub(r'customfield_(\d{5})',r'cf[\1]',newField)))
        for clause in fieldClauses:
            newQuery = newQuery.replace(clause[0],clause[1])   
            
        writer.writerow(['JQL','Info','Query: After',newQuery])
        
        return newQuery
        #Cascadefield = id
        #Status = id
        #issuetype ou type = id
        #Versions : les champs sont limités

    filters = []
    isLast = False
    startAt = 0
    pace = 100
    while not isLast:
        filtersReq = getCloud('/rest/api/3/filter/search?expand=jql,owner&startAt=' + str(startAt) + '&maxResults=' + str(pace))
        if filtersReq:
            filters = filters + filtersReq['values']
            startAt = startAt + pace
            isLast = filtersReq['isLast']
        else:
            break
        
    for filterQuery in filters:
        if check(filterQuery,'jql'):
            newJql = manageJql(filterQuery['jql'])
            if newJql != filterQuery['jql']:
                changeOwner = requests.put(cloudBaseUrl + '/rest/api/3/filter/' + str(filterQuery['id']) + '/owner',auth=basic,json={"accountId":"712020:7b1603ab-ad40-4052-81ff-215a6544c3b0"})
                if changeOwner.status_code == 204:
                    #rep = requests.put(cloudBaseUrl + '/rest/api/3/filter/' + filterQuery['id'],auth=basic,json={"name":filterQuery['name'],"jql":newJql})
                    writer.writerow(['Filter','Info','Conversion Before',str(filterQuery['id']),filterQuery['name'],filterQuery['jql']])
                    #if rep.status_code == 200:
                    writer.writerow(['Filter','Info','Conversion ?',str(filterQuery['id']),filterQuery['name'],newJql])
                    if check(filterQuery,'owner'):
                        if check(filterQuery['owner'],'accountId'):
                            changeBack = requests.put(cloudBaseUrl + '/rest/api/3/filter/' + str(filterQuery['id']) + '/owner',auth=basic,json={"accountId":filterQuery['owner']['accountId']})
                            if changeBack.status_code != 204:
                                writer.writerow(['Filter','Error','Change back ownership',str(filterQuery['id']),filterQuery['name'],json.dumps(changeBack.json())])
                        else:
                            writer.writerow(['Filter','Error','Change back ownership',str(filterQuery['id']),filterQuery['name'],'Owner sans account id'])
                    else:
                        writer.writerow(['Filter','Error','Change back ownership',str(filterQuery['id']),filterQuery['name'],'Pas d\'owner'])
                else:
                    writer.writerow(['Filter','Error','Change ownership',str(filterQuery['id']),filterQuery['name'],json.dumps(changeOwner.json())])
                    writer.writerow(['Filter','Error','Conversion Failed',str(filterQuery['id']),filterQuery['name'],json.dumps(changeOwner.json())])


