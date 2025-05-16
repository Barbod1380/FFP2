# column_mapping_ui.py - Column mapping UI for Dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from column_mapping import STANDARD_COLUMNS, REQUIRED_COLUMNS, get_missing_required_columns

def create_column_mapping_ui(df, suggested_mapping, selected_year):
    """
    Create a UI for column mapping.
    
    Parameters:
    - df: DataFrame with the uploaded data
    - suggested_mapping: Dictionary of suggested mappings
    - selected_year: The selected year for this dataset
    
    Returns:
    - component: Dash component with column mapping UI
    """
    # All available columns from the file plus None option
    all_columns = [None] + df.columns.tolist()
    
    # Split columns into three groups
    column_groups = []
    columns_per_group = len(STANDARD_COLUMNS) // 3
    remainder = len(STANDARD_COLUMNS) % 3
    
    # Adjust the split for uneven division
    split_points = [0]
    for i in range(3):
        extra = 1 if i < remainder else 0
        split_points.append(split_points[-1] + columns_per_group + extra)
    
    for i in range(3):
        start, end = split_points[i], split_points[i+1]
        column_groups.append(STANDARD_COLUMNS[start:end])
    
    # Create the mapping UI
    mapping_rows = []
    
    # Get any missing required columns
    missing_cols = get_missing_required_columns(suggested_mapping)
    missing_warning = create_missing_columns_warning(missing_cols) if missing_cols else html.Div()
    
    # Add the column selector components in a 3-column layout
    mapping_ui = html.Div([
        html.H5([
            html.I(className="fas fa-exchange-alt mr-2", style={"margin-right": "8px"}),
            "Column Mapping"
        ], className="mb-3"),
        
        html.P([
            "Map columns from your file to the standard column names. ",
            html.Strong("Required fields are marked with *."),
            " The system has automatically suggested matches based on column names."
        ], className="mb-3"),
        
        missing_warning,
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    create_column_selector(col, all_columns, suggested_mapping, selected_year)
                    for col in column_groups[0]
                ])
            ], width=4),
            dbc.Col([
                html.Div([
                    create_column_selector(col, all_columns, suggested_mapping, selected_year)
                    for col in column_groups[1]
                ])
            ], width=4),
            dbc.Col([
                html.Div([
                    create_column_selector(col, all_columns, suggested_mapping, selected_year)
                    for col in column_groups[2]
                ])
            ], width=4)
        ]),
        
        # Store for the confirmed mapping
        dcc.Store(id=f"confirmed-mapping-{selected_year}")
    ], className="column-mapping-container")
    
    return mapping_ui

def create_column_selector(std_col, all_columns, suggested_mapping, selected_year):
    """
    Create a column selector component for a standard column.
    
    Parameters:
    - std_col: Standard column name
    - all_columns: List of all available columns
    - suggested_mapping: Dictionary of suggested mappings
    - selected_year: The selected year for this dataset
    
    Returns:
    - component: Dash component with column selector
    """
    # Get the suggested mapping for this column
    suggested = suggested_mapping.get(std_col)
    
    # Check if this is a required column
    is_required = std_col in REQUIRED_COLUMNS
    label = f"{std_col}" + (" *" if is_required else "")
    
    # Format options properly for newer Dash versions
    # Create a dictionary with {value: label} format
    options = {}
    for col in all_columns:
        # Handle None values
        if col is None:
            options["null"] = "None"
        else:
            options[col] = str(col)
    
    # Check the value for selection (handle None case)
    value = suggested if suggested is not None else "null"
    
    return html.Div([
        html.Label(label, className="form-label" + (" text-danger font-weight-bold" if is_required else "")),
        dcc.Dropdown(
            id=f"column-map-{selected_year}-{std_col.replace(' ', '-').replace('[', '').replace(']', '').replace('/', '-')}",
            options=options,
            value=value,
            clearable=False,
            className="mb-3"
        )
    ])

def create_missing_columns_warning(missing_cols):
    """
    Create a warning component for missing required columns.
    
    Parameters:
    - missing_cols: List of missing required columns
    
    Returns:
    - component: Dash component with warning
    """
    if not missing_cols:
        return html.Div()
    
    return dbc.Alert(
        [
            html.I(className="fas fa-exclamation-triangle mr-2", style={"margin-right": "8px"}),
            html.Strong("Missing required columns: "),
            html.Span(", ".join(missing_cols)),
            html.P("You may proceed, but functionality may be limited.")
        ],
        color="warning",
        className="mb-3"
    )

def create_pipeline_specs_ui(selected_year):
    """
    Create a UI for entering pipeline specifications.
    
    Parameters:
    - selected_year: The selected year for this dataset
    
    Returns:
    - component: Dash component with pipeline specs UI
    """
    return html.Div([
        html.H5([
            html.I(className="fas fa-ruler mr-2", style={"margin-right": "8px"}),
            "Pipeline Specifications"
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Pipe Diameter (m)", className="form-label"),
                dbc.InputGroup([
                    dcc.Input(
                        id={"type": "pipe-diameter", "year": selected_year},
                        type="number",
                        min=0.1,
                        max=3.0,
                        step=0.1,
                        value=1.0,
                        className="form-control"
                    ),
                    dbc.InputGroupText("m")
                ]),
                html.Small("Enter the pipeline diameter in meters", className="form-text text-muted")
            ], width=6)
        ])
    ], className="pipeline-specs-container")

def collect_column_mapping(selected_year):
    """
    Create a callback function to collect the column mapping.
    
    This function should be used inside a callback to collect all the 
    individual dropdown values into a single mapping dictionary.
    
    Parameters:
    - selected_year: The selected year for this dataset
    
    Returns:
    - A callback input list to collect all dropdown values
    """
    input_list = []
    for std_col in STANDARD_COLUMNS:
        # Create a sanitized version of the column name for use in IDs
        sanitized = std_col.replace(' ', '-').replace('[', '').replace(']', '').replace('/', '-')
        input_list.append(
            (f"column-map-{selected_year}-{sanitized}", "value")
        )
    return input_list


def collect_mapping_from_inputs(inputs, standard_columns):
    """
    Collect the column mapping from the inputs dictionary.
    
    Parameters:
    - inputs: Dictionary of input values from the callback
    - standard_columns: List of standard column names
    
    Returns:
    - Dictionary mapping from standard column names to file column names
    """
    mapping = {}
    
    for i, std_col in enumerate(standard_columns):
        # Get the value from the appropriate input
        file_col = inputs[i]
        
        # Handle the "null" special case
        if file_col == "null":
            file_col = None
            
        mapping[std_col] = file_col
        
    return mapping