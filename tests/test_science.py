import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
import numpy as np
import netCDF4
from kgpv.classify import tp_classify, irradiation_classify, combine, ZONE_LABELS
from kgpv.pipeline import read_months, normals, LAT, LON

class ClassificationTests(unittest.TestCase):
    def tp(self,t,p,lat=30):
        return int(tp_classify(np.array(t,float).reshape(12,1,1),np.array(p,float).reshape(12,1,1),[lat])[0,0])

    def test_priority_and_temperature_boundaries(self):
        self.assertEqual(self.tp([10]*12,[0]*12),6)  # polar precedes desert
        self.assertEqual(self.tp([25]*12,[0]*12),2)  # desert precedes tropical
        self.assertEqual(self.tp([18]*12,[150]*12),1)
        self.assertEqual(self.tp([-3]+[12]*11,[150]*12),5)
        self.assertEqual(self.tp([-2.99]+[12]*11,[150]*12),4)

    def test_hemisphere_seasonality(self):
        # 500 mm/year, concentrated Apr-Sep; summer threshold 680, winter 400 at 20°C.
        p=[0]*3+[500/6]*6+[0]*3
        self.assertEqual(self.tp([20]*12,p,30),3)
        self.assertEqual(self.tp([20]*12,p,-30),1)

    def test_dryness_boundary_and_nodata(self):
        # Even rainfall: 20*T+140 = 540; desert threshold 270 mm.
        self.assertEqual(self.tp([20]*12,[22.5]*12),2)
        self.assertEqual(self.tp([20]*12,[45]*12),3)
        self.assertEqual(self.tp([20]*12,[45.01]*12),1)
        self.assertEqual(self.tp([np.nan]+[20]*11,[100]*12),0)
        self.assertEqual(self.tp([20]*12,[-1]+[100]*11),0)

    def test_irradiation_edges_and_merging(self):
        x=irradiation_classify(np.array([np.nan,-1,0,1130,1130.1,1560,1560.1,2070,2070.1]))
        np.testing.assert_array_equal(x,[0,0,1,1,2,2,3,3,4])
        t=np.repeat(np.arange(1,7),4);i=np.tile(np.arange(1,5),6)
        merged,raw=combine(t,i)
        np.testing.assert_array_equal(raw,np.arange(1,25))
        actual=[ZONE_LABELS[n] for n in merged]
        self.assertEqual(actual,['AH','AH','AH','AK','BH','BH','BH','BK','CH','CH','CH','CK','DL','DM','DH','DH','EL','EM','EM','EM','FL','FL','FL','FL'])

    def test_missing_and_duplicate_months_fail(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'fixture';p.write_bytes(b'fixture')
            with patch('kgpv.pipeline.read_months',return_value=iter([((2020,1),np.ones((360,720)))])):
                with self.assertRaisesRegex(ValueError,'Missing'):normals([p],'temperature',2020,2020)
            with patch('kgpv.pipeline.read_months',return_value=iter([((2020,1),np.ones((360,720))),((2020,1),np.ones((360,720)))])):
                with self.assertRaisesRegex(ValueError,'Duplicate'):normals([p],'temperature',2020,2020)

    def test_era5_daily_energy_to_monthly_and_axis_order(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'era5.nc'
            with netCDF4.Dataset(p,'w') as ds:
                for n,s in [('time',2),('latitude',360),('longitude',720)]:ds.createDimension(n,s)
                t=ds.createVariable('time','f8',('time',));t.units='days since 2020-02-01';t[:]=[0,29]
                lat=ds.createVariable('latitude','f8',('latitude',));lat[:]=LAT[::-1]
                lon=ds.createVariable('longitude','f8',('longitude',));lon[:]=(LON+360)%360
                v=ds.createVariable('SSRD','f4',('time','latitude','longitude'));v.units='W m**-2 s';v[:]=3_600_000
            results=list(read_months(p,'irradiation'))
            self.assertEqual(results[0][0],(2020,2))
            np.testing.assert_allclose(results[0][1],29)
            np.testing.assert_allclose(results[1][1],31)

if __name__=='__main__':unittest.main()
