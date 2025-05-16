# analysis_layout.py - Layout components for the analysis tab
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px


def create_analysis_layout(datasets):
    """
    Create the layout for the analysis tab
    
    Parameters:
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with analysis layout
    """
    if not datasets:
        return html.Div([
            dbc.Alert(
                "Please upload and process at least one dataset to enable analysis.",
                color="info"
            )
        ])
    
    # Filter datasets to only include those with required data
    valid_datasets = {}
    for year, data in datasets.items():
        if 'joints_df' in data and 'defects_df' in data:
            valid_datasets[year] = data
    
    if not valid_datasets:
        return html.Div([
            dbc.Alert(
                "No properly processed datasets found. Please upload and process data again.",
                color="warning"
            )
        ])
    
    # Create tab options for single and multi-year analysis
    return html.Div([
        dbc.Tabs([
            dbc.Tab(
                create_single_year_analysis_layout(valid_datasets),
                label="Single Year Analysis",
                tab_id="single-year-tab"
            ),
            dbc.Tab(
                create_multi_year_analysis_layout(valid_datasets),
                label="Multi-Year Comparison",
                tab_id="multi-year-tab",
                disabled=len(valid_datasets) < 2
            )
        ], id="analysis-tabs")
    ])



def create_single_year_analysis_layout(datasets):
    """
    Create the layout for single-year analysis
    
    Parameters:
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with single-year analysis layout
    """
    if not datasets:
        return html.Div()
    
    # Available years for analysis
    years = sorted(datasets.keys())
    
    # Format options for newer Dash versions - ensure all keys are strings
    year_options = {str(year): str(year) for year in years}
    
    return html.Div([
        html.H3("Single Year Analysis", className="mt-3"),
        
        # Year selector
        dbc.Row([
            dbc.Col([
                html.Label("Select Year to Analyze"),
                dcc.Dropdown(
                    id="year-selector-single",
                    options=year_options,
                    value=str(years[-1]),
                    clearable=False
                )
            ], width=6)
        ], className="mb-3"),
        
        # Analysis tabs
        dbc.Tabs([
            dbc.Tab(
                html.Div(id="data-preview-content"),
                label="Data Preview",
                tab_id="data-preview-tab"
            ),
            dbc.Tab(
                html.Div(id="defect-dimensions-content"),
                label="Defect Dimensions",
                tab_id="defect-dimensions-tab"
            ),
            dbc.Tab(
                html.Div(id="visualizations-content"),
                label="Visualizations",
                tab_id="visualizations-tab"
            )
        ], id="single-year-analysis-tabs", active_tab="data-preview-tab")
    ])

def create_data_preview_content(selected_year, datasets):
    """
    Create the content for the data preview tab
    
    Parameters:
    - selected_year: The selected year for analysis
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with data preview content
    """
    if selected_year not in datasets:
        return html.Div()
    
    # Get the selected dataset
    joints_df = datasets[selected_year]['joints_df']
    defects_df = datasets[selected_year]['defects_df']
    
    # Create data preview
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H4(f"{selected_year} Joints (Top 5 Records)"),
                dbc.Table.from_dataframe(
                    joints_df.head(5),
                    striped=True,
                    bordered=True,
                    hover=True,
                    responsive=True
                )
            ], width=6),
            dbc.Col([
                html.H4(f"{selected_year} Defects (Top 5 Records)"),
                dbc.Table.from_dataframe(
                    defects_df.head(5),
                    striped=True,
                    bordered=True,
                    hover=True,
                    responsive=True
                )
            ], width=6)
        ])
    ])


