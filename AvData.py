import requests
import os
import shutil
import exceptions
import Airport as a
import Runway as r
import pyppdf.patch_pyppeteer
from requests_html import HTMLSession
from datetime import datetime, timedelta, date, time
from geopy.units import degrees
from pyproj import Geod
from bs4 import BeautifulSoup

class AvData:
    """AvData is a tool to obtain realtime aeronautical information.
    ...
    AvData stores airport information and includes methods
    to obtain various types of aviation information by scraping FAA websites
    in real time.
    ...
    Attributes
    ----------
    airports : str[][]
        a list of lists which contain FAA data for each airport

    Methods
    -------
    update_airport_data()
        Downloads, parses, and saves all airport data.
    get_data(icao_ident)
        Returns airport object associated with given airport identifier.
    nearest_airports(icao_ident,num=10,min_rwy_length=8000,
                     string=True,get_centers=True)
        Returns nearest airports (using lat/long) to given airport with
        options to set minimum runway length, return type as a string, and
        including identifiers of associated ARTCC facilities.
    metar(icao_ident)
        Returns string of latest METAR of specified airport.
    taf(icao_ident)
        Returns string of latest TAF of specified airport.
    notams(icao_ident)
        Returns list of strings of latest NOTAMs of specified facility.
    AHAS_risk(icao,month,day,hour_zulu,all_data=False)
        Returns AHAS risk as string or all AHAS data as list for facility
        at specified Zulu time.
    get_PRAIM(baro_aid=True)
        Downloads current images of PRAIM for all three precision levels
        with or without baro-aiding.
    bearing_range(icao_ident_origin,icao_ident_dest)
        Returns the true heading bearing (in deg) and range (in naut. miles)
        from origin to destination facilities.
    """

    def __init__(self):
        """Initialization only includes airport data matrix."""
        self.airports = None

    def update_airport_data(self):
        """Downloads, parses, and saves all FAA airport information.

        This method only needs to be run once per instance or for long
        run-time applications, once per FAA update cycle.
        """
        self.__download_data()

        full_path = os.path.realpath(__file__)
        path,filename_self = os.path.split(full_path)
        filename_airports = path + "/data/APT.txt"
        self.airports = self.__parse_airports(filename_airports)

        shutil.rmtree(path + "/data")

    def get_data(self, icao_ident):
        """Returns Airport object corresponding to ICAO identifiers.

        Parameters
        ----------
        icao_ident : str
            Four character identifier of facility.

        Raises
        ------
        ValueError
            If the input airport is not in the FAA data set.
        """
        if not self.airports:
            self.update_airport_data()

        airport_data = None
        for airport in self.airports:
            if airport.icao_ident.upper() == icao_ident.upper():
                airport_data = airport
                break
        if airport_data is None:
            raise ValueError("Airport \"" + icao_ident
                            + "\" not found in FAA data.")
        return airport_data

    def nearest_airports(self, icao_ident, num=10, min_rwy_length=8000,
                         return_string=True, get_centers=True):
        """Returns list of nearest airports within specified parameters.

        This method also returns the origin airport.

        Parameters
        ----------
        icao_ident : str
            Four character identifier of facility.
        num : int, optional
            Number of airports to return (default is 10).
        min_rwy_length : int, optional
            Minimum runway length (ft) of returned airports (default is 8000).
        return_string : bool, optional
            If True, returns list of facilities as list of string, otherwise
            returns list of airport objects and strings for non-airports
            facilities if included. (default is True)
        get_centers : bool, optional
            If True, appends list of responsible ARTCC facilities onto return
            list. Generally used for getting NOTAMs. (default is True)

        Raises
        ------
        ValueError
            If the input airport is not in the FAA data set.
        """
        if not self.airports:
            self.update_airport_data()

        selected_aiport = None
        for a in self.airports:
            if a.icao_ident.upper() == icao_ident.upper():
                selected_aiport = a
                break
        if selected_aiport is None:
            raise ValueError("Airport \"" + icao_ident
                            + "\" not found in FAA data.")

        current_loc = selected_aiport.location
        nearest_airports=[]
        for apt in self.airports:
            shortest_runway = 0
            if apt.rwys is not None:
                for rwy in apt.rwys:
                    if rwy.surface != 'WATER' and rwy.surface != 'TURF':
                        shortest_runway = max(shortest_runway, int(rwy.length))
            g = Geod(ellps='WGS84')
            fwd_az, back_az, dist = g.inv(current_loc[1], current_loc[0],
                                            a.location[1], a.location[0])
            if shortest_runway >= min_rwy_length:
                nearest_airports.append([a, dist])

        apts_sorted = sorted(nearest_airports, key=lambda x: x[1])
        apts_sorted = apts_sorted[:min(num, len(apts_sorted))]
        centers = []
        if get_centers is True:
            for apt in apts_sorted:
                if apt[0].responsible_artcc not in centers:
                    centers.append(apt[0].responsible_artcc)
        if return_string is True:
            nearest_airport_str = []
            for a in apts_sorted:
                nearest_airport_str.append(str(a[0]))
            nearest_airport_str.extend(centers)
            return nearest_airport_str
        else:
            nearest_apt_obj = []
            for a in apts_sorted:
                nearest_apt_obj.append(a[0])
            nearest_apt_obj.extend(centers)
            return nearest_apt_obj

    def metar(self, icao_ident):
        """Returns METAR of facility.

        Parameters
        ----------
        icao_ident : str
            Four character identifier of facility.

        Raises
        ------
        ValueError
            If the input airport does not generate a valid response from
            aviation weather website.
        """
        metar = ""
        taf = []
        taf_unprocessed = []
        timestamp = ""
        query_url = ("https://www.aviationweather.gov/taf/data?ids="
                    + icao_ident.lower() + "&format=raw&metars=on&layout=on")
        try:
            page = requests.get(query_url)
        except:
            raise ValueError("No valid data found for \"" + icao_ident + "\".")
        soup = BeautifulSoup(page.content,'html.parser')
        timestamp = soup.find_all('strong')
        wx_data = soup.find_all('code')
        if len(wx_data)>0:
            metar = wx_data[0].text
        else:
            return "\"" + icao_ident + "\" has no weather data."
        return metar

    def taf(self, icao_ident):
        """Returns TAF of facility.

        Parameters
        ----------
        icao_ident : str
            Four character identifier of facility.

        Raises
        ------
        ValueError
            If the input airport does not generate a valid response from
            aviation weather website.
        """
        metar = ""
        taf = []
        taf_unprocessed = []
        timestamp = ""
        query_url = ("https://www.aviationweather.gov/taf/data?ids="
                    + icao_ident.lower() + "&format=raw&metars=on&layout=on")
        try:
            page = requests.get(query_url)
        except:
            raise ValueError("No valid data found for \"" + icao_ident + "\".")
        soup = BeautifulSoup(page.content,'html.parser')
        timestamp = soup.find_all('strong')
        wx_data = soup.find_all('code')
        if len(wx_data)>0:
            metar = wx_data[0].text
        else:
            return "\"" + icao_ident + "\" has no weather data."
        if len(wx_data)>1:
            taf_unprocessed = wx_data[1].text.split(u'\xa0')
            taf_unprocessed = list(filter(None,taf_unprocessed))
            for t in taf_unprocessed:
                taf.append(t.strip())
        else:
            return "\"" + icao_ident + "\" has no TAF."
        return taf

    def notams(self, icao_ident):
        """Returns NOTAMs at facility.

        Parameters
        ----------
        icao_ident : str
            Four character identifier of facility.

        Raises
        ------
        ValueError
            If the input airport does not generate a valid response from
            NOTAM website.
        """
        query_url = ("https://www.notams.faa.gov/dinsQueryWeb/query"
                    + "RetrievalMapAction.do?reportType=Report&retrieveLocId="
                    + icao_ident + "&actionType=notamRetrievalByICAOs")
        try:
            page = requests.get(query_url)
        except:
            raise ValueError("No valid data found for \"" + icao_ident + "\".")
        soup = BeautifulSoup(page.content,'html.parser')
        notam_list_html = soup.find_all('td',class_="textBlack12")
        notam_list = []
        for notam in notam_list_html:
            if (notam.text.strip() != "") and (notam.text.strip()
                    not in notam_list) and ("-" in notam.text):
                notam_list.append(notam.text.replace("\n"," ").split("-",1)[1].strip())
            elif (notam.text.strip() != "") and (notam.text.strip()
                    not in notam_list):
                notam_list.append(" ".join(notam.text.replace("\n"," ").strip().split()))
        return notam_list

    def AHAS_risk(self, icao_ident, month, day, hour_zulu, all_data=False):
        """Returns AHAS risk.

        Parameters
        ----------
        icao_ident : str
            Four character identifier of facility.
        month : str
            Month for AHAS query.
        day : str
            Day for AHAS query.
        hour_zulu : str
            Hour (in Zulu time) of AHAS query.
        all_data : bool, optional
            If true return all data from AHAS, else only return AHAS risk.
        """
        icaos = ("12NC*13NC*14NC*22XS*23XS*99CL*9TX5*ACES*CA62*CAU3*CO80*CO90*CYBG*F93A*F93B*F93C*F93D*FNT*K09J*K0F2*K0L9*K11R*K12J*K1R8*K1V6*K24R*K2CB*K3G5*K3MY*K40J*K4V1*K5T9*K67L*K79J*K92F*K95E*KAAA*KAAF*KABE*KABI*KABR*KABY*KACK*KACT*KACY*KADM*KADW*KAEG*KAEX*KAFF*KAFW*KAGR*KAGS*KAHC*KAHN*KALB*KALI*KALN*KAMA*KANY*KAPA*KAPG*KAPH*KAPN*KARA*KARR*KATL*KATS*KAUS*KAVK*KAVL*KAVO*KAXX*KAYX*KAZO*KAZU*KBAB*KBAD*KBAF*KBAK*KBAM*KBDL*KBEA*KBED*KBFI*KBFM*KBGE*KBGM*KBGR*KBHM*KBIF*KBIH*KBIL*KBIS*KBIX*KBJC*KBKF*KBKN*KBKS*KBKT*KBLI*KBLV*KBMG*KBMI*KBNA*KBOI*KBOI*KBOS*KBPT*KBQK*KBRO*KBTL*KBTR*KBTV*KBVU*KBWI*KBYS*KBYY*KC75*KCAE*KCAK*KCBM*KCDC*KCEF*KCEW*KCHA*KCHK*KCHS*KCIC*KCKA*KCKB*KCKP*KCLL*KCLT*KCMH*KCMY*KCNM*KCNW*KCOF*KCOS*KCOU*KCPS*KCQF*KCRP*KCRW*KCSM*KCVG*KCVN*KCVS*KCWF*KCXO*KCYS*KCZT*KD05*KDAA*KDAB*KDAL*KDAY*KDEC*KDFW*KDHN*KDHT*KDLF*KDLH*KDMA*KDOV*KDPG*KDRO*KDRT*KDSM*KDTW*KDUC*KDUG*KDVL*KDWH*KDYS*KECG*KECP*KECU*KEDG*KEDW*KEFD*KEGE*KEGI*KEGT*KEKO*KELM*KELP*KEND*KENV*KERI*KEUF*KEUG*KEVV*KEVY*KFAF*KFAR*KFAT*KFBG*KFCS*KFCT*KFDK*KFEW*KFFO*KFHB*KFHU*KFLG*KFLV*KFLY*KFMH*KFMN*KFOE*KFOK*KFRI*KFSD*KFSI*KFSM*KFST*KFTG*KFTK*KFTW*KFWA*KFYM*KFYV*KGBG*KGCK*KGCN*KGEG*KGFA*KGFK*KGGG*KGJT*KGLH*KGLS*KGNF*KGNT*KGNV*KGOK*KGON*KGOV*KGPI*KGPT*KGRB*KGRF*KGRI*KGRK*KGRR*KGSB*KGSO*KGSP*KGTB*KGTF*KGTR*KGUP*KGUR*KGUS*KGVT*KGXA*KGXF*KHBG*KHBV*KHDC*KHFF*KHGR*KHGT*KHIF*KHKA*KHLN*KHLR*KHMN*KHND*KHOB*KHOP*KHOU*KHRL*KHRT*KHRX*KHSA*KHST*KHSV*KHTH*KHUA*KHUF*KHUT*KIAB*KIAG*KIAH*KICT*KIDA*KIKR*KILG*KILM*KINS*KISO*KIWA*KJAN*KJAN*KJAX*KJCT*KJKA*KJST*KJTC*KJWG*KK02*KL25*KLAA*KLAL*KLAN*KLAS*KLAW*KLBB*KLBX*KLCH*KLCK*KLCQ*KLFI*KLFK*KLFT*KLGF*KLHW*KLHX*KLIC*KLIT*KLMT*KLMT*KLNK*KLNS*KLRD*KLRF*KLSE*KLSF*KLSV*KLTS*KLUF*KLUF*KLVS*KLWB*KMAF*KMCE*KMCF*KMCI*KMCN*KMDA*KMDQ*KMDT*KMDW*KMEI*KMEM*KMER*KMFD*KMFE*KMFR*KMGE*KMGM*KMGM*KMHR*KMHT*KMHV*KMIB*KMKC*KMKE*KMLI*KMLU*KMMH*KMMT*KMOB*KMOD*KMOT*KMQB*KMRB*KMRY*KMSN*KMSO*KMSP*KMSY*KMTC*KMTN*KMUI*KMUL*KMUO*KMVY*KMWA*KMWH*KMXF*KMYR*KNBC*KNBG*KNBJ*KNCA*KNDY*KNDZ*KNEL*KNEN*KNEW*KNFD*KNFE*KNFG*KNFJ*KNFL*KNFW*KNGP*KNGS*KNGT*KNGU*KNGW*KNHK*KNHL*KNHZ*KNID*KNIP*KNJK*KNJM*KNJW*KNKL*KNKT*KNKX*KNLC*KNMM*KNOG*KNOW*Knpa*KNQA*KNQB*KNQI*KNQX*KNRA*KNRB*KNRQ*KNSE*KNSI*KNTD*KNTU*KNUC*KNUI*KNUN*KNUQ*KNUW*KNVI*KNXP*KNXX*KNYG*KNYL*KNZX*KNZY*KO53*KOAJ*KOAK*KOCF*KODO*KOFF*KOGD*KOKC*KOMA*KOQU*KORF*KORL*KOZR*KPAE*KPAM*KPBI*KPDX*KPHF*KPHL*KPHX*KPHX*KPIA*KPIB*KPIE*KPIH*KPIL*KPIT*KPKV*KPMD*KPNC*KPNS*KPOB*KPOE*KPQL*KPRB*KPRN*KPRO*KPRZ*KPSC*KPSM*KPSP*KPSX*KPUB*KPVD*KPVJ*KPVW*KPWA*KPWM*KRBM*KRCA*KRDD*KRDG*KRDR*KRFD*KRIC*KRIV*KRKP*KRKS*KRME*KRND*KRNO*KRNT*KROA*KROW*KRST*KRSW*KRYM*KRYN*KSAC*KSAF*KSAT*KSAV*KSAW*KSBY*KSCH*KSCK*KSDF*KSEA*KSEM*KSEQ*KSGF*KSGH*KSGT*KSGU*KSH1*KSHV*KSJT*KSKA*KSKF*KSLC*KSLI*KSLJ*KSLN*KSMF*KSNS*KSPI*KSPS*KSRQ*KSSC*KSSF*KSSI*KSSN*KSTJ*KSTL*KSUS*KSUU*KSUX*KSVC*KSVN*KSWF*KSWO*KSYR*KSZL*KT69*KT70*KTAD*KTBN*KTCC*KTCL*KTCM*KTCS*KTFP*KTIK*KTIX*KTLH*KTNT*KTNX*KTOI*KTOL*KTOP*KTPH*KTTS*KTUL*KTUP*KTUS*KTVL*KTWF*KTXK*KTYS*KU30*KUNV*KUVA*KVAD*KVBG*KVBW*KVCT*KVCV*KVCV*KVGT*KVLD*KVOK*KVPS*KVQQ*KVUJ*KW94*KWAL*KWDG*KWJF*KWLD*KWMC*KWRB*KWRI*KWSD*KXMR*KXNA*KXNO*KYKM*KYNG*KYQQ*KZ*KZ10*KZ99*KZER*KZZV*LARO*Merlin_BealeAFB*MT15*NJ24*NV72*PABA*PABI*PABM*PACD*PACZ*PADK*PADM*PAED*PAEH*PAEI*PAFA*PAFB*PAGZ*PAIM*PAKK*PAKN*PAKO*PALU*PANC*PAPC*PASV*PATC*PATL*PAWT*PHHI*PHIK*PHNG*PHNP*PHSF*PPIZ*Razorback Tower*TARGET1*WS20*Z*Z").split('*')
        strs = ("ATLANTIC MCOLF*OAK GROVE MCOLF*CAMP DAVIS MCOLF*LONGHORN AUX LANDING STRIP*SHORTHORN AUX LANDING STRIP*EL MIRAGE FLD ADELANTO*CAMP BULLIS ALS CALS*ACES*MC MILLAN ASSAULT STRIP*CAMP OLIVER AAF*FOWLER*USAF ACADEMY BULLSEYE AUX*BAGOTVILLE*FLIGHT93_MEMORIAL*FLIGHT93_INDIANA*FLIGHT93_PUNXSUTAWNEY*FLIGHT93_MORGANTOWN*BISHOP INTL*JEKYLL ISLAND*BOWIE MUNI*ECHO BAY*BRENHAM MUNI*BREWTON MUNI*BAY MINETTE MUNI*FREMONT CO*DILLEY AIRPARK*CAMP BLANDING AAF*DAWSON AAF*MT HAWLEY AUXILIARY*PERRY FOLEY*SPANISH PEAKS*MAVERICK CO MEM INTL*MESQUITE*SOUTH ALABAMA RGNL AT BILL BENTON FLD*CHATTANOOGA SKY HARBOR*STALLION AAF*LOGAN CO*APALACHICOLA RGNL*LEHIGH VALLEY INTL*ABILENE RGNL*ABERDEEN FLD*SOUTHWEST GEORGIA RGNL*NANTUCKET MEM*WACO RGNL*ATLANTIC CITY INTL*ARDMORE MUNI*ANDREWS AFB*DOUBLE EAGLE II*ALEXANDRIA INTL*USAF ACADEMY AIRFIELD*FORT WORTH ALLIANCE*MACDILL AFB AUX FLD*AUGUSTA RGNL AT BUSH FLD*AMEDEE AAF*ATHENS BEN EPPS*ALBANY INTL*ALICE INTL*ST LOUIS RGNL*RICK HUSBAND AMARILLO INTERNATIONAL*ANTHONY MUNI*CENTENNIAL*PHILLIPS AAF*A P HILL AAF*ALPENA CO REGIONAL, MI*ACADIANA RGNL*AURORA MUNI*HARTSFIELD JACKSON ATLANTA INTL*ARTESIA MUNI*AUSTIN BERGSTROM INTL*ALVA RGNL*ASHEVILLE RGNL*AVON PARK EXECUTIVE*ANGEL FIRE*ARNOLD AFB*KALAMAZOO BATTLE CREEK INTL*ARROWHEAD ASSAULT STRIP*BEALE AFB*BARKSDALE AFB*BARNES MUNI*COLUMBUS MUNICIPAL, IN*BATTLE MOUNTAIN*BRADLEY INTL ARPT*BEEVILLE MUNI*LAURENCE G HANSCOM FLD*BOEING FLD KING CO INTL*MOBILE DOWNTOWN*DECATUR CO INDUSTRIAL AIR PARK*GREATER BINGHAMTON EDWIN A LINK FLD*BANGOR INTL*BIRMINGHAM INTL*BIGGS AAF*EASTERN SIERRA RGNL*BILLINGS LOGAN INTL*BISMARCK MUNI*KEESLER AFB*ROCKY MOUNTAIN METRO*BUCKLEY AFB*BLACKWELL TONKAWA MUNI*BROOKS CO*BLACKSTONE AAF ALLEN C PERKINSON MUNI*BELLINGHAM INTL*SCOTT AFB*MONROE CO*CENTRAL ILLINOIS RGNL*NASHVILLE INTL ARPT*GOWEN FIELD, ID*BOISE AIR TERMINAL*LOGAN INTL*SOUTHEAST TEXAS RGNL*BRUNSWICK GOLDEN ISLES*BROWNSVILLE SOUTH PADRE ISLAND INTL*W K KELLOGG*BATON ROUGE METRO RYAN FLD*BURLINGTON INTL*BOULDER CITY MUNI*BALTIMORE WASHINGTON INTL*BICYCLE LAKE AAF*BAY CITY RGNL*MARSHALL CO*COLUMBIA METROPOLITAN*AKRON CANTON RGNL*COLUMBUS AFB*CEDAR CITY RGNL*WESTOVER ARB, MA*BOB SIKES*LOVELL FLD*CHICKASHA MUNI*CHARLESTON AFB INTL*CHICO MUNI*KEGELMAN AF AUX FIELD*NORTH CENTRAL WEST VIRGINIA*CHEROKEE MUNI*EASTERWOOD FLD*CHARLOTTE DOUGLAS INTL*PORT COLUMBUS INTL ARPT*SPARTA FORT MCCOY*CAVERN CITY AIR TERMINAL*TSTC WACO*PATRICK AFB*PETERSON AFB*COLUMBIA RGNL*ST LOUIS DOWNTOWN*H L SONNY CALLAHAN*CORPUS CHRISTI INTL*MCLAUGHLIN ANGB*CLINTON-SHERMAN*CINCINNATI NORTHERN KENTUCKY INTL*CLOVIS MUNI*CANNON AFB*CHENNAULT INTL*LONE STAR EXECUTIVE*CHEYENNE RGNL JERRY OLSON FLD*DIMMIT CO*GARRISON MUNI*DAVISON AAF*DAYTONA BEACH INTL*DALLAS LOVE FLD*JAMES M COX DAYTON INTL*DECATUR*DALLAS FORT WORTH INTL*DOTHAN RGNL*DALHART MUNI*LAUGHLIN AFB*DULUTH INTL*DAVIS MONTHAN AFB*DOVER AFB*MICHAEL AAF*DURANGO LA PLATA CO*DEL RIO*DES MOINES INTL*DETROIT METRO WAYNE CO*HALLIBURTON FLD*BISBEE DOUGLAS INTL*DEVILS LAKE RGNL*DAVID WAYNE HOOKS MEM*DYESS AFB*ELIZABETH CITY CGAS MUNI*NORTHWEST FLORIDA BEACHES INTL*EDWARDS CO*WEIDE AHP*EDWARDS AFB*ELLINGTON FIELD, TX*EAGLE CO RGNL*EGLIN AF AUX NR 3 DUKE*WELLINGTON MUNI*ELKO RGNL*ELMIRA CORNING RGNL*EL PASO INTL*VANCE AFB*WENDOVER*ERIE INTL TOM RIDGE FLD*WEEDON FLD*MAHLON SWEET FLD*EVANSVILLE RGNL*SUMMIT*FELKER AAF*HECTOR INTL*FRESNO YOSEMITE INTL*SIMMONS AAF*BUTTS ARMY AIR FIELD*VAGABOND AAF*FREDERICK MUNICIPAL AIRPORT*FE WARREN AFB*WRIGHT-PATTERSON AFB*FERNANDINA BEACH MUNI*LIBBY AAF SIERRA VISTA MUNI*FLAGSTAFF PULLIAM*SHERMAN AAF*MEADOW LAKE*OTIS ANGB*FOUR CORNERS RGNL*FORBES FIELD*FRANCIS S GABRESKI*MARSHALL AAF*JOE FOSS FIELD, SD*HENRY POST ARMY AIR FIELD*FORT SMITH RGNL*FORT STOCKTON PECOS CO*FRONT RANGE*GODMAN AAF*FORT WORTH MEACHAM INTL*FORT WAYNE INTL*FAYETTEVILLE MUNI*DRAKE FLD*GALESBURG MUNI*GARDEN CITY RGNL*GRAND CANYON NATL PARK*SPOKANE INTL*MALMSTROM*GRAND FORKS INTL*EAST TEXAS REGIONAL*GRAND JUNCTION RGNL*MID DELTA RGNL*SCHOLES INTL AT GALVESTON*GRENADA MUNICIPAL AIRPORT*GRANTS MILAN MUNI*GAINESVILLE RGNL*GUTHRIE EDMOND RGNL*GROTON NEW LONDON*GRAYLING AAF*GLACIER PARK INTL*GULFPORT BILOXI INTL*AUSTIN STRAUBEL INTL*GRAY AAF*CENTRAL NEBRASKA RGNL*ROBERT GRAY AAF*GERALD R FORD INTL*SEYMOUR JOHNSON AFB*PIEDMONT TRIAD INTL*GREENVILLE SPARTANBURG INTL*WHEELER SACK AAF*GREAT FALLS INTL*GOLDEN TRIANGLE RGNL*GALLUP MUNI*CAMP GUERNSEY AAF*GRISSOM ARB*MAJORS ARPT*GRAY BUTTE FLD*GILA BEND AF AUX*HATTIESBURG BOBBY L CHAIN MUNI*JIM HOGG CO*HAMMOND NORTHSHORE RGNL*MACKALL AAF*HAGERSTOWN RGNL RICHARD A HENSON FLD*TUSI AHP*HILL AFB*BLYTHEVILLE MUNI*HELENA RGNL*HOOD AAF*HOLLOMAN AFB*HENDERSON EXECUTIVE*LEA CO RGNL*CAMPBELL AAF*WILLIAM P HOBBY*VALLEY INTL*HURLBURT FIELD*HEREFORD MUNI*STENNIS INTL*HOMESTEAD ARS, FL*HUNTSVILLE INTL CARL T JONES FLD*HAWTHORNE INDUSTRIAL*REDSTONE AAF*TERRE HAUTE INTL HULMAN FIELD, IN*HUTCHINSON MUNI*MCCONNELL AFB*NIAGARA FALLS ARS, NY*GEORGE BUSH INTCNTL HOUSTON*WICHITA MID CONTINENT*IDAHO FALLS RGNL*KIRTLAND AFB, NM*NEW CASTLE*WILMINGTON INTL*CREECH AFB*KINSTON RGNL JETPORT AT STALLINGS FLD*WILLIAMS GATEWAY*JACKSON EVERS INTL*ALLEN C. THOMPSON FIELD, MS*JACKSONVILLE INTL ARPT*KIMBLE CO*JACK EDWARDS*JOHN MURTHA JOHNSTOWN CAMBRIA CO*SPRINGERVILLE MUNI*WATONGA RGNL*PERRYVILLE MUNI*PEARCE FERRY*LAMAR MUNI*LAKELAND LINDER RGNL*CAPITAL REGION INTL*MC CARRAN INTL*LAWTON-FORT SILL REGIONAL*LUBBOCK INTERNATIONAL*TEXAS GULF COAST RGNL*LAKE CHARLES RGNL*RICKENBACKER ANGB, OH*LAKE CITY MUNI*LANGLEY AFB*ANGELINA CO*LAFAYETTE RGNL*LAGUNA AAF*WRIGHT AAF*LA JUNTA MUNI*LIMON MUNI*ADAMS FLD*KINGSLEY FIELD, OR*KLAMATH FALLS*LINCOLN MUNI ARPT*LANCASTER*LAREDO INTL*LITTLE ROCK AFB*LA CROSSE MUNICIPAL AIRPORT*LAWSON AAF*NELLIS AFB*ALTUS AFB*LUKE AFB*LUKE AFB AUX1*LAS VEGAS MUNI*GREENBRIER VALLEY*MIDLAND INTERNATIONAL*MERCED RGNL MACREADY FLD*MACDILL AFB*KANSAS CITY INTL*MIDDLE GEORGIA RGNL*MARTINDALE AAF*HUNTSVILLE EXECUTIVE ARPT TOM SHARP JR*HARRISBURG INTL*CHICAGO MIDWAY INTL*KEY FLD*MEMPHIS INTL*CASTLE*MANSFIELD LAHM REGIONAL, OH*MC ALLEN MILLER INTL*ROGUE VALLEY INTL MEDFORD*DOBBINS ARB ATLANTA NAS*MONTGOMERY RGNL*DANNELLY FIELD, AL*SACRAMENTO MATHER*MANCHESTER*MOJAVE*MINOT AFB*CHARLES B WHEELER DOWNTOWN*GENERAL MITCHELL IAP*QUAD CITY INTL*MONROE RGNL*MAMMOTH YOSEMITE*MC ENTIRE ANGS*MOBILE RGNL*MODESTO CITY*MINOT INTL*MACOMB MUNI*SHEPHERD FIELD, WV*MONTEREY PENINSULA*TRUAX FIELD, WI*MISSOULA INTL*MINNEAPOLIS ST PAUL INTL*LOUIS ARMSTRONG NEW ORLEANS INTL*SELFRIDGE ANGB*MARTIN STATE*MUIR AAF*SPENCE*MOUNTAIN HOME AFB*MARTHAS VINEYARD*WILLIAMSON CO RGNL*GRANT COUNTY INTL*MAXWELL AFB*MYRTLE BEACH INTL*BEAUFORT MCAS*NEW ORLEANS NAS JRB*BARIN NOLF*NEW RIVER MCAS*DAHLGREN USN SFC WAR CNTR*WHITING FLD NAS SOUTH*LAKEHURST NAES*WHITEHOUSE NOLF*LAKEFRONT*SUMMERDALE NOLF*FENTRESS NALF*CAMP PENDLETON MCAS*CHOCTAW NOLF*FALLON NAS*FORT WORTH NAS*CORPUS CHRISTI NAS*SANTA ROSA NOLF*GOLIAD NOLF*NORFOLK NAS*CABANISS FLD NOLF*PATUXENT RIVER NAS*WOLF NOLF*BRUNSWICK NAS*CHINA LAKE NAWS*JACKSONVILLE NAS*EL CENTRO NAF*BOGUE MCALF*JOE WILLIAMS NOLF*HOLLEY NOLF*CHERRY POINT MCAS*MIRAMAR MCAS*LEMOORE NAS*MERIDIAN NAS*ORANGE GROVE NALF*PORT ANGELES CGAS*PENSACOLA NAS*MILLINGTON RGNL JETPORT*SILVERHILL NOLF*KINGSVILLE NAS*KEY WEST NAS*COUPEVILLE NOLF*MAYPORT NS*SPENCER NOLF*WHITING FLD NAS NORTH*SAN NICOLAS ISLAND NOLF*POINT MUGU NAWS*OCEANA NAS*SAN CLEMENTE ISLAND NALF*WEBSTER NOLF*SAUFLEY FLD NOLF*MOFFETT FEDERAL AIRFIELD*WHIDBEY ISLAND NAS*PACE NOLF*TWENTYNINE PALMS EAF*WILLOW GROVE NAS*QUANTICO MCAF*YUMA MCAS YUMA INTL*HAROLD NOLF*NORTH ISLAND NAS*MEDFORD MUNI*ALBERT J ELLIS*METROPOLITAN OAKLAND INTL*OCALA INTL JIM TAYLOR FLD*ODESSA SCHLEMEYER FLD*OFFUTT AFB*OGDEN HINCKLEY*WILL ROGERS WORLD*EPPLEY AFLD*QUONSET STATE*NORFOLK INTL*EXECUTIVE*CAIRNS AAF*SNOHOMISH CO*TYNDALL AFB*PALM BEACH INTL*PORTLAND INTL*NEWPORT NEWS WILLIAMSBURG INTL*PHILADELPHIA INTL*PAPAGO AAF*PHOENIX SKY HARBOR INTL*GREATER PEORIA RGNL*HATTIESBURG LAUREL RGNL*ST PETE CLEARWATER INTL*POCATELLO RGNL*PORT ISABEL CAMERON CO*PITTSBURGH INTL*CALHOUN CO*PALMDALE AF PLANT NR 42*PONCA CITY RGNL*PENSACOLA GULF COAST RGNL*POPE AFB*POLK AAF*TRENT LOTT INTL*PASO ROBLES MUNI*MAC CRENSHAW MEM*PERRY MUNI*PORTALES MUNI*TRI CITIES*PEASE ANGS, NH*PALM SPRINGS INTL*PALACIOS MUNI*PUEBLO MEM*THEODORE FRANCIS GREEN STATE*PAULS VALLEY MUNI*HALE CO*WILEY POST*PORTLAND INTL JETPORT*ROBINSON AAF*ELLSWORTH AFB*REDDING MUNI*READING RGNL CARL A SPAATZ FLD*GRAND FORKS AFB*GREATER ROCKFORD*BYRD FIELD, VA*MARCH ARB, CA*ARANSAS CO*ROCK SPRINGS SWEETWATER CO*GRIFFISS AIRFIELD*RANDOLPH AFB*RENO TAHOE INTL*RENTON MUNI*ROANOKE RGNL WOODRUM FLD*ROSWELL INTL AIR CENTER*ROCHESTER INTL*SOUTHWEST FLORIDA INTL*RAY S MILLER AAF*RYAN FLD*SACRAMENTO EXECUTIVE*SANTA FE MUNI*SAN ANTONIO INTL*SAVANNAH HILTON HEAD INTL*SAWYER INTL*SALISBURY OCEAN CITY WICOMICO RGNL*SCHENECTADY CO*STOCKTON METRO*LOUISVILLE INTL STANDIFORD FIELD, KY*SEATTLE TACOMA INTL*CRAIG FLD*RANDOLPH AFB AUX*SPRINGFIELD BRANSON NATL*SPRINGFIELD-BECKLEY MUNICIPAL*STUTTGART MUNI*ST GEORGE MUNI*SHELBY AUX FIELD*SHREVEPORT RGNL*SAN ANGELO RGNL MATHIS FLD*FAIRCHILD AFB*KELLY AFB*SALT LAKE CITY INTL*LOS ALAMITOS AAF*HAGLER AAF*SALINA MUNI*SACRAMENTO INTL*SALINAS MUNI*ABRAHAM LINCOLN CAPITAL*SHEPPARD AFB WICHITA FALLS MUNI*SARASOTA BRADENTON INTL*SHAW AFB*STINSON MUNI*MCKINNON ST SIMONS ISLAND*SENECA AAF*ROSECRANS MEMORIAL ARPT*LAMBERT ST. LOUIS IAP*SPIRIT OF ST LOUIS*TRAVIS AFB*SIOUX GATEWAY AIRPORT*GRANT CO*HUNTER AAF*STEWART INTL*STILLWATER RGNL*HANCOCK FIELD, NY*WHITEMAN AFB*ALFRED C BUBBA THOMAS*LAUGHLIN AFB AUX NR 1*PERRY STOKES*FORNEY AAF*TUCUMCARI MUNI*TUSCALOOSA RGNL*MC CHORD AFB*TRUTH OR CONSEQUENCES MUNI*MC CAMPBELL PORTER*TINKER AFB*SPACE COAST RGNL*TALLAHASSEE RGNL*DADE COLLIER TRAINING AND TRANSITION*TONOPAH TEST RANGE*TROY MUNI*TOLEDO EXPRESS, OH*PHILIP BILLARD MUNI*TONOPAH*NASA SHUTTLE LANDING FACILITY*TULSA INTERNATIONAL*TUPELO RGNL*TUCSON ANG*LAKE TAHOE*JOSLIN FLD MAGIC VALLEY RGNL*TEXARKANA RGNL WEBB FLD*MCGHEE TYSON*TEMPLE BAR*UNIVERSITY PARK*GARNER FLD*MOODY AFB*VANDENBERG AFB*BRIDGEWATER AIR PARK AIRPORT*VICTORIA RGNL*VICTORVILLE*SOUTHERN CALIFORNIA LOGISTICS*NORTH LAS VEGAS*VALDOSTA RGNL*VOLK FIELD, WI*EGLIN AFB*CECIL FIELD NAS*STANLY COUNTY*CAMP PEARY LANDING STRIP*WALLOPS FLIGHT FACILITY*ENID WOODRING RGNL*GENERAL WM J FOX AFLD*STROTHER FLD*WINNEMUCCA MUNI*ROBINS AFB*MC GUIRE AFB*CONDRON AAF*CAPE CANAVERAL AS SKID STRIP*NORTHWEST ARKANSAS RGNL*NORTH AF AUX*McALLISTER FIELD*YOUNGSTOWN WARREN REGIONAL, OH*COMOX*AUX FIELD 6 LANDING ZONE*PACEMAKER LANDING ZONE*SELAH CREEK LANDING ZONE*SCHUYLKILL CO*ZANESVILLE MUNICIPAL, OH*LAKE ROOSEVELT*Merlin_BealeAFB*FORT HARRISON AAF*WARREN GROVE RANGE*SWEETWATER*BARTER ISLAND LRRS*ALLEN AAF*BIG MOUNTAIN AFS*COLD BAY*CAPE ROMANZOF LRRS*ADAK*MARSHALL DON HUNTER SR*ELMENDORF AFB*CAPE NEWENHAM LRRS*EIELSON AFB*FAIRBANKS INTL*WAINWRIGHT AAF*GRANITE MOUNTAIN AFS*INDIAN MOUNTAIN LRRS*KOYUK ALFRED ADAMS*KING SALMON*NIKOLSKI AS*CAPE LISBURNE LRRS*TED STEVENS ANCHORAGE INTL*PORT CLARENCE CGS*SPARREVOHN LRRS*TIN CITY LRRS*TATALINA LRRS*WAINWRIGHT AS*WHEELER AAF*HICKAM AFB*KANEOHE BAY MCAF*FORD ISLAND NALF*BRADSHAW AAF*POINT LAY LRRS*Razorback Tower*TARGET1*YOUNG LANDING ZONE*EDWARDS AF AUX NORTH BASE*COLUMBUS AFB AUX FIELD").split('*')

        ahas_keys = dict(zip(icaos, strs))
        year = date.today().year
        if icao_ident not in ahas_keys:
            return "No AHAS data available."
        if datetime.utcnow() > datetime(year,month,day,hour_zulu, 0, 0, 0):
            if len(str(hour_zulu)) == 1:
                hour_zulu = "0" + str(hour_zulu)
            url = ("https://www.usahas.com/webservices/Fluffy_AHAS.asmx"
                + "/GetAHASRisk_PAST?Area=%27"
                + ahas_keys[icao_ident] + "%27&iMonth=" + str(month)
                + "&iDay=" + str(day) + "&sTime=" + str(hour_zulu) + ":00")
        else:
            url = ("https://www.usahas.com/webservices/Fluffy_AHAS.asmx"
                + "/GetAHASRisk?Area=%27"
                + ahas_keys[icao_ident] + "%27&iMonth="
                + str(month) + "&iDay=" + str(day) + "&iHour=" + str(hour_zulu))
        session = HTMLSession()

        page = session.get(url)
        page.html.render()
        soup = BeautifulSoup(page.html.html, "xml")
        ahas_data = []
        tables = soup.find_all("Table")
        for table in tables:
            route = table.find("Route").get_text()
            segment = table.find("Segment").get_text()
            if datetime.utcnow()>datetime(year,month,day,int(hour_zulu), 0, 0, 0):
                hour = str(hour_zulu)
            else:
                hour = table.find("Hour").get_text()
            date_time = table.find("DateTime").get_text()
            nexrad_risk = table.find("NEXRADRISK").get_text()
            soar_risk = table.find("SOARRISK").get_text()
            ahas_risk = table.find("AHASRISK").get_text()
            based_on = table.find("NEXRADRISK").get_text()
            TI_depth = table.find("TIDepth").get_text()
            ahas_data.append([route, segment, hour, date_time, nexrad_risk,
                            soar_risk, ahas_risk, based_on, TI_depth])

        if not all_data:
            return ahas_data[0][6]
        return ahas_data

    def get_PRAIM(self, baro_aid=True):
        """Downloads current PRAIM outage images.

        Parameters
        ----------
        baro_aid : bool, optional
            If true download baro-aided PRAIM, else use non-baro-aided.
            (default is True.)
        """
        query_url = "https://sapt.faa.gov/default.php"
        page = requests.get(query_url)
        soup = BeautifulSoup(page.content,'html.parser')
        if baro_aid:
            enroute = soup.find("a", title="En Route w/ Baro Aiding")
            terminal = soup.find("a", title="Terminal w/ Baro Aiding")
            npa = soup.find("a", title="Non-Precision Approach w/ Baro Aiding")
            baro_str = "_baro"
        else:
            enroute = soup.find("a", title="En Route w/o Baro Aiding")
            terminal = soup.find("a", title="Terminal w/o Baro Aiding")
            npa = soup.find("a", title="Non-Precision Approach w/o Baro Aiding")
            baro_str = "_nobaro"

        enroute_num = enroute.find("img")['src'].split('=')[1]
        terminal_num = terminal.find("img")['src'].split('=')[1]
        npa_num = terminal.find("img")['src'].split('=')[1]
        enroute_url = ("https://sapt.faa.gov/enroute" + baro_str
                        + ".png?t=" + str(enroute_num))
        terminal_url = ("https://sapt.faa.gov/terminal" + baro_str
                        + ".png?t=" + str(terminal_num))
        npa_url = ("https://sapt.faa.gov/npa" + baro_str
                        + ".png?t=" + str(npa_num))

        full_path = os.path.realpath(__file__)
        path,filename = os.path.split(full_path)
        enroute_path = path + "/enroute.png"
        terminal_path = path + "/terminal.png"
        npa_path = path + "/npa.png"
        r = requests.get(enroute_url, stream=True)

        if r.status_code == 200:
            with open(enroute_path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        r = requests.get(terminal_url, stream=True)
        if r.status_code == 200:
            with open(terminal_path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        r = requests.get(npa_url, stream=True)
        if r.status_code == 200:
            with open(npa_path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)

    def bearing_range(self, icao_ident_origin, icao_ident_dest):
        """Returns and bearing and range from origin to destination.

        Parameters
        ----------
        icao_ident_origin : str
            Four character identifier of origin facility.
        icao_ident_dest : str
            Four character identifier of destin facility.
        """
        origin = self.get_data(icao_ident_origin)
        destination = self.get_data(icao_ident_dest)
        g = Geod(ellps='WGS84')
        fwd_az,back_az,dist = g.inv(origin.location[1], origin.location[0],
                destination.location[1], destination.location[0])
        if fwd_az < 0:
            fwd_az = 360 + fwd_az
        dist = dist/1852
        return [fwd_az, dist]

    def __generate_URL(self):
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

    def __download_url(self, url, save_path, chunk_size=128):
        r= requests.get(url)
        with open(save_path,'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)

    def __download_data(self):
        full_path = os.path.realpath(__file__)
        path,filename=os.path.split(full_path)
        self.__download_url(self.__generate_URL(),path+'/temp.zip')
        shutil.unpack_archive(path+'/temp.zip',path+'/data')
        os.remove(path+'/temp.zip')

    def __parse_airports(self,filename):
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
                apt.location = self.__convert_to_deg([lines[i][523:537],lines[i][550:565]])
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

    def __convert_to_deg(self,coords):
        s1 = coords[0]
        s2 = coords[1]
        a = int(s1[0:2])+degrees(0,int(s1[3:5]),float(s1[6:13]))
        if s1[-1]=='S':
            a=-a
        b = int(s2[0:3])+degrees(0,int(s2[4:6]),float(s2[7:14]))
        if s2[-1]=='W':
            b=-b

        return [a,b]
