from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment
from Utilities.OrgEnvironment import OrgEnvironment
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
orgId = environment["org_id"]
orgToken = environment["org_token"]
folder = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\TME\Scripts'

env = JiraEnvironment(baseUrl,user,token,folder)
org = OrgEnvironment(orgId,orgToken,folder)


groups = org.getGroups()
projects = env.getProjects()
permissionSchemes = env.getPermissionSchemes({'expand': 'permissions'})

for permissionScheme in permissionSchemes:
    if 'permissions' in permissionScheme:
        permissionScheme['groups'] = [permission['holder']['parameter'] for permission in permissionScheme['permissions'] if permission['holder']['type'] == 'group']
        permissionScheme['groups'] = list(dict.fromkeys(permissionScheme['groups']))
        print(str(permissionScheme['groups']))
    else:
        permissionScheme['groups'] = []

workbook = xlsxwriter.Workbook(folder + r'\Groups.xlsx')

worksheet = workbook.add_worksheet('Group')
worksheet.write(0,0, "Group Name")
worksheet.write(0,1, "Project ID")
worksheet.write(0,2, "Project Key")
worksheet.write(0,3, "Project Name")

i = 1
for project in projects:
    projectScheme = env.getProjectPermissionScheme(project['id'])
    if 'id' in projectScheme:
        project['groups'] = [group for permissionScheme in permissionSchemes if projectScheme['id'] == permissionScheme['id'] for group in permissionScheme['groups']]
        print(str(project['groups']))
    if 'groups' in project:
        for group in project['groups']:
            print(str(group))
            worksheet.write(i,0,str(group))
            worksheet.write(i,1,project['id'])
            worksheet.write(i,2,project['key'])
            worksheet.write(i,3,project['name'])
            i += 1

workbook.close()