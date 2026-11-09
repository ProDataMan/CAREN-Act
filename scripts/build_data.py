#!/usr/bin/env python3
"""Fetch public datasets and build compact JSON files for the advocacy map.

Run locally:   python3 scripts/build_data.py
Run in CI:     .github/workflows/refresh-data.yml (weekly + manual)

Outputs go to website/data/. Every file is regenerated from the primary source;
nothing in website/data/ should be hand-edited except residual_ordinances.json,
which is a curated, cited list.

Requires: Python 3.9+, openpyxl (for the Mapping Police Violence spreadsheet).
"""
import csv
import datetime as dt
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "website", "data")
UA = "CAREN-Act-advocacy-data-builder (+https://github.com/ProDataMan/CAREN-Act)"
TODAY = dt.date.today()

SOURCES = {
    "acs": "https://www2.census.gov/programs-surveys/acs/summary_file/{y}/table-based-SF/data/5YRData/acsdt5y{y}-b03002.dat",
    "gazetteer": "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{y}_Gazetteer/{y}_Gaz_counties_national.zip",
    "eji_pdf": "https://eji.org/wp-content/uploads/2020/02/02-07-20-lynching-in-america-county-supplement.pdf",
    "mpv": "https://mappingpoliceviolence.us/s/MPVDatasetDownload.xlsx",
    "fbi_signed": "https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key=additional-datasets/hate-crime/hate_crime.zip",
    "fbi_agencies": "https://cde.ucr.cjis.gov/LATEST/agency/byStateAbbr/{st}",
    "holc": "https://dsl.richmond.edu/panorama/redlining/static/mappinginequality.json",
    "zcta_cd": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_zcta520_natl.txt",
    "cdc_injury": "https://data.cdc.gov/resource/nt65-c7a7.json",
    "cdc_suicide": "https://data.cdc.gov/resource/w26f-tf3h.json",
}

STATES = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
    "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT",
    "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY", "72": "PR",
}
ABBR_TO_FIPS = {v: k for k, v in STATES.items()}
STATE_NAMES = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA", "COLORADO": "CO",
    "CONNECTICUT": "CT", "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC", "FLORIDA": "FL", "GEORGIA": "GA",
    "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM",
    "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
}
# EJI lists some counties that no longer exist; map them to the modern county that absorbed them.
HISTORIC_COUNTIES = {
    ("GA", "campbell"): "13121", ("GA", "milton"): "13121",  # merged into Fulton 1932
    ("TN", "james"): "47065",  # merged into Hamilton 1919
    ("VA", "nansemond"): "51800",  # now City of Suffolk
    ("VA", "princessanne"): "51810",  # now City of Virginia Beach
    ("VA", "norfolk"): "51550",  # Norfolk County -> City of Chesapeake
    ("VA", "elizabethcity"): "51650",  # now City of Hampton
    ("VA", "warwick"): "51700",  # now City of Newport News
    ("DC", "washingtondc"): "11001",
}

