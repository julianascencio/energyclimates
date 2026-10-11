"""Export actual rasters, inspectable values and a browser layer catalogue."""
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from PIL import Image, ImageColor
from .classify import ZONE_LABELS,COLORS,TP_LABELS

PAPER='https://doi.org/10.1016/j.solener.2019.08.072'
BASE='https://data.mendeley.com/datasets/z3byd8jyfn/1'
CRU='https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.10/'
GPCC='https://opendata.dwd.de/climate_environment/GPCC/html/gpcc_precipitation_analysis_monthly_v2025_doi_download.html'
ERA='https://gdex.ucar.edu/datasets/d633001/'
CDS='https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means'
TP_NAMES=['','Tropical','Desert','Steppe','Temperate','Cold','Polar']
BASE_WARNING='Published CSV labels conflict with its coordinates and meteorological values. Values are shown unchanged; do not use these labels to quantify climate change. See the data-quality report.'

def write_layer(dist,id,title,array,group,period,units,description,source,*,labels=None,colors=None,limits=None,legacy=False,warning=None,transform=None):
    data=Path(dist)/'data';data.mkdir(parents=True,exist_ok=True)
    a=np.asarray(array,dtype='<f4').copy()
    if labels:a[a==0]=np.nan
    transform=transform or (from_origin(-180.25,90.25,.5,.5) if legacy else from_origin(-180,90,.5,.5))
    if transform.a<=0 or transform.e!=-transform.a or transform.b or transform.d:
        raise ValueError('Expected a north-up square EPSG:4326 grid')
    path=data/f'{id}.tif'
    with rasterio.open(path,'w',driver='GTiff',height=a.shape[0],width=a.shape[1],count=1,dtype='float32',crs='EPSG:4326',transform=transform,nodata=np.nan,compress='deflate',tiled=True) as dst:
        dst.write(a,1);dst.update_tags(title=title,period=period,source=source,description=description)
    (data/f'{id}.bin').write_bytes(a.tobytes())
    finite=a[np.isfinite(a)]
    lo,hi=limits or (float(np.percentile(finite,2)),float(np.percentile(finite,98)))
    if hi<=lo:hi=lo+1
    if not colors:colors=['#133b76','#168bb5','#73d8ca','#f0ed94','#f4a153','#c73249']
    merc=np.full((1024,1024),np.nan,dtype='float32');extent=20037508.342789244
    reproject(a,merc,src_transform=transform,src_crs='EPSG:4326',src_nodata=np.nan,
              dst_transform=from_origin(-extent,extent,2*extent/1024,2*extent/1024),dst_crs='EPSG:3857',dst_nodata=np.nan,resampling=Resampling.nearest)
    rgba=np.zeros((*merc.shape,4),dtype='uint8');valid=np.isfinite(merc)
    if labels:
        for i,color in enumerate(colors):
            if i:rgba[valid & (merc==i)]=ImageColor.getcolor(color,'RGBA')
    else:
        ramp=np.array([ImageColor.getcolor(c,'RGBA') for c in colors]);v=np.clip((np.nan_to_num(merc,nan=lo)-lo)/(hi-lo),0,1)*(len(colors)-1)
        lower=np.floor(v).astype(int);upper=np.minimum(lower+1,len(colors)-1);f=(v-lower)[...,None]
        rgba=((1-f)*ramp[lower]+f*ramp[upper]).astype('uint8');rgba[~valid]=0
    Image.fromarray(rgba).save(data/f'{id}.png')
    layer={'id':id,'title':title,'group':group,'period':period,'units':units,'description':description,'source':source,'warning':warning,
           'labels':labels,'colors':colors,'min':lo,'max':hi,'width':a.shape[1],'height':a.shape[0],
           'west':float(transform.c),'north':float(transform.f),'resolution':float(transform.a),
           'count':int(finite.size),'image':f'/data/{id}.png','values':f'/data/{id}.bin','download':f'/data/{id}.tif'}
    if labels:
        layer['present_classes']=[int(v) for v in np.unique(finite)]
        lat=layer['north']-(np.arange(a.shape[0])+.5)*layer['resolution']
        weights=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],a.shape)
        total=weights[np.isfinite(a)].sum()
        layer['shares']={str(i):round(float(weights[a==i].sum()/total*100),2) for i in range(1,len(labels))}
    return layer

