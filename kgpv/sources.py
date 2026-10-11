"""Version-pinned, resumable official-provider download connectors.

ERA5 is produced by ECMWF. NCAR is a public distributor of that same dataset,
not a substituted irradiation model. CDS is used for the newest years.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import requests

CRU = "https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.10/cruts.2604091129.v4.10/tmp/"
GPCC = "https://opendata.dwd.de/climate_environment/GPCC/GPCC_Precipitation_Analysis_Monthly/Version_2025/050_degree/"
NCAR = "https://tds.gdex.ucar.edu/thredds/fileServer/files/g/d633001_nc/e5.moda.fc.sfc.accumu/"
BASELINE = "https://data.mendeley.com/public-api/datasets/z3byd8jyfn/files?folder_id=root&version=1"

def download(url, target, expected_sha256=None):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if expected_sha256 and digest != expected_sha256:
            raise ValueError(f"Checksum mismatch: {target.name}")
        return target
    temporary = target.with_suffix(target.suffix+'.partial')
    digest = hashlib.sha256()
    try:
        with requests.get(url, stream=True, timeout=(20, 180)) as r:
            r.raise_for_status()
            with temporary.open('wb') as f:
                for chunk in r.iter_content(1024*1024):
                    f.write(chunk); digest.update(chunk)
        if expected_sha256 and digest.hexdigest() != expected_sha256:
            raise ValueError(f"Checksum mismatch: {target.name}")
        temporary.replace(target)
        target.with_suffix(target.suffix+'.source.json').write_text(json.dumps({"url":url,"sha256":digest.hexdigest()},indent=2))
        print(json.dumps({"event":"downloaded","file":target.name}), flush=True)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target

def fetch_baseline(raw):
    r = requests.get(BASELINE,timeout=30); r.raise_for_status()
    item = next(x for x in r.json() if x['filename']=='KGPV_PVmcSi_05x05.csv')
    return download(item['content_details']['download_url'],Path(raw)/item['filename'],item['content_details']['sha256_hash'])

def fetch_era5_ncar(raw, start=1996, end=2022):
    jobs = []
    for y in range(start,end+1):
        name=f'e5.moda.fc.sfc.accumu.128_169_ssrd.ll025sc.{y}010100_{y}120100.nc'
        jobs.append((f'{NCAR}{y}/{name}', Path(raw)/name))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda job:download(*job),jobs))

def fetch_era5_cds(raw,start=2023,end=2025):
    """Uses the user's configured CDS_API_KEY / .cdsapirc; never saves credentials."""
    import cdsapi
    client=cdsapi.Client()
    for year in range(start,end+1):
        path=Path(raw)/f'era5-cds-ssrd-{year}.nc'
        if path.exists():continue
        request={"product_type":["monthly_averaged_reanalysis"],"variable":["surface_solar_radiation_downwards"],
                 "year":[str(year)],"month":[f'{m:02}' for m in range(1,13)],"time":["00:00"],
                 "data_format":"netcdf","download_format":"unarchived"}
        partial=path.with_suffix('.partial.nc')
        client.retrieve('reanalysis-era5-single-levels-monthly-means',request,str(partial))
        partial.replace(path)
        path.with_suffix('.source.json').write_text(json.dumps({"dataset":"reanalysis-era5-single-levels-monthly-means","request":request,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()},indent=2))

def fetch_climate(raw):
    jobs=[]
    for period in ['1991.2000','2001.2010','2011.2020','2021.2025']:
        name=f'cru_ts4.10.{period}.tmp.dat.nc.gz';jobs.append((CRU+name,Path(raw)/name))
    for period in ['1996_2000','2001_2005','2006_2010','2011_2015','2016_2020','2021_2024']+[f'2025_{m:02}' for m in range(1,13)]:
        name=f'gpcc_precipitation_analysis_monthly_{period}_v2025_050.nc.gz';jobs.append((GPCC+name,Path(raw)/name))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda job:download(*job),jobs))
