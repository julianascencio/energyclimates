"""Import pinned, published PVCZ data without executing upstream Python/pickles.

This imports the author's 2010–2018 product; it does not recalculate PVCZ from
new GLDAS observations. Grid positions come from the author's numeric NPZ.
"""
import argparse
import colorsys
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import numpy as np
import pandas as pd
from rasterio.transform import from_origin
from .export import write_layer

COMMIT='aa89fab8d1d66f46f4ea8575e2452aa75a927535'
REPO='https://github.com/toddkarin/pvcz'
BASE=f'https://raw.githubusercontent.com/toddkarin/pvcz/{COMMIT}/'
FILES={
 'pvcz.csv':('pvcz/PVCZ-2019_ver0p2_world_PV_climate_stressors_and_zones.csv','14e7e06010620f8054b3ba7ee49256bc4d26c017c51da2d188d9753cff7d9801'),
 'PVCZ-2019_GLDAS_NOAH025_3H_info.npz':('pvcz/PVCZ-2019_GLDAS_NOAH025_3H_info.npz','83d755ba712d0007f0004e674c1c4af0ecb6ced23b77149e6f32f2397c2d93b4'),
 'pvcz-LICENSE.txt':('LICENSE','e9aa38aa880a2851e6ff970155883b1c173698379946725ba8134c1ce43fa66b')}

RESEARCH=[
 {'name':'PVCZ · Photovoltaic Climate Zones','authors':'Todd Karin, C. Birk Jones & Anubhav Jain','year':'2019 · data v0.2','status':'Available as map layers','layer':'pvcz-combined','url':REPO,
  'description':'Degradation-oriented zones combine module equivalent temperature and specific humidity, with a separate wind class. GLDAS climate inputs cover 2010–2018 at 0.25°. This published product is imported unchanged in value; it is not a new GLDAS refresh.',
  'availability':'Includes the combined zone, rack/roof temperature zones, humidity zones and principal climate stressors. The catalogue links the original data and its MIT licence.'},
 {'name':'A machine learning approach to PV-climate classification','authors':'Francisco Javier Triana de las Heras, Olindo Isabella & Malte Ruben Vogt','year':'2026 · online June 2025','status':'Paper found · raster pending','layer':None,'url':'https://doi.org/10.1016/j.renene.2025.123685',
  'description':'Cites KGPV and uses its simulated c-Si specific yield for comparison. Supervised feature selection followed by k-means yields 21 clusters from seven features, including mountainous climates. Climate inputs span 1991–2021 on a 0.5° grid.',
  'availability':'The paper states that location-to-zone data are in its supplement. The publisher supplement could not be retrieved here; no published cluster raster has been added. Supply the supplement to enable an exact import.'},
 {'name':'PVZones · Physics-guided machine learning','authors':'Jabir Bin Jahangir & Muhammad Ashraful Alam','year':'2025 · preprint 2024','status':'Paper found · raster pending','layer':None,'url':'https://doi.org/10.1016/j.apenergy.2025.126192',
  'description':'The open preprint cites the 2019 KGPV methodology as reference 17. Its PVZones map uses k-means (seven zones) with GHI, ambient temperature and clearness index to support representative sampling for PV yield prediction.',
  'availability':'The open preprint contains the map and methods, but no downloadable, georeferenced zone dataset was located in this search. The atlas does not infer zone cells from the printed figure.'}
]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fetch(raw):
    raw=Path(raw);raw.mkdir(parents=True,exist_ok=True)
    for name,(remote,sha) in FILES.items():
        path=raw/name
        if not path.exists():
            temp=path.with_suffix(path.suffix+'.part')
            try:
                with urllib.request.urlopen(BASE+remote,timeout=120) as r, temp.open('wb') as f:
                    shutil.copyfileobj(r,f)
                if digest(temp)!=sha:raise ValueError(f'Checksum mismatch: {name}')
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
        if digest(path)!=sha:raise ValueError(f'Checksum mismatch: {name}')
    return raw