def publish(raw='raw',work='work',dist='atlas'):
    raw,work,dist=Path(raw),Path(work),Path(dist);layers=[]
    run_paths=sorted(work.glob('run-*.json'),key=lambda p:(json.loads(p.read_text())['climate_only'],-json.loads(p.read_text())['end']))
    runs=[json.loads(p.read_text()) for p in run_paths]
    latest_full=max(m['end'] for m in runs if not m['climate_only'])
    for path in run_paths:
        meta=json.loads(path.read_text());start,end=meta['start'],meta['end'];period=f'{start}–{end}'
        v=np.load(work/f'layers-{start}-{end}.npz')
        group='Climate refresh · 2025' if meta['climate_only'] else f'Recalculated · {end}'
        desc='Complete monthly coverage required; 0.5° grid. Research output; not independently validated.'
        order=['kgpv','tp','irradiation_zone','ghi','temperature','precipitation','kgpv24']
        spec={'kgpv':('KGPV · 12 zones','',ZONE_LABELS,COLORS),
              'tp':('Temperature–precipitation zones','', [f'{a} · {b}' if a else '' for a,b in zip(TP_LABELS,TP_NAMES)],['#00000000','#bd0030','#ffcd00','#81258e','#00965e','#075da8','#969696']),
              'irradiation_zone':('Irradiation zones','',['','L · Low','M · Medium','H · High','K · Very high'],['#00000000','#203f84','#389bbc','#efd171','#f58b30']),
              'ghi':('Global horizontal irradiation','kWh/m²/year',None,None),
              'temperature':('Mean air temperature','°C',None,None),
              'precipitation':('Annual precipitation','mm/year',None,None),
              'kgpv24':('KGPV · 24 unmerged zones','',['']+[a+b for a in 'ABCDEF' for b in 'LMHK'],['#00000000']+[c for c in ['#d5505e','#e4b92d','#9b6eb7','#459976','#277ec0','#8999a8'] for _ in range(4)])}
        for key in order:
            if key not in v:continue
            title,units,labels,colors=spec[key]
            source=CRU if key=='temperature' else GPCC if key=='precipitation' else ERA if key in ['ghi','irradiation_zone'] and end<=2022 else PAPER
            warning='Temperature and precipitation are updated through 2025. The full 1996–2025 KGPV layer awaits ERA5 irradiation for 2023–2025.' if meta['climate_only'] else None
            layers.append(write_layer(dist,f'{key}-{start}-{end}',title,v[key],group,period,units,desc,source,labels=labels,colors=colors,warning=warning))
        shutil.copy(path,atlas/'data'/path.name)
    df=pd.read_csv(raw/'KGPV_PVmcSi_05x05.csv',skiprows=16,encoding='latin1')
    df['Longitude']=(df.Longitude+180)%360-180
    rows=np.rint((90-df.Latitude)*2).astype(int);cols=np.rint((df.Longitude+180)*2).astype(int)
    entries=[('KGPV_nb','KGPV · published labels','',ZONE_LABELS,COLORS),('Yf','Final energy yield','kWh/kWp/year',None,None),
             ('H_ann','Global horizontal irradiation','kWh/m²/year',None,None),('H_eff','Effective plane-of-array irradiation','kWh/m²/year',None,None),
             ('PR','Performance ratio','%',None,None),('UCF','Capacity factor','%',None,None),('Tamb_avg','Mean air temperature','°C',None,None),
             ('Tmod_avg','Mean module temperature','°C',None,None),('Tmod_max','Maximum module temperature','°C',None,None),('Tilt','Optimal fixed tilt','°',None,None)]
    for field,title,unit,labels,colors in entries:
        a=np.full((361,720),np.nan);a[rows,cols]=df[field]*(100 if field in ['PR','UCF'] else 1)
        layers.append(write_layer(dist,f'original-{field}',title,a,'Published · 2019','1990–2016',unit,
                                 'Original 2019 deposit; 55,418 points. Typical c-Si system; Ross 0.03 °C m²/W, temperature coefficient −0.45%/°C, BoS 85%. Source field: '+field,
                                 BASE,labels=labels,colors=colors,legacy=True,warning=BASE_WARNING if labels else None))
    downloads=atlas/'downloads';downloads.mkdir(exist_ok=True)
    shutil.copy(raw/'KGPV_PVmcSi_05x05.csv',downloads/'KGPV_PVmcSi_05x05.csv')
    catalog={'generated':'2026-09-12','layers':layers,'default':next(x['id'] for x in layers if x['id'].startswith('kgpv-')),
             'baseline_warning':BASE_WARNING,'baseline_rows':len(df),'method_url':PAPER,'baseline_url':BASE,
             'runs':[{'start':m['start'],'end':m['end'],'climate_only':m['climate_only']} for m in runs],
             'latest_full_year':latest_full,
             'full_refresh_status':('Calculated through 2025' if latest_full>=2025 else 'ERA5 2023–2025 must be retrieved with a configured Copernicus CDS account. No CDS credentials were available for this build.'),
             'sources':[{'name':'CRU TS 4.10','role':'Air temperature','period':'1901–2025','url':CRU,'status':'Used','license':'ODbL / Database Contents License'},
                        {'name':'GPCC Monthly v2025','role':'Precipitation','period':'1891–present; complete years used through 2025','url':GPCC,'status':'Used','license':'DWD terms; attribution required'},
                        {'name':'ECMWF ERA5 / NCAR','role':'Solar irradiation','period':'1996–2022 downloaded','url':ERA,'status':'Used','license':'CC BY 4.0; Copernicus attribution'},
                        {'name':'ECMWF ERA5 / CDS','role':'Latest solar irradiation','period':'2023–2025 needed','url':CDS,'status':'Access needed','license':'Copernicus licence'},
                        {'name':'Mendeley · KGPV 2019','role':'Published classification + PV metrics','period':'1990–2016','url':BASE,'status':'Used · label issue','license':'CC BY 4.0'},
                        {'name':'IPSL · CMIP6 SSP5-8.5','role':'Future projections from the original paper','period':'2015–2100','url':'https://doi.org/10.22033/ESGF/CMIP6.1534','status':'Not ingested','license':'See individual model asset'},
                        {'name':'CIESIN · GPWv4','role':'Original population-based class selection','period':'Original lookup retained','url':'https://doi.org/10.7927/H4DZ068D','status':'Fixed 2019 lookup','license':'See original dataset'}]}
    external=atlas/'data/external-catalog.json'
    if external.exists():
        ext=json.loads(external.read_text())
        catalog['layers']+=ext.get('layers',[])
        catalog['sources']+=ext.get('sources',[])
        catalog['research']=ext.get('research',[])
        if ext.get('energy'):
            catalog['energy']=ext['energy']
            catalog['default']=ext['energy']['schemes']['pv']['rules']
    (atlas/'data/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
    report={'dataset':BASE,'sha256':'58eb8de3c3c7cb3c2b6dac205f5fd62cc10ebc966c581c585e366f6706cf0083',
            'finding':BASE_WARNING,'example':df.iloc[0].to_dict(),
            'interpretation':'A class-label ordering mismatch is suspected. No labels have been repaired or inverted automatically.',
            'consequence':'No baseline-to-update zone-transition statistic is published. Raw continuous PV values are retained as deposited, not independently validated.',
            'coverage':{'rows':len(df),'latitude_min':float(df.Latitude.min()),'latitude_max':float(df.Latitude.max())},
            'header_note':'The deposit describes Tamb_avg as module temperature, but variable name and paper indicate ambient temperature. Both Tmod_avg and Tmod_max exist separately.'}
    (downloads/'data-quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'event':'exported','layers':len(layers)}))
