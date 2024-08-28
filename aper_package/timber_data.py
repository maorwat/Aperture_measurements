import pandas as pd
import numpy as np
import yaml
import tfs

from typing import Any, Dict, Optional, Union, List, Tuple

import pytimber
from datetime import datetime, timedelta
from scipy.optimize import least_squares

from aper_package.utils import shift_by, print_and_clear

class BPMData:

    def __init__(self, spark):
        """
        Initializes the BPMData class.

        Parameters:
            spark: Spark session for accessing the LoggingDB.
        """

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)

    def load_data(self, t: datetime) -> None:
        """
        Loads BPM data from Timber.

        Parameters:
            t: A datetime object or a list containing a datetime object representing the time to fetch data.
        """
        
        print_and_clear("Loading BPM data...")

        # Define the end time for data fetching
        end_time = t + timedelta(seconds=1)
        
        # Fetch BPM data
        try:
            bpm_positions_h = self.ldb.get('BFC.LHC:OrbitAcq:positionsH', t, end_time)
            bpm_positions_v = self.ldb.get('BFC.LHC:OrbitAcq:positionsV', t, end_time)
            bpm_names_data = self.ldb.get('BFC.LHC:Mappings:fBPMNames_h', t, t + timedelta(minutes=1))
        except Exception as e:
            print_and_clear(f"Error loading BPM data: {e}")
            return

        try:
            # Extract BPM readings
            bpm_readings_h = bpm_positions_h['BFC.LHC:OrbitAcq:positionsH'][1][0]  
            bpm_readings_v = bpm_positions_v['BFC.LHC:OrbitAcq:positionsV'][1][0] 

            # Ensure BPM names are in lowercase for merging with Twiss data later
            bpm_names = np.char.lower(bpm_names_data['BFC.LHC:Mappings:fBPMNames_h'][1][0].astype(str))

            # Create a DataFrame with the extracted data
            self.data = pd.DataFrame({
                'name': bpm_names,
                'x': bpm_readings_h/1e6, # Change units to metres to stay consistent
                'y': bpm_readings_v/1e6
            })

        except KeyError: self.data = None

        print_and_clear("Done loading BPM data.")

    def process(self, twiss: object) -> None:
        """
        Processes the loaded BPM data by merging it with the Twiss data to find BPM positions.

        Parameters:
            twiss: An ApertureData object containing Twiss data for beam 1 and beam 2.
        """
        if self.data is None:
            print("No BPM data to process. Please load data first.")
            return
        
        # Merge BPM data with Twiss data to find positions
        self.b1 = pd.merge(self.data, twiss.tw_b1[['name', 's']], on='name')
        self.b2 = pd.merge(self.data, twiss.tw_b2[['name', 's']], on='name')

    def least_squares_fit(self,
                        aper_data: object,
                        init_angle: float,
                        knob: str,
                        plane: str,
                        angle_range: Optional[Tuple[float, float]] = (-500, 500), 
                        s_range: Optional[Tuple[float, float]] = None):
        """
        Data needs to be loaded using self.load befor performing the fit.
        """

        # Remove the outliers aroundd ip1 and ip5
        self.data = self.data[~self.data['name'].str.contains('bpmwf')]

        result = least_squares(self._objective, x0=[init_angle], bounds=angle_range, args=(aper_data, knob, s_range, plane))

        # Extract the optimized parameter, Jacobian, and residuals
        params = result.x
        jacobian = result.jac
        residuals = self._objective(params, aper_data, knob, s_range, plane)
        
        # Compute statistics
        n = len(residuals)
        p = len(params)
        sigma_squared = np.sum(residuals**2) / (n - p)
        covariance = np.linalg.inv(jacobian.T @ jacobian) * sigma_squared
        param_uncertainty = np.sqrt(np.diag(covariance))

        return round(params[0], 2), round(param_uncertainty[0], 2)

    def _merge_twiss_and_bpm(self, twiss_data, s_range):
    
        # Rename the columns to differentiate between simulated and measured data
        simulated_data = twiss_data[['name', 's', 'x', 'y']].rename(columns={'x': 'x_simulated', 'y': 'y_simulated'})
        
        # Merge the measured and simulated data into one dataframe
        merged = pd.merge(self.data, simulated_data, on='name').sort_values(by='s').reset_index(drop=True)
        
        # If range was specified, use it
        if s_range: merged = merged[(merged['s'] >= s_range[0]) & (merged['s'] <= s_range[1])]
        
        return merged

    def _simulate(self, angle, aper_data, knob, s_range):
        
        # Vary the crossing angle
        aper_data.change_knob(knob, angle)
        aper_data.twiss()
        
        # Merge new simulated data with the measured data
        merged_b1 = self._merge_twiss_and_bpm(aper_data.tw_b1, s_range)
        merged_b2 = self._merge_twiss_and_bpm(aper_data.tw_b2, s_range)
        
        # Perform the fitting on both beams simultanously
        return pd.concat([merged_b1, merged_b2], ignore_index=True)

    def _objective(self, angle, aper_data, knob, s_range, plane):
        
        df = self._simulate(angle, aper_data, knob, s_range)

        # Calculate the residuals for the plane of interest
        if plane == 'horizontal': residuals = df['x'] - df['x_simulated']
        elif plane == 'vertical': residuals =  df['y'] - df['y_simulated']
            
        return residuals