def create_defect_dimensions_content(selected_year, datasets):
    """
    Create the content for the defect dimensions tab
    
    Parameters:
    - selected_year: The selected year for analysis
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with defect dimensions content
    """
    from defect_analysis import create_dimension_statistics_table, create_dimension_distribution_plots, create_combined_dimensions_plot
    
    if selected_year not in datasets:
        return html.Div(dbc.Alert("No dataset available for selected year", color="warning"))
    
    # Check if the dataset has the required keys
    if 'joints_df' not in datasets[selected_year] or 'defects_df' not in datasets[selected_year]:
        return html.Div(dbc.Alert("Dataset is missing required data. Please process the data again.", color="warning"))
    
    # Get the selected dataset
    defects_df = datasets[selected_year]['defects_df']
    
    # Create dimension statistics table
    stats_df = create_dimension_statistics_table(defects_df)
    stats_table = html.Div()
    if not stats_df.empty:
        stats_table = html.Div([
            html.H4("Dimension Statistics"),
            dbc.Table.from_dataframe(
                stats_df,
                striped=True,
                bordered=True,
                hover=True,
                responsive=True
            )
        ])
    else:
        stats_table = dbc.Alert("No dimension data available for analysis.", color="info")
    
    # Create distribution plots
    dimension_figs = create_dimension_distribution_plots(defects_df)
    
    # Prepare graph components
    graph_components = []
    
    if dimension_figs:
        # Create a row for each dimension (up to 3 columns per row)
        row_components = []
        for i, (col_name, fig) in enumerate(dimension_figs.items()):
            if i > 0 and i % 3 == 0:
                # Start a new row after every 3 columns
                graph_components.append(dbc.Row(row_components, className="mb-4"))
                row_components = []
            
            # Add this graph to the current row
            row_components.append(
                dbc.Col(
                    dcc.Graph(figure=fig),
                    width=4
                )
            )
        
        # Add any remaining graphs to a final row
        if row_components:
            graph_components.append(dbc.Row(row_components, className="mb-4"))
        
        # Add combined dimensions plot
        combined_fig = create_combined_dimensions_plot(defects_df)
        graph_components.append(
            html.Div([
                html.H4("Defect Dimensions Relationship"),
                dcc.Graph(figure=combined_fig)
            ])
        )
    else:
        graph_components = [dbc.Alert("No dimension data available for plotting distributions.", color="info")]
    
    # Combine all components
    return html.Div([
        stats_table,
        html.Hr(),
        html.Div(graph_components)
    ])


def create_visualizations_content(selected_year, datasets):
    """
    Create the content for the visualizations tab
    
    Parameters:
    - selected_year: The selected year for analysis
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with visualizations content
    """
    if selected_year not in datasets:
        return html.Div(dbc.Alert("No dataset available for selected year", color="warning"))
    
    # Check if the dataset has the required keys
    if 'joints_df' not in datasets[selected_year] or 'defects_df' not in datasets[selected_year]:
        return html.Div(dbc.Alert("Dataset is missing required data. Please process the data again.", color="warning"))
    
    # Get the selected dataset
    joints_df = datasets[selected_year]['joints_df']
    defects_df = datasets[selected_year]['defects_df']
    
    # Create visualization options
    return html.Div([
        html.H4("Pipeline Visualization"),
        
        # Visualization type selection
        dbc.RadioItems(
            id="viz-type-single",
            options={"complete": "Complete Pipeline", "joint": "Joint-by-Joint"},
            value="complete",
            inline=True,
            className="mb-3"
        ),
        
        # Container for the selected visualization
        html.Div(id="visualization-container")
    ])



def create_multi_year_analysis_layout(datasets):
    """
    Create the layout for multi-year analysis
    
    Parameters:
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with multi-year analysis layout
    """
    if len(datasets) < 2:
        return html.Div([
            dbc.Alert(
                "Please upload at least two datasets from different years to enable comparison.",
                color="warning"
            )
        ])
    
    # Available years for analysis
    years = sorted(datasets.keys())
    
    # Format options for newer Dash versions - ensure all keys are strings
    all_year_options = {str(year): str(year) for year in years}
    earlier_year_options = {str(year): str(year) for year in years[:-1]}
    later_year_options = {str(year): str(year) for year in years[1:]}
    
    # Create layout for comparison
    return html.Div([
        html.H3("Multi-Year Comparison", className="mt-3"),
        
        # Year selectors
        dbc.Row([
            dbc.Col([
                html.Label("Select Earlier Year"),
                dcc.Dropdown(
                    id="earlier-year-selector",
                    options=earlier_year_options,
                    value=str(years[0]),
                    clearable=False
                )
            ], width=6),
            dbc.Col([
                html.Label("Select Later Year"),
                dcc.Dropdown(
                    id="later-year-selector",
                    options=later_year_options,
                    value=str(years[-1]),
                    clearable=False
                )
            ], width=6)
        ], className="mb-3"),
        
        # Distance tolerance
        dbc.Row([
            dbc.Col([
                html.Label("Distance Tolerance (m)"),
                dcc.Slider(
                    id="distance-tolerance-slider",
                    min=0.001,
                    max=0.1,
                    step=0.001,
                    value=0.01,
                    marks={i/100: f"{i/100:.2f}" for i in range(0, 11, 2)},
                ),
                dbc.FormText(
                    "Maximum distance between defects to consider them at the same location"
                )
            ], width=12)
        ], className="mb-3"),
        
        # Compare button
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Compare Defects",
                    id="compare-defects-btn",
                    color="primary"
                )
            ], width=12)
        ], className="mb-3"),
        
        # Comparison results container
        html.Div(id="comparison-results-container")
    ])



