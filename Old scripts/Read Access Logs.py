import csv

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\SNCF\Access logs Analysis\Access logs Analysis\Jira 0831\result.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    user = ''
    nbLine=0
    nbLineUser=0
    maxNbLineUser=1
    resultHour=[True for i in range(48)]
    for row in reader:
        if row[0] != user:
            user=row[0]
            if nbLineUser > maxNbLineUser:
                maxNbLineUser=nbLineUser
            nbLineUser=0
        nbLineUser+=1
    maxNbLineUser = 4
    print("Nb de journées max : " + str(maxNbLineUser))
    csvfile.seek(0)
    for row in reader:
        total=0
        if nbLine==0:
            nbLine+=1
            continue
        if row[0] != user:
            if True in resultHour and nbLine > 1 and nbLineUser==maxNbLineUser:
                print(user + ' bot créneau')
            resultHour=[True for i in range(48)]
            user=row[0]
            nbLineUser=0
        for i in range(2,49):
            j=i-2
            resultHour[j]=(resultHour[j]==True and row[j] != '0' and row[j-1] == '0' and row[j+1] == '0')
            if row[i] != '0':
                total += 1
        if row[49] != '0' and total == 47:
                print(user + ' bot total')
        resultHour[47]=(resultHour[47]==True and row[49] != '0' and row[48]=='0')
        nbLineUser+=1
        nbLine+=1