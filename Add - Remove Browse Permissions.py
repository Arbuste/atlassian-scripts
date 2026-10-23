from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment
from Utilities.Utilities import SafeDict
import json
import math
import csv
import xlsxwriter
from datetime import datetime

# TME
environment = get_environment("tme")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
folder = r'./Files'

env = JiraEnvironment(baseUrl,user,token,folder)

action = 'delete'
accountId = '5cb7202121109e0e4d3c6986'

permissionSchemes = env.getPermissionSchemes({'expand': 'permissions'})
print(str(len(permissionSchemes)))
for permissionScheme in permissionSchemes:
    if action == 'grant':
        env.grantBrowsePermission(accountId,permissionScheme['id'])
    elif action == 'delete':
        browsePermission = [permission for permission in permissionScheme['permissions'] if permission['permission'] == 'BROWSE_PROJECTS' and permission['holder']['type'] == 'user' and 'value' in permission['holder'] and permission['holder']['value'] == accountId]
        if browsePermission:
            env.deletePermission(permissionScheme['id'],browsePermission[0]['id'])