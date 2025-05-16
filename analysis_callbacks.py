from dash import callback, Input, Output, State, ctx, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from analysis_layout import (
    create_analysis_layout,
    create_data_preview_content,
    create_defect_dimensions_content,
    create_visualizations_content,
    create_complete_pipeline_visualization,
    create_joint_visualization_options,
    create_joint_visualization,
    create_comparison_results
)

from multi_year_analysis import compare_defects

def register_analysis_callbacks(app, datasets):
    """Register all callbacks related to data analysis"""
    
    @app.callback(
        Output("analysis-content", "children"),
        Input("processed-data-info", "data"),
        Input("clear-all-datasets-btn", "n_clicks")
    )
    
    def update_analysis_content(processed_data, clear_clicks):
        """Update the analysis content based on processed data"""
        return create_analysis_layout(datasets)

    @app.callback(
        Output("data-preview-content", "children"),
        Input("year-selector-single", "value")
    )
    def update_data_preview(selected_year):
        """Update the data preview content based on selected year"""
        # Convert string to int for dataset lookup
        if selected_year and selected_year.isdigit():
            year_key = selected_year
        else:
            # If not a valid year string, return empty div
            return html.Div()
            
        return create_data_preview_content(year_key, datasets)

    @app.callback(
        Output("defect-dimensions-content", "children"),
        Input("year-selector-single", "value")
    )
    def update_defect_dimensions(selected_year):
        """Update the defect dimensions content based on selected year"""
        # Convert string to int for dataset lookup
        if selected_year and selected_year.isdigit():
            year_key = selected_year
        else:
            # If not a valid year string, return empty div
            return html.Div()
            
        return create_defect_dimensions_content(year_key, datasets)

    @app.callback(
        Output("visualizations-content", "children"),
        Input("year-selector-single", "value")
    )
    def update_visualizations_content(selected_year):
        """Update the visualizations content based on selected year"""
        # Convert string to int for dataset lookup
        if selected_year and selected_year.isdigit():
            year_key = selected_year
        else:
            # If not a valid year string, return empty div
            return html.Div()
            
        return create_visualizations_content(year_key, datasets)

    @app.callback(
        Output("visualization-container", "children"),
        Input("viz-type-single", "value"),
        Input("year-selector-single", "value")
    )
    def update_visualization_container(viz_type, selected_year):
        """Update the visualization container based on selected visualization type"""
        if viz_type == "complete":
            return html.Div([
                dbc.Button(
                    "Show Complete Pipeline Visualization",
                    id="show-pipeline-btn",
                    color="primary",
                    className="mb-3"
                ),
                html.Div(id="complete-pipeline-container")
            ])
        else:
            return create_joint_visualization_options(selected_year, datasets)

    @app.callback(
        Output("complete-pipeline-container", "children"),
        Input("show-pipeline-btn", "n_clicks"),
        State("year-selector-single", "value"),
        prevent_initial_call=True
    )
    def update_complete_pipeline(n_clicks, selected_year):
        """Update the complete pipeline visualization"""
        if n_clicks:
            return create_complete_pipeline_visualization(selected_year, datasets)
        return html.Div()

    @app.callback(
        Output("joint-visualization-container", "children"),
        Input("show-joint-btn", "n_clicks"),
        State("year-selector-single", "value"),
        State("joint-selector-single", "value"),
        prevent_initial_call=True
    )
    def update_joint_visualization(n_clicks, selected_year, selected_joint):
        """Update the joint visualization"""
        if n_clicks and selected_joint is not None:
            return create_joint_visualization(selected_year, selected_joint, datasets)
        return html.Div()


    @app.callback(
        Output("later-year-selector", "options"),
        Input("earlier-year-selector", "value")
    )
    def update_later_year_options(earlier_year):
        """Update the later year options based on the selected earlier year"""
        all_years = sorted([year for year in datasets.keys()])
        later_years = [year for year in all_years if year > earlier_year]
        
        # Updated for newer Dash format - ensure all keys are strings
        options = {str(year): str(year) for year in later_years}
        return options
    
    @app.callback(
        Output("comparison-results-container", "children"),
        Input("compare-defects-btn", "n_clicks"),
        State("earlier-year-selector", "value"),
        State("later-year-selector", "value"),
        State("distance-tolerance-slider", "value"),
        prevent_initial_call=True
    )
    def update_comparison_results(n_clicks, earlier_year, later_year, tolerance):
        """Update the comparison results"""
        if n_clicks:
            # Show loading indicator
            loading_indicator = dbc.Spinner(html.Div("Comparing defects..."), color="primary")
            
            # Convert string years to integers for comparison
            earlier_year_int = int(earlier_year)
            later_year_int = int(later_year)
            
            # Get the datasets
            if earlier_year in datasets and later_year in datasets:
                earlier_defects = datasets[earlier_year]['defects_df']
                later_defects = datasets[later_year]['defects_df']
                
                try:
                    # Perform the comparison
                    comparison_results = compare_defects(
                        earlier_defects, 
                        later_defects,
                        old_year=earlier_year_int,
                        new_year=later_year_int,
                        distance_tolerance=tolerance
                    )
                    
                    # Create the comparison results display
                    return create_comparison_results(comparison_results)
                    
                except Exception as e:
                    return dbc.Alert(
                        f"Error comparing defects: {str(e)}. Make sure both datasets have the required columns and compatible data formats.",
                        color="danger"
                    )
            else:
                return dbc.Alert("Selected years not found in datasets.", color="danger")
        
        return html.Div()