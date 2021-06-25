import requests
from bs4 import BeautifulSoup
class Notam:
    def __init__(self):
        pass


    def getNotams(self,icao_ident):
        icao_ident = icao_ident
        query_url = "https://www.notams.faa.gov/dinsQueryWeb/queryRetrievalMapAction.do?reportType=Report&retrieveLocId="+icao_ident+"&actionType=notamRetrievalByICAOs"
        page = requests.get(query_url)
        soup = BeautifulSoup(page.content,'html.parser')
        notam_list_html = soup.find_all('td',class_="textBlack12")
        notam_list = []
        for notam in notam_list_html:
            if not notam.text.strip()=="" and not notam.text.strip() in notam_list and "-" in notam.text:
                notam_list.append(notam.text.replace("\n"," ").split("-",1)[1].strip())
            elif not notam.text.strip()=="" and not notam.text.strip() in notam_list:
                notam_list.append(" ".join(notam.text.replace("\n"," ").strip().split()))


        return notam_list
