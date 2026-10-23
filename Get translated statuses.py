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

# Environment configuration
environment = get_environment("open_groupe_sandbox")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
folder = r'./Files'

env = JiraEnvironment(baseUrl,user,token,folder)

statuses = env.getAllStatuses()
workbook = xlsxwriter.Workbook(folder + r'\Translated statuses.xlsx')

worksheet = workbook.add_worksheet('Statuses')
worksheet.write(0,0, "ID")
worksheet.write(0,1, "Name")
worksheet.write(0,2, "Translated Name")

i = 1
for status in statuses:
    if (status['untranslatedName'] != status['name']):
        worksheet.write(i,0,str(status['id']))
        worksheet.write(i,1,status['untranslatedName'])
        worksheet.write(i,2,status['name'])
        i += 1

workbook.close()