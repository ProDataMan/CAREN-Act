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
    for r in rows:
        g = r[0]
        if not g.startswith("0500000US"):
            continue
        try:
            tot = int(r[ix["B03002_E001"]])
            nhw = int(r[ix["B03002_E003"]])
            blk = int(r[ix["B03002_E004"]])
            aian = int(r[ix["B03002_E005"]])
            asn = int(r[ix["B03002_E006"]])
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
        }
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


# ---------------------------------------------------------------- County priority index
def pctl(values, q):
    v = sorted(values)
    if not v:
        return 0
    return v[min(len(v) - 1, int(q * (len(v) - 1)))]


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
        score = round(0.3 * L + 0.3 * P + 0.15 * H + 0.25 * M, 3)
        overlap = sum([lynch.get(f, 0) >= max(thr["l"], 1), rates_p.get(f, 0) >= thr["p"] and police.get(f, 0) >= 2,
                       rates_h.get(f, 0) >= thr["h"] and hate.get(f, 0) >= 2, a["minority"] >= thr["m"]])
        rows.append([f, c["name"], c["st"], c["lat"], c["lon"], a["pop"], a["minority"], a["black"], a["hispanic"],
                     lynch.get(f, 0), police.get(f, 0), police_black.get(f, 0), hate.get(f, 0), score, overlap])
    rows.sort(key=lambda r: -r[13])
    write_json("counties.json", {
        "fields": ["fips", "name", "state", "lat", "lon", "pop", "pct_minority", "pct_black", "pct_hispanic",
                   "lynchings", "police_killings", "police_killings_black", "race_hate_crimes", "score", "overlap"],
        "weights": {"lynchings": 0.3, "police_killings_per_capita": 0.3, "race_hate_crimes_per_capita": 0.15, "pct_minority": 0.25},
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
    if only == {"cdc"}:
        global manifest
        manifest = json.load(open(os.path.join(OUT, "manifest.json")))
        build_cdc_deaths()
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
    manifest_path = os.path.join(OUT, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log("done")


if __name__ == "__main__":
    main()