def create_complete_pipeline_visualization(selected_year, datasets):
    """
    Create the complete pipeline visualization
    
    Parameters:
    - selected_year: The selected year for analysis
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with pipeline visualization
    """
    from visualizations import create_unwrapped_pipeline_visualization
    
    if selected_year not in datasets:
        return html.Div(dbc.Alert("No dataset available for selected year", color="warning"))
    
    # Check if the dataset has the required keys
    if 'joints_df' not in datasets[selected_year] or 'defects_df' not in datasets[selected_year]:
        return html.Div(dbc.Alert("Dataset is missing required data. Please process the data again.", color="warning"))
    
    # Get the selected dataset
    joints_df = datasets[selected_year]['joints_df']
    defects_df = datasets[selected_year]['defects_df']
    pipe_diameter = datasets[selected_year].get('pipe_diameter', 1.0)
    
    # Check if we have any data
    if joints_df.empty or defects_df.empty:
        return html.Div(dbc.Alert("No data available for visualization", color="warning"))
    
    try:
        # Create visualization
        fig = create_unwrapped_pipeline_visualization(defects_df, joints_df, pipe_diameter)
        
        return html.Div([
            html.H4(f"Pipeline Defect Map ({selected_year})"),
            dcc.Graph(figure=fig)
        ])
    except Exception as e:
        return html.Div(dbc.Alert(f"Error creating visualization: {str(e)}", color="danger"))


def create_joint_visualization_options(selected_year, datasets):
    """
    Create the joint visualization options
    
    Parameters:
    - selected_year: The selected year for analysis
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with joint selection options
    """
    if selected_year not in datasets:
        return html.Div(dbc.Alert("No dataset available for selected year", color="warning"))
    
    # Check if the dataset has the required keys
    if 'joints_df' not in datasets[selected_year]:
        return html.Div(dbc.Alert("Dataset is missing joint data. Please process the data again.", color="warning"))
    
    # Get the selected dataset
    joints_df = datasets[selected_year]['joints_df']
    
    # Check if we have any joints
    if joints_df.empty:
        return html.Div(dbc.Alert("No joint data available for this year", color="warning"))
    
    # Format joint numbers with distance
    available_joints = sorted(joints_df["joint number"].unique())
    if not available_joints:
        return html.Div(dbc.Alert("No joint numbers found in the data", color="warning"))
    
    # Convert joint numbers to strings when using as dictionary keys
    joint_options = {}
    for joint in available_joints:
        joint_row = joints_df[joints_df["joint number"] == joint].iloc[0]
        distance = joint_row["log dist. [m]"]
        # Use string representation of joint as the key
        joint_options[str(joint)] = f"Joint {joint} (at {distance:.1f}m)"
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Select Joint to Visualize"),
                dcc.Dropdown(
                    id="joint-selector-single",
                    options=joint_options,
                    value=str(available_joints[0]) if available_joints else None,
                    clearable=False
                )
            ], width=8),
            dbc.Col([
                html.Label("View Mode"),
                dbc.RadioItems(
                    id="joint-view-mode",
                    options={"2D": "2D Unwrapped"},
                    value="2D",
                    inline=True
                )
            ], width=4)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Show Joint Visualization",
                    id="show-joint-btn",
                    color="primary"
                )
            ], width=12)
        ], className="mb-3"),
        html.Div(id="joint-visualization-container")
    ])


