import numpy as np
import pandas as pd

import plotly.graph_objects as go
from typing import List, Tuple

def plot_BPM_data(data: object, 
                  plane: str, 
                  twiss: object) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Assign all BPMs to positions s based on twiss data and generate Plotly traces.

    Parameters:
        data: An object BPMData, expected to have attribute data.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).
        twiss: An ApertureData object containing aperture data used for processing BPM positions.

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing an array of booleans and a list of Plotly scatter traces.
    """
    # Assign BPMs to some position along the ring s by merging with twiss
    data.process(twiss)

    # Select data based on plane
    if plane == 'h': y_b1, y_b2 = data.b1.x, data.b2.x
    elif plane == 'v': y_b1, y_b2 = data.b1.y, data.b2.y

    # Make sure the units are in meters like twiss data
    b1 = go.Scatter(x=data.b1.s, y=y_b1/1e6, mode='markers', 
                          line=dict(color='blue'), text = data.b1.name, name='BPM beam 1')
    
    b2 = go.Scatter(x=data.b2.s, y=y_b2/1e6, mode='markers', 
                          line=dict(color='red'), text = data.b2.name, name='BPM beam 2')
    
    return np.full(2, True), [b1, b2]

def plot_machine_components(data: object) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Generates Plotly traces for various machine components based on their type and position.

    Parameters:
        data: An ApertureData object containing machine element data, expected to have a DataFrame 'elements'
              with columns 'KEYWORD', 'S', 'L', 'K1L', and 'NAME'.

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing an array of visibility flags and a list of Plotly scatter traces.
    """
    # Specify the elements to plot and corresponding colors
    objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
    colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

    # Array to store visibility of the elements
    visibility_arr = np.array([], dtype=bool)

    # Dictionary to store combined data for each object type
    combined_traces = {obj: {'x': [], 'y': [], 'name': obj, 'color': colors[n]} for n, obj in enumerate(objects)}

    # Iterate over all object types
    for n, obj in enumerate(objects):
        obj_df = data.elements[data.elements['KEYWORD'] == obj]
        
        # Collect x and y coordinates for the current object type
        x_coords = []
        y_coords = []

        for i in range(obj_df.shape[0]):
            x0, x1 = obj_df.iloc[i]['S']-obj_df.iloc[i]['L']/2, obj_df.iloc[i]['S']+obj_df.iloc[i]['L']/2
            if obj == 'QUADRUPOLE':
                y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)
            else:
                y0, y1 = -0.5, 0.5

            # Append coordinates to the respective object type
            x_coords.extend([x0, x0, x1, x1, None])  # None to separate shapes
            y_coords.extend([y0, y1, y1, y0, None])

        # Add combined coordinates to the dictionary
        combined_traces[obj]['x'].append(x_coords)
        combined_traces[obj]['y'].append(y_coords)

    # Convert combined traces to Plotly Scatter objects
    traces = []
    for obj in objects:
        trace_data = combined_traces[obj]
        trace = go.Scatter(
            x=np.concatenate(trace_data['x']),
            y=np.concatenate(trace_data['y']),
            fill='toself',
            mode='lines',
            fillcolor=trace_data['color'],
            line=dict(color=trace_data['color']),
            name=obj
        )
        traces.append(trace)

    # Append to always show the elements
    visibility_arr = np.append(visibility_arr, np.full(len(objects), True))

    return visibility_arr, traces

