# app.py - Basic Dash app structure
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import re
import numpy as np
from datetime import datetime

# Import functions from modules
from data_processing import process_pipeline_data
from utils import *  # standard_surface_location, parse_clock, etc.
from column_mapping import (
    suggest_column_mapping, 
    apply_column_mapping, 
    get_missing_required_columns, 
    STANDARD_COLUMNS,
    REQUIRED_COLUMNS
)
from multi_year_analysis import (
    compare_defects, 
    create_comparison_stats_plot, 
    create_new_defect_types_plot,
    create_defect_location_plot,
    create_growth_rate_histogram,
    create_negative_growth_plot
)
from defect_analysis import *  # Various analysis functions

# Import our custom modules
from file_handling import parse_uploaded_file, create_file_preview
from file_processing import create_file_processing_layout, register_upload_callbacks
from analysis_layout import create_analysis_layout
from analysis_callbacks import register_analysis_callbacks

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True
)

# For deployment
server = app.server

# Global data store - replaces Streamlit's session state
# Will store datasets as {year: {'joints_df': df1, 'defects_df': df2, 'pipe_diameter': float}}
datasets = {}
current_year = None

# Define app layout
app.layout = html.Div([
    # Store for sidebar collapse state
    dcc.Store(id="sidebar-collapsed", data=False),
    
    # App header
    dbc.Row([
        dbc.Col([
            html.H1([
                html.I(className="fas fa-project-diagram mr-2", style={"margin-right": "10px"}), 
                "Pipeline Inspection Analysis"
            ]),
            html.P("Upload inspection data to analyze pipeline defects and assess fitness for purpose")
        ], width=12, className="mb-4")
    ]),
    
    # Main layout with sidebar and content area
    dbc.Row([
        # Sidebar for file management
        dbc.Col([
            html.Div([
                # Sidebar header with toggle button
                html.Div([
                    html.H3([
                        html.I(className="fas fa-database mr-2", style={"margin-right": "10px"}),
                        html.Span("Data Management", id="sidebar-title")
                    ]),
                    html.I(
                        id="sidebar-toggle",
                        className="fas fa-chevron-left sidebar-toggle",
                        style={"cursor": "pointer"}
                    )
                ], className="sidebar-header d-flex justify-content-between align-items-center mb-3"),
                
                # This will be populated with loaded datasets
                html.Div(id="loaded-datasets-display", className="mb-4"),
                
                # Add new dataset section
                html.Div([
                    html.H4([
                        html.I(className="fas fa-plus-circle mr-2", style={"margin-right": "8px"}),
                        html.Span("Add New Dataset", id="add-dataset-title")
                    ], className="mb-3"),
                    
                    # Year selection dropdown
                    # Year selection dropdown
                    html.Div([
                        html.Label("Select Inspection Year", className="form-label"),
                        dcc.Dropdown(
                            id="year-selector",
                            options={str(year): str(year) 
                                     for year in range(datetime.now().year - 30, datetime.now().year + 1)},
                            value=datetime.now().year,
                            clearable=False
                        )
                    ], className="mb-3", id="year-selector-container"),
                    
                    # File upload component
                    html.Div([
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div([
                                html.I(className="fas fa-file-upload mb-2", style={"font-size": "2rem"}),
                                html.Div('Drag and Drop or'),
                                html.Div([html.A('Select CSV File')])
                            ], className="d-flex flex-column align-items-center justify-content-center"),
                            className="upload-zone",
                            multiple=False
                        )
                    ], id="upload-component"),
                    
                    # Button to clear all datasets
                    html.Div([
                        dbc.Button(
                            [html.I(className="fas fa-trash-alt mr-2", style={"margin-right": "8px"}), "Clear All Datasets"],
                            id="clear-all-datasets-btn",
                            color="danger",
                            className="w-100 mt-3"
                        )
                    ], id="clear-button-container")
                ], id="add-dataset-section"),
                
                # Store file upload info
                dcc.Store(id="upload-info"),
                
                # Store for column mapping
                dcc.Store(id="column-mapping-store"),
                
                # Store for processed data
                dcc.Store(id="processed-data-info")
            ], id="sidebar", className="p-3 bg-light border rounded sidebar")
        ], width=3, id="sidebar-col"),
        
        # Main content area
        dbc.Col([
            # Tabs for file processing and analysis
            dbc.Card([
                dbc.CardHeader(
                    dbc.Tabs(id="main-tabs", active_tab="upload-tab", children=[
                        dbc.Tab(
                            label="File Processing", 
                            tab_id="upload-tab"
                        ),
                        dbc.Tab(
                            label="Data Analysis", 
                            tab_id="analysis-tab"
                        ),
                    ])
                ),
                dbc.CardBody([
                    html.Div(id="tab-content")
                ])
            ])
        ], width=9, id="content-col", className="main-content")
    ])
])

