"""Compute monthly normals with full temporal coverage and a common 0.5° grid."""
from pathlib import Path
import gzip
import hashlib
import json
import calendar
import numpy as np
import netCDF4
from .classify import tp_classify, irradiation_classify, combine

LAT=np.arange(89.75,-90,-.5)
LON=np.arange(-179.75,180,.5)

def read_months(path,kind):
    path=Path(path)
    if path.suffix=='.gz':
        with gzip.open(path,'rb') as f:ds=netCDF4.Dataset('memory',memory=f.read())
    else:ds=netCDF4.Dataset(path)
    try:
        varname={'temperature':'tmp','precipitation':'precip','irradiation':('SSRD' if 'SSRD' in ds.variables else 'ssrd')}[kind]
        var=ds[varname]
        if kind=='temperature' and 'celsius' not in var.units.lower():raise ValueError('Unexpected temperature units')
        if kind=='precipitation' and var.units.lower() not in ['mm/month','mm']:raise ValueError('Unexpected precipitation units')
        if kind=='irradiation' and var.units not in ['W m**-2 s','J m**-2','J m-2']:raise ValueError('Expected ERA5 monthly mean daily accumulation in J/m2')
        tn='valid_time' if 'valid_time' in ds.variables else 'time'
        times=netCDF4.num2date(ds[tn][:],ds[tn].units,calendar=getattr(ds[tn],'calendar','standard'))
        ln='latitude' if 'latitude' in ds.variables else 'lat'
        xn='longitude' if 'longitude' in ds.variables else 'lon'
        lat=np.asarray(ds[ln][:]);lon=(np.asarray(ds[xn][:])+180)%360-180
        # Target cell centres occur exactly on the ERA5 0.25° grid and on CRU/GPCC grids.
        yi=np.abs(lat[:,None]-LAT).argmin(0);xi=np.abs(lon[:,None]-LON).argmin(0)
        if not np.allclose(lat[yi],LAT) or not np.allclose(lon[xi],LON):
            raise ValueError('Source grid must contain the canonical 0.5° cell centres')
        if var.dimensions!=(tn,ln,xn):raise ValueError(f'Unsupported variable dimensions: {var.dimensions}')
        for i,d in enumerate(times):
            a=np.asarray(np.ma.filled(var[i,:,:],np.nan),dtype=float)[yi][:,xi]
            if kind=='irradiation':
                # ECMWF moda accumulations are monthly means of DAILY totals, not monthly totals.
                # Tiny negative reanalysis roundoff is zeroed; genuine negatives remain missing.
                a=np.where(a>=-1,np.maximum(a,0),np.nan)*calendar.monthrange(d.year,d.month)[1]/3_600_000
            yield (d.year,d.month),a
    finally:ds.close()

def normals(paths,kind,start,end):
    sums=np.zeros((12,360,720),float);counts=np.zeros(sums.shape,'uint16');seen=set()
    provenance=[]
    for path in paths:
        for date,a in read_months(path,kind):
            year,month=date
            if not start<=year<=end:continue
            if date in seen:raise ValueError(f'Duplicate month {date} for {kind}')
            seen.add(date);valid=np.isfinite(a)
            sums[month-1]+=np.where(valid,a,0);counts[month-1]+=valid
        provenance.append({'file':Path(path).name,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()})
    expected={(y,m) for y in range(start,end+1) for m in range(1,13)}
    if seen!=expected:raise ValueError(f'Missing {kind} months: {sorted(expected-seen)[:15]}')
    n=end-start+1
    return np.divide(sums,n,out=np.full_like(sums,np.nan),where=counts==n),provenance

def calculate(raw,output,start=1996,end=2022,climate_only=False):
    raw,output=Path(raw),Path(output);output.mkdir(parents=True,exist_ok=True)
    sources={}
    t,sources['temperature']=normals(sorted(raw.glob('cru_ts4.10.*.tmp.dat.nc.gz')),'temperature',start,end)
    p,sources['precipitation']=normals(sorted(raw.glob('gpcc*.nc.gz')),'precipitation',start,end)
    tp=tp_classify(t,p,LAT)
    values={'temperature':t.mean(0),'precipitation':p.sum(0),'tp':tp}
    if not climate_only:
        paths=sorted(raw.glob('e5.moda*ssrd*.nc'))+sorted(raw.glob('era5-cds-ssrd-*.nc'))
        h,sources['irradiation']=normals(paths,'irradiation',start,end)
        ghi=h.sum(0);ghi[tp==0]=np.nan
        iz=irradiation_classify(ghi);zone,rawzone=combine(tp,iz)
        values.update({'ghi':ghi,'irradiation_zone':iz,'kgpv':zone,'kgpv24':rawzone})
    np.savez_compressed(output/f'layers-{start}-{end}.npz',**values)
    np.savez_compressed(output/f'monthly-{start}-{end}.npz',temperature=t,precipitation=p,**({'irradiation':h} if not climate_only else {}))
    manifest={'start':start,'end':end,'complete_months':12*(end-start+1),'grid':'0.5 degree, EPSG:4326',
              'climate_only':climate_only,'thresholds_kwh_m2':[1130,1560,2070],
              'method':'Ascencio-Vasquez et al. 2019, Figure A1 and Table 4',
              'resampling':'exact sampling of continuous source fields at CRU 0.5 degree grid cell centres',
              'temperature_normal':'equal weight per calendar month','precipitation_variable':'precip (not precip_infill)',
              'minimum_data':'Every month in the selected period required per cell; no infilling',
              'sources':sources}
    (output/f'run-{start}-{end}.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'event':'calculated','period':f'{start}-{end}','valid_tp_cells':int((tp>0).sum())}),flush=True)
    return values,manifest
