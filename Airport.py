class Airport:
    def __init__(self,icao_ident):
        """Airport a class that saves all FAA airport data.
        ...
        Attributes
        ----------
        icao_ident : str
            Four character identifier of facility.
        All others: see FAA APT.txt formatting for further info.
        """
        self.icao_ident = icao_ident
        self.location = None
        self.facility_type = None
        self.location = None
        self.region_code = None
        self.state = None
        self.county = None
        self.city = None
        self.facility_name = None
        self.owner_type = None
        self.facility_use = None
        self.elevation = None
        self.traffic_patt_alt = None
        self.sectional = None
        self.boundary_artcc = None
        self.responsible_artcc = None
        self.rwys = []


    def __str__(self):
     return self.icao_ident
