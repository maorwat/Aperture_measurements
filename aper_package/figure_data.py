import numpy as np
import pandas as pd

import plotly.graph_objects as go
from typing import List, Tuple
from aper_package.utils import merge_twiss_and_aper, print_and_clear, find_s_value

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
    if plane == 'horizontal': y_b1, y_b2 = data.b1.x, data.b2.x
    elif plane == 'vertical': y_b1, y_b2 = data.b1.y, data.b2.y

    # Make sure the units are in meters like twiss data
    b1 = go.Scatter(x=data.b1.s, y=y_b1, mode='markers', 
                          line=dict(color='blue'), text = data.b1.name, name='BPM beam 1')
    
    b2 = go.Scatter(x=data.b2.s, y=y_b2, mode='markers', 
                          line=dict(color='red'), text = data.b2.name, name='BPM beam 2', visible=False)
    
    return np.array([True, False]), [b1, b2]

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

    # Dictionary to store combined data for each object type
    combined_traces = {obj: {'x': [], 'y': [], 'name': []} for obj in objects}
    centers = {obj: {'x': [], 'y': [], 'name': []} for obj in objects}

    # Iterate over all object types
    for obj in objects:
        obj_df = data.elements[data.elements['KEYWORD'] == obj]

        for i in range(obj_df.shape[0]):
            # Calculate x-coordinates
            x0 = obj_df.iloc[i]['S'] - obj_df.iloc[i]['L'] / 2
            x1 = obj_df.iloc[i]['S'] + obj_df.iloc[i]['L'] / 2

            # Calculate y-coordinates
            if obj == 'QUADRUPOLE':
                y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)
                if y0 == y1:  # Skip if K1L is 0
                    continue
            else:
                y0, y1 = -0.5, 0.5

            # Append coordinates, separated by `None`
            combined_traces[obj]['x'].extend([x0, x0, x1, x1, None])
            combined_traces[obj]['y'].extend([y0, y1, y1, y0, None])
            # Calculate the center of the polygon
            x_center = np.mean([x0, x1])
            y_center = np.mean([y0, y1])
            centers[obj]['x'].append(x_center)
            centers[obj]['y'].append(y_center)
            centers[obj]['name'].append(obj_df.iloc[i]['NAME'])

    # Convert combined traces to Plotly Scatter objects
    traces = []
    for obj in objects:
        trace_data = combined_traces[obj]
        trace = go.Scatter(
            x=trace_data['x'],
            y=trace_data['y'],
            fill='toself',
            mode='lines',
            showlegend=False,
            hoverinfo='skip',
            fillcolor=colors[objects.index(obj)],
            line=dict(color=colors[objects.index(obj)])
        )
        traces.append(trace)

        # Add a trace for the names in the middle of the rectangles
        center_trace = go.Scatter(
            x=centers[obj]['x'],
            y=centers[obj]['y'],
            mode='none',
            text=centers[obj]['name'],
            showlegend=False,
            hoverinfo='text'
        )
        traces.append(center_trace)

    # Visibility flags for all objects
    visibility_arr = np.full(len(objects) * 2, True)

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
        plane: A string indicating the plane ('horizontal' for horizontal, 'vertical' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    # Select the appropriate DataFrames based on the plane
    if plane == 'horizontal':
        df_b1, df_b2 = data.colx_b1, data.colx_b2
    elif plane == 'vertical':
        df_b1, df_b2 = data.coly_b1, data.coly_b2

    # Initialize lists for combined coordinates for Beam 1 and Beam 2
    combined_traces = {
        'beam1': {'x': [], 'y': [], 'names': [], 'centers_x': [], 'centers_y': []},
        'beam2': {'x': [], 'y': [], 'names': [], 'centers_x': [], 'centers_y': []}
    }

    # Function to append collimator data to the combined traces
    def add_collimator_traces(df, beam_key):
        for i in range(df.shape[0]):
            x0 = df.s.iloc[i] - 0.5
            x1 = df.s.iloc[i] + 0.5
            y0t = df.top_gap_col.iloc[i]
            y0b = df.bottom_gap_col.iloc[i]
            y1 = 0.1

            # Top and bottom collimator combined in the same trace
            combined_traces[beam_key]['x'].extend([x0, x0, x1, x1, None, x0, x0, x1, x1, None])
            combined_traces[beam_key]['y'].extend([y0t, y1, y1, y0t, None, y0b, -y1, -y1, y0b, None])

            # Calculate the center of the collimator's filled area
            x_center = np.mean([x0, x1])
            y_center_top = np.mean([y0t, 0.05])
            y_center_bottom = np.mean([y0b, -0.05])
            combined_traces[beam_key]['centers_x'].append(x_center)
            combined_traces[beam_key]['centers_x'].append(x_center)
            combined_traces[beam_key]['centers_y'].append(y_center_top)
            combined_traces[beam_key]['centers_y'].append(y_center_bottom)
            # Use the name from the DataFrame
            combined_traces[beam_key]['names'].append(df.name.iloc[i])
            combined_traces[beam_key]['names'].append(df.name.iloc[i])

    # Add data for both beams
    add_collimator_traces(df_b1, 'beam1')
    add_collimator_traces(df_b2, 'beam2')

    # Create traces for the collimators
    collimators = []
    for beam_key in combined_traces:
        trace_data = combined_traces[beam_key]
        # Trace for filled areas
        collimator_trace = go.Scatter(
            x=trace_data['x'],
            y=trace_data['y'],
            fill="toself",
            mode='lines',
            fillcolor='black',
            hoverinfo='skip',
            showlegend=False,
            line=dict(color='black'),
            visible=True if beam_key == 'beam1' else False
        )
        collimators.append(collimator_trace)

        # Trace for names in the middle of the collimators
        center_trace = go.Scatter(
            x=trace_data['centers_x'],
            y=trace_data['centers_y'],
            mode='none',
            text=trace_data['names'],
            showlegend=False,
            hoverinfo='text',
            visible=True if beam_key == 'beam1' else False
        )
        collimators.append(center_trace)

    # Visibility array: show only Beam 1 collimators by default
    visibility_arr = np.array([True, True, False, False])

    return visibility_arr, collimators

def plot_envelopes(data: object, plane: str):
    """
    Plot the beam envelopes for a given plane.

    Parameters:
        data: An ApertureData object containing beam envelope data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """
    
    upper_b1 = create_envelope(data.tw_b1, plane, 'beam 1', 'up', None, True)
    lower_b1 = create_envelope(data.tw_b1, plane, 'beam 1', 'down', 'tonexty', True)
    upper_b2 = create_envelope(data.tw_b2, plane, 'beam 2', 'up', None, False)
    lower_b2 = create_envelope(data.tw_b2, plane, 'beam 2', 'down', 'tonexty', False)

    visibility = np.array([True, True, False, False])
    traces = [upper_b1, lower_b1, upper_b2, lower_b2]

    return visibility, traces

def create_envelope(twiss_df, plane, beam, up_or_down, fill, visibility):

    # Define hover template with customdata
    hover_template = ("s: %{x:.2f} [m]<br>"
                        "x: %{y:.4f} [m]<br>"
                        "x: %{customdata[2]:.2f} [σ]<br>"
                        "element: %{text}<br>"
                        "distance from nominal: %{customdata[0]:.2f} [mm]<br>"
                        "distance from nominal: %{customdata[1]:.2f} [σ]")
    
    base_column = 'x' if plane == 'horizontal' else 'y'
    
    position_column, sigma = base_column+'_'+up_or_down, 'sigma_'+base_column
    
    if up_or_down == 'up': nom_to_envelope_column, name = base_column+'_from_nom_to_top', 'Upper envelope '+beam
    elif up_or_down == 'down': nom_to_envelope_column, name = base_column+'_from_nom_to_bottom', 'Bottom envelope '+beam
            
    if beam == 'beam 1': color = 'rgba(0,0,255,0.1)'
    elif beam == 'beam 2': color = 'rgba(255,0,0,0.1)'


    customdata = list(zip(twiss_df[nom_to_envelope_column], twiss_df[nom_to_envelope_column]*1e-3/twiss_df[sigma], twiss_df[position_column]/twiss_df[sigma]))

    trace = go.Scatter(x=twiss_df.s, 
            y=twiss_df[position_column], 
            mode='lines', 
            text=twiss_df.name, 
            name=name, 
            fill=fill, 
            line=dict(color='rgba(0, 0, 0, 0)'),
            fillcolor=color,
            customdata=customdata, 
            hovertemplate=hover_template,
            visible = visibility)
    
    return trace

def plot_beam_positions(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the beam positions for a given plane.

    Parameters:
        data: An ApertureData object containing beam position data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'horizontal': y_b1, y_b2 = data.tw_b1.x, data.tw_b2.x
    elif plane == 'vertical': y_b1, y_b2 = data.tw_b1.y, data.tw_b2.y

    b1 = go.Scatter(x=data.tw_b1.s, y=y_b1, mode='lines', line=dict(color='blue'), text = data.tw_b1.name, name='Beam 1')
    b2 = go.Scatter(x=data.tw_b2.s, y=y_b2, mode='lines', line=dict(color='red'), text = data.tw_b2.name, name='Beam 2', visible=False)
    
    return np.array([True, False]), [b1, b2]

def plot_nominal_beam_positions(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the nominal beam positions for a given plane.

    Parameters:
        data: An ApertureData object containing nominal beam position data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'horizontal': y_b1, y_b2 = data.nom_b1.x, data.nom_b2.x
    elif plane == 'vertical': y_b1, y_b2 = data.nom_b1.y, data.nom_b2.y

    b1 = go.Scatter(x=data.nom_b1.s, y=y_b1, mode='lines', line=dict(color='blue', dash='dash'), text = data.nom_b1.name, name='Nominal beam 1')
    b2 = go.Scatter(x=data.nom_b2.s, y=y_b2, mode='lines', line=dict(color='red', dash='dash'), text = data.nom_b2.name, name='Nominal beam 2', visible=False)
    
    return np.array([True, False]), [b1, b2]

def plot_aperture(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the aperture for a given plane.

    Parameters:
        data: An ApertureData object containing aperture data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'horizontal':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')     
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    elif plane == 'vertical':
            
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

def generate_2d_plot(element, beam, data, n, width=600, height=600):
    
    # Create the figure
    fig = go.Figure()
    
    if beam == 'both': 
        beam_center_trace_b1, envelope_trace_b1, aperture_trace_b1 = add_beam_trace(element, 'beam 1', data, n)
        beam_center_trace_b2, envelope_trace_b2, aperture_trace_b2 = add_beam_trace(element, 'beam 2', data, n)
        # Add scatter trace for beam center
        fig.add_trace(beam_center_trace_b1)
        fig.add_trace(envelope_trace_b1)
        fig.add_trace(aperture_trace_b1)
        fig.add_trace(beam_center_trace_b2)
        fig.add_trace(envelope_trace_b2)
        fig.add_trace(aperture_trace_b2)
    else:
        beam_center_trace, envelope_trace, aperture_trace = add_beam_trace(element, beam, data, n)

        # Add scatter trace for beam center
        fig.add_trace(beam_center_trace)
        fig.add_trace(envelope_trace)
        fig.add_trace(aperture_trace)

    # Update layout for the figure with custom width and height
    fig.update_layout(
        plot_bgcolor='white',
        xaxis_title='x [m]',
        yaxis_title='y [m]',
        showlegend=False,
        width=width,  # Set the width of the figure
        height=height  # Set the height of the figure
    )
    
    # Add gridlines for both axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey', zeroline=True, zerolinewidth=1, zerolinecolor='lightgrey')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey', zeroline=True, zerolinewidth=1, zerolinecolor='lightgrey')

    # Set axis limits to -0.05 to 0.05 for both x and y axes
    fig.update_xaxes(range=[-0.05, 0.05])
    fig.update_yaxes(range=[-0.05, 0.05])

    return go.FigureWidget(fig)

def add_beam_trace(element, beam, data, n):

    # Merging and filtering logic for beam 1 and beam 2
    if beam == 'beam 1': 
        if hasattr(data, 'aper_b1'):
            twiss, aper = data.tw_b1, data.aper_b1
            merged = merge_twiss_and_aper(twiss, aper)
        else: merged = data.tw_b1
        color = 'rgba(0,0,255,1)'
        color_fill = 'rgba(0,0,255,0.5)'
    elif beam == 'beam 2': 
        if hasattr(data, 'aper_b2'):
            twiss, aper = data.tw_b2, data.aper_b2
            merged = merge_twiss_and_aper(twiss, aper)
        else: merged = data.tw_b2
        color = 'rgba(255,0,0,1)'
        color_fill = 'rgba(255,0,0,0.5)'
        
    element_position = find_s_value(element, data)
    merged = merged.reset_index(drop=True)
    # Filter the data for the given element
    try:
        filtered_df = merged.iloc[(merged['s'] - element_position).abs().idxmin()]
    except:
        print_and_clear('Incorrect element')
        return go.Scatter(), go.Scatter(), go.Scatter()

    if hasattr(data, 'aper_b1'):
        # Extract rectangle dimensions from APER_1 and APER_2
        aper_x = filtered_df['APER_1']
        aper_y = filtered_df['APER_2']
        
        # Define the rectangle corners as a scatter trace
        aperture_trace = go.Scatter(
            x=[-aper_x, aper_x, aper_x, -aper_x, -aper_x],  # Close the rectangle
            y=[-aper_y, -aper_y, aper_y, aper_y, -aper_y],  # Close the rectangle
            mode='lines',
            line=dict(color='grey', width=2),
            fill='toself',  # To close the shape
            fillcolor='rgba(0, 0, 0, 0)'  # No fill
        )
    # If aperture isn't loaded return an empty trace
    else: aperture_trace = go.Scatter()
    
    beam_center_trace = go.Scatter(
        x=[filtered_df['x']], 
        y=[filtered_df['y']], 
        mode='markers+lines', 
        name='Beam center', 
        hoverinfo='text',
        text=['Beam center'],
        line=dict(color=color)
    )

    # Extract rectangle coordinates
    x0 = filtered_df['x'] - n * filtered_df['sigma_x']
    x1 = filtered_df['x'] + n * filtered_df['sigma_x']
    y0 = filtered_df['y'] - n * filtered_df['sigma_y']
    y1 = filtered_df['y'] + n * filtered_df['sigma_y']
    
    # Define the rectangle corners as a scatter trace
    envelope_trace = go.Scatter(
        x=[x0, x1, x1, x0, x0],  # Close the rectangle by repeating x0 at the end
        y=[y0, y0, y1, y1, y0],  # Close the rectangle by repeating y0 at the end
        mode='lines',
        line=dict(color=color, width=2),
        fill='toself',  # To fill the shape (optional)
        fillcolor=color_fill  # Example fill color with some transparency
    )
    
    return beam_center_trace, envelope_trace, aperture_trace