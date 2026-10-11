"""Check exported rasters and all PVCZ source rows without running a browser."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import pandas as pd
import rasterio
from PIL import Image

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--pvcz-raw',type=Path);args=p.parse_args()
cat=json.loads((root/'atlas/data/catalog.json').read_text());ids=[l['id'] for l in cat['layers']]
assert len(ids)==len(set(ids))
assert cat['default'] in ids
for l in cat['layers']:
    with rasterio.open(root/'atlas'/l['download'].lstrip('/')) as ds:
        a=ds.read(1)
        assert ds.crs.to_epsg()==4326
        assert (ds.width,ds.height)==(l['width'],l['height'])
        assert (ds.transform.c,ds.transform.f,ds.transform.a)==(l['west'],l['north'],l['resolution'])
        b=np.fromfile(root/'atlas'/l['values'].lstrip('/'),dtype='<f4').reshape(a.shape)
        np.testing.assert_array_equal(a,b)
        assert np.isfinite(a).sum()==l['count']
        if l.get('labels'):
            actual=np.unique(a[np.isfinite(a)])
            assert np.equal(actual,actual.astype(int)).all()
            assert actual.min()>=1 and actual.max()<len(l['labels'])
            assert len(l['labels'])==len(l['colors'])
            assert list(actual)==l['present_classes']
            assert abs(sum(l['shares'].values())-100)<.15
        with Image.open(root/'atlas'/l['image'].lstrip('/')) as im:
            assert im.size==(1024,1024) and im.mode=='RGBA'
if args.pvcz_raw:
    df=pd.read_csv(args.pvcz_raw/'pvcz.csv')
    with np.load(args.pvcz_raw/'PVCZ-2019_GLDAS_NOAH025_3H_info.npz',allow_pickle=False) as z:
        mask=z['keepers']
    for l in cat['layers']:
        if not l['id'].startswith('pvcz-'):continue
        a=np.fromfile(root/'atlas'/l['values'].lstrip('/'),dtype='<f4').reshape(600,1440)[::-1].ravel()
        assert np.isnan(a[~mask]).all()
        # Compare the complete native grid against the independently loaded source column.
        expected=df[l['source_field']].to_numpy(dtype=float)+l['source_id_offset']
        if l['id']=='pvcz-wind-zone':expected[df.wind_speed<0]=np.nan
        if l['id']=='pvcz-wind-asce':expected[df.wind_speed<=0]=np.nan
        np.testing.assert_array_equal(a[mask],expected.astype('float32'))
    combined=np.fromfile(root/'atlas/data/pvcz-combined.bin',dtype='<f4').reshape(600,1440)[::-1].ravel()[mask]
    assert np.count_nonzero(combined==1)==np.count_nonzero(df.pvcz==0)>0
    assert len(np.unique(combined))==37
    print(f'All {len(df):,} source rows agree across 18 PVCZ rasters; first class retained; masks verified.')
print(f'{len(ids)} layers: binary/GeoTIFF agreement, transforms, labels, counts and PNGs passed.')
