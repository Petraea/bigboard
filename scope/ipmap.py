import pygame
import random
import math
import json
import urllib
import re
import bt_ips
import multiprocessing

user_agents = [
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
    'Opera/9.25 (Windows NT 5.1; U; en)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
    'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
    'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9'
]
class URLOpener(urllib.FancyURLopener):
        version = random.choice(user_agents)
urlopen = URLOpener().open

#Set up a service that constantly hunts for IPs
#Pipe that information into a renderer

def display(screen):
    drawComputersWithOrthodromes(screen)
#    drawCities(screen)
    #drawWind(screen) #Costly and expensive to run. Needs to be deprioritised.

def drawBackground(screen):
    drawMap(screen) #Simple for now, but can be upgraded here.
    drawCities(screen)
    drawMyIP(screen)
    
def drawMap(screen):
    file = open('scope/WorldCountries.csv','r')
    lines = file.readlines()
    file.close()
    colour = (0,0,0)
    oldname = ''
    for line in lines:
        data = line.split(',')
        pointlist = []
        name = data[0]
        cn = data[1]
        for datum in data[2:]:
            coord = datum.split(':')
            coords = (coord[1],coord[0]) #Why are the map coords reversed?
            pointlist.append(mapTransform(coords,screen))
        if name == oldname:
            pygame.draw.polygon(screen,colour,pointlist,1)
        else:
            oldname = name
            colour = (120+random.randint(-20,20),30+random.randint(-20,20),30+random.randint(-20,20))
            pygame.draw.polygon(screen,colour,pointlist,1)

def mapTransform(latlon,screen):
    rect = screen.get_rect()
#    print (latlong)
#    x = 3*float(latlong[0])/(2*math.pi)*(math.pi**2/3-float(latlong[1])**2)**0.5 # Kavrayskiy
    x = float(latlon[1])
    y = float(latlon[0])
    xout = (180+x)/360*rect.width
    yout = (90-y)/180*rect.height
    return (int(xout),int(yout))

def drawCities(screen):
    file = open('scope/agglomoutput.csv','r')
    lines = file.readlines()
    file.close()
    oldname = ''
    for line in lines:
        colour = pygame.Color(150+random.randint(-10,10),140+random.randint(-10,10),random.randint(0,40),240)
        data = line.split(',')
        pointlist = []
        name = data[1]
        country = data[2]
        size = data[3]
        coords = (data[4],data[5])
        mag = int(math.sqrt(int(size)/1000000))
        pygame.draw.circle(screen, colour, mapTransform(coords,screen),mag)

def drawAirports(screen):
    file = open('scope/airports.json','r')
    string = file.read()
    file.close()
    jsondata = json.loads(string)
    for airport in jsondata:
        coords = [airport['lat'],airport['lon']]
        pygame.draw.circle(screen, (10,50,250), mapTransform(coords,screen),1)

def drawMyIP(screen):
    IPdata = bt_ips.IPInfoDBLookup(bt_ips.getMyIP())
    coords = [IPdata['latitude'],IPdata['longitude']]
    pygame.draw.circle(screen, (255,255,255), mapTransform(coords,screen),5,2)
        
def drawComputers(screen):
    IPlist = bt_ips.activeIPs(passive=True) #VERY slow function
    for IPdata in IPlist:
        coords = [IPdata['latitude'],IPdata['longitude']]
        pygame.draw.circle(screen, (50,250,10), mapTransform(coords,screen),3)

def drawComputersWithOrthodromes(screen,origin=None):
    IPlist = bt_ips.activeIPs(passive=True) #VERY slow function
    if origin is None:
        IPdata = bt_ips.IPInfoDBLookup(bt_ips.getMyIP())
        origin = [IPdata['latitude'],IPdata['longitude']]    
    for IPdata in IPlist:
        coords = [IPdata['latitude'],IPdata['longitude']]
        pygame.draw.circle(screen, (50,250,10,240), mapTransform(coords,screen),3)
        drawOrthodrome(screen, origin, coords)
    
