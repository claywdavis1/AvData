import requests
from bs4 import BeautifulSoup
class AvWeather:
    def __init__(self):
        pass


    def getMetarTaf(self,icao_ident):
        metar = ""
        taf,taf_unprocessed = [],[]
        timestamp = ""
        icao_ident = icao_ident
        query_url = "https://www.aviationweather.gov/taf/data?ids="+icao_ident.lower()+"&format=raw&metars=on&layout=on"
        page = requests.get(query_url)
        soup = BeautifulSoup(page.content,'html.parser')
        timestamp = soup.find_all('strong')
        wx_data = soup.find_all('code')
        if len(wx_data)>0:
            metar = wx_data[0].text
        else:
            print(icao_ident+" has no wx.")
        if len(wx_data)>1:
            taf_unprocessed = wx_data[1].text.split(u'\xa0')
            taf_unprocessed = list(filter(None,taf_unprocessed))
            for t in taf_unprocessed:
                taf.append(t.strip())
        else:
            print(icao_ident+" has no taf.")
        return [metar,taf,timestamp]
