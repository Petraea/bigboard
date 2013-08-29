import subprocess
import re
import time
import urllib
import json
import os
import pymongo

with open('ipinfodbkey','r') as f:
    IPINFODBKEY = f.read()
TRANSMISSION_IP='192.168.2.251'
db = pymongo.mongo_client.MongoClient()

#def sqliteToMongo():
#    conn = sqlite3.connect(IP_DB)
#    c = conn.cursor()
#    db = pymongo.mongo_client.MongoClient().bt_ips
#    c.execute('SELECT * FROM myip')
#    rows = c.fetchall()
#    for row in rows:
#        print (row)
#        localIp, date = row
#        db.myip.insert({'localIp':localIp,'date':date})
#    c.execute('SELECT * FROM traceroutes')
#    row = c.fetchone()
#    while row is not None:
#        print (row)
#        localIp, remoteIp, hopList = row
#        hl = hopList.split(':')
#        db.traceroutes.insert({'localIp':localIp,'remoteIp':remoteIp,'hopList':hl})
#        row = c.fetchone()
#    c.execute('SELECT * FROM ips')
#    row = c.fetchone()
#    while row is not None:
#        print (row)
#        statusCode, statusMessage, ipAddress, countryCode, countryName, regionName, cityName, zipCode, latitude, longitude, timeZone = row
#        db.ips.insert({'statusCode':statusCode, 'statusMessage':statusMessage, 'ipAddress':ipAddress, 'countryCode':countryCode, 'countryName':countryName, 'regionName':regionName, 'cityName':cityName, 'zipCode':zipCode, 'latitude':latitude, 'longitude':longitude, 'timeZone':timeZone})
#        row = c.fetchone()
#    conn.commit()
#    conn.close()
    

def updateIP():
    ipdata = urllib.urlopen('http://api.ipinfodb.com/v3/ip-city/?key='+IPINFODBKEY+'&format=json').read()
    dict = json.loads(ipdata)
    myip=dict['ipAddress']
    docs = db.bt_ips.myip.find().limit(1).sort('date',-1)
    for doc in docs:
        ip = doc['localIp']
    if myip != ip:
        db.bt_ips.myip.insert({'localIp':myip,'date':time.strftime('%M:%H %d-%m-%Y')})
    return ip

def getMyIP():
    docs = db.bt_ips.myip.find().limit(1).sort('date',-1)
    for doc in docs:
        ip = doc['localIp']
    return ip

def transmissionList():
    pop = subprocess.Popen(['transmission-remote',TRANSMISSION_IP,'-l'], stdout=subprocess.PIPE)
    out = pop.communicate()[0]
    lines = out.split('\n')
    TRlist = []
    keys = [x.lstrip() for x in re.split('  +',lines[0])]
    for line in lines[1:-2]:
        values = [x.lstrip() for x in re.split('  +',line.lstrip())]
        TRlist.append(dict(zip(keys,values)))
    return TRlist

def IPstrip(t):
    pop = subprocess.Popen(['transmission-remote',TRANSMISSION_IP,'-t',t['ID'],'-ip'], stdout=subprocess.PIPE)
    out = pop.communicate()[0]
    lines = out.split('\n')
    IPlist = []
    keys = [x.lstrip() for x in re.split('  +',lines[0])]
    for line in lines[1:]:
        values = [x.lstrip() for x in re.split('  +',line.lstrip())]
        IPlist.append(dict(zip(keys,values)))
    return IPlist

def traceroute(IP,myIP=getMyIP(),passive=False):
    IPlist = []
    db.start_request()
    doc = db.bt_ips.traceroutes.find_one({'localIp':myIP,'remoteIp':IP})
    if doc is not None:
        IPlist = doc['hopList']
    elif passive == False:
        IPList = doTraceroute(IP)
        doc = db.bt_ips.traceroutes.find_one({'localIp':myIP,'remoteIp':IP})
        if doc is None:
            db.bt_ips.traceroutes.insert({'localIp':myIP,'remoteIp':IP,'hopList':IPList})
    db.end_request()
    return IPlist

def doTraceroute(IP):
    IPlist = []
    pop = subprocess.Popen(['traceroute','-M','udp',IP], stdout=subprocess.PIPE)
    out = pop.communicate()[0] #Halting...
    lines = out.split('\n')
    for line in lines[1:]:
        match = re.search('\(\d+\.\d+\.\d+\.\d+\)',line)
        if match:
            string = match.group(0)[1:-1]
            IPlist.append(string)
    return IPList

    
def IPInfoDBLookup(IP):
    db.start_request()
    doc = db.bt_ips.ips.find_one({'ipAddress':IP})
    if doc is None:
        ipdata = urllib.urlopen('http://api.ipinfodb.com/v3/ip-city/?key='+IPINFODBKEY+'&ip='+IP+'&format=json').read()
        doc = json.loads(ipdata)
        db.bt_ips.ips.insert(doc)
    db.end_request()
    return doc

def activeIPs(passive=False):
    db.start_request()
    activeIP = []
    if passive==False:
        entries = transmissionList()
        for entry in entries:
            IPs = IPstrip(entry)
            for IP in IPs:
                if not IP['Address'] == '':
                    activeIP.append(IPInfoDBLookup(IP['Address']))
    else:
        docs = db.bt_ips.aIPCache.find().limit(1).sort('$natural',-1) #Find the youngest (race condition catch)
        for doc in docs:
            activeIP = doc['activeIPs']
    db.end_request()
    return activeIP

def activeIPWorker():
    print('Starting AIP Worker.')
    myIP = getMyIP()
    entries = activeIPs()
    db.bt_ips.aIPCache.insert({'activeIPs':entries}) #put in a new entry...
    count = db.bt_ips.aIPCache.count()
    docs = db.bt_ips.aIPCache.find().limit(count-1).sort('$natural',1) 
    for doc in docs: #Remove everthing but the youngest.
        db.bt_ips.aIPCache.remove({'_id':doc['_id']})
    print('Finished AIP Worker.')
#    return True

def tracerouteWorker():
    print('Starting TR Worker.')
    myIP = getMyIP()
    docs = db.bt_ips.aIPCache.find().limit(1).sort('$natural',-1) #Find the youngest (race condition catch)
    for i in docs:
        doc = i
    entries = doc['activeIPs']
    for entry in entries:
        doc = db.bt_ips.traceroutes.find_one({'localIp':myIP,'remoteIp':entry['ipAddress']})
        if doc is not None:
            IPlist = doTraceroute(entry['ipAddress'])
            db.bt_ips.traceroutes.insert({'localIp':myIP,'remoteIp':IP,'hopList':IPList})
    print('Finished TR Worker.')
    return True
