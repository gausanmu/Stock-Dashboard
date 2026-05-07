"""
NSE universe definitions for the scanner.

Supports multiple universes:
  - NIFTY_50, NIFTY_NEXT_50, NIFTY_100
  - NIFTY_MIDCAP_100, NIFTY_SMALLCAP_100
  - NIFTY_200 (50+next50+midcap), NIFTY_500 (200+smallcap+more)
  - FNO_UNDERLYING — futures-eligible underlying stocks
  - PENNY — curated low-price smallcaps

NOTE: These are static curated lists. They will not auto-update with NSE
re-balancing — refresh quarterly when NSE publishes new constituents.
"""
from typing import List

NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
    "SUNPHARMA", "BAJFINANCE", "HCLTECH", "WIPRO", "ULTRACEMCO",
    "NESTLEIND", "NTPC", "POWERGRID", "ONGC",
    "COALINDIA", "ADANIENT", "ADANIPORTS", "TATASTEEL", "JSWSTEEL",
    "TECHM", "BAJAJFINSV", "INDUSINDBK", "HINDALCO", "DRREDDY",
    "DIVISLAB", "CIPLA", "EICHERMOT", "BPCL", "TATACONSUM",
    "GRASIM", "APOLLOHOSP", "HEROMOTOCO", "SBILIFE", "BAJAJ-AUTO",
    "BEL", "TRENT", "SHRIRAMFIN", "DLF", "LICI",
]

NIFTY_NEXT_50 = [
    "ABB", "AMBUJACEM", "ATGL", "BANKBARODA", "BERGEPAINT",
    "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", "CONCOR",
    "DABUR", "DMART", "GODREJCP", "HDFCAMC", "HDFCLIFE",
    "HAL", "HAVELLS", "ICICIPRULI", "IDFCFIRSTB", "INDHOTEL",
    "IOC", "IRCTC", "IRFC", "JINDALSTEL", "LICHSGFIN",
    "LUPIN", "MARICO", "MAXHEALTH", "MUTHOOTFIN", "NHPC",
    "OFSS", "PAGEIND", "PFC", "PIDILITIND",
    "PNB", "POLYCAB", "RECLTD", "SBICARD", "SIEMENS",
    "SRF", "TATAELXSI", "TATAPOWER", "TORNTPHARM", "TVSMOTOR",
    "UNIONBANK", "VEDL", "VBL", "YESBANK",
]

NIFTY_MIDCAP_100 = [
    "ABCAPITAL", "ACC", "ADANIGREEN", "ADANIPOWER", "ALKEM",
    "AUROPHARMA", "BALKRISIND", "BANDHANBNK", "BATAINDIA", "BHARATFORG",
    "BHEL", "BIOCON", "BSE", "CANFINHOME", "CGPOWER",
    "CHAMBLFERT", "COFORGE", "COROMANDEL", "CROMPTON", "CUMMINSIND",
    "DEEPAKNTR", "DEVYANI", "DIXON", "ESCORTS", "FACT",
    "FEDERALBNK", "FORTIS", "GAIL", "GLENMARK", "GMRINFRA",
    "GNFC", "GRANULES", "GUJGASLTD", "HAPPSTMNDS", "HONASA",
    "IEX", "INDUSTOWER", "JKCEMENT", "JSWENERGY", "JUBLFOOD",
    "KALYANKJIL", "KEI", "KPITTECH", "LAURUSLABS", "LTF",
    "LTTS", "M&MFIN", "MANAPPURAM", "MANKIND", "MCX",
    "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS",
    "MRF", "NAM-INDIA", "NATIONALUM", "NAUKRI", "NAVINFLUOR",
    "NCC", "NMDC", "OBEROIRLTY", "OIL", "PAYTM",
    "PERSISTENT", "PETRONET", "PRESTIGE", "PVRINOX", "RAMCOCEM",
    "RVNL", "SAIL", "SJVN", "SOLARINDS", "SONACOMS",
    "STARHEALTH", "SUNDARMFIN", "SUNTV", "SUPREMEIND", "SYNGENE",
    "TATACHEM", "TATACOMM", "THERMAX", "TIINDIA", "TORNTPOWER",
    "UBL", "UPL", "VOLTAS", "WHIRLPOOL", "ZYDUSLIFE",
]

