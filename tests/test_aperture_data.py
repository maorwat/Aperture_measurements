import unittest
import pandas as pd

from pathlib import Path
import sys

home_path = str(Path.cwd().parent)
sys.path.append(home_path)

from aper_package.aperture_data import ApertureData

class TestAperData(unittest.TestCase):

    def setUp(self):

        line = home_path+'/test_data/Martas_injection_b1.json'
        self.data = ApertureData(line)

    def test_init(self):

        self.assertEqual(self.data.gamma, 479.6050161552533)
        self.assertEqual(self.data.tw_b1.shape, (34939, 20))
        self.assertEqual(self.data.tw_b2.shape, (34963, 20))
        self.assertEqual(self.data.nom_b1.shape, (34939, 4))
        self.assertEqual(self.data.nom_b2.shape, (34963, 4))
        self.assertEqual(self.data.tw_b1['name'].iloc[0], 'ip1')
        self.assertEqual(self.data.tw_b2['name'].iloc[0], 'lhcb2ip1.l1_p_')
        self.assertEqual(self.data.nom_b1['name'].iloc[0], 'ip1')
        self.assertEqual(self.data.nom_b2['name'].iloc[0], 'lhcb2ip1.l1_p_')

        self.assertTrue((self.data.tw_b1['x_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b1['x_from_nom_to_bottom'] == 0).all())
        self.assertTrue((self.data.tw_b2['x_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b2['x_from_nom_to_bottom'] == 0).all())

        self.assertTrue((self.data.tw_b1['y_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b1['y_from_nom_to_bottom'] == 0).all())
        self.assertTrue((self.data.tw_b2['y_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b2['y_from_nom_to_bottom'] == 0).all())

    def test_aperture(self):

        path = home_path+'/test_data/all_optics_B1.tfs'
        self.data.load_aperture(path)

        # Convert names to lower case for case-insensitive comparison
        self.data.aper_b2['NAME'] = self.data.aper_b2['NAME'].str.lower()

        # Merge the dataframes on the name columns
        merged_df = pd.merge(self.data.aper_b2, self.data.tw_b2, left_on='NAME', right_on='name')

        # Check for equality of the 'S' and 's' columns
        pd.testing.assert_series_equal(merged_df['S'], merged_df['s'], check_names=False)
        
        self.assertEqual(self.data.aper_b1.shape, (29057, 10)) # ['S', 'NAME', 'APER_1', 'APER_2', 'APER_3', 'APER_4', 'MECH_SEP'] and tolerances
        self.assertEqual(self.data.aper_b2.shape, (29085, 10))
        
    def test_cycle(self):
        
        self.data.cycle('ip5')
        
        self.assertEqual(self.data.tw_b1['name'].iloc[0], 'ip5')
        self.assertEqual(self.data.nom_b1['name'].iloc[0], 'ip5')
        self.assertEqual(self.data.tw_b1.shape, (34939, 20))
        self.assertEqual(self.data.tw_b2.shape, (34963, 20))
        self.assertEqual(self.data.nom_b1.shape, (34939, 4))
        self.assertEqual(self.data.nom_b2.shape, (34963, 4))
        
    def test_envelope(self):
        
        self.data.envelope(n=11)
        
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['x_up'].values[0], 0.0031231811749489633, 6)
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['x_down'].values[0], -0.0031233080241618244, 6)
        self.assertAlmostEqual(self.data.tw_b2[self.data.tw_b2['name']=='ip2']['x_up'].values[0], 0.006476917796463266, 6)
        self.assertAlmostEqual(self.data.tw_b2[self.data.tw_b2['name']=='ip2']['x_down'].values[0], 0.0005231509606190639, 6)
        
    def test_knobs(self):
        
        self.data.change_knob('on_x5', 0)
        self.data.twiss()
        
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['y'].values[0], 0.0020000105705815104, 6)
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['x'].values[0], -8.854797816681602e-08, 6)
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['x_from_nom_to_top'].values[0], 2.512337173648877e-05, 6)
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['x_from_nom_to_bottom'].values[0], 2.512337173648877e-05, 6)
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['y_from_nom_to_bottom'].values[0], 6.86575432574596e-06, 6)
        self.assertAlmostEqual(self.data.tw_b1[self.data.tw_b1['name']=='ip5']['y_from_nom_to_top'].values[0], 6.86575432574596e-06, 6)
        
    def test_collimators_and_elements(self):
        
        path = home_path+'/test_data/injection.yaml'
        self.data.load_collimators_from_yaml(path = path)
        
        self.assertTrue((self.data.colx_b1['angle'] == 0).all())
        self.assertTrue((self.data.colx_b2['angle'] == 0).all())
        self.assertTrue((self.data.coly_b1['angle'] == 90).all())
        self.assertTrue((self.data.coly_b2['angle'] == 90).all())
        
        self.assertEqual(self.data.colx_b1.shape, (20, 24))
        self.assertEqual(self.data.colx_b2.shape, (20, 24))
        self.assertEqual(self.data.coly_b1.shape, (9, 24))
        self.assertEqual(self.data.coly_b2.shape, (10, 24))
        
        self.assertAlmostEqual(self.data.colx_b1[self.data.colx_b1['name']=='tcp.c6l7.b1']['gap'].values[0], 5.7, 6)
        self.assertAlmostEqual(self.data.colx_b1[self.data.colx_b1['name']=='tcp.c6l7.b1']['top_gap_col'].values[0], 0.005777892163007533, 6)
        self.assertAlmostEqual(self.data.colx_b1[self.data.colx_b1['name']=='tcp.c6l7.b1']['bottom_gap_col'].values[0], -0.005781499604695189, 6)
        
        ind = self.data.coly_b2['name']=='tctpv.4r2.b2'
        
        self.assertAlmostEqual(self.data.coly_b2[ind]['y'].values[0]+self.data.coly_b2[ind]['gap'].values[0]*self.data.coly_b2[ind]['sigma_y'].values[0], self.data.coly_b2[ind]['top_gap_col'].values[0], 6)
        
        path = home_path+'/test_data/thick_all_optics_B1.tfs'
        self.data.load_elements(path = path)
        self.data.elements.shape==(6724, 5)

    def test_reset_knobs(self):

        self.data.change_knob('on_x5', 0)
        self.data.change_knob('on_x8h', 0)
        self.data.twiss()

        self.data.reset_knobs()

        self.assertTrue((self.data.knobs['initial value']==self.data.knobs['current value']).all())

        pass

if __name__ == '__main__':
    unittest.main()