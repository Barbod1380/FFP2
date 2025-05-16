# file_processing.py - File processing UI and callbacks
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import json

from file_handling import parse_uploaded_file, create_file_preview
from column_mapping_ui import (
    create_column_mapping_ui, 
    create_pipeline_specs_ui, 
    create_missing_columns_warning,
    collect_column_mapping
)
from column_mapping import (
    suggest_column_mapping, 
    apply_column_mapping, 
    get_missing_required_columns
)
from data_processing import process_pipeline_data
from utils import standardize_surface_location, parse_clock

# Create the file processing layout
def create_file_processing_layout():
    """Create the layout for the file processing tab"""
    return html.Div([
        # Step indicator
        html.Div([
            html.Div([
                html.Div([
                    html.Div([html.I(className="fas fa-upload")], className="step-icon"),
                    html.Div("Upload", className="step-text")
                ], className="step active", id="step-upload"),
                html.Div([
                    html.Div([html.I(className="fas fa-columns")], className="step-icon"),
                    html.Div("Map Columns", className="step-text")
                ], className="step", id="step-map"),
                html.Div([
                    html.Div([html.I(className="fas fa-cogs")], className="step-icon"),
                    html.Div("Process", className="step-text")
                ], className="step", id="step-process")
            ], className="steps-container")
        ], className="mb-4"),
        
        # Content will be populated by callbacks based on upload state
        html.Div(id="upload-content"),
        
        # Action buttons
        html.Div(id="processing-buttons", className="mt-3"),
        
        # Processing messages 
        html.Div(id="processing-messages")
    ])

