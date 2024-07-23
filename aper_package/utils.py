from ipyfilechooser import FileChooser
import pandas as pd
import tkinter as tk
from tkinter import filedialog

def shift_by(df, by, s):
    """
    shifts a graph by a given value
    """
    # Add the value to shift to the dataframe
    df.loc[:, s] = df.loc[:, s] + by

    # Calculate the shift required to set new_zero as 0
    last_value = 26658.88318

    if by > 0:
        # Substract length of the graph from 'S' values more than 26658.88318
        df.loc[df[s] > last_value, s] -= last_value
    else: 
        # Add length of the graph to 'S' values less than 0
        # This is the same as setting a new 0
        df.loc[df[s] < 0, s] += last_value

    df = df.sort_values(by=s)
    df = df.reset_index(drop=True)

    return df

def select_file(title, initial_path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/'):
    
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(initialdir=initial_path, title=title)
    return file_path