def native_grid(df,info):
    """Recover exact cell positions, validating all rounded CSV coordinates."""
    lat=info['lat_all'];lon=info['lon_all'];keepers=info['keepers']
    if not (len(lat)==600 and len(lon)==1440 and keepers.dtype==bool and keepers.shape==(864000,)):
        raise ValueError('Unexpected PVCZ native grid')
    np.testing.assert_allclose(lat,np.arange(-59.875,90,.25),rtol=0,atol=1e-8)
    np.testing.assert_allclose(lon,np.arange(-179.875,180,.25),rtol=0,atol=1e-8)
    if int(keepers.sum())!=len(df):raise ValueError('PVCZ row/mask mismatch')
    gx,gy=np.meshgrid(lon,lat)
    for column,exact in [('lat',gy.ravel()[keepers]),('lon',gx.ravel()[keepers])]:
        rounded=np.array([float(f'{x:.3g}') for x in exact])
        if not np.array_equal(rounded,df[column].to_numpy()):
            raise ValueError(f'PVCZ CSV ordering mismatch: {column}')
    return keepers

def to_grid(values,keepers):
    a=np.full(keepers.shape,np.nan,dtype='float32');a[keepers]=values
    return a.reshape(600,1440)[::-1].copy()

def colour(h,s,l):
    return '#'+''.join(f'{round(c*255):02x}' for c in colorsys.hls_to_rgb(h,l,s))

