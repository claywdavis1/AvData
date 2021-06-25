import AeroData as ad
import Notam as notam_bot
import AvWeather as aw

class Preflight:
    def __init__(self,icao_ident,num_airports=10,getCenter=True):
        self.no = notam_bot.Notam()
        self.a = ad.AeroData()
        self.wx = aw.AvWeather()
        self.apts_notams = []
        self.apts = []
        self.facility_str = []
        print("Assembling airport list...")
        self.apts = self.a.nearestApts(home_airport,num_airports,getCenter)



    def nearestAptNotams(self):
        self.apts_notams = []
        self.facility_str = []
        for apt in self.apts:
            self.facility_str.append(str(apt[0]))
        for apt in self.apts:
            if not apt[0].responsible_artcc in self.facility_str:
                self.facility_str.append(apt[0].responsible_artcc)
        print("Downloading NOTAMs...")

        for s in self.facility_str:
            n = self.no.getNotams(s)
            self.apts_notams.append([s,n])
        print("Complete!")
        return self.apts_notams

    def nearestAptWx(self):
        print("Getting weather...")
        weather = []
        for apt in self.apts:
            weather.append(self.wx.getMetarTaf(str(apt[0])))
        print("Complete!")
        return weather


home_airport = "KVPS"
num_airports = 10

p = Preflight(home_airport,num_airports,True)
notams = p.nearestAptNotams()
weather = p.nearestAptWx()