# Callback to update the active tab content
@callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def update_tab_content(active_tab):
    if active_tab == "upload-tab":
        return create_file_processing_layout()
    elif active_tab == "analysis-tab":
        return create_analysis_layout(datasets)
    return html.Div()

# Callback to toggle sidebar collapse
@callback(
    Output("sidebar", "className"),
    Output("sidebar-collapsed", "data"),
    Output("sidebar-toggle", "className"),
    Output("sidebar-title", "style"),
    Output("add-dataset-title", "style"),
    Output("year-selector-container", "style"),
    Output("upload-component", "style"),
    Output("clear-button-container", "style"),
    Output("sidebar-col", "width"),
    Output("content-col", "width"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-collapsed", "data"),
)
def toggle_sidebar(n_clicks, is_collapsed):
    if n_clicks is None:
        n_clicks = 0
        
    if n_clicks == 0:
        # Initial state
        return (
            "p-3 bg-light border rounded sidebar",  # sidebar class
            False,  # is_collapsed
            "fas fa-chevron-left sidebar-toggle",  # toggle icon
            {"display": "inline"},  # sidebar title style
            {"display": "inline"},  # add dataset title style
            {"display": "block"},  # year selector style
            {"display": "block"},  # upload component style
            {"display": "block"},  # clear button style
            3,  # sidebar width
            9   # content width
        )
    
    # Toggle state
    if not is_collapsed:
        # Collapse sidebar
        return (
            "p-3 bg-light border rounded sidebar sidebar-collapsed",
            True,
            "fas fa-chevron-right sidebar-toggle",
            {"display": "none"},
            {"display": "none"},
            {"display": "none"},
            {"display": "none"},
            {"display": "none"},
            1,
            11
        )
    else:
        # Expand sidebar
        return (
            "p-3 bg-light border rounded sidebar",
            False,
            "fas fa-chevron-left sidebar-toggle",
            {"display": "inline"},
            {"display": "inline"},
            {"display": "block"},
            {"display": "block"},
            {"display": "block"},
            3,
            9
        )

# Callback to update available dataset display
@callback(
    Output("loaded-datasets-display", "children"),
    Input("processed-data-info", "data"),
    Input("clear-all-datasets-btn", "n_clicks")
)
def update_loaded_datasets(processed_data, clear_clicks):
    global datasets
    
    # Handle clearing all datasets
    if clear_clicks and ctx.triggered_id == "clear-all-datasets-btn":
        datasets = {}
        return html.Div("No datasets loaded")
    
    # Display loaded datasets
    if datasets:
        dataset_items = []
        for year in sorted(datasets.keys()):
            # Get some basic stats
            n_joints = len(datasets[year]['joints_df']) if 'joints_df' in datasets[year] else 0
            n_defects = len(datasets[year]['defects_df']) if 'defects_df' in datasets[year] else 0
            
            dataset_items.append(
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-calendar-alt mr-2", style={"margin-right": "8px"}),
                            f"{year} Dataset"
                        ], className="card-title"),
                        html.Div([
                            dbc.Badge(f"{n_joints} Joints", color="primary", className="mr-2", style={"margin-right": "8px"}),
                            dbc.Badge(f"{n_defects} Defects", color="info")
                        ])
                    ])
                ], className="mb-2")
            )
        
        return html.Div([
            html.H4([
                html.I(className="fas fa-list mr-2", style={"margin-right": "8px"}),
                "Loaded Datasets"
            ], className="mb-3"),
            html.Div(dataset_items, id="dataset-cards")
        ])
    else:
        return html.Div([
            html.Div(
                dbc.Alert([
                    html.I(className="fas fa-info-circle mr-2", style={"margin-right": "8px"}),
                    "No datasets loaded yet"
                ], color="info"),
                id="no-datasets-message"
            )
        ])

# Register all callbacks
register_upload_callbacks(app, datasets)
register_analysis_callbacks(app, datasets)

# Main app entry point
if __name__ == "__main__":
    app.run(debug=True)