class CollimatorsData:

    def __init__(self, 
                 spark,
                 yaml_path: Union[str, List[str]] = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/injection.yaml'):
        """
        Initializes the CollimatorsData class.

        Parameters:
            spark: Spark session for accessing the LoggingDB.
            yaml_path: Path to the YAML file containing collimator configurations.
        """
        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)
        self.yaml_path = yaml_path

    def load_data(self, t: datetime) -> None:
        """
        Loads collimator data from the specified YAML file and Timber.

        Parameters:
            t: Datetime object representing the time to fetch data.
        """
        # Load the file  
        with open(self.yaml_path, 'r') as file:
            f = yaml.safe_load(file)

        # Create a data frame for beam 1
        col_b1 = pd.DataFrame(f['collimators']['b1']).loc[['angle']].T
        col_b1 = col_b1.reset_index().rename(columns={'index': 'name'})

        # Create a data frame for beam 2
        col_b2 = pd.DataFrame(f['collimators']['b2']).loc[['angle']].T
        col_b2 = col_b2.reset_index().rename(columns={'index': 'name'})

        # Get a list of collimator names to load from timber
        names_b1 = col_b1['name'].str.upper().to_list()
        names_b2 = col_b2['name'].str.upper().to_list()

        for i, name in enumerate(names_b1): names_b1[i]=name+':MEAS_LVDT_GD'
        for i, name in enumerate(names_b2): names_b2[i]=name+':MEAS_LVDT_GD'

        print_and_clear("Loading collimators data...")

        col_b1_from_timber = self.ldb.get(names_b1, t, t+timedelta(seconds=1)) 
        col_b2_from_timber = self.ldb.get(names_b2, t, t+timedelta(seconds=1))

        # Iterate over all rows and add the gap column's values
        for index, row in col_b1.iterrows():
            try:
                name_to_search = row['name'].upper()+':MEAS_LVDT_GD'
                # Make sure the gaps are in units of metres to match everythong else
                col_b1.at[index, 'gap'] = col_b1_from_timber[name_to_search][1][0]/1e3
            except: col_b1.at[index, 'gap'] = np.nan

        # Iterate over all rows and add the gap column's values
        for index, row in col_b2.iterrows():
            try:
                name_to_search = row['name'].upper()+':MEAS_LVDT_GD'
                # Make sure the gaps are in units of metres to match everythong else
                col_b2.at[index, 'gap'] = col_b2_from_timber[name_to_search][1][0]/1e3
            except: col_b2.at[index, 'gap'] = np.nan

        self.colx_b1 = col_b1[col_b1['angle']==0].dropna()
        self.colx_b2 = col_b2[col_b2['angle']==0].dropna()
        self.coly_b1 = col_b1[col_b1['angle']==90].dropna()
        self.coly_b2 = col_b2[col_b2['angle']==90].dropna()

        print_and_clear("Done loading collimators data.")
        
    def process(self, twiss: object) -> None:
        """
        Processes the loaded collimator data with the provided Twiss data.

        Parameters:
            twiss: An ApertureData object containing Twiss data for beam 1 and beam 2.
        """
        
        self.colx_b1 = self._add_collimator_positions(twiss.tw_b1, self.colx_b1, 'x')
        self.colx_b2 = self._add_collimator_positions(twiss.tw_b2, self.colx_b2, 'x')
        self.coly_b1 = self._add_collimator_positions(twiss.tw_b1, self.coly_b1, 'y')
        self.coly_b2 = self._add_collimator_positions(twiss.tw_b2, self.coly_b2, 'y')
               
    def _add_collimator_positions(self, 
                                  twiss: pd.DataFrame, 
                                  col: pd.DataFrame, 
                                  position_key: str) -> pd.DataFrame:
        """
        Merges collimator data with Twiss data to add positions.

        Parameters:
            twiss: DataFrame containing Twiss data.
            col: DataFrame containing collimator data.
            position_key: The key indicating the position ('x' or 'y').

        Returns:
            pd.DataFrame: The merged DataFrame with updated positions.
        """

        # Ensure 'col' is a copy to avoid SettingWithCopyWarning
        col = col.copy()

        # Change names to lowercase to match twiss
        col.loc[:, 'name'] = col['name'].str.lower()

        # Merge with twiss data to find collimator positions
        col = pd.merge(col[['name', 'gap', 'angle']], twiss[['name', 's', 'x', 'y']], on='name', how='left')

        # Calculate gap in meters and add to the dataFrame
        col.loc[:, 'top_gap_col'] = col['gap'] + col[position_key]
        col.loc[:, 'bottom_gap_col'] = -col['gap'] + col[position_key]
        
        return col