manifest = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "datasets": {}}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fetch(url, binary=True, timeout=180, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            log(f"  retry {i + 1} for {url}: {e}")
            time.sleep(2 * (i + 1))
    raise last


def exists(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def write_json(name, obj):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
    log(f"  wrote {name} ({os.path.getsize(path) / 1024:.0f} KB)")


def norm_county(name):
    n = name.lower()
    n = re.sub(r"\b(county|parish|borough|census area|municipality|city and borough|planning region)\b", "", n)
    n = n.replace("saint ", "st ").replace("ste.", "ste").replace("st.", "st")
    return re.sub(r"[^a-z]", "", n)


# ---------------------------------------------------------------- Gazetteer (county names + centroids)
def build_gazetteer():
    log("Gazetteer counties")
    for y in range(TODAY.year, TODAY.year - 5, -1):
        url = SOURCES["gazetteer"].format(y=y)
        if exists(url):
            break
    else:
        raise RuntimeError("No gazetteer found")
    z = zipfile.ZipFile(io.BytesIO(fetch(url)))
    text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    counties = {}
    by_name = {}
    text = text.lstrip("\ufeff")
    delim = "|" if "|" in text.splitlines()[0] else "\t"
    for row in csv.DictReader(io.StringIO(text), delimiter=delim):
        row = {k.strip(): v.strip() for k, v in row.items()}
        fips = row["GEOID"]
        st = row["USPS"]
        counties[fips] = {"name": row["NAME"], "st": st,
                          "lat": round(float(row["INTPTLAT"]), 4), "lon": round(float(row["INTPTLONG"]), 4)}
        key = (st, norm_county(row["NAME"]))
        # Prefer the county over an independent city with the same name (VA, MD, MO)
        if key not in by_name or not row["NAME"].lower().endswith(" city"):
            by_name[key] = fips
    manifest["datasets"]["gazetteer"] = {"source": url, "year": y, "records": len(counties)}
    return counties, by_name


def match_county(by_name, st, name):
    k = norm_county(name)
    if (st, k) in HISTORIC_COUNTIES:
        return HISTORIC_COUNTIES[(st, k)]
    if (st, k) in by_name:
        return by_name[(st, k)]
    if (st, k + "city") in by_name:
        return by_name[(st, k + "city")]
    return None


# ---------------------------------------------------------------- ACS race/ethnicity by county
def build_acs():
    log("ACS B03002")
    for y in range(TODAY.year, TODAY.year - 5, -1):
        url = SOURCES["acs"].format(y=y)
        if exists(url):
            break
    else:
        raise RuntimeError("No ACS file found")
    log(f"  using ACS 5-year {y}")
    text = fetch(url, timeout=600).decode("utf-8", "replace")
    rows = csv.reader(io.StringIO(text), delimiter="|")
    header = next(rows)
    ix = {h: i for i, h in enumerate(header)}
    out = {}
    # Districts from the same file: 119th Congress (5001900US), state senate (610U900US), state house (620L900US).
    dist_prefix = {"5001900US": "cd", "610U900US": "sldu", "620L900US": "sldl"}
    districts = {"cd": {}, "sldu": {}, "sldl": {}}
    for r in rows:
        g = r[0]
        kind = dist_prefix.get(g[:9])
        if kind:
            try:
                tot, nhw, blk, hisp, aian, asn, nhpi, oth, multi = (int(r[ix[k]]) for k in (
                    "B03002_E001", "B03002_E003", "B03002_E004", "B03002_E012", "B03002_E005", "B03002_E006", "B03002_E007", "B03002_E008", "B03002_E009"))
            except (ValueError, KeyError):
                continue
            if tot > 0:
                pc = lambda x: round(100 * x / tot, 1)  # noqa: E731
                districts[kind][g[9:]] = [tot, pc(tot - nhw), pc(blk), pc(hisp), pc(asn), pc(aian), pc(nhpi), pc(oth + multi)]
            continue
        if not g.startswith("0500000US"):
            continue
        try:
            tot = int(r[ix["B03002_E001"]])
            nhw = int(r[ix["B03002_E003"]])
            blk = int(r[ix["B03002_E004"]])
            aian = int(r[ix["B03002_E005"]])
            asn = int(r[ix["B03002_E006"]])
            nhpi = int(r[ix["B03002_E007"]])
            oth = int(r[ix["B03002_E008"]]) + int(r[ix["B03002_E009"]])
            hisp = int(r[ix["B03002_E012"]])
        except (ValueError, KeyError):
            continue
        if tot <= 0:
            continue
        out[g[-5:]] = {
            "pop": tot,
            "minority": round(100 * (tot - nhw) / tot, 1),
            "black": round(100 * blk / tot, 1),
            "hispanic": round(100 * hisp / tot, 1),
            "native": round(100 * aian / tot, 1),
            "asian": round(100 * asn / tot, 1),
            "pacific": round(100 * nhpi / tot, 1),
            "other": round(100 * oth / tot, 1),
        }
    write_json("districts.json", {"fields": ["pop", "pct_minority", "pct_black", "pct_hispanic", "pct_asian", "pct_native", "pct_pacific", "pct_other_or_multiracial"], "vintage": f"ACS 5-year {y - 4}-{y}", **districts})
    manifest["datasets"]["districts"] = {"source": url, "publisher": "U.S. Census Bureau", "vintage": f"ACS 5-year {y - 4}-{y}",
                                         "congressional": len(districts["cd"]), "state_senate": len(districts["sldu"]),
                                         "state_house": len(districts["sldl"])}
    manifest["datasets"]["acs"] = {"source": url, "vintage": f"ACS 5-year {y - 4}-{y}", "records": len(out),
                                   "publisher": "U.S. Census Bureau", "table": "B03002 Hispanic or Latino Origin by Race"}
    return out, y


# ---------------------------------------------------------------- EJI lynchings by county
def build_lynchings(by_name, counties):
    log("EJI lynchings")
    pdf = fetch(SOURCES["eji_pdf"])
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf)
        tmp = f.name
    try:
        text = subprocess.run(["pdftotext", "-layout", tmp, "-"], capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(tmp)
    state = None
    out, unmatched, total = {}, [], 0
    pair = re.compile(r"([A-Z][A-Za-z.,'\- ]*?[A-Za-z.*])\s{2,}(\d+)(?=\s|$)")
    heading = re.compile(r"^([A-Z][A-Z .,]+?)(?:\s{2,}.*)?$")
    for line in text.splitlines():
        s = line.strip()
        m = heading.match(s)
        if m and (m.group(1) in STATE_NAMES or m.group(1).startswith("WASHINGTON, D")):
            state = "DC" if m.group(1).startswith("WASHINGTON, D") else STATE_NAMES[m.group(1)]
            continue
        if not state or s.startswith(("County", "Jurisdiction")) or "Lynching" in s or "Victims" in s or "Updated" in s:
            continue
        for name, num in pair.findall(s):
            n = int(num)
            total += n
            fips = match_county(by_name, state, name.strip())
            if fips:
                out[fips] = out.get(fips, 0) + n
            else:
                unmatched.append(f"{name.strip()}, {state} ({n})")
    if unmatched:
        log("  unmatched EJI counties:", "; ".join(unmatched))
    manifest["datasets"]["lynchings"] = {
        "source": SOURCES["eji_pdf"], "publisher": "Equal Justice Initiative",
        "description": "Documented African American racial terror lynching victims, 1877-1950, per county (EJI county supplement, updated Feb 2020)",
        "total_victims": total, "counties": len(out), "unmatched": unmatched,
    }
    return out


# ---------------------------------------------------------------- Mapping Police Violence
def build_police(by_name):
    log("Mapping Police Violence")
    import openpyxl  # noqa: PLC0415

    data = fetch(SOURCES["mpv"], timeout=300)
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h else "" for h in next(rows)]

    def col(prefix):
        for i, h in enumerate(header):
            if h.lower().startswith(prefix.lower()):
                return i
        raise KeyError(prefix)

    c = {k: col(p) for k, p in {
        "name": "Victim's name", "age": "Victim's age", "race": "Victim's race", "date": "Date of Incident",
        "city": "City", "state": "State", "county": "County", "agency": "Agency responsible",
        "armed": "Armed/Unarmed", "lat": "Latitude", "lon": "Longitude", "link": "Link to news",
    }.items()}
    race_code = {"Black": "B", "White": "W", "Hispanic": "H", "Asian": "A", "Native American": "N",
                 "Pacific Islander": "P", "Unknown race": "U", "Unknown Race": "U"}
    points, by_county, black_by_county = [], Counter(), Counter()
    years = Counter()
    latest = None
    for r in rows:
        if not r or r[c["date"]] is None:
            continue
        d = r[c["date"]]
        if isinstance(d, dt.datetime):
            d = d.date()
        elif isinstance(d, str):
            try:
                d = dt.datetime.strptime(d.strip(), "%m/%d/%Y").date()
            except ValueError:
                continue
        years[d.year] += 1
        latest = max(latest, d) if latest else d
        race = race_code.get(str(r[c["race"]] or "").strip(), "U")
        st = str(r[c["state"]] or "").strip()
        cty = str(r[c["county"]] or "").strip()
        fips = match_county(by_name, st, cty) if st and cty else None
        if fips:
            by_county[fips] += 1
            if race == "B":
                black_by_county[fips] += 1
        try:
            lat, lon = float(r[c["lat"]]), float(r[c["lon"]])
        except (TypeError, ValueError):
            continue
        armed = str(r[c["armed"]] or "")
        points.append([
            round(lat, 4), round(lon, 4), d.isoformat(), race,
            str(r[c["name"]] or "").strip()[:60], str(r[c["city"]] or "").strip(), st,
            str(r[c["agency"]] or "").strip()[:80],
            "U" if armed.lower().startswith("unarmed") else ("A" if "armed" in armed.lower() else "?"),
        ])
    points.sort(key=lambda p: p[2], reverse=True)
    write_json("police_killings.json", {
        "fields": ["lat", "lon", "date", "race", "name", "city", "state", "agency", "armed"],
        "race_codes": {v: k for k, v in race_code.items()},
        "rows": points,
    })
    manifest["datasets"]["police_killings"] = {
        "source": "https://mappingpoliceviolence.org/", "download": SOURCES["mpv"],
        "publisher": "Mapping Police Violence", "records": len(points), "latest_incident": latest.isoformat() if latest else None,
        "by_year": dict(sorted(years.items())),
    }
    return by_county, black_by_county


# ---------------------------------------------------------------- FBI hate crimes
RACE_BIAS = ("Anti-Black", "Anti-Hispanic", "Anti-Asian", "Anti-American Indian", "Anti-Arab",
             "Anti-Multiple Races", "Anti-Other Race", "Anti-Native Hawaiian", "Anti-Other Ethnicity",
             "Anti-White")


def build_hate_crimes(by_name):
    log("FBI hate crimes")
    signed = json.loads(fetch(SOURCES["fbi_signed"], binary=False))
    url = list(signed.values())[0]
    z = zipfile.ZipFile(io.BytesIO(fetch(url, timeout=600)))
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    years = Counter()
    rows = []
    with z.open(name) as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace")):
            y = int(row["data_year"])
            years[y] += 1
            rows.append((y, row["ori"], row["state_abbr"], row["pug_agency_name"], row["bias_desc"]))
    last_year = max(years)
    first_year = last_year - 4
    by_ori = defaultdict(lambda: {"total": 0, "race": 0, "black": 0})
    ori_meta = {}
    state_tot = Counter()
    for y, ori, st, agency, bias in rows:
        if y < first_year:
            continue
        rec = by_ori[ori]
        rec["total"] += 1
        state_tot[st] += 1
        if any(b in bias for b in RACE_BIAS):
            rec["race"] += 1
        if "Anti-Black" in bias:
            rec["black"] += 1
        ori_meta[ori] = (st, agency)
    # Agency coordinates from the FBI CDE agency directory
    coords = {}
    for st in sorted({m[0] for m in ori_meta.values()}):
        try:
            d = json.loads(fetch(SOURCES["fbi_agencies"].format(st=st), binary=False, timeout=60))
        except Exception as e:  # noqa: BLE001
            log(f"  agency lookup failed for {st}: {e}")
            continue
        if not isinstance(d, dict):
            log(f"  unexpected agency payload for {st}")
            continue
        for cty, agencies in d.items():
            if not isinstance(agencies, list):
                continue
            for a in agencies:
                if not isinstance(a, dict) or not a.get("ori"):
                    continue
                coords[a["ori"]] = (a.get("latitude"), a.get("longitude"), (a.get("counties") or cty or "").split(",")[0])
        time.sleep(0.2)
    points, by_county, missing = [], Counter(), 0
    for ori, rec in by_ori.items():
        st, agency = ori_meta[ori]
        lat, lon, cty = coords.get(ori, (None, None, ""))
        fips = match_county(by_name, st, cty.title()) if cty else None
        if fips:
            by_county[fips] += rec["race"]
        if lat is None or lon is None:
            missing += 1
            continue
        points.append([round(lat, 4), round(lon, 4), agency, st, rec["total"], rec["race"], rec["black"]])
    points.sort(key=lambda p: -p[5])
    write_json("hate_crimes.json", {
        "years": [first_year, last_year],
        "fields": ["lat", "lon", "agency", "state", "total", "race_ethnicity_bias", "anti_black"],
        "rows": points, "state_totals": dict(state_tot),
    })
    manifest["datasets"]["hate_crimes"] = {
        "source": "https://cde.ucr.cjis.gov/", "publisher": "FBI Uniform Crime Reporting (Crime Data Explorer)",
        "years": f"{first_year}-{last_year}", "agencies": len(points), "agencies_without_coordinates": missing,
        "incidents": sum(state_tot.values()),
        "caveat": "Hate crime reporting to the FBI is voluntary and uneven; low counts can mean low reporting.",
    }
    return by_county, (first_year, last_year)


# ---------------------------------------------------------------- HOLC redlining
def build_redlining():
    log("Mapping Inequality HOLC")
    d = json.loads(fetch(SOURCES["holc"], timeout=300))
    feats = []

    def rnd(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], 4), round(c[1], 4)]
        return [rnd(x) for x in c]

    for f in d["features"]:
        p = f.get("properties") or {}
        g = (p.get("grade") or "").strip().upper()
        if g not in ("A", "B", "C", "D") or not f.get("geometry"):
            continue
        feats.append({"type": "Feature", "properties": {"g": g, "c": p.get("city"), "s": p.get("state"), "l": p.get("label")},
                      "geometry": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}})
    write_json("redlining.json", {"type": "FeatureCollection", "features": feats})
    manifest["datasets"]["redlining"] = {
        "source": "https://dsl.richmond.edu/panorama/redlining/", "publisher": "Mapping Inequality (University of Richmond)",
        "description": "HOLC residential security maps, 1935-1940", "features": len(feats),
        "grade_counts": dict(Counter(f["properties"]["g"] for f in feats)),
    }


