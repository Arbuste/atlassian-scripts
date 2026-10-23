import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
environment = get_environment("datanumia")

import requests
import time
from requests.auth import HTTPBasicAuthbaseUrl = environment["jira_base_url"]
login = environment["username"]
password = environment["user_token"]

query = 'filter = "Stories avec sous-tâche PI null"'

fieldName = 'PI'

fields = requests.get(baseUrl + '/rest/api/2/field',auth=HTTPBasicAuth(login,password))
assert fields.status_code == 200

allFields = fields.json()

for field in allFields:
    if field['name'] == fieldName:
        sourceField = field
        break

assert sourceField, "No field found with name '${sourceFieldName}'"

sourceType = sourceField['schema']['type']

#startAt = 0
total = 100
pace = 100
count = 0
errors = ''

while total > 0:
    storyReq = requests.get(baseUrl + '/rest/api/2/search',auth=HTTPBasicAuth(login,password), params={
            'jql': query,
            'startAt': '0',
            'maxResults': pace,
            'fields': sourceField['key'] + ',subtasks',
            'expand': 'names,schema'
            })

    assert storyReq.status_code == 200

    time.sleep(2)

    storyResult = storyReq.json()
    
    try:
        total = storyResult['total']
    except KeyError:
        total = 0
    print(str(total))

    for story in storyResult['issues']:
        storyFields = story['fields']
        storySourceFieldValue = storyFields[sourceField['key']]
        
        if not storySourceFieldValue is None:
            updateDoc = {
                'fields': {
                    sourceField['key']: { 'value': storySourceFieldValue['value'] }
                }
            }
            
        try:
            subtasks = story['fields']['subtasks']
        except KeyError:
            continue
            
        for subtask in subtasks:
            print(subtask['key'] + " : " + str(storySourceFieldValue))
            respSubtask = requests.put(baseUrl + '/rest/api/2/issue/' + subtask['key'],
                    auth=HTTPBasicAuth(login,password),
                    params={
                        'notifyUsers': 'false'
                    },
                    headers={'Content-Type':'application/json'},
                    json=updateDoc)
            time.sleep(2)
            if (respSubtask.status_code > 299):
                print("Failed to update " + subtask['key'] + ": " + str(respSubtask.status_code) + " - " + str(respSubtask.json()))
                errorMessages = respSubtask.json()['errorMessages']
                errors += "\nERROR: " + subtask['key'] + ": " + ",".join(errorMessages)
            else:
                print(subtask['key'] + ' edited')
                count += 1
print("Updated " + fieldName + " on " + str(count) + " issues")
print(errors)
