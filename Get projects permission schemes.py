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

permissionSchemes = env.getPermissionSchemes()
projects = env.getProjects()

workbook = xlsxwriter.Workbook(folder + r'\Projects - Permission Schemes.xlsx')

worksheet = workbook.add_worksheet('Permission Schemes')
worksheet.write(0,0, "ID")
worksheet.write(0,1, "Name")

i = 1
for ps in permissionSchemes:
    worksheet.write(i,0,str(ps['id']))
    worksheet.write(i,1,ps['name'])
    i += 1

worksheet = workbook.add_worksheet('Projects')
worksheet.write(0,0, "ID")
worksheet.write(0,1, "Key")
worksheet.write(0,2, "Name")
worksheet.write(0,3, "Permission Scheme ID")

i = 1
for project in projects:
    worksheet.write(i,0,str(project['id']))
    worksheet.write(i,1,project['key'])
    worksheet.write(i,2,project['name'])
    projectPs = env.getProjectPermissionScheme(project['id'])
    if projectPs:
        worksheet.write(i,3,str(projectPs['id']))
    i += 1

workbook.close()