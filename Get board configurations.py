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

boards = env.getBoards()

workbook = xlsxwriter.Workbook(folder + r'\Boards.xlsx')
worksheet = workbook.add_worksheet('Boards')
worksheet.write(0,0, "Board ID")
worksheet.write(0,1, "Board Name")
worksheet.write(0,2, "Location")
worksheet.write(0,3, "Type")
worksheet.write(0,4, "Estimation field")

i = 1
for board in boards:
    boardConf = env.getBoardConfiguration(board['id'])
    print(str(boardConf))
    worksheet.write(i,0,boardConf['id'])
    worksheet.write(i,1,boardConf['name'])
    if 'location' in boardConf:
        if boardConf['location']['type'] == 'project':
            worksheet.write(i,2,str(boardConf['location']['name']))
        elif boardConf['location']['type'] == 'user':
            worksheet.write(i,2,'User')
    else:
        worksheet.write(i,2,'No location')
    worksheet.write(i,3,boardConf['type'])
    if 'estimation' in boardConf:
        estimation = boardConf['estimation']
        if estimation['type'] == 'none':
            worksheet.write(i,4,'No estimation')
        elif estimation['type'] == 'field':
            worksheet.write(i,4,'Field : ' + estimation['field']['displayName'])
        else:
            worksheet.write(i,4,estimation['type'])
    else:
        worksheet.write(i,4,'No estimation')
    i += 1

workbook.close()