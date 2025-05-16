# file_handling.py - File upload and handling for Dash
import base64
import io
import pandas as pd
import re
from dash import html, dcc
import dash_bootstrap_components as dbc
import numpy as np

def parse_uploaded_file(contents, filename):
    """
    Parse the uploaded file contents and return a DataFrame
    
    Parameters:
    - contents: Contents of the uploaded file (base64 encoded)
    - filename: Name of the uploaded file
    
    Returns:
    - df: Pandas DataFrame with the loaded data
    - encoding: The successful encoding used
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    # Try to load the file with different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            # Try to read with current encoding
            df = pd.read_csv(
                io.StringIO(decoded.decode(encoding)),
                sep=None,  # Auto-detect separator
                engine='python',  # More flexible engine
                on_bad_lines='warn'  # Continue despite bad lines
            )
            
            # Check and convert clock column if needed
            if 'clock' in df.columns:
                # Check if any values are numeric (floating point)
                if df['clock'].dtype.kind in 'fi' or any(isinstance(x, (int, float)) for x in df['clock'].dropna()):
                    # Convert numeric values to clock format
                    df['clock'] = df['clock'].apply(
                        lambda x: float_to_clock(float(x)) if pd.notna(x) and isinstance(x, (int, float)) else x
                    )
                
                # For string values that don't look like clock format (HH:MM)
                clock_pattern = re.compile(r'^\d{1,2}:\d{2}$')
                non_standard = df['clock'].apply(
                    lambda x: pd.notna(x) and isinstance(x, str) and not clock_pattern.match(x)
                ).any()
            
            return df, encoding, None  # None for error
            
        except Exception as e:
            continue  # Try next encoding
    
    # If all encodings fail
    return None, None, "Failed to load the file with any of the standard encodings."


def create_file_preview(df, filename, encoding):
    """
    Create a file preview component
    
    Parameters:
    - df: DataFrame with the loaded data
    - filename: Name of the uploaded file
    - encoding: The encoding used to load the file
    
    Returns:
    - component: Dash component with file preview
    """
    # Create encoding info alert if not UTF-8
    if encoding != 'utf-8':
        encoding_info = dbc.Alert([
            html.I(className="fas fa-info-circle mr-2", style={"margin-right": "8px"}),
            f"File loaded with {encoding} encoding. Some special characters may display differently."
        ], color="info")
    else:
        encoding_info = html.Div()
    
    # Create a card with file info
    file_info = dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.I(className="fas fa-file-csv", style={"font-size": "2rem", "color": "#1565c0"})
                ], style={"margin-right": "15px"}),
                html.Div([
                    html.H5(filename, className="mb-1"),
                    html.P([
                        f"Rows: {df.shape[0]} • ",
                        f"Columns: {df.shape[1]}"
                    ], className="text-muted mb-0")
                ])
            ], className="d-flex align-items-center")
        ])
    ], className="mb-3")
    
    # Create the data preview table
    preview_table = dbc.Table.from_dataframe(
        df.head(100),
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        style={"overflowX": "auto", "fontSize": "0.9rem"}
    )
    
    return html.Div([
        file_info,
        encoding_info,
        html.Div([
            html.H5([
                html.I(className="fas fa-table mr-2", style={"margin-right": "8px"}),
                "Data Preview"
            ], className="mb-3"),
            html.Div(preview_table, style={"overflowX": "auto", "maxHeight": "400px"})
        ])
    ])


def float_to_clock(time_float):
    """Convert float time to clock format (HH:MM)"""
    if pd.isna(time_float):
        return None  # or return "NaN" or ""

    total_minutes = time_float * 24 * 60
    hours = int(total_minutes // 60)
    minutes = int(round(total_minutes % 60))
    return f"{hours:02d}:{minutes:02d}"