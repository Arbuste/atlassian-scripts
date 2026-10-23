import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
environment = get_environment("habiteo")

import requests
import time
from requests.auth import HTTPBasicAuthbaseUrl = environment["jira_base_url"]
login = environment["username"]
password = environment["user_token"]

query = 'filter = "Filtre issue keys"'

destFieldName = 'Issue Key Copy'

fields = requests.get(baseUrl + '/rest/api/2/field',auth=HTTPBasicAuth(login,password))
assert fields.status_code == 200

allFields = fields.json()

for field in allFields:
    if field['name'] == destFieldName:
        destField = field

assert destField, "No dest field found with name '${destFieldName}'"

#startAt = 0
total = 100
pace = 100
count = 0
errors = ''

while total > 0:
    issuesReq = requests.get(baseUrl + '/rest/api/2/search',auth=HTTPBasicAuth(login,password), params={
            'jql': query,
            'startAt': '0',
            'maxResults': pace,
            'expand': 'names,schema'
            })

    assert issuesReq.status_code == 200

    time.sleep(2)

    issuesResult = issuesReq.json()
    
    try:
        total = issuesResult['total']
    except KeyError:
        total = 0
    print(str(total))

    for issue in issuesResult['issues']:
        #issueFields = issue['fields']
        #issueSourceFieldValue = issueFields[sourceField['key']]
        
        #if not issueSourceFieldValue is None:
        updateDoc = {
            'fields': {
                destField['key']: issue['key']
            }
        }
        
        print(issue['key'])
        respIssue = requests.put(baseUrl + '/rest/api/2/issue/' + issue['key'],
                auth=HTTPBasicAuth(login,password),
                params={
                    'notifyUsers': 'false'
                },
                headers={'Content-Type':'application/json'},
                json=updateDoc)
        time.sleep(0.5)
        if (respIssue.status_code > 299):
            print("Failed to update " + issue['key'] + ": " + str(respIssue.status_code) + " - " + str(respIssue.json()))
            errorMessages = respIssue.json()['errorMessages']
            errors += "\nERROR: " + issue['key'] + ": " + ",".join(errorMessages)
        else:
            print(issue['key'] + ' edited')
            count += 1
print("Updated " + destFieldName + " on " + str(count) + " issues")
print(errors)

