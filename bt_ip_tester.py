#!/usr/bin/python
import bt_ips
#import pymongo
#import subprocess
#import sys

#db = pymongo.mongo_client.MongoClient().bt_ips

#for reply in db.ips.find({'countryName':'INDIA'}):
#    print (reply)

#for IP in bt_ips.traceroute('131.111.8.42'):
#    print(bt_ips.IPInfoDBLookup(IP))
#for entry in bt_ips.transmissionList():
#    print(bt_ips.IPstrip(entry))
print(bt_ips.tracerouteWorker())

#import subprocess
#proc = subprocess.Popen('traceroute 131.111.8.42',
#                       shell=True,
#                       stdout=subprocess.PIPE,
#                       )
#while proc.poll() is None:
#    output = proc.stdout.readline()
#    print (output)
