import csv

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\SNCF\Access logs Analysis\Access logs Analysis\Jira 0831\result - Copie.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    user = ''
    nbLine=0
    moyennes=[]
    for row in reader:
        total=0
        if nbLine==0:
            nbLine+=1
            continue
        if nbLine==1:
            for i in range(2,50):
                moyennes.append(row[i])
            nbLine+=1
            continue
        if row[0] != user:
            user=row[0]
            nbLineUser=0
        for i in range(2,50):
            total+=abs(float(row[i])-float(moyennes[i-2]))
        if total > 10000:
            print(user + ' ' + str(total))
        nbLine+=1
