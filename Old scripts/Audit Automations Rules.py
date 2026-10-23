import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
dc_environment = get_environment("open_groupe_prod", "data_center")

import json
import requests
import csv
import re
import time
from requests.auth import HTTPBasicAuth 

#Chemin vers le fichier source
inputPath = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Open\Analyse Automation\export.json'
#Chemin vers le fichier de logs
logPath = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Open\Analyse Automation\output 2.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]
#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Rule","Component","JQL","Smart Value","Detail","Additional detail"])
        
    def getDC(url,headers={}):
        headers['Authorization'] = f"Bearer {bearer_token}"
        retour = requests.get(DCBaseUrl + url, headers=headers)
        print(retour.status_code)
        time.sleep(30)
        return retour.json()

    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res

    #Chargement des éléments
    #Fields
    dcFields = getDC('/rest/api/2/field')

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
            writer.writerow(['INITIALISATION','INITIALISATION','Asset Fields','Error','Couldn\'t find the field ID in DC',assetField['id']])

    #User fields on DC
    dcUserPickerFieldsReq = getDC('/rest/api/2/customFields?types=com.atlassian.jira.plugin.system.customfieldtypes:userpicker&types=types=com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker')['values']
    dcUserFields = ['assignee','reporter','creator','Issue creator','Request participants','customfield_10003']
    dcUserClauses = dcUserFields

    for userField in dcUserPickerFieldsReq:
        improvedFields = list(filter(lambda field: field['id'] == userField['id'], dcFields))
        if improvedFields:
            improvedField = improvedFields[0]
            if check(improvedField,'clauseNames'):
                dcUserClauses = dcUserClauses + improvedField['clauseNames']
            else:
                dcUserClauses.append(improvedField['name'])
            dcUserFields.append(improvedField['id'])
            dcUserFields.append(improvedField['name'])
        else:
            writer.writerow(['INITIALISATION','INITIALISATION','User Fields','Error','Couldn\'t find the field ID in DC',userField['id']])

    currentRule = ''
    currentComponent = ''

    def mapTeam(id):
        writer.writerow([currentRule,currentComponent,'Team','Info',str(id)])

    def mapOrganization(id):
        writer.writerow([currentRule,currentComponent,'Organization','Info',str(id)])
       
    def mapAsset(key):
        writer.writerow([currentRule,currentComponent,'Asset','Info',str(key)])

    def mapUser(userKey,type='key'):
        writer.writerow([currentRule,currentComponent,'User','Info',str(userKey)])

    def manageSmartValues(element):
        writer.writerow([currentRule,currentComponent,'Manage Smart Values','All',str(element)])
        smFields = re.search('customfield_\d{5}',element,flags=re.I)
        if smFields:
            writer.writerow([currentRule,currentComponent,'Manage Smart Values','Fields in smart values',str(element)])
        
        smAssets = re.search('lookupAssets',element,flags=re.I)
        if smAssets:
            writer.writerow([currentRule,currentComponent,'Manage Smart Values','lookupAssets in smart values',str(element)])

        smWebhook = re.search('webhookResponse',element,flags=re.I)
        if smWebhook:
            writer.writerow([currentRule,currentComponent,'Manage Smart Values','webhookResponse in smart values',str(element)])

    def manageJql(query):
        writer.writerow([currentRule,currentComponent,'JQL','Query',query])
        if 'issuefunction' in query.lower():
            writer.writerow([currentRule,currentComponent,'JQL','Contains Scriptrunner function',query])
 
        #Teams
        teamRegex = '''(?=("?'?(?:team|cf\[11700\])"?'?\s*(?:!?=| (?:not )?in )\s*\(?((?:\s*"?'?\d+"?'?\s*,?)+)\)?))'''
        if re.search(teamRegex,query,flags=re.I):
            writer.writerow([currentRule,currentComponent,'JQL','Contains Team',query])
        
        #Users
        #On ne prend pas en compte les clauses BY et CHANGED FROM ou TO username
        userClause = '|'.join([re.escape(d) for d in dcUserClauses])
        userRegex = f'''(?=("?'?(?:{userClause})"?'?\s*(?:!?=| was(?: not)?(?: in)? |(?: not)? in | changed )\s*(\([^\)]+\)|"?'?[^\s]+"?'?)))'''
        if re.search(userRegex,query,flags=re.I):
            writer.writerow([currentRule,currentComponent,'JQL','Contains User',query])
     
        #Assets
        #Clause classique type "Owner Team" in (TEAM-124,TEAM-125), rarement présente
        assetClause = '|'.join([re.escape(d) for d in dcAssetClauses])
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
            resa = re.search(assetRegex,query,flags=re.I)
            if resa:
                writer.writerow([currentRule,currentComponent,'JQL','Contains Asset',query])
                break

    def manageAql(query):
        writer.writerow([currentRule,currentComponent,'X','AQL Query',query])
            
    def editFields(componentvalue):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(componentvalue)])
        if componentvalue['operations']:
            for operation in componentvalue['operations']:
                if check(operation,'fieldId'):
                    if operation['fieldId'] == 'customfield_10002':
                        writer.writerow([currentRule,currentComponent,'X','Présence de Request Type'])
                    if check(operation,'value'):
                        if isinstance(operation['value'],str):
                            manageSmartValues(operation['value'])
                            #writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation with String value',str(operation)])
                        elif operation['type'] == 'SET':
                            if operation['fieldId'] in dcUserFields:
                                if isinstance(operation['value'],list):
                                    for value in operation['value']:
                                        if value['type'] == 'ID':
                                            mapUser(value['value'])
                                elif isinstance(operation['value'],dict):
                                    value = operation['value']
                                    if value['type'] == 'ID':
                                        mapUser(value['value'])
                            elif operation['fieldId'] in dcAssetFields:
                                if isinstance(operation['value'],list):
                                    for value in operation['value']:
                                        mapAsset(value['value'])                                 
                                elif isinstance(operation['value'],dict):
                                    mapAsset(operation['value']['value'])
                            elif operation['fieldId'] == 'customfield_10008': #Sprint
                                writer.writerow([currentRule,currentComponent,'X','Sprint'])
        if check(componentvalue,'advancedFields'):
            for sm in re.findall('{{.*}}',componentvalue['advancedFields'],flags=re.I):
                newValue = re.sub(r'([^\\])"',r'\1\\"',sm)
                componentvalue['advancedFields'] = componentvalue['advancedFields'].replace(sm,newValue)
            try:
                advancedFields = json.loads(componentvalue['advancedFields'])
                for action in advancedFields.keys(): #update or fields
                    fields = advancedFields[action]
                    for key in fields:
                        if key.lower() in ['Team','team','customfield_11700']:
                            if action == 'update':
                                for operation in fields[key]:
                                    for operationAction in operation.keys():
                                        mapTeam(operation[operationAction])
                            elif action == 'fields':
                                mapTeam(fields[key])
                        if key in dcUserFields:
                            if action == 'update':
                                for operation in fields[key]:
                                    for operationAction in operation.keys():
                                        mapUser(operation[operationAction]['name'])
                            elif action == 'fields':
                                if isinstance(fields[key],list):
                                    for user in fields[key]:
                                        if check(user,'name'):
                                            mapUser(user['name'])
                                elif isinstance(fields[key],dict):
                                    if check(fields[key],'name'):
                                        mapUser(fields[key]['name'])
                        if key in dcAssetFields:
                            if action == 'update':
                                for operation in fields[key]:
                                    for operationAction in operation.keys():
                                       mapAsset(fields[key]['key'])
                            elif action == 'fields':
                                if isinstance(fields[key],list):
                                    for obj in fields[key]:
                                        mapAsset(obj['key'])
                                elif isinstance(fields[key],dict):
                                    mapAsset(fields[key]['key'])
                manageSmartValues(componentvalue['advancedFields'])
                #Resterait à gérer tous les éléments qui peuvent être définis par leur ID : options de champs select / mutli select, statut, etc.
            except ValueError as e:
                writer.writerow([currentRule,currentComponent,'Error','Advanced Fields: impossible to decode JSON',str(e),str(componentvalue['advancedFields'])])
                
    def jirajqlscheduled(component):
        writer.writerow([currentRule,currentComponent,'Oui','Oui',str(component)])
        manageJql(component['value']['jql'])

    def jiraconditioncontainerblock(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiraconditionifblock(component):
        convert(component['conditions'])
#         for condition in component['conditions']:
#             if "value" in condition:
#                 searchSmartValues(condition['value'])
#             functions[condition['type']](condition)

    def jiraissuecomment(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'comment'):
            manageSmartValues(component['value']['comment'])
       
        
    def jiraissuetransition(component):
        editFields(component['value'])

    def jiraissueedit(component):
        editFields(component['value'])

    def jiraissuefieldchanged(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiraissuecondition(component):
        #Pas Team : pas possible à sélectionner
        #Pas asset non plus
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'selectedField'):
            field = component['value']['selectedField']
            if field['type'] == 'ID':
                if check(component['value'],'compareValue'):
                    if check(component['value']['compareValue'],'type'):
                        if component['value']['compareValue']['type'] == 'ID':
                            try:
                                value = json.loads(str(component['value']['compareValue']['value']))
                                if field['value'] in dcUserFields:
                                    retour = []
                                    if isinstance(value,list):
                                        for user in value:
                                            mapUser(user)
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        mapUser(component['value']['compareValue']['value'])    
                            except ValueError as e: #Pas au format json = string
                                if field['value'] in dcUserFields:
                                    mapUser(component['value']['compareValue']['value'])
                
    def jiraissueclone(component):
        editFields(component['value'])

    def jiramanualtriggerissue(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueassign(component):
        writer.writerow([currentRule,currentComponent,'Oui','Oui',str(component)])
        if check(component['value'],'jql'):
            manageJql(component['value']['jql'])
        
        if check(component['value'],'userList'):
            for user in component['value']['userList']:
                mapUser(user['value'])
        
        if check(component['value'],'excludeUsers'):
            for user in component['value']['excludeUsers']:
                mapUser(user['value'])
        
        if check(component['value'],'assignee'):
            if component['value']['assignee']['type'] == 'SMART':
                manageSmartValues(component['value']['assignee']['value'])
            elif component['value']['assignee']['type'] == 'ID':
                mapUser(component['value']['assignee']['value'])
                
        if check(component['value'],'smartValue'):
            manageSmartValues(component['value']['smartValue'])

    def jiraissuerefreshissue(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggercreated(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggermoved(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jirausercondition(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        for condition in component['value']['conditions']:
            if check(condition,'check'):
                match condition['check']:
                    case 'USER_IS':
                        for criteria in condition['criteria']:
                            if criteria['type'] == 'ID':
                                mapUser(criteria['value'])
                            if criteria['type'] == 'SMART':
                                manageSmartValues(criteria['value'])
                    case 'IN_ORGANISATION':
                        for criteria in condition['criteria']:
                            if criteria['type'] == 'ID':
                                mapOrganization(criteria['value'])
                

    def jiraissueoutgoingemail(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'to'):
            for field in component['value']['to']:
                if field['type'] == 'SMART':
                    manageSmartValues(field['value'])
        if component['value']['cc']:
            for field in component['value']['cc']:
                if field['type'] == 'SMART':
                    manageSmartValues(field['value'])
        if component['value']['bcc']:
            for field in component['value']['bcc']:
                if field['type'] == 'SMART':
                    manageSmartValues(field['value'])
        if check(component['value'],'subject'):
            manageSmartValues(component['value']['subject'])
        if check(component['value'],'body'):
            manageSmartValues(component['value']['body'])
         
    def jirajqlcondition(component):
        writer.writerow([currentRule,currentComponent,'Oui','Oui',str(component)])
        manageJql(component['value'])

    def codebarrelactionlog(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        manageSmartValues(component['value'])

    def comonresolvejiragroovygroovyrunnerlookupobjectbeans(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'assetKey'):
            manageSmartValues(mapAsset(component['value']['assetKey']))

    def jirasetentityproperty(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component,'value'):
            value = component['value']
            if check(value,'entityType'):
                if value['entityType'] in ['USER','USERLEGACY']:
                    if check(value,'entity'):
                        if value['entity']['type'] == 'ID':
                            mapUser(value['entity']['value'])
                        elif value['entity']['type'] == 'SMART':
                            manageSmartValues(value['entity']['value'])
#                         else: n'exise pas
#                             writer.writerow([currentRule,currentComponent,'Set entity property','User - Type nor ID not SMART',str(value)])
                manageSmartValues(value['key'])
                manageSmartValues(value['value'])

    def jiraissueoutgoingwebhook(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if not 'http' in component['value']['url']:
            writer.writerow([currentRule,currentComponent,'X','URL is a secret',str(component['value']['url'])])
        headers = []
        if check(component['value'],'headers'):
            for header in component['value']['headers']:
                manageSmartValues(header['value']['keyOrValue'])
        if check(component['value'],'customBody'):
            manageSmartValues(component['value']['customBody'])

    def jiraissuerelated(component):
        writer.writerow([currentRule,currentComponent,'Oui','Oui',str(component)])
        if component['value']['relatedType'] == 'jql':
            component['value']['jql'] = manageJql(component['value']['jql'])

    def jiraissuecreate(component):
        editFields(component['value'])

    def jiraissueeventtriggertransitioned(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiraissueeventtriggercommented(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggerupdated(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def msteamsnotification(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if not 'http' in component['value']['webhookUrl']['key']:
            writer.writerow([currentRule,currentComponent,'X','URL is a secret',str(component['value']['webhookUrl']['key'])])
        
        if check(component['value'],'title'):
            manageSmartValues(component['value']['title'])
        if check(component['value'],'body'):
            manageSmartValues(component['value']['body'])

    def automationtriggerservicelimit(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueaddwatcher(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'watchers'):
            for watcher in component['value']['watchers']:
                if watcher['type'] == 'SMART':
                    manageSmartValues(watcher['value'])
                else:
                    mapUser(watcher['value'])
        if check(component['value'],'removeWatchers'):
            for watcher in component['value']['removeWatchers']:
                if watcher['type'] == 'SMART':
                    manageSmartValues(watcher['value'])
                else:
                    mapUser(watcher['value'])

    def jiraissuesrelatedcondition(component):
        writer.writerow([currentRule,currentComponent,'Oui','Oui',str(component)])
        if check(component['value'],'relatedJql'):
            manageJql(component['value']['relatedJql'])
        if check(component['value'],'compareJql'):
            manageJql(component['value']['compareJql'])
        if check(component['value'],'jql'):
            manageJql(component['value']['jql'])
            
    def jiraissueeventtriggerlink(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jirasdaddcustomer(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'email'):
            manageSmartValues(component['value']['email'])
        if check(component['value'],'displayName'):
            manageSmartValues(component['value']['displayName'])
        if check(component['value'],'organization'):
            if component['value']['organization']['type'] == 'ID':
                mapOrganization(component['value']['organization']['value'])  
   
    def jirapublishevent(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiraissuelink(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiramultipleissueevent(component):
        for event in component['value']['events']:
            if event['event'] in ['issue_commented','issue_comment_edited','issue_resolved','issue_reopened','issue_closed']:
                writer.writerow([currentRule,currentComponent,'Non','Non',str(component),'Unmanaged event',event['event']])

    def jiraissuearchive(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiracomparatorcondition(component):
        #A convertir dans la deuxième valeur (pas utile pour CDiscount) :
        #Assets
        #Sprint
        #Teams
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        manageSmartValues(component['value']['first'])
        manageSmartValues(component['value']['second'])
        
    def jiraissueeventtriggerassigned(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jirasprinteventtriggerstarted(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiraworklogadd(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'timeSpent'):
            manageSmartValues(component['value']['timeSpent'])
        if check(component['value'],'dateStarted'):
            if check(component['value']['dateStarted'],'value'):
                manageSmartValues(component['value']['dateStarted']['value'])

    def comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiraissuecreatesubtasks(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'subtasks'):
            for subtask in component['value']['subtasks']:
                manageSmartValues(subtask['summary'])

    def jiraissuedelete(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jirasprinteventtriggerclosed(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])

    def jiralookupissues(component):
        writer.writerow([currentRule,currentComponent,'Oui','Oui',str(component)])
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                manageJql(component['value']['query']['value'])

    def jiracreatevariable(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'name'):
            if check (component['value']['name'],'value'):
                manageSmartValues(component['value']['name']['value'])
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                manageSmartValues(component['value']['query']['value'])
                
    def jiraslathresholdtrigger(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component)])
        
    def comonresolvejiragroovygroovyrunnerexecutescriptissueaction(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])
        
    def jiraissueeventtriggerlinkdeleted(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def slacknotification(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component['value'])])
        if check(component['value'],'channel'):
            manageSmartValues(component['value']['channel'])
        if check(component['value'],'body'):
            manageSmartValues(component['value']['body'])
        
    def jiraissuehasAttachments(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggerdeleted(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])

    def jiraissuecommenteventtriggerupdated(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])
    
    def jiraversioneventtriggerreleased(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])
        
    def jiraincomingwebhook(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])
        
    def jiraissueeventtriggerworklog(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])
        
    def jirasprinteventtriggercreated(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component['value'])])
        
    def jiraversioncreate(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component['value'])])
        
    #Smart Checklists
    def comokapyajirachecklistautomationimporttemplateaction(component):
        writer.writerow([currentRule,currentComponent,'Non','Non',str(component['value'])])
    
    def comokapyajirachecklistautomationdeleteitemsaction(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component['value'])])
    
    def comokapyajirachecklistautomationchecklistcondition(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component['value'])])
        
    def comokapyajirachecklistautomationedititemsaction(component):
        writer.writerow([currentRule,currentComponent,'Non','Oui',str(component['value'])])
        
    functions = {
        'com.okapya.jira.checklist:automation-delete-items-action':comokapyajirachecklistautomationdeleteitemsaction,
        'com.okapya.jira.checklist:automation-import-template-action':comokapyajirachecklistautomationimporttemplateaction,
        'com.okapya.jira.checklist:automation-checklist-condition':comokapyajirachecklistautomationchecklistcondition,
         'com.okapya.jira.checklist:automation-edit-items-action':comokapyajirachecklistautomationedititemsaction,
        'jira.version.create':jiraversioncreate,
        'jira.sprint.event.trigger:created':jirasprinteventtriggercreated,
        'jira.issue.event.trigger:worklog':jiraissueeventtriggerworklog,
        'jira.incoming.webhook':jiraincomingwebhook,
        'jira.version.event.trigger:released':jiraversioneventtriggerreleased,
        'jira.jql.scheduled':jirajqlscheduled,
        'jira.condition.container.block':jiraconditioncontainerblock,
        'jira.condition.if.block':jiraconditionifblock,
        'jira.issue.comment':jiraissuecomment,
        'jira.issue.transition':jiraissuetransition,
        'jira.issue.edit':jiraissueedit,
        'jira.issue.field.changed':jiraissuefieldchanged,
        'jira.issue.condition':jiraissuecondition,
        'jira.issue.clone':jiraissueclone,
        'jira.manual.trigger.issue':jiramanualtriggerissue,
        'jira.issue.assign':jiraissueassign,
        'jira.issue.refresh.issue':jiraissuerefreshissue,
        'jira.issue.event.trigger:created':jiraissueeventtriggercreated,
        'jira.issue.event.trigger:moved':jiraissueeventtriggermoved,
        'jira.user.condition':jirausercondition,
        'jira.issue.outgoing.email':jiraissueoutgoingemail,
        'jira.jql.condition':jirajqlcondition,
        'codebarrel.action.log':codebarrelactionlog,
        'com.onresolve.jira.groovy.groovyrunner:lookup-object-beans':comonresolvejiragroovygroovyrunnerlookupobjectbeans,
        'jira.set.entity.property':jirasetentityproperty,
        'jira.issue.outgoing.webhook':jiraissueoutgoingwebhook,
        'jira.issue.related':jiraissuerelated,
        'jira.issue.create':jiraissuecreate,
        'jira.issue.event.trigger:transitioned':jiraissueeventtriggertransitioned,
        'jira.issue.event.trigger:commented':jiraissueeventtriggercommented,
        'jira.issue.event.trigger:updated':jiraissueeventtriggerupdated,
        'msteams.notification':msteamsnotification,
        'automation.trigger.service.limit':automationtriggerservicelimit,
        'jira.issue.add.watcher':jiraissueaddwatcher,
        'jira.issues.related.condition':jiraissuesrelatedcondition,
        'jira.issue.event.trigger:link':jiraissueeventtriggerlink,
        'jira.sd.add.customer':jirasdaddcustomer,
        'jira.publish.event':jirapublishevent,
        'jira.issue.link':jiraissuelink,
        'jira.multiple.issue.event':jiramultipleissueevent,
        'jira.issue.archive':jiraissuearchive,
        'jira.comparator.condition':jiracomparatorcondition,
        'jira.issue.event.trigger:assigned':jiraissueeventtriggerassigned,
        'jira.sprint.event.trigger:started':jirasprinteventtriggerstarted,
        'jira.worklog.add':jiraworklogadd,
        'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action-v2':comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2,
        'jira.issue.create.subtasks':jiraissuecreatesubtasks,
        'jira.issue.delete':jiraissuedelete,
        'jira.sprint.event.trigger:closed':jirasprinteventtriggerclosed,
        'jira.lookup.issues':jiralookupissues,
        'jira.create.variable':jiracreatevariable,
        'jira.sla.threshold.trigger':jiraslathresholdtrigger,
        'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action':comonresolvejiragroovygroovyrunnerexecutescriptissueaction,
        'jira.issue.event.trigger:link_deleted':jiraissueeventtriggerlinkdeleted,
        'slack.notification':slacknotification,
        'jira.issue.hasAttachments':jiraissuehasAttachments,
        'jira.issue.event.trigger:deleted':jiraissueeventtriggerdeleted,
        'jira.issue.comment.event.trigger:updated':jiraissuecommenteventtriggerupdated
    }
    
    def convert(components):
        global currentComponent
        global parentComponent
        for component in components:
            parentComponent = components
            if "type" in component and "component" in component:
                currentComponent = component["component"] + ' ' + component["type"]

                results = functions[component['type']](component)
            else:
                writer.writerow([currentRule,currentComponent,'Convert','Problem','Component exists but it has no type or subtype'])

            if "children" in component:
                if component["children"]:
                    convert(component["children"])

    with open(inputPath,encoding='utf-8') as f:
        file = json.load(f)
        rules = file['rules']
        rules = [d for d in rules if d['state'] == 'ENABLED']
        
        for rule in rules:
            currentRule = str(rule['id']) + ' - ' + rule['name']
            
            #On fait le trigger en premier parce qu'il peut avoir pour effet de copier la règle existante, et dans ce cas il ne faut pas copier la version convertie du Owner et des projets
            currentComponent = 'TRIGGER - ' + rule['trigger']['type']
            functions[rule['trigger']['type']](rule['trigger'])
            
            currentComponent = 'GENERAL'
            parentComponent = None
            
            convert(rule['components'])