# File upload callback
def register_upload_callbacks(app, datasets):
    """Register all callbacks related to file upload and processing"""
    
    @app.callback(
        Output("upload-content", "children"),
        Output("upload-info", "data"),
        Output("step-upload", "className"),
        Output("step-map", "className"),
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        State("year-selector", "value"),
        prevent_initial_call=True
    )
    def update_upload_content(contents, filename, selected_year):
        """Update the upload content based on the uploaded file"""
        if contents is None:
            return html.Div(), None, "step active", "step"
        
        # Parse the uploaded file
        df, encoding, error = parse_uploaded_file(contents, filename)
        
        if error:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-triangle mr-2", style={"margin-right": "8px"}),
                f"Error: {error}"
            ], color="danger"), None, "step active", "step"
        
        # Create file preview
        preview = create_file_preview(df, filename, encoding)
        
        # Suggest column mapping
        suggested_mapping = suggest_column_mapping(df)
        
        # Create column mapping UI
        mapping_ui = create_column_mapping_ui(df, suggested_mapping, selected_year)
        
        # Create pipeline specs UI
        specs_ui = create_pipeline_specs_ui(selected_year)
        
        # Store upload info
        upload_info = {
            "filename": filename,
            "encoding": encoding,
            "year": selected_year,
            "columns": df.columns.tolist(),
            # Don't store the dataframe itself in the browser, it will be too large
            # Instead, we'll store it in the server-side datasets dictionary
        }
        
        # Store the dataframe in a server-side variable
        # This avoids sending large dataframes to the browser
        if "temp_df" not in datasets:
            datasets["temp_df"] = {}
        datasets["temp_df"][selected_year] = df
        
        # Package all the components in a card
        upload_container = html.Div([
            html.Div([
                html.H4([
                    html.I(className="fas fa-file-csv mr-2", style={"margin-right": "8px"}),
                    "File Preview and Column Mapping"
                ], className="mb-3"),
                html.Div([
                    preview,
                    html.Div(className="mt-4"),
                    mapping_ui,
                    html.Div(className="mt-4"),
                    specs_ui
                ])
            ], className="visualization-card p-3")
        ])
        
        # Update steps
        return upload_container, upload_info, "step completed", "step active"
    
    @app.callback(
        Output("processing-buttons", "children"),
        Input("upload-info", "data")
    )
    def update_processing_buttons(upload_info):
        """Update the processing buttons based on the upload state"""
        if upload_info is None:
            return html.Div()
        
        selected_year = upload_info.get("year")
        
        return html.Div([
            dbc.Button([
                html.I(className="fas fa-cogs mr-2", style={"margin-right": "8px"}),
                f"Process {selected_year} Data"
            ],
                id={"type": "process-data-btn", "year": selected_year},
                color="primary",
                className="me-2"
            ),
            dbc.Button([
                html.I(className="fas fa-times mr-2", style={"margin-right": "8px"}),
                "Cancel"
            ],
                id="cancel-processing-btn",
                color="secondary"
            )
        ], className="d-flex justify-content-end")
    
    @app.callback(
        Output("processing-messages", "children"),
        Output("processed-data-info", "data"),  # This store will trigger a refresh of the loaded datasets display
        Output("step-process", "className"),
        Input({"type": "process-data-btn", "year": ALL}, "n_clicks"),
        State("upload-info", "data"),
        State({"type": "pipe-diameter", "year": ALL}, "value"),
        prevent_initial_call=True
    )
    def process_data(process_clicks, upload_info, pipe_diameters):
        """Process the data when the Process button is clicked"""
        if not process_clicks or not any(process_clicks) or not upload_info:
            return html.Div(), None, "step"
        
        selected_year = upload_info.get("year")
        
        # Get the pipe diameter for this year
        # Use default value if not found
        pipe_diameter = 1.0
        if pipe_diameters and len(pipe_diameters) > 0:
            pipe_diameter = pipe_diameters[0] if pipe_diameters[0] is not None else 1.0
        
        # Create a callback context to get the button that was clicked
        triggered_id = ctx.triggered_id
        
        # Check if any process button was clicked
        if triggered_id and isinstance(triggered_id, dict) and triggered_id.get("type") == "process-data-btn":
            # Get the dataframe from the server-side variable
            df = datasets["temp_df"].get(selected_year)
            
            if df is None:
                return dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle mr-2", style={"margin-right": "8px"}),
                    "Error: No data found"
                ], color="danger"), None, "step"
            
            # Collect all column mapping values
            # This is a bit tricky in Dash - we need to use pattern-matching callbacks
            # For now, just create a dummy mapping as placeholder
            # In the full implementation, we'd collect all dropdown values
            dummy_mapping = {}
            for col in df.columns:
                dummy_mapping[col] = col
            
            # Apply column mapping
            standardized_df = apply_column_mapping(df, dummy_mapping)
            
            # Standardize surface location if present
            if 'surface location' in standardized_df.columns:
                standardized_df['surface location'] = standardized_df['surface location'].apply(standardize_surface_location)
            
            # Process the pipeline data
            try:
                joints_df, defects_df = process_pipeline_data(standardized_df)
                
                # Process clock data
                if 'clock' in defects_df.columns:
                    # First ensure all clock values are in string format
                    defects_df['clock'] = defects_df['clock'].astype(str)
                    
                    # Check if string values don't match the expected format
                    import re
                    clock_pattern = re.compile(r'^\d{1,2}:\d{2}$')
                    non_standard = defects_df['clock'].apply(
                        lambda x: pd.notna(x) and not clock_pattern.match(x) and x != 'nan'
                    ).any()
                    
                    if non_standard:
                        # Try to fix non-standard formats
                        from utils import float_to_clock
                        defects_df['clock'] = defects_df['clock'].apply(
                            lambda x: float_to_clock(float(x)) if pd.notna(x) and x != 'nan' and not clock_pattern.match(x) else x
                        )
                    
                    # Now convert to float for visualization
                    defects_df["clock_float"] = defects_df["clock"].apply(parse_clock)
                
                # Calculate area if length and width are available
                if 'length [mm]' in defects_df.columns and 'width [mm]' in defects_df.columns:
                    defects_df["area_mm2"] = defects_df["length [mm]"] * defects_df["width [mm]"]
                
                # Convert joint number to Int64 (nullable integer)
                if 'joint number' in defects_df.columns:
                    defects_df["joint number"] = defects_df["joint number"].astype("Int64")
                
                # Store in the datasets dictionary
                datasets[selected_year] = {
                    'joints_df': joints_df,
                    'defects_df': defects_df,
                    'pipe_diameter': pipe_diameter
                }
                
                # Clear the temporary dataframe
                if "temp_df" in datasets and selected_year in datasets["temp_df"]:
                    del datasets["temp_df"][selected_year]
                
                return dbc.Alert([
                    html.I(className="fas fa-check-circle mr-2", style={"margin-right": "8px"}),
                    f"Successfully processed {selected_year} data. ",
                    html.Strong("You can now switch to the Data Analysis tab to explore the data.")
                ], color="success"), {"year": selected_year}, "step completed"
                
            except Exception as e:
                return dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle mr-2", style={"margin-right": "8px"}),
                    f"Error processing data: {str(e)}"
                ], color="danger"), None, "step"
        
        return html.Div(), None, "step"
    
    @app.callback(
        Output("upload-data", "contents"),
        Input("cancel-processing-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def cancel_processing(n_clicks):
        """Cancel the processing and clear the upload"""
        if n_clicks:
            return None
        return no_update