# ---------------------------------------------------------------- ZIP -> congressional district (119th)
def build_zip_districts():
    log("ZCTA -> CD119")
    text = fetch(SOURCES["zcta_cd"], binary=False, timeout=300).lstrip("﻿")
    z = defaultdict(dict)
    for row in csv.DictReader(io.StringIO(text), delimiter="|"):
        zc, cd = row["GEOID_ZCTA5_20"], row["GEOID_CD119_20"]
        if not zc or not cd:
            continue
        z[zc][cd] = z[zc].get(cd, 0) + int(row["AREALAND_PART"] or 0)
    out = {}
    for zc, cds in z.items():
        tot = sum(cds.values()) or 1
        # keep districts covering >=1% of the ZCTA land area, largest first
        out[zc] = [cd for cd, a in sorted(cds.items(), key=lambda kv: -kv[1]) if a / tot >= 0.01 or len(cds) == 1]
    write_json("zip_districts.json", out)
    manifest["datasets"]["zip_districts"] = {"source": SOURCES["zcta_cd"], "publisher": "U.S. Census Bureau",
                                             "description": "2020 ZCTA to 119th Congress district relationship", "zips": len(out)}


# ---------------------------------------------------------------- CDC national injury deaths by race
def socrata(url, where, select=None, limit=50000):
    q = {"$where": where, "$limit": str(limit)}
    if select:
        q["$select"] = select
    return json.loads(fetch(url + "?" + urllib.parse.urlencode(q), binary=False, timeout=180))


