import time
import multiprocessing
import web
import bt_ips
import os
import json

PAGE_FOLDER = 'ipfront/'
PAGE_NAME = 'map.htm'
WORKER_FREQ=60
SLOW_FREQ=3000

urls = (
'^/$','Map',
'^/aip/?$','aIP',
'^/iip/?$','iIP',
'^/(.*)$','Other'
)


class Other:
    def GET(self,name):
        if os.path.exists(os.path.join(PAGE_FOLDER,name)):
            page_file = open(os.path.join(PAGE_FOLDER,name),'r')
            page = page_file.read()
            page_file.close()
            return page
        return '[{\"message\":\"ERROR!!!\"}]'

class Map:
    def GET(self):
        page_file = open(os.path.join(PAGE_FOLDER,PAGE_NAME),'r')
        page = page_file.read()
        page_file.close()
        web.header('Content-Type', 'text/html')
        return page
        

class aIP:
    def GET(self):
        print('Getting myIP')
        myIP = json.loads(bt_ips.MyIPJSON())
        print('Getting AIPs')
        activeIPs = json.loads(bt_ips.ActiveIPsJSON())
        
        return json.dumps(dict(myIP, **activeIPs),indent=4)

class iIP:
    def GET(self):
        print('Getting myIP')
        myIP = json.loads(bt_ips.MyIPJSON())
        print('Getting IIPs')
        inactiveIPs = json.loads(bt_ips.InactiveIPsJSON())
        return json.dumps(dict(myIP, **inactiveIPs),indent=4)
        
def MultiManager():
    while True:
        worker = multiprocessing.Process(target=bt_ips.MultiWorker)
        worker.start()
        time.sleep(WORKER_FREQ)

def SlowerManager():
    while True:
        worker = multiprocessing.Process(target=bt_ips.UpdateIIPCache)
        worker.start()
#        worker = multiprocessing.Process(target=bt_ips.UpdateIP)
#        worker.start()
        time.sleep(SLOW_FREQ)
        
        
if __name__ == "__main__":
    manager = multiprocessing.Process(target=MultiManager)
    manager.start()
    slowmanager = multiprocessing.Process(target=SlowerManager)
    slowmanager.start()
    app = web.application(urls,globals())
    app.run()
    
#my_IP=GetMyIP()
#entries = TransmissionList()
#activeIP = []
#for entry in entries:
#    activeIP = list(set(activeIP)|set(IPstrip(entry)))

    
#jsondict = {'activeIPs',IPstrip(x)}
#print (jsondict)
#for entry in entries:
#    print(entry['ID']+': '+entry['Name'])
#    for IP in IPstrip(entry):
        # if IP['Address'] is not '':
            # details = IPInfoDBLookup(IP['Address'])
            # print('Target: '+IP['Address']+' in '+details['cityName']+','+details['countryName'])
            # route = TraceRoute(my_IP, IP['Address'])
            # # for i, mid in enumerate(route):
                # mid_details = IPInfoDBLookup(mid)
                # print(str(i)+': '+mid+' in '+mid_details['cityName']+','+mid_details['countryName'])

