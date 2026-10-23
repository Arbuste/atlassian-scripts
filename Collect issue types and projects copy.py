from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment
from Utilities.OrgEnvironment import OrgEnvironment
from Utilities.Utilities import SafeDict
import json
import math
import csv
import xlsxwriter
from datetime import datetime
import collections

# TME
environment = get_environment("tme")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
folder = r'./Files'

env = JiraEnvironment(baseUrl,user,token,folder)


issueTypeSchemes = env.getIssueTypeSchemes({'expand': 'issueTypes,projects'})
res = []

print(str(len(issueTypeSchemes)))

for issueTypeScheme in issueTypeSchemes:
    print(str(issueTypeScheme))
    print('Issue types:')
    print(str(issueTypeScheme['issueTypes']))
    issueTypeNames = [val['name'] for val in issueTypeScheme['issueTypes']['values']]
    found = False
    for item in res:
        if collections.Counter(issueTypeNames) == collections.Counter(item['issueTypes']):
            found = True
            if 'projects' in issueTypeScheme:
                item['projects'] += issueTypeScheme['projects']['values']
                break
    if not found:
        res.append({'issueTypes':issueTypeNames,'projects': issueTypeScheme['projects']['values']})

workbook = xlsxwriter.Workbook(folder + r'\Issue Type Schemes.xlsx')

worksheet = workbook.add_worksheet('Issue Types')
worksheet.write(0,0, "Issue Types")
worksheet.write(0,1, "Project ID")
worksheet.write(0,2, "Project Key")
worksheet.write(0,3, "Project Name")

i = 1
for item in res:
    for project in item['projects']:
        worksheet.write(i,0, str(item['issueTypes']))
        worksheet.write(i,1, project['id'])
        worksheet.write(i,2, project['key'])
        worksheet.write(i,3, project['name'])
        i += 1

workbook.close()