def build_cdc_deaths():
    log("CDC injury deaths by race")
    races = {"Non-Hispanic black": "Black", "Non-Hispanic white": "White", "Hispanic": "Hispanic", "All races": "All"}
    rows = socrata(SOURCES["cdc_injury"],
                   "sex='Both sexes' AND age_years='All Ages' AND injury_mechanism in('Suffocation','All Mechanisms')")
    injury = defaultdict(lambda: defaultdict(dict))  # mechanism -> intent -> race -> {year: [deaths, rate]}
    years = set()
    for r in rows:
        race = races.get(r["race"])
        if not race:
            continue
        y = int(r["year"])
        years.add(y)
        mech = "suffocation" if r["injury_mechanism"] == "Suffocation" else "all"
        injury[mech][r["injury_intent"]].setdefault(race, {})[y] = [int(float(r["deaths"])), round(float(r["age_specific_rate"]), 2)]
    sui = socrata(SOURCES["cdc_suicide"],
                  "classification='Demographic Characteristic' AND `group`='Race and Hispanic origin' AND estimate_type like '%age adjusted%'")
    suicide = defaultdict(dict)
    for r in sui:
        if not r.get("estimate"):
            continue
        suicide[r["subgroup"]][r["time_period"]] = float(r["estimate"])
    write_json("cdc_deaths.json", {
        "injury_years": [min(years), max(years)] if years else None,
        "injury": injury,
        "suicide_age_adjusted": suicide,
        "notes": {
            "suffocation": "CDC 'suffocation' mechanism = hanging, strangulation and suffocation (ICD-10 X70, X91, Y20, W75-W84 and related). Most suffocation suicides are hangings.",
            "rates": "Injury rates are crude deaths per 100,000. Suicide rates are age-adjusted per 100,000.",
        },
    })
    manifest["datasets"]["cdc_deaths"] = {
        "source": "https://data.cdc.gov/", "publisher": "CDC National Center for Health Statistics",
        "injury": f"{SOURCES['cdc_injury']} ({min(years)}-{max(years)})" if years else SOURCES["cdc_injury"],
        "suicide": SOURCES["cdc_suicide"],
        "latest_suicide_year": max((max(v) for v in suicide.values() if v), default=None),
        "caveat": "National totals only: CDC does not allow state/county breakdowns by race through automated access.",
    }


# ---------------------------------------------------------------- CDC WONDER manual exports (state x race x intent)
def num(v):
    v = (v or "").replace(",", "").strip()
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return None  # "Suppressed", "Unreliable", "Not Applicable"


