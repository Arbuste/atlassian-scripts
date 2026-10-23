import requests
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from environment_config import get_environment
environment = get_environment("open_groupe_preprod_boards", environment_type="data_center")
token = environment["jira_pat"]
baseUrl = environment["jira_base_url"].rstrip("/")

boards = []
startAt = 0
maxResults = 50
isLast = False

while not isLast:
    reqBoards = requests.get(baseUrl + '/rest/agile/1.0/board',headers={'Authorization': 'Bearer ' + token},params={'startAt': startAt, 'maxResults': maxResults})
    if reqBoards and reqBoards.status_code == 200:
        respBoards = reqBoards.json()
        boards.extend(respBoards['values'])
        isLast = respBoards['isLast']
        startAt += maxResults
        time.sleep(1)
    else:
        print('Error getting boards: ' + str(reqBoards))
        print('Headers: ' + str(reqBoards.headers))
        print('Response: ' + str(reqBoards.text))
        break

print (str(boards))
