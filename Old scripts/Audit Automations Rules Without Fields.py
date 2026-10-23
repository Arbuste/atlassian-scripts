import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("tme", service_account=True)

import json
import requests
import csv
import re
import time
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier source
inputPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Open\Audit\Analyse Automation\export 1109.json'
#Chemin vers le fichier de logs
logPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Open\Audit\Analyse Automation\Automation - Logged 1109.csv'

isCloud = False

if (isCloud):
    #URL de l'instance Cloud cible : uniquementcloudBaseUrl = cloud_environment["jira_base_url"]
    #Identifiants pour interroger l'instance Cloud
    basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

def getCloud(url):
    return requests.get(cloudBaseUrl + url,auth=basic).json()

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Rule","Scope","Component","JQL","Smart Value","Detail","Additional detail"])

    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res

    currentRule = ''
    currentComponent = ''
    scope = ''

    if (isCloud):
        projects = []
        startAt = 0
        pace = 100
        isLast = False
        while not isLast:
            projectsReq = getCloud('/rest/api/3/project/search?startAt=' + str(startAt))
            if projectsReq:
                projects = projects + projectsReq['values']
                startAt = startAt + pace
                isLast = projectsReq['isLast']
            else:
                break

    def mapTeam(id):
        writer.writerow([currentRule,scope,currentComponent,'Team','Info',str(id)])

    def mapOrganization(id):
        writer.writerow([currentRule,scope,currentComponent,'Organization','Info',str(id)])
       
    def mapAsset(key):
        writer.writerow([currentRule,scope,currentComponent,'Asset','Info',str(key)])

    def mapUser(userKey,type='key'):
        writer.writerow([currentRule,scope,currentComponent,'User','Info',str(userKey)])

    def manageSmartValues(element):
        writer.writerow([currentRule,scope,currentComponent,'Manage Smart Values','All',str(element)])
        smFields = re.search('customfield_\d{5}',element,flags=re.I)
        if smFields:
            writer.writerow([currentRule,scope,currentComponent,'Manage Smart Values','Fields in smart values',str(element)])
        
        smAssets = re.search('lookupAssets',element,flags=re.I)
        if smAssets:
            writer.writerow([currentRule,scope,currentComponent,'Manage Smart Values','lookupAssets in smart values',str(element)])

        smWebhook = re.search('webhookResponse',element,flags=re.I)
        if smWebhook:
            writer.writerow([currentRule,scope,currentComponent,'Manage Smart Values','webhookResponse in smart values',str(element)])

    def manageJql(query):
        writer.writerow([currentRule,scope,currentComponent,'JQL','Query',query])
        if 'issuefunction' in query.lower():
            writer.writerow([currentRule,scope,currentComponent,'JQL','Contains Scriptrunner function',query])
 
        #Teams
        teamRegex = '''(?=("?'?(?:team|cf\[11700\])"?'?\s*(?:!?=| (?:not )?in )\s*\(?((?:\s*"?'?\d+"?'?\s*,?)+)\)?))'''
        if re.search(teamRegex,query,flags=re.I):
            writer.writerow([currentRule,scope,currentComponent,'JQL','Contains Team',query])

    def manageAql(query):
        writer.writerow([currentRule,scope,currentComponent,'X','AQL Query',query])
            
    def editFields(componentvalue):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(componentvalue)])
        if componentvalue['operations']:
            for operation in componentvalue['operations']:
                if check(operation,'fieldId'):
                    if operation['fieldId'] == 'customfield_10002':
                        writer.writerow([currentRule,scope,currentComponent,'X','Présence de Request Type'])
                    if check(operation,'value'):
                        if isinstance(operation['value'],str):
                            manageSmartValues(operation['value'])
                            #writer.writerow([currentRule,scope,currentComponent,'Edit issue (create, edit, clone)','Operation with String value',str(operation)])
                        elif operation['type'] == 'SET':
                            if operation['fieldId'] == 'customfield_10008': #Sprint
                                writer.writerow([currentRule,scope,currentComponent,'X','Sprint'])
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
                manageSmartValues(componentvalue['advancedFields'])
                #Resterait à gérer tous les éléments qui peuvent être définis par leur ID : options de champs select / mutli select, statut, etc.
            except ValueError as e:
                writer.writerow([currentRule,scope,currentComponent,'Error','Advanced Fields: impossible to decode JSON',str(e),str(componentvalue['advancedFields'])])
                
    def jirajqlscheduled(component):
        writer.writerow([currentRule,scope,currentComponent,'Oui','Oui',str(component)])
        manageJql(component['value']['jql'])

    def jiraconditioncontainerblock(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non'])

    def jiraconditionifblock(component):
        convert(component['conditions'])
#         for condition in component['conditions']:
#             if "value" in condition:
#                 searchSmartValues(condition['value'])
#             functions[condition['type']](condition)

    def jiraissuecomment(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'comment'):
            manageSmartValues(component['value']['comment'])
       
        
    def jiraissuetransition(component):
        editFields(component['value'])

    def jiraissueedit(component):
        editFields(component['value'])

    def jiraissuefieldchanged(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiraissuecondition(component):
        #Pas Team : pas possible à sélectionner
        #Pas asset non plus
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        
    def jiraissueclone(component):
        editFields(component['value'])

    def jiramanualtriggerissue(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueassign(component):
        writer.writerow([currentRule,scope,currentComponent,'Oui','Oui',str(component)])
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
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggercreated(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggermoved(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jirausercondition(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
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
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
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
        writer.writerow([currentRule,scope,currentComponent,'Oui','Oui',str(component)])
        manageJql(component['value'])

    def codebarrelactionlog(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        manageSmartValues(component['value'])

    def comonresolvejiragroovygroovyrunnerlookupobjectbeans(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'assetKey'):
            manageSmartValues(mapAsset(component['value']['assetKey']))

    def jirasetentityproperty(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
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
#                             writer.writerow([currentRule,scope,currentComponent,'Set entity property','User - Type nor ID not SMART',str(value)])
                manageSmartValues(value['key'])
                manageSmartValues(value['value'])

    def jiraissueoutgoingwebhook(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if not 'http' in component['value']['url']:
            writer.writerow([currentRule,scope,currentComponent,'X','URL is a secret',str(component['value']['url'])])
        headers = []
        if check(component['value'],'headers'):
            for header in component['value']['headers']:
                manageSmartValues(header['value']['keyOrValue'])
        if check(component['value'],'customBody'):
            manageSmartValues(component['value']['customBody'])

    def jiraissuerelated(component):
        writer.writerow([currentRule,scope,currentComponent,'Oui','Oui',str(component)])
        if component['value']['relatedType'] == 'jql':
            component['value']['jql'] = manageJql(component['value']['jql'])

    def jiraissuecreate(component):
        editFields(component['value'])

    def jiraissueeventtriggertransitioned(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiraissueeventtriggercommented(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiraissueeventtriggerupdated(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def msteamsnotification(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])     
        if check(component['value'],'title'):
            manageSmartValues(component['value']['title'])
        if check(component['value'],'body'):
            manageSmartValues(component['value']['body'])

    def automationtriggerservicelimit(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueaddwatcher(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
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
        writer.writerow([currentRule,scope,currentComponent,'Oui','Oui',str(component)])
        if check(component['value'],'relatedJql'):
            manageJql(component['value']['relatedJql'])
        if check(component['value'],'compareJql'):
            manageJql(component['value']['compareJql'])
        if check(component['value'],'jql'):
            manageJql(component['value']['jql'])
            
    def jiraissueeventtriggerlink(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jirasdaddcustomer(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'email'):
            manageSmartValues(component['value']['email'])
        if check(component['value'],'displayName'):
            manageSmartValues(component['value']['displayName'])
        if check(component['value'],'organization'):
            if component['value']['organization']['type'] == 'ID':
                mapOrganization(component['value']['organization']['value'])  
   
    def jirapublishevent(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiraissuelink(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiramultipleissueevent(component):
        for event in component['value']['events']:
            if event['event'] in ['issue_commented','issue_comment_edited','issue_resolved','issue_reopened','issue_closed']:
                writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component),'Unmanaged event',event['event']])

    def jiraissuearchive(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiracomparatorcondition(component):
        #A convertir dans la deuxième valeur (pas utile pour CDiscount) :
        #Assets
        #Sprint
        #Teams
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        manageSmartValues(component['value']['first'])
        manageSmartValues(component['value']['second'])
        
    def jiraissueeventtriggerassigned(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jirasprinteventtriggerstarted(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiraworklogadd(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'timeSpent'):
            manageSmartValues(component['value']['timeSpent'])
        if check(component['value'],'dateStarted'):
            if check(component['value']['dateStarted'],'value'):
                manageSmartValues(component['value']['dateStarted']['value'])

    def comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiraissuecreatesubtasks(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'subtasks'):
            for subtask in component['value']['subtasks']:
                manageSmartValues(subtask['summary'])

    def jiraissuedelete(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jirasprinteventtriggerclosed(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])

    def jiralookupissues(component):
        writer.writerow([currentRule,scope,currentComponent,'Oui','Oui',str(component)])
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                manageJql(component['value']['query']['value'])

    def jiracreatevariable(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component)])
        if check(component['value'],'name'):
            if check (component['value']['name'],'value'):
                manageSmartValues(component['value']['name']['value'])
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                manageSmartValues(component['value']['query']['value'])
                
    def jiraslathresholdtrigger(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component)])
        
    def comonresolvejiragroovygroovyrunnerexecutescriptissueaction(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])
        
    def jiraissueeventtriggerlinkdeleted(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def slacknotification(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component['value'])])
        if check(component['value'],'channel'):
            manageSmartValues(component['value']['channel'])
        if check(component['value'],'body'):
            manageSmartValues(component['value']['body'])
        
    def jiraissuehasAttachments(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraissueeventtriggerdeleted(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraissuecommenteventtriggerupdated(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])
    
    def jiraversionrelease(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    def jiraversioneventtriggerreleased(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])
        
    def jiraincomingwebhook(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])
        
    def jiraissueeventtriggerworklog(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])
        
    def jirasprinteventtriggercreated(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component['value'])])
        
    def jiraversioncreate(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component['value'])])
        
    #Smart Checklists
    def comokapyajirachecklistautomationimporttemplateaction(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])
    
    def comokapyajirachecklistautomationdeleteitemsaction(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component['value'])])
    
    def comokapyajirachecklistautomationchecklistcondition(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component['value'])])
        
    def comokapyajirachecklistautomationedititemsaction(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Oui',str(component['value'])])
    
    def comxiplinkjiragitjira_git_pluginpullrequestmergedtrigger(component):
        writer.writerow([currentRule,scope,currentComponent,'Non','Non',str(component['value'])])

    functions = {
        'com.okapya.jira.checklist:automation-delete-items-action':comokapyajirachecklistautomationdeleteitemsaction,
        'com.okapya.jira.checklist:automation-import-template-action':comokapyajirachecklistautomationimporttemplateaction,
        'com.okapya.jira.checklist:automation-checklist-condition':comokapyajirachecklistautomationchecklistcondition,
         'com.okapya.jira.checklist:automation-edit-items-action':comokapyajirachecklistautomationedititemsaction,
        'jira.version.release':jiraversionrelease,
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
        'jira.issue.comment.event.trigger:updated':jiraissuecommenteventtriggerupdated,
        'com.xiplink.jira.git.jira_git_plugin:pull-request-merged-trigger':comxiplinkjiragitjira_git_pluginpullrequestmergedtrigger
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
                writer.writerow([currentRule,scope,currentComponent,'Convert','Problem','Component exists but it has no type or subtype'])

            if "children" in component:
                if component["children"]:
                    convert(component["children"])

    with open(inputPath,encoding='utf-8') as f:
        file = json.load(f)
        rules = file['rules']
        rules = [d for d in rules if d['state'] == 'ENABLED']
        
        for rule in rules:
            if (isCloud):
                if check(rule,'ruleScope'):
                    if check(rule['ruleScope'],'resources'):
                        scope = ''
                        for ressource in rule['ruleScope']['resources']:
                            if 'ari:cloud:jira::site' in ressource:
                                scope = 'Global'
                                break
                            elif 'ari:cloud:jira-software::site' in ressource:
                                scope = 'Jira Software'
                                break
                            elif 'ari:cloud:jira-service::site' in ressource:
                                scope = 'Jira Service'
                                break
                            elif 'project/' in ressource:
                                projectId = ressource[ressource.find('project/') + 8:]
                                projectTab = [project for project in projects if project['id'] == projectId]
                                if projectTab:
                                    project = projectTab[0]
                                    scope += project['key']
                            
                            
            currentRule = str(rule['id']) + ' - ' + rule['name']
            
            #On fait le trigger en premier parce qu'il peut avoir pour effet de copier la règle existante, et dans ce cas il ne faut pas copier la version convertie du Owner et des projets
            currentComponent = 'TRIGGER - ' + rule['trigger']['type']
            functions[rule['trigger']['type']](rule['trigger'])
            
            currentComponent = 'GENERAL'
            parentComponent = None
            
            convert(rule['components'])


