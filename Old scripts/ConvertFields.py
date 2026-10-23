import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys_sandbox_migration_01")
dc_environment = get_environment("cdiscount", "data_center")

import json
import requests
import csv
import re
from requests.auth import HTTPBasicAuthDCBaseUrl = dc_environment["jira_base_url"]
cloudBaseUrl = cloud_environment["jira_base_url"]
bearer_token = dc_environment["jira_pat"]

headers = {"Authorization": f"Bearer {bearer_token}"}
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

dcFields = requests.get(DCBaseUrl + '/field', headers=headers).json()
cloudFields = requests.get(cloudBaseUrl + '/field',auth=basic).json()

currentRule = ''
currentComponent = ''

def manageJql(query):
    if re.search('issueFunction',query):
        writer.writerow([currentRule,currentComponent,'JQL',query])

def mapUser(userKey):
    svcJira = '712020:367293a3-5f77-422a-9b4f-a582251933c0'
    dcUserReq = requests.get(DCBaseUrl + '/user?key=' + userKey,headers=headers)
    if dcUserReq is None:
        return svcJira
    else:
        dcUser = dcUserReq.json()
        cloudUser = requests.get(cloudBaseUrl + '/user/search?query=' + dcUser['emailAddress'],auth=basic)
        if cloudUser is None:
            return svcJira
        else:
            return cloudUser.json()[0]['accountId']
        
def mapFieldFromId(id):
    if id in ['initiator','parent']:
        return id
    dcFieldsReq = list(filter(lambda field: field['id'] == id, dcFields))
    if dcFieldsReq:
        dcField = dcFieldsReq[0]
        if dcField['id'] in ['components','fixVersions','duedate']:
            return dcField['id']
        elif dcField['id'] == 'customfield_10002':
            dcField['name'] = 'Request Type'
        elif dcField['id'] == 'customfield_11200':
            dcField['name'] = 'Story points'
        elif dcField['id'] == 'customfield_14300':
            dcField['name'] = 'Flagged'
        cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields)) 
        if cloudFieldsReq:
            return cloudFieldsReq[0]['id']
        else:
            for clauseName in dcField['clauseNames']:
                cloudFieldsReq = list(filter(lambda field: field['name'] == clauseName and field['schema']['type'] == dcField['schema']['type'], cloudFields)) 
                if cloudFieldsReq:
                    return cloudFieldsReq[0]['id']
            return 'Not found, type = ' + dcField['schema']['custom']

def mapFieldFromName(name):
    dcFieldsReq = list(filter(lambda field: field['name'] == name, dcFields))
    if dcFieldsReq:
        dcField = dcFieldsReq[0]
        cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields))
        if cloudFieldsReq:
            return cloudFieldsReq[0]['id']

def editFields(componentvalue):
    if componentvalue['operations']:
        results = []
        for operation in componentvalue['operations']:
            if operation['fieldId'] == 'customfield_10002':
                results.append({
                    'action': 'addComponent',
                    'component': 'jira.edit.request.type',
                    'value': 'prout' #A FAIRE : DETERMINER LA VALEUR SACHANT QU'ON NE DISPOSE QUE DE l'ID !?
                })
                componentvalue['operations'].remove(operation)
                writer.writerow([currentRule,currentComponent,operation['fieldId'], mapFieldFromId(operation['fieldId'])])
                continue
            writer.writerow([currentRule,currentComponent,operation['fieldId'], mapFieldFromId(operation['fieldId'])])
            if 'value' in operation and operation['type'] == 'COPY':
                if 'additional' in operation['value']:
                    writer.writerow([currentRule,currentComponent,operation['value']['additional'], mapFieldFromId(operation['value']['additional'])])
        return results

def jirajqlscheduled(component):
    manageJql(component['value']['jql'])

def jiraconditioncontainerblock(component):
    return

def jiraconditionifblock(component):
    for condition in component['conditions']:
        functions[condition['type']](condition)

def jiraissuecomment(component):
    return

def jiraissuetransition(component):
    editFields(component['value'])

def jiraissueedit(component):
    editFields(component['value'])

def jiraissuefieldchanged(component):
    for field in component['value']['fields']:
        if field['type'] == 'field':
            writer.writerow([currentRule,currentComponent,field['value'], mapFieldFromId(field['value'])])
        elif field['type'] == 'match':
            writer.writerow([currentRule,currentComponent,field['value'], mapFieldFromName(field['value'])])


def jiraissuecondition(component):
    if component['value']['selectedField']:
        field = component['value']['selectedField']
        if field['type'] == 'ID':
            writer.writerow([currentRule,currentComponent,field['value'], mapFieldFromId(field['value'])])
    if 'compareValue' in component['value']:
        if component['value']['compareValue']['type'] == 'FIELD':
            field = component['value']['compareValue']['value']
            writer.writerow([currentRule,currentComponent,field, mapFieldFromId(field)])