def drawWind(screen):
    file = open('scope/airports.json','r')
    string = file.read()
    file.close()
    jsondata = json.loads(string)
    for airport in jsondata:
        dir = 0
        speed = 0
        page = urlopen('http://www.aviationweather.gov/adds/tafs/?station_ids='+airport['icao']).read()
        regex = re.search('(\d{5,6})(KT|MPS|MPH)', page)
        if regex is not None:
#            print (regex.groups())
            wind = regex.groups()[0]
            multiplier = 1
            if regex.groups()[-1] == 'MPS':
                multiplier = 1.9438
            if regex.groups()[-1] == 'MPH':
                multiplier = 0.8689
            dir = math.pi*int(wind[0:2])/180
            speed = int(wind[3:])*multiplier
        coords = [airport['lat'],airport['lon']]
        endlon = math.cos(dir)*speed/10+float(airport['lon'])
        endlat = math.sin(dir)*speed/10+float(airport['lat'])
        pygame.draw.line(screen, (150,150,200), mapTransform(coords,screen),mapTransform([endlat,endlon],screen))
        pygame.display.update()

def sphDist(coords1, coords2):
    lat1 = math.radians(float(coords1[0]))
    lat2 = math.radians(float(coords2[0]))
    lon1 = math.radians(float(coords1[1]))
    lon2 = math.radians(float(coords2[1]))
    dLat = (lat2-lat1)
    dLon = (lon2-lon1)
    a = math.sin(dLat/2)*math.sin(dLat/2)+math.sin(dLon/2)*math.sin(dLon/2)*math.cos(lat1)*math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return c # A radian length of arc between points

def sphBisectArc(coords1, coords2):
    lat1 = math.radians(float(coords1[0]))
    lat2 = math.radians(float(coords2[0]))
    lon1 = math.radians(float(coords1[1]))
    lon2 = math.radians(float(coords2[1]))
    dLat = (lat2-lat1)
    dLon = (lon2-lon1)
    Bx = math.cos(lat2)*math.cos(dLon)
    By = math.cos(lat2)*math.sin(dLon)
    midpointlat = math.atan2(math.sin(lat1)+math.sin(lat2),math.sqrt((math.cos(lat1)+Bx)*(math.cos(lat1)+Bx)+By*By ) );
    midpointlon = lon1 + math.atan2(By, math.cos(lat1) + Bx)
#    print (math.degrees(midpointlat), math.degrees(midpointlon))
    return (math.degrees(midpointlat), math.degrees(midpointlon))

def sphBearing(coords1, coords2): #Free function!
    lat1 = math.radians(float(coords1[0]))
    lat2 = math.radians(float(coords2[0]))
    lon1 = math.radians(float(coords1[1]))
    lon2 = math.radians(float(coords2[1]))
    dLat = (lat2-lat1)
    dLon = (lon2-lon1)
    y = math.sin(dLon)*math.cos(lat2)
    x = math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(dLon)
    return math.atan2(y, x) #In radians, from north.

def orthodrome(coords1, coords2):
    linepath = [coords1,coords2]
    numberofsegments = int(sphDist(linepath[0],linepath[1])/(math.pi/180)) #Draw in degree chunks at worst    
    while len(linepath)-1<numberofsegments:
        linepathcopy = []
        for pos, coords in enumerate(linepath[:-1]):
            nextcoords = linepath[pos+1]
            linepathcopy.append(coords)
            linepathcopy.append(sphBisectArc(coords, nextcoords))
        linepathcopy.append(linepath[-1])
        linepath = linepathcopy[:]
    return linepath #Will always return a path with n**2+1 points

#For standpoint lat1, lon1 and forepoint lat2, lon2
def drawOrthodrome(surface, coords1, coords2, colour=(255,255,255),closed=False,width=1):
    pointlist = [mapTransform(x, surface) for x in orthodrome(coords1,coords2)]
    pygame.draw.lines(surface, colour,closed,pointlist,width)


def aIPManager():
    while True: #Spin off one process over and over.
        p = multiprocessing.Process(target=bt_ips.activeIPWorker())
        p.start()
        p.join()


def ManagerManager():
    m = multiprocessing.Process(target=aIPManager)
    m.start() #Spin off the aIP manager
    return m.is_alive()

ManagerManager()
