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

roles = env.getAllProjectRoles()
workbook = xlsxwriter.Workbook(folder + r'\Project roles.xlsx')

worksheet = workbook.add_worksheet('Project Roles')
worksheet.write(0,0, "ID")
worksheet.write(0,1, "Name")

i = 1
for role in roles['values']:
    worksheet.write(i,0,str(role['id']))
    worksheet.write(i,1,role['name'])
    i += 1

workbook.close()