def create_joint_visualization(selected_year, selected_joint, datasets):
    """
    Create the joint visualization
    
    Parameters:
    - selected_year: The selected year for analysis
    - selected_joint: The selected joint for visualization (as string)
    - datasets: Dictionary of loaded datasets
    
    Returns:
    - component: Dash component with joint visualization
    """
    from visualizations import create_joint_defect_visualization
    from defect_analysis import create_joint_summary
    
    if selected_year not in datasets:
        return html.Div(dbc.Alert("No dataset available for selected year", color="warning"))
    
    # Check if the dataset has the required keys
    if 'joints_df' not in datasets[selected_year] or 'defects_df' not in datasets[selected_year]:
        return html.Div(dbc.Alert("Dataset is missing required data. Please process the data again.", color="warning"))
    
    # Get the selected dataset
    joints_df = datasets[selected_year]['joints_df']
    defects_df = datasets[selected_year]['defects_df']
    
    # Convert string joint number back to the original type for data lookup
    try:
        # First try to convert to float
        joint_num_float = float(selected_joint)
        
        # Check if it's really an integer
        if joint_num_float.is_integer():
            joint_num = int(joint_num_float)
        else:
            joint_num = joint_num_float
            
    except ValueError:
        # If conversion fails, keep it as a string
        joint_num = selected_joint
    
    # Check if selected joint exists
    if joint_num not in joints_df["joint number"].values:
        return html.Div(dbc.Alert(f"Joint {joint_num} not found in the data", color="warning"))
    
    # Get joint information
    try:
        joint_row = joints_df[joints_df["joint number"] == joint_num].iloc[0]
        joint_label = f"Joint {joint_num} (at {joint_row['log dist. [m]']:.1f}m)"
    except:
        joint_label = f"Joint {joint_num}"
    
    try:
        # Get joint summary
        joint_summary = create_joint_summary(defects_df, joints_df, joint_num)
        
        # Create summary metrics
        summary_metrics = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Defect Count", className="card-title"),
                        html.H3(joint_summary["defect_count"], className="card-text")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Defect Types", className="card-title"),
                        html.Div([
                            # Format defect types as a string
                            html.H3(
                                len(joint_summary["defect_types"]) if joint_summary["defect_types"] else "None",
                                className="card-text"
                            ),
                            html.Small(
                                ", ".join([f"{count} {type_}" for type_, count in joint_summary["defect_types"].items()]) if joint_summary["defect_types"] else "",
                                className="text-muted"
                            )
                        ])
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Joint Length", className="card-title"),
                        html.H3(
                            f"{joint_summary['joint_length']:.2f}m" if joint_summary["joint_length"] != "N/A" else "N/A",
                            className="card-text"
                        )
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Severity Rank", className="card-title"),
                        html.H3(joint_summary["severity_rank"], className="card-text")
                    ])
                ])
            ], width=3)
        ], className="mb-3")
        
        # Create visualization
        fig = create_joint_defect_visualization(defects_df, joint_num)
        
        return html.Div([
            html.H4(f"Defect Map for {joint_label} ({selected_year})"),
            summary_metrics,
            dcc.Graph(figure=fig)
        ])
    except Exception as e:
        return html.Div(dbc.Alert(f"Error creating joint visualization: {str(e)}", color="danger"))
    

