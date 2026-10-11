import argparse
from .sources import fetch_baseline, fetch_climate, fetch_era5_ncar, fetch_era5_cds
from .pipeline import calculate

def main():
    p=argparse.ArgumentParser(description='KGPV provider refresh and reproducible classification')
    p.add_argument('command',choices=['fetch','fetch-era5-cds','calculate','publish-layers'])
    p.add_argument('--raw',default='raw');p.add_argument('--output',default='work')
    p.add_argument('--start',type=int,default=1996);p.add_argument('--end',type=int,default=2022)
    p.add_argument('--climate-only',action='store_true')
    a=p.parse_args()
    if a.start>a.end:p.error('start must be <= end')
    if a.command=='fetch':
        fetch_baseline(a.raw);fetch_climate(a.raw);fetch_era5_ncar(a.raw,a.start,min(a.end,2022))
        if a.end>2022:fetch_era5_cds(a.raw,2023,a.end)
    elif a.command=='fetch-era5-cds':fetch_era5_cds(a.raw,a.start,a.end)
    elif a.command=='calculate':calculate(a.raw,a.output,a.start,a.end,a.climate_only)
    else:
        from .export import publish
        publish(a.raw,a.output,'atlas')

if __name__=='__main__':main()