def jiraissueclone(component):
    editFields(component['value'])

def jiramanualtriggerissue(component):
    return


def jiraissueassign(component):
    return

def jiraissuerefreshissue(component):
    return

def jiraissueeventtriggercreated(component):
    return

def jiraissueeventtriggermoved(component):
    return

def jirausercondition(component):
    for condition in component['value']['conditions']:
        if 'field' in condition:
            writer.writerow([currentRule,currentComponent,condition['field'], mapFieldFromId(condition['field'])])
            

def jiraissueoutgoingemail(component):
    if component['value']['to']:
        for field in component['value']['to']:
            if field['type'] == 'COPY':
                writer.writerow([currentRule,currentComponent,field['value'], mapFieldFromId(field['value'])])
    if component['value']['cc']:
        for field in component['value']['cc']:
            if field['type'] == 'COPY':
                writer.writerow([currentRule,currentComponent,field['value'], mapFieldFromId(field['value'])])
    if component['value']['bcc']:
        for field in component['value']['bcc']:
            if field['type'] == 'COPY':
                writer.writerow([currentRule,currentComponent,field['value'], mapFieldFromId(field['value'])])

def jirajqlcondition(component):
    manageJql(component['value'])

def codebarrelactionlog(component):
    return

def comonresolvejiragroovygroovyrunnerlookupobjectbeans(component):
    return

def jirasetentityproperty(component):
    return

def jiraissueoutgoingwebhook(component):
    headers = []
    for header in component['value']['headers']:
        headers.append(header['value']['keyOrValue'] + ' ' + str(header['value']['secret']))
    writer.writerow([currentRule,currentComponent,component['value']['url']] + headers)

def jiraissuerelated(component):
    if component['value']['relatedType'] == 'jql':
        manageJql(component['value']['jql'])

def jiraissuecreate(component):
    editFields(component['value'])

def jiraissueeventtriggertransitioned(component):
    return

def jiraissueeventtriggercommented(component):
    return

def jiraissueeventtriggerupdated(component):
    return


def msteamsnotification(component):
    writer.writerow([currentRule,currentComponent,component['value']['webhookUrl'], ''])
    
def automationtriggerservicelimit(component):
    return


def jiraissueaddwatcher(component):
    return

def jiraissuesrelatedcondition(component):
    if component['value']['relatedType'] == 'jql':
        manageJql(component['value']['relatedJql'])
        manageJql(component['value']['compareJql'])

def jiraissueeventtriggerlink(component):
    return

def jirasdaddcustomer(component):
    return

def jirapublishevent(component):
    return

def jiraissuelink(component):
    return

def jiramultipleissueevent(component):
    for event in component['value']['events']:
        writer.writerow([currentRule,currentComponent,event['event'],''])


def jiraissuearchive(component):
    return

def jiracomparatorcondition(component):
    return

def jiraissueeventtriggerassigned(component):
    return

def jirasprinteventtriggerstarted(component):
    return

def jiraworklogadd(component):
    return

def comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2(component):
    return

def jiraissuecreatesubtasks(component):
    return

def jiraissuedelete(component):
    return

def jirasprinteventtriggerclosed(component):
    return

def jiralookupissues(component):
    if component['value']['type'] == 'JQL':
        manageJql(component['value']['query']['value'])

def jiracreatevariable(component):
    return

def jiraslathresholdtrigger(component):
    writer.writerow([currentRule,currentComponent,component['value']['customFieldId'], mapFieldFromId(component['value']['customFieldId'])])

def comonresolvejiragroovygroovyrunnerexecutescriptissueaction(component):
    return

def jiraissueeventtriggerlinkdeleted(component):
    return

def slacknotification(component):
    writer.writerow([currentRule,currentComponent,component['value']['webhookUrl'], ''])

def jiraissuehasAttachments(component):
    return

def jiraissueeventtriggerdeleted(component):
    return