def import_pvcz(raw='raw/pvcz',dist='atlas',all_activation_energies=False):
    raw=fetch(raw);dist=Path(dist);df=pd.read_csv(raw/'pvcz.csv')
    with np.load(raw/'PVCZ-2019_GLDAS_NOAH025_3H_info.npz',allow_pickle=False) as info:
        keepers=native_grid(df,info)
        if str(info['time_stamp_units'])!='minutes since 2000-01-01 03:00:00':raise ValueError('Unknown timestamp units')
        dates=[dt.datetime(2000,1,1,3)+dt.timedelta(minutes=float(x)) for x in info['time_stamp'][[0,-1]]]
    if [d.year for d in dates]!=[2010,2018]:raise ValueError('Unexpected PVCZ period')
    # The published numeric IDs are zero-based; reserve raster zero for no-data.
    combined=df.pvcz.to_numpy()
    expected=df['T_equiv_rack_1p1eV_zone']+10*df.specific_humidity_mean_zone
    if not np.array_equal(combined,expected):raise ValueError('PVCZ component-label inconsistency')
    text_labels=np.array([f'T{int(v)%10+1}:H{int(v)//10+1}' for v in combined])
    if not np.array_equal(text_labels,df.pvcz_labeled):raise ValueError('PVCZ text-label inconsistency')
    group='PVCZ · Karin 2019';period='2010–2018';layers=[]
    description='Published PVCZ v0.2; GLDAS 2010–2018. Native 0.25° cells, recovered from the author’s grid metadata. Atlas colours; source values retained.'
    def add(key,title,field,units='',labels=None,colors=None,mask=None,warning=None,offset=0):
        v=df[field].to_numpy(dtype=float)+offset
        if mask is not None:v[~mask]=np.nan
        layer=write_layer(dist,'pvcz-'+key,title,to_grid(v,keepers),group,period,units,
                          description+' Source field: '+field,REPO,labels=labels,colors=colors,warning=warning,
                          transform=from_origin(-180,90,.25,.25))
        layer.update({'source_field':field,'source_commit':COMMIT,'source_id_offset':offset,'license':'MIT; retain upstream notice'})
        layers.append(layer)
    temp_colors=['#00000000']+[colour(.62-.61*i/9,.75,.78-.43*i/9) for i in range(10)]
    humid_colors=['#00000000','#e7cc74','#aecdb1','#6aadc1','#427dbc','#444298']
    bivariate=['#00000000']+[colour([.12,.32,.5,.61,.79][h],.58,.88-.54*t/9) for h in range(5) for t in range(10)]
    add('combined','PVCZ · temperature × humidity','pvcz',labels=['']+[f'T{t}:H{h}' for h in range(1,6) for t in range(1,11)],colors=bivariate,offset=1,
        warning='PVCZ describes degradation stress. It uses 2010–2018 climate and is not a current-year update or an energy-yield classification.')
    for mount in ['rack','roof']:
        add('temperature-zone-'+mount,f'PVCZ · {mount} temperature zones','T_equiv_'+mount+'_1p1eV_zone',labels=['']+[f'T{i}' for i in range(1,11)],colors=temp_colors,offset=1)
    add('humidity-zone','PVCZ · humidity zones','specific_humidity_mean_zone',labels=['']+[f'H{i}' for i in range(1,6)],colors=humid_colors,offset=1)
    add('wind-zone','PVCZ · U.S. wind zones','wind_speed_zone',labels=['','W1 · Special wind region','W2 · Below 33 m/s','W3 · 33–36 m/s','W4 · 36–39 m/s','W5 · Above 39 m/s'],
        colors=['#00000000','#666666','#f8dea0','#f3a957','#dd6547','#862b63'],offset=1,mask=df.wind_speed.to_numpy()>=0,
        warning='ASCE 7-16 25-year recurrence wind field supplied by PVCZ; limited U.S. coverage. W1 is a special wind region. Negative sentinel values outside coverage are masked. Not current design-code guidance.')
    kg=df.groupby('KG_numeric_zone').KG_zone.agg(lambda x:list(set(x)))
    if not all(len(x)==1 for x in kg):raise ValueError('Conflicting KG labels')
    kg_labels=['']+[kg.loc[i][0] if i in kg else f'ID {i}' for i in range(int(df.KG_numeric_zone.max())+1)]
    add('koppen-geiger','Köppen–Geiger · PVCZ reference','KG_numeric_zone',labels=kg_labels,
        colors=['#00000000']+[colour(i*.618%1,.62,.47) for i in range(len(kg_labels)-1)],offset=1,
        warning='Reference KG labels packaged with PVCZ. The original KG climatology period is not specified in this CSV; 2010–2018 refers to its GLDAS stressors.')
    specs=[('temperature-mean','Mean ambient temperature','T_ambient_mean','°C'),
           ('temperature-min','Minimum ambient temperature','T_ambient_min','°C'),
           ('temperature-max','Maximum ambient temperature','T_ambient_max','°C'),
           ('equivalent-rack','Equivalent module temperature · rack','T_equiv_rack_1p1eV','°C'),
           ('equivalent-roof','Equivalent module temperature · roof','T_equiv_roof_1p1eV','°C'),
           ('cycling-rack','Thermal cycling · rack','T_velocity_rack','°C/hour'),
           ('cycling-roof','Thermal cycling · roof','T_velocity_roof','°C/hour'),
           ('humidity','Mean specific humidity','specific_humidity_mean','g/kg'),
           ('ghi','Mean daily horizontal irradiation','GHI_mean','kWh/m²/day'),
           ('wind-rms','GLDAS wind speed · RMS','wind_speed_rms','m/s'),
           ('wind-max','GLDAS wind speed · maximum','wind_speed_max','m/s')]
    if all_activation_energies:
        for mount in ['rack','roof']:
            for suffix in ['0p1','0p3','0p5','0p7','0p9','1p3','1p5','1p7','1p9','2p1']:
                specs.append((f'equivalent-{mount}-{suffix}',f'Equivalent temperature · {mount} · {suffix.replace("p",".")} eV',f'T_equiv_{mount}_{suffix}eV','°C'))
    for key,title,field,unit in specs:
        warning='Arrhenius-weighted equivalent module temperature; activation energy 1.1 eV.' if key in ['equivalent-rack','equivalent-roof'] else None
        if key.startswith('wind-'):warning='GLDAS 3-hourly grid values, 2010–2018; not 3-second design gusts or return-period estimates.'
        add(key,title,field,unit,warning=warning)
    add('wind-asce','ASCE 25-year recurrence wind · U.S.','wind_speed','m/s',mask=df.wind_speed.to_numpy()>0,
        warning='ASCE 7-16 values packaged with PVCZ. Negative no-data and zero-valued special wind regions are masked; consult the separate wind-zone layer. Not current design-code guidance.')
    provenance={'provider':REPO,'commit':COMMIT,'product':'PVCZ-2019 v0.2','period':[d.isoformat() for d in dates],
        'input_files':[{ 'file':name,'url':BASE+remote,'sha256':sha} for name,(remote,sha) in FILES.items()],
        'rows':len(df),'duplicate_rounded_csv_coordinates':int(df.duplicated(['lat','lon']).sum()),
        'grid_note':'CSV coordinates are rounded to 3 significant digits. All rows were checked against the rounded exact metadata coordinates before gridding via the original keepers mask. Never deduplicate or grid the rounded CSV coordinates.',
        'encoding':'Categorical raster code = source numeric code + 1. Zero is reserved; no-data stored as NaN. CSV values retain published precision.',
        'mask_note':'ASCE wind -5 is missing, 0 is special wind region. Continuous wind masks both; wind classes retain the special category.',
        'omitted_fields':'Duplicate KG class fragments/ASCE aliases and specific_humidity_rms are omitted. The latter is smaller than the mean in the source and requires provider clarification. Additional activation energies can be included with --all-activation-energies.',
        'palette':'Atlas-specific colours; not the original paper palette. Mercator previews use nearest neighbour; native rasters and point values stay at 0.25°.',
        'layers':[l['id'] for l in layers]}
    (atlas/'data/pvcz-provenance.json').write_text(json.dumps(provenance,indent=2))
    downloads=atlas/'downloads';downloads.mkdir(exist_ok=True)
    shutil.copy(raw/'pvcz-LICENSE.txt',downloads/'pvcz-LICENSE.txt')
    sources=[{'name':'Todd Karin · PVCZ v0.2','role':'Degradation zones and climate stressors','period':'GLDAS 2010–2018; native 0.25°','url':REPO,'status':'Used · published product','license':'MIT'}]
    external=atlas/'data/external-catalog.json'
    previous=json.loads(external.read_text()) if external.exists() else {}
    ext={'layers':[l for l in previous.get('layers',[]) if not l['id'].startswith('pvcz-')]+layers,
         'sources':[s for s in previous.get('sources',[]) if s['url']!=REPO]+sources,'research':RESEARCH}
    if previous.get('energy'):ext['energy']=previous['energy']
    external.write_text(json.dumps(ext,ensure_ascii=False,indent=2))
    catalog_path=atlas/'data/catalog.json'
    catalog=json.loads(catalog_path.read_text())
    old_ids={l['id'] for l in previous.get('layers',[])}
    catalog['layers']=[l for l in catalog['layers'] if l['id'] not in old_ids and not l['id'].startswith('pvcz-')]+ext['layers']
    ext_urls={s['url'] for s in ext['sources']}
    catalog['sources']=[s for s in catalog['sources'] if s['url'] not in ext_urls]+ext['sources']
    catalog['research']=RESEARCH;catalog['generated']=dt.date.today().isoformat()
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
    print(json.dumps({'event':'PVCZ imported','layers':len(layers),'cells':len(df),'period':'2010–2018','total_layers':len(catalog['layers'])}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',default='raw/pvcz');p.add_argument('--dist',default='atlas');p.add_argument('--all-activation-energies',action='store_true')
    a=p.parse_args();import_pvcz(a.raw,a.dist,a.all_activation_energies)