def create_comparison_results(comparison_results):
    """
    Create the comparison results display
    
    Parameters:
    - comparison_results: Results from the comparison function
    
    Returns:
    - component: Dash component with comparison results
    """
    if not comparison_results:
        return html.Div()
    
    # Create summary metrics
    summary_metrics = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Total Defects", className="card-title"),
                    html.H3(comparison_results['total_defects'], className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Common Defects", className="card-title"),
                    html.H3(comparison_results['common_defects_count'], className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("New Defects", className="card-title"),
                    html.H3(comparison_results['new_defects_count'], className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("% New Defects", className="card-title"),
                    html.H3(f"{comparison_results['pct_new']:.1f}%", className="card-text")
                ])
            ])
        ], width=3)
    ], className="mb-3")
    
    # Create visualizations
    from multi_year_analysis import (
        create_comparison_stats_plot, 
        create_new_defect_types_plot,
        create_growth_rate_histogram,
        create_negative_growth_plot
    )
    
    # Create tabs for different visualizations
    viz_tabs = dbc.Tabs([
        dbc.Tab([
            dcc.Graph(figure=create_comparison_stats_plot(comparison_results))
        ], label="New vs Common", tab_id="new-vs-common-tab"),
        dbc.Tab([
            dcc.Graph(figure=create_new_defect_types_plot(comparison_results))
        ], label="New Defect Types", tab_id="new-defect-types-tab"),
        dbc.Tab([
            html.Div([
                # Check if growth rate analysis is available
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Avg Growth Rate", className="card-title"),
                                    html.H3(
                                        f"{comparison_results['growth_stats']['avg_positive_growth_rate_mm']:.3f} mm/yr" if comparison_results.get('has_wt_data', False) else f"{comparison_results['growth_stats']['avg_positive_growth_rate_pct']:.3f} %/yr",
                                        className="card-text"
                                    )
                                ])
                            ])
                        ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Max Growth Rate", className="card-title"),
                                    html.H3(
                                        f"{comparison_results['growth_stats']['max_growth_rate_mm']:.3f} mm/yr" if comparison_results.get('has_wt_data', False) else f"{comparison_results['growth_stats']['max_growth_rate_pct']:.3f} %/yr",
                                        className="card-text"
                                    )
                                ])
                            ])
                        ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Negative Growth Defects", className="card-title"),
                                    html.H3(
                                        f"{comparison_results['growth_stats']['negative_growth_count']} ({comparison_results['growth_stats']['pct_negative_growth']:.1f}%)",
                                        className="card-text"
                                    )
                                ])
                            ])
                        ], width=4)
                    ], className="mb-3"),
                    dcc.Graph(figure=create_growth_rate_histogram(comparison_results))
                ]) if comparison_results.get('has_depth_data', False) and comparison_results.get('calculate_growth', False) else dbc.Alert(
                    "Growth rate analysis not available. Requires depth data in both datasets and valid year values.",
                    color="info"
                )
            ])
        ], label="Growth Rate", tab_id="growth-rate-tab"),
        dbc.Tab([
            html.Div([
                # Check if negative growth analysis is available
                html.Div([
                    dcc.Graph(figure=create_negative_growth_plot(comparison_results)),
                    dbc.Alert(
                        [
                            html.Strong("Negative Growth Explanation:"),
                            html.P([
                                "Defects showing negative growth rates (red triangles) indicate areas where the defect ",
                                "depth appears to have decreased between inspections. This is physically unlikely and ",
                                "usually indicates:"
                            ]),
                            html.Ul([
                                html.Li("Measurement errors in one or both inspections"),
                                html.Li("Different inspection tools or calibration between surveys"),
                                html.Li("Possible repair work that wasn't documented")
                            ]),
                            html.P([
                                "These areas should be flagged for verification and further investigation."
                            ])
                        ],
                        color="info"
                    )
                ]) if comparison_results.get('has_depth_data', False) and comparison_results.get('calculate_growth', False) else dbc.Alert(
                    "Negative growth analysis not available. Requires depth data in both datasets and valid year values.",
                    color="info"
                )
            ])
        ], label="Negative Growth", tab_id="negative-growth-tab")
    ], id="comparison-viz-tabs")
    
    # Create accordion for detailed data
    defect_details = []
    
    if not comparison_results['matches_df'].empty:
        common_defects_table = dash_table.DataTable(
            data=comparison_results['matches_df'].to_dict('records'),
            columns=[{"name": i, "id": i} for i in comparison_results['matches_df'].columns],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={
                'minWidth': '80px', 'width': '120px', 'maxWidth': '200px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
            }
        )
        defect_details.append(
            dbc.AccordionItem(
                [
                    html.Div([
                        html.H5("Common Defects"),
                        common_defects_table
                    ])
                ],
                title="Common Defects"
            )
        )
        
    if not comparison_results['new_defects'].empty:
        new_defects_table = dash_table.DataTable(
            data=comparison_results['new_defects'].to_dict('records'),
            columns=[{"name": i, "id": i} for i in comparison_results['new_defects'].columns],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={
                'minWidth': '80px', 'width': '120px', 'maxWidth': '200px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
            }
        )
        defect_details.append(
            dbc.AccordionItem(
                [
                    html.Div([
                        html.H5("New Defects"),
                        new_defects_table
                    ])
                ],
                title="New Defects"
            )
        )
    
    detailed_lists = html.Div([
        dbc.Accordion(defect_details, start_collapsed=True)
    ]) if defect_details else html.Div()
    
    return html.Div([
        html.H4("Comparison Summary"),
        summary_metrics,
        viz_tabs,
        detailed_lists
    ])