def build_cdc_wonder():
    """Parse tab-delimited CDC WONDER exports dropped into website/data/cdc_wonder/ by volunteers."""
    folder = os.path.join(OUT, "cdc_wonder")
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".txt")) if os.path.isdir(folder) else []
    if not files:
        log("CDC WONDER: no exports yet (website/data/cdc_wonder/*.txt)")
        return
    log(f"CDC WONDER: {len(files)} export(s)")
    rows, meta = [], []
    for fn in files:
        with open(os.path.join(folder, fn), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        data_lines, footer = [], []
        for ln in lines:
            if ln.strip().strip('"') == "---":
                footer = lines[lines.index(ln) + 1:]
                break
            data_lines.append(ln)
        reader = csv.reader(data_lines, delimiter="\t", quotechar='"')
        header = next(reader, [])
        col = {h.strip(): i for i, h in enumerate(header)}
        def find(*names):
            for n in names:
                for h, i in col.items():
                    if h.lower() == n.lower():
                        return i
            return None
        c_state, c_race = find("State"), find("Single Race 6", "Race", "Single Race 3")
        c_cat = find("UCD - ICD Sub-Chapter", "UCD - Injury Intent", "ICD Sub-Chapter", "Injury Intent", "UCD - ICD-10 Codes", "Cause of death")
        c_year = find("Year")
        c_d, c_p, c_r = find("Deaths"), find("Population"), find("Crude Rate")
        if c_state is None or c_d is None:
            log(f"  skipped {fn}: needs at least State and Deaths columns")
            continue
        n = 0
        for r in reader:
            if not r or len(r) <= c_d or (r[0] or "").strip().lower() == "total" or not r[c_state].strip():
                continue
            g = lambda c: r[c].strip() if c is not None and c < len(r) else ""
            rows.append({"file": fn, "state": g(c_state), "race": g(c_race) or "All", "category": g(c_cat) or "All",
                         "year": g(c_year) or None, "deaths": num(g(c_d)), "population": num(g(c_p)),
                         "rate": num(g(c_r)), "flag": None if num(g(c_d)) is not None else g(c_d)})
            n += 1
        dataset = next((x.strip('"').split(":", 1)[1].strip() for x in footer if x.strip('"').startswith("Dataset:")), "")
        meta.append({"file": fn, "rows": n, "dataset": dataset})
    write_json("cdc_wonder_states.json", {"files": meta, "rows": rows})
    manifest["datasets"]["cdc_wonder"] = {"source": "https://wonder.cdc.gov/", "publisher": "CDC WONDER (manual exports by volunteers)",
                                          "files": meta, "records": len(rows)}


# ---------------------------------------------------------------- City "suspicious person" 911 calls
# Resident-initiated calls only. Outcomes are grouped into three buckets so cities can be compared.
# Locations are binned to a ~500 m grid and bins with fewer than 3 calls are dropped.
CITY_CALLS = [
    {
        "city": "San Francisco, CA", "portal": "https://data.sfgov.org/d/2zdj-bwza",
        "url": "https://data.sf.gov/resource/2zdj-bwza.json", "time": "received_datetime",
        "where": "call_type_final_desc='SUSPICIOUS PERSON' AND onview_flag='N'",
        "call_type": "Suspicious person (final call type), resident-initiated",
        "outcome": "disposition", "point": "intersection_point",
        "enforce": {"ARR", "CIT", "REP"}, "nothing": {"GOA", "UTL", "NOM"}, "drop": {"CAN", "DUP"},
    },
    {
        "city": "Seattle, WA", "portal": "https://data.seattle.gov/d/33kz-ixgy",
        "url": "https://data.seattle.gov/resource/33kz-ixgy.json", "time": "cad_event_original_time_queued",
        "where": "initial_call_type='SUSPICIOUS PERSON, VEHICLE, OR INCIDENT'",
        "call_type": "Suspicious person, vehicle or incident (initial call type)",
        "outcome": "cad_event_clearance_description", "lat": "dispatch_latitude", "lon": "dispatch_longitude",
        "enforce": {"PHYSICAL ARREST MADE", "CITATION", "REPORT WRITTEN (NO ARREST)", "OTHER REPORT MADE", "FOLLOW-UP REPORT MADE"},
        "nothing": {"UNABLE TO LOCATE INCIDENT OR COMPLAINANT", "FALSE COMPLAINT/UNFOUNDED", "NO POLICE ACTION POSSIBLE OR NECESSARY"},
        "drop": {"DUPLICATE EVENT", "CANCELLED EVENT", "RESPONDING UNIT(S) CANCELLED BY RADIO"},
    },
    {
        "city": "New Orleans, LA", "portal": "https://data.nola.gov/", "nola": True, "time": "timecreate",
        "where": "initialtypetext='SUSPICIOUS PERSON' AND selfinitiated='N'",
        "call_type": "Suspicious person (initial call type), resident-initiated",
        "outcome": "dispositiontext", "point": "location",
        "enforce": {"REPORT TO FOLLOW"}, "nothing": {"GONE ON ARRIVAL", "UNFOUNDED"},
        "drop": {"DUPLICATE", "VOID", "Canceled By Complainant"},
    },
]


def nola_datasets(years):
    cat = json.loads(fetch("https://api.us.socrata.com/api/catalog/v1?domains=data.nola.gov&q=calls%20for%20service&limit=50", binary=False))
    ids = {}
    for r in cat["results"]:
        m = re.fullmatch(r"Calls for Service (\d{4})", r["resource"]["name"].strip())
        if m and int(m.group(1)) in years:
            ids[int(m.group(1))] = r["resource"]["id"]
    return [f"https://data.nola.gov/resource/{ids[y]}.json" for y in sorted(ids)]


def soql(url, query):
    return json.loads(fetch(url + "?" + urllib.parse.urlencode({"$query": query}), binary=False, timeout=300))


def build_city_calls():
    log("City suspicious-person 911 calls")
    since = (TODAY - dt.timedelta(days=365)).isoformat()
    cities = []
    for c in CITY_CALLS:
        urls = nola_datasets({TODAY.year - 1, TODAY.year}) if c.get("nola") else [c["url"]]
        where = f"{c['where']} AND {c['time']} > '{since}'"
        outcomes, grid = Counter(), Counter()
        for url in urls:
            for r in soql(url, f"SELECT {c['outcome']} AS o, count(*) AS n WHERE {where} GROUP BY {c['outcome']} LIMIT 1000"):
                outcomes[r.get("o") or ""] += int(r["n"])
            cols = c["point"] if "point" in c else f"{c['lat']}, {c['lon']}"
            off = 0
            while True:
                rows = soql(url, f"SELECT {cols} WHERE {where} LIMIT 50000 OFFSET {off}")
                for r in rows:
                    try:
                        if "point" in c:
                            lon, lat = r[c["point"]]["coordinates"]
                        else:
                            lat, lon = float(r[c["lat"]]), float(r[c["lon"]])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if lat and lon:
                        grid[(round(lat / 0.005) * 0.005, round(lon / 0.005) * 0.005)] += 1
                if len(rows) < 50000:
                    break
                off += 50000
        # Drop grid cells far from the city's main cluster (bad geocodes, e.g. 0,0 or out of state).
        if grid:
            pts = sorted(grid.items(), key=lambda kv: -kv[1])
            clat, clon = pts[0][0]
            grid = Counter({k: v for k, v in grid.items() if abs(k[0] - clat) < 0.6 and abs(k[1] - clon) < 0.6})
        total = sum(n for o, n in outcomes.items() if o not in c["drop"])
        enforce = sum(n for o, n in outcomes.items() if o in c["enforce"])
        nothing = sum(n for o, n in outcomes.items() if o in c["nothing"])
        cities.append({
            "city": c["city"], "portal": c["portal"], "call_type": c["call_type"], "since": since,
            "calls": total, "enforcement": enforce, "nothing_found": nothing, "other": total - enforce - nothing,
            "enforcement_codes": sorted(c["enforce"]), "nothing_codes": sorted(c["nothing"]),
            "outcomes": dict(outcomes.most_common(25)),
            "points": [[round(k[0], 3), round(k[1], 3), v] for k, v in sorted(grid.items()) if v >= 3],
        })
        log(f"  {c['city']}: {total} calls, {enforce} enforcement, {len(cities[-1]['points'])} grid cells")
    write_json("city_calls.json", {"generated": TODAY.isoformat(), "cities": cities})
    manifest["datasets"]["city_calls"] = {"publisher": "City open-data portals (San Francisco, Seattle, New Orleans)",
                                          "since": since, "cities": {x["city"]: x["calls"] for x in cities},
                                          "source": "https://data.sfgov.org/d/2zdj-bwza"}


# ---------------------------------------------------------------- Racial covenants (Mapping Prejudice)
COVENANT_REPO = "UMNLibraries/mp-us-racial-covenants"


def polygon_center(geom):
    coords = geom["coordinates"]
    ring = coords[0][0] if geom["type"] == "MultiPolygon" else coords[0]
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return sum(ys) / len(ys), sum(xs) / len(xs)


def build_covenants():
    log("Mapping Prejudice racial covenants")
    listing = json.loads(fetch(f"https://api.github.com/repos/{COVENANT_REPO}/contents", binary=False))
    rows, per = [], {}
    for item in listing:
        if item["type"] != "dir":
            continue
        name = item["name"]
        url = f"https://media.githubusercontent.com/media/{COVENANT_REPO}/main/{name}/covenants-{name}.geojson"
        try:
            d = json.loads(fetch(url, timeout=600))
        except Exception as e:  # noqa: BLE001
            log(f"  skipped {name}: {e}")
            continue
        n = 0
        cells = {}
        for f in d.get("features", []):
            p, g = f.get("properties") or {}, f.get("geometry")
            if not g:
                continue
            try:
                lat, lon = polygon_center(g)
            except (IndexError, KeyError, TypeError, ZeroDivisionError):
                continue
            yr = p.get("deed_year")
            yr = int(yr) if isinstance(yr, (int, float)) and yr else None
            # ~250 m cells keep the file small; each cell keeps a count, deed-year range and the most common city.
            key = (round(lat / 0.0025) * 0.0025, round(lon / 0.0025) * 0.0025)
            c = cells.setdefault(key, [0, None, None, Counter()])
            c[0] += 1
            if yr:
                c[1] = yr if c[1] is None else min(c[1], yr)
                c[2] = yr if c[2] is None else max(c[2], yr)
            c[3][(p.get("city") or "").title()] += 1
            n += 1
        county = name.split("-", 1)[1].replace("-", " ").title()
        for (lat, lon), (cnt, y0, y1, cities) in cells.items():
            rows.append([round(lat, 4), round(lon, 4), cnt, y0, y1, cities.most_common(1)[0][0], county, name[:2].upper()])
        per[name] = n
        log(f"  {name}: {n}")
    write_json("covenants.json", {"fields": ["lat", "lon", "count", "first_year", "last_year", "city", "jurisdiction", "state"],
                                  "cell_degrees": 0.0025, "total": sum(per.values()), "rows": rows})
    manifest["datasets"]["covenants"] = {"source": f"https://github.com/{COVENANT_REPO}", "publisher": "Mapping Prejudice (University of Minnesota) and partners",
                                         "records": sum(per.values()), "cells": len(rows), "jurisdictions": per}


# ---------------------------------------------------------------- Lynchings of all races (Monroe Work Today)
MWT_URL = "https://monroeworktoday.org/explore/data/s_1_3.txt"


def mwt_group(r):
    r = float(r)
    if r == 2:
        return "B"
    if 3 <= r < 4:
        return "L"
    if 4 <= r < 5:
        return "N"
    if r in (5, 9):
        return "A"
    if r in (1, 6, 7, 8):
        return "W"
    return "U"


def build_mwt():
    log("Monroe Work Today lynchings (all races)")
    d = json.loads(fetch(MWT_URL, timeout=300))
    rows = []
    for f in d["features"]:
        p, g = f["properties"], f.get("geometry") or {}
        try:
            lon, lat = g["coordinates"][:2]
            r = mwt_group(p.get("r") or 99)
        except (KeyError, TypeError, ValueError):
            continue
        yr = int(p["yr"]) if str(p.get("yr", "")).isdigit() else None
        cty = p.get("cty_m") or p.get("cty_k") or ""
        # MWT parks cases with an unknown county offshore; keep the record but leave it off the map.
        unknown = bool(re.search(r"unknown|indeterminate", cty, re.I))
        place = ", ".join(x for x in [p.get("town") or "", "" if unknown or not cty else cty + " County", p.get("st_k") or ""] if x)
        rows.append([None if unknown else round(lat, 4), None if unknown else round(lon, 4), yr, r, (p.get("name") or "").strip(), place, (p.get("web_n") or "").strip()])
    groups = Counter(r[3] for r in rows)
    years = [r[2] for r in rows if r[2]]
    write_json("lynchings_all_races.json", {"fields": ["lat", "lon", "year", "group", "name", "place", "summary"],
                                            "groups": {"B": "Black", "L": "Latino / Mexican", "N": "Native American", "A": "Asian", "W": "White (incl. Italian, Irish)", "U": "Unknown / other"},
                                            "license": "Summaries CC BY-NC 4.0, Monroe Work Today (monroeworktoday.org)", "rows": rows})
    manifest["datasets"]["mwt"] = {"source": "https://monroeworktoday.org/", "publisher": "Monroe Work Today (auut studio)",
                                   "records": len(rows), "unmapped_unknown_county": sum(1 for r in rows if r[0] is None), "years": f"{min(years)}-{max(years)}", "groups": dict(groups),
                                   "license": "CC BY-NC 4.0 (attribution, non-commercial)"}


# ---------------------------------------------------------------- BJS Police-Public Contact Survey
BJS_PPCS = "https://bjs.ojp.gov/document/cbpp20.zip"


def bjs_table(z, name):
    text = z.read(name).decode("latin-1").lstrip("ï»¿﻿")
    return list(csv.reader(io.StringIO(text)))


def pnum(v):
    try:
        return float(v.replace(",", ""))
    except (AttributeError, ValueError):
        return None


def build_bjs():
    log("BJS Police-Public Contact Survey 2020")
    z = zipfile.ZipFile(io.BytesIO(fetch(BJS_PPCS, timeout=300)))
    races = {"White": "White", "Black": "Black", "Hispanic": "Hispanic", "Asian": "Asian"}
    force, street = {}, {}
    for row in bjs_table(z, "cbpp20t03.csv"):
        if len(row) > 12 and row[1]:
            k = row[1].split("/")[0].rstrip("*")
            if k in races:
                force[races[k]] = pnum(row[12])
    for row in bjs_table(z, "cbpp20t06.csv"):
        if len(row) > 21 and row[1]:
            k = row[1].split("/")[0].rstrip("*")
            if k in races:
                street[races[k]] = {"no_enforcement": pnum(row[15]), "search_or_arrest": pnum(row[21])}
    out = {
        "survey": "Police-Public Contact Survey, 2020", "report": "Contacts Between Police and the Public, 2020 (NCJ 304527)",
        "report_url": "https://bjs.ojp.gov/library/publications/contacts-between-police-and-public-2020",
        "force_pct_of_contacts": force, "street_stops": street,
        "notes": "Percent of residents 16+ with any police contact whose contact involved the threat or nonfatal use of force (table 3), and "
                 "outcomes of street stops (table 6). Blank values were suppressed by BJS for small samples.",
    }
    write_json("bjs_contacts.json", out)
    manifest["datasets"]["bjs"] = {"source": out["report_url"], "publisher": "Bureau of Justice Statistics", "survey": out["survey"],
                                   "force_pct_of_contacts": force}


# ---------------------------------------------------------------- County priority index
def pctl(values, q):
    v = sorted(values)
    if not v:
        return 0
    return v[min(len(v) - 1, int(q * (len(v) - 1)))]


COUNTY_EXTRA_FIELDS = ["pct_asian", "pct_native", "pct_pacific", "pct_other_or_multiracial"]


def county_extra(a):
    return [a.get("asian", 0), a.get("native", 0), a.get("pacific", 0), a.get("other", 0)]


def refresh_county_demographics(acs):
    """Standalone `acs` run: update the race columns in counties.json without rebuilding everything else."""
    path = os.path.join(OUT, "counties.json")
    d = json.load(open(path, encoding="utf-8"))
    d["fields"] = d["fields"][:15] + COUNTY_EXTRA_FIELDS
    for r in d["rows"]:
        a = acs.get(r[0])
        if a:
            r[5:9] = [a["pop"], a["minority"], a["black"], a["hispanic"]]
        r[15:] = county_extra(a or {})
    write_json("counties.json", d)


# Priority-score weights. Change these to re-balance the heat map (they should add up to 1),
# then run the full build: python3 scripts/build_data.py
PRIORITY_WEIGHTS = {"lynchings": 0.30, "police_killings_per_capita": 0.30, "race_hate_crimes_per_capita": 0.15, "pct_minority": 0.25}


def build_priority(counties, acs, lynch, police, police_black, hate):
    log("Priority index")
    # Smoothed per-100k rates: adding a 25k-person prior keeps tiny counties with one incident from dominating.
    rates_p = {f: 1e5 * police[f] / (acs[f]["pop"] + 25000) for f in acs if police.get(f)}
    rates_h = {f: 1e5 * hate[f] / (acs[f]["pop"] + 25000) for f in acs if hate.get(f)}
    cap_l = pctl([v for v in lynch.values() if v], 0.95) or 1
    cap_p = pctl(list(rates_p.values()), 0.95) or 1
    cap_h = pctl(list(rates_h.values()), 0.95) or 1
    thr = {"l": pctl([v for v in lynch.values() if v], 0.5), "p": pctl(list(rates_p.values()), 0.75),
           "h": pctl(list(rates_h.values()), 0.75), "m": 40.0}
    rows = []
    for f, a in acs.items():
        c = counties.get(f)
        if not c:
            continue
        L = min(1, math.log1p(lynch.get(f, 0)) / math.log1p(cap_l))
        P = min(1, rates_p.get(f, 0) / cap_p)
        H = min(1, rates_h.get(f, 0) / cap_h)
        M = a["minority"] / 100
        W = PRIORITY_WEIGHTS
        score = round(W["lynchings"] * L + W["police_killings_per_capita"] * P + W["race_hate_crimes_per_capita"] * H + W["pct_minority"] * M, 3)
        overlap = sum([lynch.get(f, 0) >= max(thr["l"], 1), rates_p.get(f, 0) >= thr["p"] and police.get(f, 0) >= 2,
                       rates_h.get(f, 0) >= thr["h"] and hate.get(f, 0) >= 2, a["minority"] >= thr["m"]])
        rows.append([f, c["name"], c["st"], c["lat"], c["lon"], a["pop"], a["minority"], a["black"], a["hispanic"],
                     lynch.get(f, 0), police.get(f, 0), police_black.get(f, 0), hate.get(f, 0), score, overlap] + county_extra(a))
    rows.sort(key=lambda r: -r[13])
    write_json("counties.json", {
        "fields": ["fips", "name", "state", "lat", "lon", "pop", "pct_minority", "pct_black", "pct_hispanic",
                   "lynchings", "police_killings", "police_killings_black", "race_hate_crimes", "score", "overlap"] + COUNTY_EXTRA_FIELDS,
        "weights": PRIORITY_WEIGHTS,
        "rows": rows,
    })
    manifest["datasets"]["priority_index"] = {
        "description": "Composite county score = 0.30 x lynchings (log-scaled) + 0.30 x police killings per capita + "
                       "0.15 x race/ethnicity-bias hate crimes per capita + 0.25 x minority population share. "
                       "Per-capita rates are smoothed (population + 25,000) so very small counties are not dominated by single incidents. "
                       "Each factor is capped at its 95th percentile and scaled 0-1. 'overlap' counts how many factors "
                       "are high (lynchings >= median of counties with any, killings/hate crime rates >= 75th pct, minority >= 40%).",
        "counties": len(rows),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    # Standalone builders: `python3 scripts/build_data.py calls covenants` reruns just those and keeps the rest of the manifest.
    standalone = {"cdc": build_cdc_deaths, "wonder": build_cdc_wonder, "calls": build_city_calls, "covenants": build_covenants,
                  "mwt": build_mwt, "bjs": build_bjs, "acs": lambda: refresh_county_demographics(build_acs()[0])}
    if only and only <= set(standalone):
        global manifest
        manifest = json.load(open(os.path.join(OUT, "manifest.json")))
        manifest["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        for k in standalone:
            if k in only:
                standalone[k]()
        json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
        return
    counties, by_name = build_gazetteer()
    acs, _ = build_acs()
    lynch = build_lynchings(by_name, counties)
    police, police_black = build_police(by_name)
    hate, _ = build_hate_crimes(by_name)
    build_priority(counties, acs, lynch, police, police_black, hate)
    if not only or "redlining" in only:
        build_redlining()
    if not only or "zip" in only:
        build_zip_districts()
    build_cdc_deaths()
    build_cdc_wonder()
    # Newer sources: a failure in one shouldn't block the weekly refresh of the others.
    try:
        previous = json.load(open(os.path.join(OUT, "manifest.json")))["datasets"]
    except (OSError, ValueError, KeyError):
        previous = {}
    for fn, key in ((build_city_calls, "city_calls"), (build_covenants, "covenants"), (build_mwt, "mwt"), (build_bjs, "bjs")):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            log(f"  {fn.__name__} failed, keeping last week's file: {e}")
            if key in previous:
                manifest["datasets"][key] = previous[key]
    manifest_path = os.path.join(OUT, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log("done")


if __name__ == "__main__":
    main()
