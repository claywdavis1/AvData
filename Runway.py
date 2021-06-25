class Runway:
    def __init__(self,rwy_ident):
        self.rwy_ident = rwy_ident
        self.length = None
        self.width = None
        self.surface = None
        self.cond = None
        self.TORA = None
        self.TODA = None
        self.ASDA = None
        self.LDA =  None

    def __str__(self):
     return self.rwy_ident