def plot_collimators_from_yaml(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot collimators based on YAML data.

    Parameters:
        data: An ApertureData object containing collimator data.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    
    return plot_collimators(data, plane)

def plot_collimators_from_timber(collimator_data: object, data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    
    """
    Plot collimators after processing data from TIMBER.

    Parameters:
        collimator_data: A CollimatorData object containing raw collimator data.
        data: An ApertureData object containing additional data needed for processing.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    collimator_data.process(data)
    
    return plot_collimators(collimator_data, plane)

def plot_collimators(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot collimators for a given plane.

    Parameters:
        data: An object containing collimator data with attributes `colx_b1`, `colx_b2`, `coly_b1`, `coly_b2`.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    # Select the appropriate DataFrames based on the plane
    if plane == 'h': df_b1, df_b2 = data.colx_b1, data.colx_b2
    elif plane == 'v': df_b1, df_b2 = data.coly_b1, data.coly_b2

    # Create empty lists for traces
    collimators = []

    # Plot
    for df, vis in zip([df_b1, df_b2], [True, False]):

        for i in range(df.shape[0]):
            x0, y0b, y0t, x1, y1 = df.s.iloc[i] - 0.5, df.bottom_gap_col.iloc[i], df.top_gap_col.iloc[i], df.s.iloc[i] + 0.5, 0.1

            top_col = go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i], visible=vis)
            bottom_col = go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i], visible=vis)
            
            collimators.append(top_col)
            collimators.append(bottom_col)
        
    # Create visibility array: show only Beam 1 collimators by default
    visibility_arr_b1 = np.concatenate((np.full(df_b1.shape[0]*2, True), np.full(df_b2.shape[0]*2, False)))

    return visibility_arr_b1, collimators

def plot_envelopes(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the beam envelopes for a given plane.

    Parameters:
        data: An ApertureData object containing beam envelope data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    # Define hover template with customdata
    hover_template = ("s: %{x} [m]<br>"
                            "x: %{y} [m]<br>"
                            "element: %{text}<br>"
                            "distance from nominal: %{customdata} [mm]")

    if plane == 'h':

        upper_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.x_up, mode='lines', 
                                  text = data.tw_b1.name, name='Upper envelope beam 1', 
                                  fill=None, line=dict(color='rgba(0,0,255,0)'),
                                  customdata=data.tw_b1.x_from_nom_to_top, hovertemplate=hover_template)
        lower_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.x_down, mode='lines', 
                                  text = data.tw_b1.name, name='Lower envelope beam 1', 
                                  line=dict(color='rgba(0,0,255,0)'), fill='tonexty', fillcolor='rgba(0,0,255,0.1)',
                                  customdata=data.tw_b1.x_from_nom_to_bottom, hovertemplate=hover_template)
        upper_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.x_up, mode='lines', 
                                  text = data.tw_b2.name, name='Upper envelope beam 2', 
                                  fill=None, line=dict(color='rgba(255,0,0,0)'),
                                  customdata=data.tw_b2.x_from_nom_to_top, hovertemplate=hover_template)
        lower_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.x_down, mode='lines', 
                                  text = data.tw_b2.name, name='Lower envelope beam 2', 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)', 
                                  customdata=data.tw_b2.x_from_nom_to_bottom, hovertemplate=hover_template)
        
    elif plane == 'v':

        upper_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.y_up, mode='lines', 
                                  text = data.tw_b1.name, name='Upper envelope beam 1', 
                                  fill=None, line=dict(color='rgba(0,0,255,0)'),
                                  customdata=data.tw_b1.y_from_nom_to_top, hovertemplate=hover_template)
        lower_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.y_down, mode='lines', 
                                  text = data.tw_b1.name, name='Lower envelope beam 1', 
                                  line=dict(color='rgba(0,0,255,0)'), fill='tonexty', fillcolor='rgba(0,0,255,0.1)',
                                  customdata=data.tw_b1.y_from_nom_to_bottom, hovertemplate=hover_template)
        upper_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.y_up, mode='lines', 
                                  text = data.tw_b2.name, name='Upper envelope beam 2', 
                                  fill=None, line=dict(color='rgba(255,0,0,0)'),
                                  customdata=data.tw_b2.y_from_nom_to_top, hovertemplate=hover_template)
        lower_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.y_down, mode='lines', 
                                  text = data.tw_b2.name, name='Lower envelope beam 2', 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)',
                                  customdata=data.tw_b2.y_from_nom_to_bottom, hovertemplate=hover_template)
        
    visibility = np.full(4, True)
    traces = [upper_b1, lower_b1, upper_b2, lower_b2]

    return visibility, traces

def plot_beam_positions(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the beam positions for a given plane.

    Parameters:
        data: An ApertureData object containing beam position data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'h': y_b1, y_b2 = data.tw_b1.x, data.tw_b2.x
    elif plane == 'v': y_b1, y_b2 = data.tw_b1.y, data.tw_b2.y

    b1 = go.Scatter(x=data.tw_b1.s, y=y_b1, mode='lines', line=dict(color='blue'), text = data.tw_b1.name, name='Beam 1')
    b2 = go.Scatter(x=data.tw_b2.s, y=y_b2, mode='lines', line=dict(color='red'), text = data.tw_b2.name, name='Beam 2')
    
    return np.full(2, True), [b1, b2]

def plot_nominal_beam_positions(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the nominal beam positions for a given plane.

    Parameters:
        data: An ApertureData object containing nominal beam position data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'h': y_b1, y_b2 = data.nom_b1.x, data.nom_b2.x
    elif plane == 'v': y_b1, y_b2 = data.nom_b1.y, data.nom_b2.y

    b1 = go.Scatter(x=data.nom_b1.s, y=y_b1, mode='lines', line=dict(color='blue', dash='dash'), text = data.nom_b1.name, name='Nominal beam 1')
    b2 = go.Scatter(x=data.nom_b2.s, y=y_b2, mode='lines', line=dict(color='red', dash='dash'), text = data.nom_b2.name, name='Nominal beam 2')
    
    return np.full(2, True), [b1, b2]

def plot_aperture(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the aperture for a given plane.

    Parameters:
        data: An ApertureData object containing aperture data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'h':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')     
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    elif plane == 'v':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    traces = [top_aper_b1, bottom_aper_b1, top_aper_b2, bottom_aper_b2]
    visibility = np.array([True, True, False, False])

    return visibility, traces

def add_velo(data: object) -> go.Scatter:
    """
    Add a VELO trace at the IP8 position.

    Parameters:
        data: An ApertureData object containing twiss data for beam 1.

    Returns:
        go.Scatter: A Plotly scatter trace representing the VELO.
    """

    # Find ip8 position
    ip8 = data.tw_b1.loc[data.tw_b1['name'] == 'ip8', 's'].values[0]

    # VELO position
    x0=ip8-0.2
    x1=ip8+0.8
    y0=-0.05
    y1=0.05

    trace = go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], mode='lines', line=dict(color='orange'), name='VELO')

    return trace