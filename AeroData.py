import requests
import os
import zipfile
import shutil
import Airport as a
import Runway as r
import Notam as no
from datetime import datetime, timedelta
from geopy.units import degrees
from pyproj import Geod
import heapq

class AeroData:
    def __init__(self):
        full_path = os.path.realpath(__file__)
        path,fn=os.path.split(full_path)
        filename = path+"/data/APT.txt"
        self.update_data()
        self.apts = self.parseAirports(filename)
        shutil.rmtree(path+"/data")

    def generateURL(self):
        s = "10/08/2020"
        start_date = datetime.strptime(s,"%m/%d/%Y")
        current_end_date = start_date+timedelta(days=28)
        t = datetime.today()

        while t>current_end_date:
            start_date = current_end_date
            current_end_date = start_date+timedelta(days=28)

        date_str = datetime.strftime(start_date,"%Y-%m-%d")

        start_str = 'https://nfdc.faa.gov/webContent/28DaySub/28DaySubscription_Effective_'
        end_str = '.zip'
        output_str = start_str + date_str + end_str
        return output_str


    def download_url(self,url,save_path,chunk_size=128):
        r= requests.get(url)
        with open(save_path,'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)


    def update_data(self):
        print("Downloading airport data...")
        full_path = os.path.realpath(__file__)
        path,filename=os.path.split(full_path)
        self.download_url(self.generateURL(),path+'/temp.zip')
        shutil.unpack_archive(path+'/temp.zip',path+'/data')
        os.remove(path+'/temp.zip')


    def parseAirports(self,filename):
        #parse relevant fields based on https://nfdc.faa.gov/webContent/28DaySub/2021-07-15/Layout_Data/apt_rf.txt
        print("Extracting data...")
        f = open(filename,"r",encoding = "ISO-8859-1")
        lines = []
        for line in f:
            lines.append(line)
        airports = []
        for i in range(len(lines)):
            if lines[i][0:3]=='APT':
                icao_ident = lines[i][27:31].rstrip()
                if len(icao_ident)==3:
                    icao_ident = 'K'+icao_ident
                apt = a.Airport(icao_ident)
                apt.facility_type = lines[i][14:27].rstrip()
                apt.location = self.convertToDeg([lines[i][523:537],lines[i][550:565]])
                apt.region_code = lines[i][41:44]
                apt.state = lines[i][50:70].rstrip()
                apt.county = lines[i][70:91].rstrip()
                apt.city = lines[i][93:133].rstrip()
                apt.facility_name = lines[i][133:183].rstrip()
                apt.owner_type = lines[i][183:185]
                apt.facility_use = lines[i][185:187]
                apt.elevation = lines[i][578:585].lstrip()
                apt.traffic_patt_alt = lines[i][593:597].lstrip() #AGL
                apt.sectional = lines[i][597:627].rstrip()
                apt.responsible_artcc = lines[i][674:678].rstrip()
                if len(apt.responsible_artcc)==3:
                    apt.responsible_artcc="K"+apt.responsible_artcc
                n = 1
                runway = []
                while not lines[i+n][0:3]=='RMK' and not lines[i+n][0:3]=='APT' and not lines[i+n][0:3]=='ARR':
                    if lines[i+n][0:3]=='RWY':
                        rwy_ident = lines[i+n][16:23].rstrip()
                        rwy = r.Runway(rwy_ident)
                        rwy.length = lines[i+n][23:28].lstrip()
                        rwy.width = lines[i+n][28:32].lstrip()
                        surf_cond = lines[i+n][32:44].rstrip()
                        if "-" in surf_cond:
                            surface,cond = surf_cond.rsplit("-",1)
                        else:
                            surface,cond = surf_cond,""
                        rwy.surface = surface
                        rwy.cond = cond
                        rwy.TORA = lines[i+n][698:703].lstrip()
                        rwy.TODA = lines[i+n][703:708].lstrip()
                        rwy.ASDA = lines[i+n][708:713].lstrip()
                        rwy.LDA  = lines[i+n][713:718].lstrip()

                        apt.rwys.append(rwy)
                    n+=1
                airports.append(apt)
        f.close()
        return airports

    def convertToDeg(self,coords):
        s1 = coords[0]
        s2 = coords[1]
        a = int(s1[0:2])+degrees(0,int(s1[3:5]),float(s1[6:13]))
        if s1[-1]=='S':
            a=-a
        b = int(s2[0:3])+degrees(0,int(s2[4:6]),float(s2[7:14]))
        if s2[-1]=='W':
            b=-b

        return [a,b]


    def nearestApts(self,aptID,num=20,getCenters=False):
        myAptIdent = aptID
        myApt = None
        #find my airport

        for a in self.apts:
            if a.icao_ident==myAptIdent:
                myApt = a
                break

        myLoc = myApt.location
        nearestApts=[]

        for a in self.apts:
            l = 0
            s = []
            if a.rwys:
                for r in a.rwys:
                    if not r.surface=='WATER' and not r.surface=='TURF':
                        l = max(l,int(r.length))
            g = Geod(ellps='WGS84')
            fwd_az,back_az,dist = g.inv(myLoc[1],myLoc[0],a.location[1], a.location[0])
            dist=dist/1852.0
            if fwd_az<0:
                fwd_az+=360

            if l>=8000 and dist<1000:
                nearestApts.append([a,fwd_az,dist])

        nearestApts_reordered = sorted(nearestApts, key=lambda x: x[2])



        return nearestApts_reordered[:min(num,len(nearestApts_reordered))]
