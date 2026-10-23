import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
environment = get_environment("bienici")

import requests
import time
from requests.auth import HTTPBasicAuth

def parse_string(string):
    string = string.replace(' - ','_')
    string = string.replace(' ','_')
    return string
    
def convert_priority(val):
    match val:
        case 'Highest':
            return 'P1'
        case 'High':
            return 'P2'
        case 'Medium':
            return 'P3'
        case 'Low' | 'Lowest':
            return 'P4'
        case 'P1':
            return 'P1'
        case 'P2':
            return 'P2'
        case 'P3':
            return 'P3'
        case _:
            return 'P4'

def convert_severity(val):
    match val:
        case 'Critical':
            return { 'value': 'Forte' }
        case 'Major' | 'Minor':
            return { 'value': 'Normale' }

def convert_impact(val):
    match val:
        case 'Extensive / Widespread':
            return { 'value': 'Elevé' }
        case 'Significant / Large' | 'Moderate / Limited (disabled)':
            return { 'value': 'Moyen' }
        case 'Minor / Localized':
            return { 'value': 'Bas' }

def convert_product(updateDoc, val):
    match val:
        case '3D - Animation' | '3D - Blender' | '3D - Environnement 3D' | '3D - Lot' | '3D - Maquette' | '3D - Mini-site' | '3D - Perspectives' | '3D - Vue Drone' | '3D - Widgets' | '3D - Karto':
            updateDoc['fields']['labels'].append(parse_string(val))
            updateDoc['fields']['components'].append({ 'name': '3D' })
        case 'myHabiteo - myH Essentiel' | 'myHabiteo - myH Free' | 'Produits Internes - Addons' | 'Produits Internes - Asset Manager' | 'Produits Internes - Backoffice' | 'Produits Internes - BI' | 'Produits Internes - Builder' | 'Produits Internes - Flux' | 'Produits Internes - Renderfarm' | 'Produits Internes - Review' | 'Produits Internes - User3D' | 'Produits Configurables - Configurateur' | 'Produits Configurables - VV Configurable' | 'Produits Configurables - Plan 3D Dynamique' | 'Produits Configurables - Showroom':
            updateDoc['fields']['labels'].append(parse_string(val))
            updateDoc['fields']['components'].append({ 'name': 'Habiteo' })
        case 'Dette Technique':
            updateDoc['fields']['components'].append({ 'name': 'Dette' })

def map_squad(val):
    if val != None:
        match val:
            case 'Smaug':
                return '8c7f58b3-9994-4153-b8c0-fa6ff3b0e1b0'
            case 'Abra' | 'Kiss' | '9':
                return 'b4b6bbe7-78a7-43ba-84d5-3dcb809ea454'
            case 'MIB':
                return 'ba320e01-d881-4451-a4e0-c33fdc6cc35c'
            case 'Kaa':
                return 'f531c67e-66e5-4ad3-bb43-89702c027626'    

def convert_squads(val,vals):
    if val != None:
        return map_squad(val['name'])
    elif vals != None:
        return map_squad(vals[0]['name'])baseUrl = environment["jira_base_url"]
login = environment["username"]
password = environment["user_token"]

query = 'filter = "Tickets"'

fieldNames = ['Squad','Squads','Product','Priority','Labels','Team','Components','Severity','Sévérité','Impact négatif','Impact (migrated)']

fields = requests.get(baseUrl + '/rest/api/2/field',auth=HTTPBasicAuth(login,password))
assert fields.status_code == 200

allFields = fields.json()
fields = {}
for field in allFields:
    if field['name'] in fieldNames:
        if (field['name'] == 'Impact négatif' and field['id'] == 'customfield_10004') or field['name'] != 'Impact négatif':
            fields[field['name']] = field['id']

#startAt = 0
total = 100
pace = 100
count = 0
errors = ''

while count < total:
    issueReq = requests.get(baseUrl + '/rest/api/2/search',auth=HTTPBasicAuth(login,password), params={
            'jql': query,
            'startAt': '0',
            'maxResults': pace,
            'fields': ','.join(list(fields.values())) + ',issuetype',
            'expand': 'names,schema'
            })

    assert issueReq.status_code == 200

    issueResult = issueReq.json()
    
    try:
        total = issueResult['total']
    except KeyError:
        total = 0
    print("Total : " + str(total))

    for issue in issueResult['issues']:
        issueFields = issue['fields']
        updateDoc = {
            "fields": {
                    fields['Components']: [],
                    "labels": ["MigratedFromHabiteo"]
                }
            }
        if issueFields[fields['Priority']] != None:
            updateDoc['fields'][fields['Priority']] = { 'name': convert_priority(issueFields[fields['Priority']]['name']) }
        if issueFields[fields['Severity']] != None:
            updateDoc['fields'][fields['Sévérité']] = convert_severity(issueFields[fields['Severity']]['value'])
        if issueFields[fields['Impact (migrated)']] != None:
            updateDoc['fields'][fields['Impact négatif']] = convert_impact(issueFields[fields['Impact (migrated)']]['value'])
        if issueFields[fields['Product']] != None:
            convert_product(updateDoc,issueFields[fields['Product']]['value'])
        if 'R&D' in issueFields[fields['Labels']]:
            updateDoc['fields'][fields['Components']].append({ 'name': 'R&D' })
        if issueFields[fields['Squads']] != None:
            updateDoc['fields']['labels'].append('MultiSquadsMigration')
        if issueFields['issuetype']['subtask'] == False:
            updateDoc['fields'][fields['Team']] = convert_squads(issueFields[fields['Squad']],issueFields[fields['Squads']])
        
        if 'Sévérité' in updateDoc['fields'] or 'Impact négatif' in updateDoc['fields']:
            print(updateDoc)
            
        respUpdate = requests.put(baseUrl + '/rest/api/2/issue/' + issue['key'],
                auth=HTTPBasicAuth(login,password),
                params={
                    'notifyUsers': 'false'
                },
                headers={'Content-Type':'application/json'},
                json=updateDoc)

        if (respUpdate.status_code > 299):
            print("Failed to update " + issue['key'] + ": " + str(respUpdate.status_code) + " - " + str(respUpdate.json()))
            errorMessages = respUpdate.json()['errorMessages']
            errors += "\nERROR: " + issue['key'] + ": " + ",".join(errorMessages)
        else:
            print(issue['key'] + ' edited')
        time.sleep(0.2)
        count += 1
            
print("Updated " + str(count) + " issues")
print(errors)
        
        

        
    