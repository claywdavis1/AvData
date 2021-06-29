import AvData as a

ad = a.AvData()
ad.update_airport_data()
apt = ad.get_data("KVPS")
print(apt.icao_ident+" data downloaded. Airfield name: "+apt.facility_name)
try:
    apt = ad.get_data("7777")
except:
    print("7777 not a valid facility.")
n = ad.nearest_airports("KVPS")
print(n)
print(ad.metar("KVPS"))
print(ad.taf("KVPS"))
print(ad.notams("KVPS"))
try:
    apt = ad.metar("7777")
except:
    print("7777 not a valid facility.")
try:
    apt = ad.taf("7777")
except:
    print("7777 not a valid facility.")
try:
    apt = ad.notams("7777")
except:
    print("7777 not a valid facility.")
print(ad.AHAS_risk("KVPS",6,29,20))
print(ad.AHAS_risk("KVPS",6,29,4))
print(ad.AHAS_risk("Koij",6,29,20))
ad.get_PRAIM()
print(ad.bearing_range("KVPS","KPAM"))
