import subprocess
import re
import time
import urllib
import json
import sqlite3
import os
import pymongo

IPINFODBKEY = '58cf0e1cd74e0b7b11c6ed72f5d3ef7781262cba1f8f8e6533bdab9ecaf1683b'
IP_DB='BT_IPs.db'
TRANSMISSION_IP='192.168.2.251'

def createNewDB():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ips(statusCode text, statusMessage text, ipAddress text,
    countryCode text, countryName text, regionName text, cityName text, zipCode text,
    latitude text, longitude text, timeZone text)''')
    c.execute('CREATE TABLE IF NOT EXISTS traceroutes(localIp text, remoteIp text, hopList text)')
    c.execute('CREATE TABLE IF NOT EXISTS myip(localIp text, date text)')
    c.execute('CREATE TABLE IF NOT EXISTS myipcache(page text)')
    c.execute('CREATE TABLE IF NOT EXISTS aipcache(page text)')
    c.execute('CREATE TABLE IF NOT EXISTS iipcache(page text)')
    conn.commit()
    conn.close()

def sqliteToMongo():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    db = pymongo.mongo_client.MongoClient().bt_ips
#    c.execute('SELECT * FROM myip')
#    rows = c.fetchall()
#    for row in rows:
#        print (row)
#        localIp, date = row
#        db.myip.insert({'localIp':localIp,'date':date})
    c.execute('SELECT * FROM traceroutes')
    row = c.fetchone()
    while row is not None:
        print (row)
        localIp, remoteIp, hopList = row
        hl = hopList.split(':')
        db.traceroutes.insert({'localIp':localIp,'remoteIp':remoteIp,'hopList':hl})
        row = c.fetchone()
    c.execute('SELECT * FROM ips')
    row = c.fetchone()
    while row is not None:
        print (row)
        statusCode, statusMessage, ipAddress, countryCode, countryName, regionName, cityName, zipCode, latitude, longitude, timeZone = row
        db.ips.insert({'statusCode':statusCode, 'statusMessage':statusMessage, 'ipAddress':ipAddress, 'countryCode':countryCode, 'countryName':countryName, 'regionName':regionName, 'cityName':cityName, 'zipCode':zipCode, 'latitude':latitude, 'longitude':longitude, 'timeZone':timeZone})
        row = c.fetchone()
    conn.commit()
    conn.close()
    

def updateIP():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    ipdata = urllib.urlopen('http://api.ipinfodb.com/v3/ip-city/?key='+IPINFODBKEY+'&format=json').read()
    dict = json.loads(ipdata)
    myip=dict['ipAddress']
    c.execute('INSERT INTO myip VALUES (?,?)', (myip, time.strftime('%M:%H %d-%m-%Y')))
    conn.commit()
    conn.close()
    return True

def getMyIP():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM myip')
    rows = c.fetchall()
    conn.commit()
    conn.close()
    rows.sort(key=lambda tup: tup[1], reverse=True)
    currentip, timestamp = rows[0]    
    return currentip    

#for each id in transmission-remote -l:
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
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM traceroutes WHERE localIp=? AND remoteIp=?',(myIP,IP))
    dbentry = c.fetchone()
    if dbentry is not None:
        routestring = ''
        li, ri, routestring = dbentry
        IPlist = routestring.split(':')
    elif passive == False:
        pop = subprocess.Popen(['traceroute','-M','udp',IP], stdout=subprocess.PIPE)
        out = pop.communicate()[0]
        lines = out.split('\n')
        for line in lines[1:]:
            match = re.search('\(\d+\.\d+\.\d+\.\d+\)',line)
            if match:
                string = match.group(0)[1:-1]
                IPlist.append(string)
        routestring = ':'.join(IPlist)
        c.execute('SELECT * FROM traceroutes WHERE localIp=? AND remoteIp=?',(myIP,IP))
        dbentry = c.fetchone()
        if dbentry is None:
            c.execute('INSERT INTO traceroutes VALUES (?,?,?)', (myIP,IP,routestring))
    conn.commit()
    conn.close()
    return IPlist
    
def IPInfoDBLookup(IP):
    dict = {}
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM ips WHERE ipAddress=?',(IP,))
    dbentry = c.fetchone()
    if dbentry is not None:
        dict['statusCode'],dict['statusMessage'], dict['ipAddress'], dict['countryCode'], dict['countryName'],dict['regionName'], dict['cityName'], dict['zipCode'], dict['latitude'], dict['longitude'], dict['timeZone'] = dbentry
    else:
        ipdata = urllib.urlopen('http://api.ipinfodb.com/v3/ip-city/?key='+IPINFODBKEY+'&ip='+IP+'&format=json').read()
        dict = json.loads(ipdata)
        to_db = (dict['statusCode'],dict['statusMessage'], dict['ipAddress'], dict['countryCode'], dict['countryName'],dict['regionName'], dict['cityName'], dict['zipCode'], dict['latitude'], dict['longitude'], dict['timeZone'])
        c.execute('INSERT INTO ips VALUES (?,?,?,?,?,?,?,?,?,?,?)', to_db)
    conn.commit()
    conn.close()
    return dict

def myIPJSON():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM myipcache')
    dbentry = c.fetchone()
    conn.close()
    return dbentry[0]

def activeIPs():
    entries = transmissionList()
    activeIP = []
    for entry in entries:
        IPs = IPstrip(entry)
        for IP in IPs:
            if not IP['Address'] == '':
                activeIP.append(IPInfoDBLookup(IP['Address']))
    return activeIP

def activeIPsJSON():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM aipcache')
    dbentry = c.fetchone()
    conn.close()
    return dbentry[0]
    
    
def inactiveIPs(activeip=activeIPs(), myIP=getMyIP()):
    inactiveip = []
    ActiveIPs = [x['ipAddress'] for x in activeip]
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM traceroutes WHERE localIp=? AND remoteIP NOT IN (?)',(myIP,','.join(ActiveIPs)))
    dbentries = c.fetchall()
    for dbentry in dbentries:
        localip, remoteip, path = dbentry
        inactiveip.append(IPInfoDBLookup(remoteip))
    conn.close()
    return inactiveip

def inactiveIPsJSON():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM iipcache')
    dbentry = c.fetchone()
    conn.close()
    return dbentry[0]
    
    
def updateIIPCache():
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    myIP = GetMyIP()
    entries = transmissionList()
    activeIP = []
    for entry in entries:
        IPs = IPstrip(entry)
        for IP in IPs:
            if not IP['Address'] == '':
                activeIP.append(IPInfoDBLookup(IP['Address']))
    inactiveIP = []
    c.execute('SELECT * FROM traceroutes WHERE localIp=? AND remoteIP NOT IN (?)',(myIP,','.join([x['ipAddress'] for x in activeIP])))
    dbentries = c.fetchall()
    for dbentry in dbentries:
        localip, remoteip, path = dbentry
        inactiveIP.append(IPInfoDBLookup(remoteip))
    c.execute('DELETE FROM iipcache')
    c.execute('INSERT INTO iipcache VALUES (?)', (json.dumps({'inactiveIPs':inactiveIP}, indent=4),))
    conn.commit()    
    conn.close()
    
    
def multiWorker():
    print('Starting Worker.')
    myIP = getMyIP()
    entries = transmissionList()
    conn = sqlite3.connect(IP_DB)
    c = conn.cursor()
    c.execute('DELETE FROM myipcache')
    c.execute('INSERT INTO myipcache VALUES (?)', (json.dumps({'myIP':IPInfoDBLookup(myIP)}, indent=4),))
    conn.commit()
    activeIP = []
    for entry in entries:
        IPs = IPstrip(entry)
        for IP in IPs:
            if not IP['Address'] == '':
                activeIP.append(IPInfoDBLookup(IP['Address']))
    for i, IP in enumerate(activeIP):
        print('Tracing '+IP['ipAddress']+'... ('+str(len(activeIP)-i)+' remaining)')
        IPlist = traceroute(IP['ipAddress'],myIP)#passive=true
        IP['hops'] = [IPInfoDBLookup(x) for x in IPlist]
    c.execute('DELETE FROM aipcache')
    c.execute('INSERT INTO aipcache VALUES (?)', (json.dumps({'activeIPs':activeIP}, indent=4),))
    conn.commit()
    print('Finished Worker.')
    conn.close()
    return True
    
#createNewDB()