NIFTY_SMALLCAP_100 = [
    "AARTIIND", "AFFLE", "AJANTPHARM", "ANGELONE", "APARINDS",
    "ASTRAL", "ATUL", "AVANTIFEED", "BASF", "BAYERCROP",
    "BDL", "BSOFT", "CAMPUS", "CARBORUNIV", "CDSL",
    "CENTURYTEX", "CESC", "CLEAN", "CMSINFO", "COCHINSHIP",
    "CUB", "CYIENT", "DCMSHRIRAM", "ELGIEQUIP", "EMAMILTD",
    "ENGINERSIN", "EQUITASBNK", "FINCABLES", "FINEORG", "FLUOROCHEM",
    "GESHIP", "GILLETTE", "GLAXO", "GRINDWELL", "GSPL",
    "HATSUN", "HINDPETRO", "HUDCO", "IDFC", "IIFL",
    "INDIACEM", "INDIANB", "IRCON", "ITI", "JBCHEPHARM",
    "JKLAKSHMI", "JMFINANCIL", "JSL", "JSWINFRA", "JUSTDIAL",
    "KALPATPOWR", "KANSAINER", "KEC", "KFINTECH", "KNRCON",
    "LALPATHLAB", "LATENTVIEW", "LAXMIMACH", "LINDEINDIA", "MAPMYINDIA",
    "MASTEK", "MCDOWELL-N", "MEDANTA", "MOTILALOFS", "MRPL",
    "NATCOPHARM", "NBCC", "NETWORK18", "NLCINDIA", "POWERINDIA",
    "PRAJIND", "RADICO", "RAJESHEXPO", "RATNAMANI", "RAYMOND",
    "REDINGTON", "RENUKA", "ROUTE", "RPOWER", "SANOFI",
    "SCHAEFFLER", "SCHNEIDER", "SFL", "SOBHA", "SPARC",
    "SUMICHEM", "SUVENPHAR", "SWSOLAR", "TANLA", "TATAINVEST",
    "TTML", "TV18BRDCST", "USHAMART", "VAIBHAVGBL", "VGUARD",
    "VINATIORGA", "VSTIND", "WELCORP", "ZEEL",
]

# Additional smallcaps to bring count near 200 (needed for "NIFTY 500" total)
NIFTY_SMALLCAP_EXTRA = [
    "ABFRL", "ANANTRAJ", "APLAPOLLO", "ASTRAZEN", "BAJAJHLDNG",
    "BLUEDART", "BLUESTARCO", "BSE", "CASTROLIND", "CEATLTD",
    "CENTRALBK", "CENTURYPLY", "CERA", "CHENNPETRO", "CIEINDIA",
    "CRISIL", "CSBBANK", "DCBBANK", "DCXINDIA", "DELHIVERY",
    "EIDPARRY", "EIHOTEL", "ENDURANCE", "FINPIPE", "FIVESTAR",
    "GMDCLTD", "GODFRYPHLP", "GODREJAGRO", "GODREJIND", "GRSE",
    "HBLPOWER", "HFCL", "HINDCOPPER", "HINDZINC", "HSCL",
    "ICRA", "INDIAMART", "INTELLECT", "ISEC", "JBMA",
    "JINDALSAW", "JKPAPER", "KAJARIACER", "KARURVYSYA", "KFINTECH",
    "KIRLOSBROS", "KIRLOSENG", "KPRMILL", "KSB", "LEMONTREE",
    "MAHABANK", "MAHSEAMLES", "MAZDOCK", "MMTC", "MOIL",
    "NESCO", "NEULANDLAB", "NEWGEN", "NLCINDIA", "NUVAMA",
    "ORIENTHOT", "PCBL", "PFIZER", "PIIND", "POONAWALLA",
    "PPLPHARMA", "PRINCEPIPE", "PTCIL", "RAILTEL", "RAJESHEXPO",
    "RBLBANK", "RHIM", "RKFORGE", "RTNINDIA", "SAREGAMA",
    "SHARDACROP", "SOUTHBANK", "STARCEMENT", "SUNDRMFAST", "SUVEN",
    "SWANENERGY", "SYRMA", "TARC", "TCI", "TEJASNET",
    "TIMKEN", "TITAGARH", "TRIVENI", "UCOBANK", "UNOMINDA",
    "UTIAMC", "VOLTAMP", "WELSPUNLIV", "WESTLIFE", "YESBANK",
    "ZENSARTECH", "ZFCVINDIA",
]