functions = {'jira.jql.scheduled':jirajqlscheduled,'jira.condition.container.block':jiraconditioncontainerblock,'jira.condition.if.block':jiraconditionifblock,'jira.issue.comment':jiraissuecomment,'jira.issue.transition':jiraissuetransition,'jira.issue.edit':jiraissueedit,'jira.issue.field.changed':jiraissuefieldchanged,'jira.issue.condition':jiraissuecondition,'jira.issue.clone':jiraissueclone,'jira.manual.trigger.issue':jiramanualtriggerissue,'jira.issue.assign':jiraissueassign,'jira.issue.refresh.issue':jiraissuerefreshissue,'jira.issue.event.trigger:created':jiraissueeventtriggercreated,'jira.issue.event.trigger:moved':jiraissueeventtriggermoved,'jira.user.condition':jirausercondition,'jira.issue.outgoing.email':jiraissueoutgoingemail,'jira.jql.condition':jirajqlcondition,'codebarrel.action.log':codebarrelactionlog,'com.onresolve.jira.groovy.groovyrunner:lookup-object-beans':comonresolvejiragroovygroovyrunnerlookupobjectbeans,'jira.set.entity.property':jirasetentityproperty,'jira.issue.outgoing.webhook':jiraissueoutgoingwebhook,'jira.issue.related':jiraissuerelated,'jira.issue.create':jiraissuecreate,'jira.issue.event.trigger:transitioned':jiraissueeventtriggertransitioned,'jira.issue.event.trigger:commented':jiraissueeventtriggercommented,'jira.issue.event.trigger:updated':jiraissueeventtriggerupdated,'msteams.notification':msteamsnotification,'automation.trigger.service.limit':automationtriggerservicelimit,'jira.issue.add.watcher':jiraissueaddwatcher,'jira.issues.related.condition':jiraissuesrelatedcondition,'jira.issue.event.trigger:link':jiraissueeventtriggerlink,'jira.sd.add.customer':jirasdaddcustomer,'jira.publish.event':jirapublishevent,'jira.issue.link':jiraissuelink,'jira.multiple.issue.event':jiramultipleissueevent,'jira.issue.archive':jiraissuearchive,'jira.comparator.condition':jiracomparatorcondition,'jira.issue.event.trigger:assigned':jiraissueeventtriggerassigned,'jira.sprint.event.trigger:started':jirasprinteventtriggerstarted,'jira.worklog.add':jiraworklogadd,'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action-v2':comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2,'jira.issue.create.subtasks':jiraissuecreatesubtasks,'jira.issue.delete':jiraissuedelete,'jira.sprint.event.trigger:closed':jirasprinteventtriggerclosed,'jira.lookup.issues':jiralookupissues,'jira.create.variable':jiracreatevariable,'jira.sla.threshold.trigger':jiraslathresholdtrigger,'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action':comonresolvejiragroovygroovyrunnerexecutescriptissueaction,'jira.issue.event.trigger:link_deleted':jiraissueeventtriggerlinkdeleted,'slack.notification':slacknotification,'jira.issue.hasAttachments':jiraissuehasAttachments,'jira.issue.event.trigger:deleted':jiraissueeventtriggerdeleted}

def searchSmartValues(component):
    if component:
        if re.search('{{[^}]+}}',str(component)):
            smartValues = re.findall('{{[^}]+}}',str(component))
            for sm in smartValues:
                for customField in filter(lambda field: field.startswith('customfield_'),sm.split('.')):
                    writer.writerow([currentRule, currentComponent, customField.replace('}','').replace(')',''), mapFieldFromId(customField.replace('}','').replace(')','')), 'Oui'])

def convert(components):
    global currentComponent
    for component in components:
        if "type" in component and "component" in component:
            currentComponent = component["component"] + ' ' + component["type"]
            
        #Smart values
        if "value" in component:
            searchSmartValues(component['value'])
        
        if "conditions" in component:
            searchSmartValues(component['conditions'])
        
        #Champs particuliers
        results = functions[component['type']](component)
        if results:
            for result in results:
                if result['action'] == 'addComponent':
                    if result['component'] == 'jira.edit.request.type':
                        newComponent = {
                            "component": "ACTION",
                            "parentId":null,
                            "conditionParentId":null,
                            "schemaVersion":1,
                            "type":"jira.edit.request.type",
                            "value": {
                                "requestType": {
                                    "type":"NAME",
                                    "value":result['value']
                                },
                                "sendNotifications":False
                            },
                            "children":[],
                            "conditions":[],
                            "connectionId":null
                        }
                        components.append(newComponent)
        
        if "children" in component:
            if component["children"]:
                convert(component["children"])

with open(r'C:\Users\simon.lucchesini\Documents\Analyse Automation\automation-rules-202502071516.json',encoding='utf-8') as f:
    rules = json.load(f)['rules']
    with open(r'C:\Users\simon.lucchesini\Downloads\output.csv', 'w', newline='', encoding='utf-8') as f2:
        writer = csv.writer(f2, delimiter=',',quotechar='"')
        writer.writerow(['Règle','Composant','Field DC','Field Cloud','Smart value ?'])
                    
        for rule in rules:
            if rule['state'] == 'ENABLED':
                currentRule = rule['name']
                currentComponent = 'TRIGGER - ' + rule['trigger']['type']
                searchSmartValues(rule['trigger'])
                functions[rule['trigger']['type']](rule['trigger'])    
                convert(rule['components'])
            
            


