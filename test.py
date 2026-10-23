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
folder = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\TME\Scripts'

workbook.close()