# F&O underlying stocks (~190 stocks eligible for derivatives on NSE)
FNO_UNDERLYING = list(set(NIFTY_50 + NIFTY_NEXT_50 + [
    "ALKEM", "APLAPOLLO", "ASTRAL", "AUROPHARMA", "BANDHANBNK",
    "BANKBARODA", "BATAINDIA", "BHARATFORG", "BHEL", "BIOCON",
    "BSOFT", "CANBK", "CHAMBLFERT", "CHOLAFIN", "COFORGE",
    "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUMMINSIND",
    "DABUR", "DELHIVERY", "DEEPAKNTR", "DIXON", "ESCORTS",
    "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA",
    "GODREJCP", "GODREJPROP", "GRANULES", "HAL", "HDFCAMC",
    "HDFCLIFE", "HINDPETRO", "ICICIPRULI", "IDFCFIRSTB",
    "INDIAMART", "INDIGO", "INDHOTEL", "INDUSTOWER", "IGL",
    "IPCALAB", "IRCTC", "JINDALSTEL", "JSWENERGY", "JUBLFOOD",
    "KEI", "KPITTECH", "LICHSGFIN", "LUPIN", "M&MFIN",
    "MANAPPURAM", "MARICO", "MAXHEALTH", "MCX", "METROPOLIS",
    "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MUTHOOTFIN",
    "NATIONALUM", "NAUKRI", "NMDC", "OBEROIRLTY", "OFSS",
    "PAGEIND", "PERSISTENT", "PETRONET", "PFC", "PIIND",
    "POLYCAB", "PNB", "RAMCOCEM", "RBLBANK", "RECLTD",
    "SAIL", "SBICARD", "SIEMENS", "SRF", "SUNTV",
    "SUPREMEIND", "SYNGENE", "TATACHEM", "TATACOMM", "TATAPOWER",
    "TORNTPHARM", "TVSMOTOR", "UBL", "UPL", "VEDL",
    "VOLTAS", "ZYDUSLIFE",
]))

# Penny stocks: curated smallcap list that historically trades < ₹50.
# A live price filter is also applied at scan time as an extra guard.
PENNY = [
    "YESBANK", "IDFC", "TTML", "RPOWER", "SUZLON",
    "RENUKA", "JPPOWER", "SAIL", "BANKINDIA", "VODAFONEIDEA",
    "IDBI", "NHPC", "NBCC", "PNB", "UNIONBANK",
    "GMRINFRA", "BHEL", "MAHABANK", "UCOBANK", "CENTRALBK",
    "TRIDENT", "JISLJALEQS", "ASHOKLEY", "INDIACEM", "TV18BRDCST",
    "ZEEL", "GTLINFRA", "RTNPOWER", "SOUTHBANK", "JPASSOCIAT",
    "RTNINDIA", "ALOKINDS", "SOUTHWEST", "MMTC", "HINDCOPPER",
    "NLCINDIA", "FACT", "ITI", "GMRP&UI", "WELCORP",
]

NIFTY_100 = NIFTY_50 + NIFTY_NEXT_50
NIFTY_200 = NIFTY_100 + NIFTY_MIDCAP_100[:100]
NIFTY_500 = list(set(NIFTY_200 + NIFTY_SMALLCAP_100 + NIFTY_SMALLCAP_EXTRA))


UNIVERSE_MAP = {
    "nifty50": NIFTY_50,
    "nifty100": NIFTY_100,
    "nifty200": NIFTY_200,
    "nifty500": NIFTY_500,
    "midcap": NIFTY_MIDCAP_100,
    "smallcap": NIFTY_SMALLCAP_100 + NIFTY_SMALLCAP_EXTRA,
    "fno": FNO_UNDERLYING,
    "penny": PENNY,
    "full": NIFTY_500,
}


def get_tickers(level: str = "nifty50") -> List[str]:
    return UNIVERSE_MAP.get(level.lower(), NIFTY_50)


def get_scan_info() -> dict:
    """Returns metadata about each universe for the frontend dropdown."""
    return {
        "nifty50":  {"label": "Nifty 50",         "count": len(NIFTY_50),               "est_minutes": 3,  "tier": "fast"},
        "nifty100": {"label": "Nifty 100",        "count": len(NIFTY_100),              "est_minutes": 6,  "tier": "fast"},
        "nifty200": {"label": "Nifty 200",        "count": len(NIFTY_200),              "est_minutes": 12, "tier": "medium"},
        "nifty500": {"label": "Nifty 500",        "count": len(NIFTY_500),              "est_minutes": 28, "tier": "deep"},
        "midcap":   {"label": "Nifty Midcap 100", "count": len(NIFTY_MIDCAP_100),       "est_minutes": 6,  "tier": "medium"},
        "smallcap": {"label": "Smallcap 200",     "count": len(NIFTY_SMALLCAP_100) + len(NIFTY_SMALLCAP_EXTRA), "est_minutes": 12, "tier": "deep"},
        "fno":      {"label": "F&O Stocks",       "count": len(FNO_UNDERLYING),         "est_minutes": 11, "tier": "medium"},
        "penny":    {"label": "Penny Stocks",     "count": len(PENNY),                  "est_minutes": 3,  "tier": "fast"},
    }


# Index proxies for sentiment aggregation
INDEX_PROXIES = {
    "NIFTY":      "^NSEI",
    "BANKNIFTY":  "^NSEBANK",
    "FINNIFTY":   "NIFTY_FIN_SERVICE.NS",
    "MIDCAPNIFTY": "^NSEMDCP50",
    "NIFTYIT":    "^CNXIT",
}
