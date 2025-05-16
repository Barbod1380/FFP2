import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import decimal_to_clock_str


def create_unwrapped_pipeline_visualization(defects_df, joints_df, pipe_diameter=1.0):
    """
    Create an enhanced unwrapped cylinder visualization of pipeline defects,
    optimized for performance with large datasets.
    """
    # Performance optimization - use Scattergl instead of Scatter for large datasets
    use_webgl = defects_df.shape[0] > 1000
    scatter_type = go.Scattergl if use_webgl else go.Scatter
    
    # Simplify customdata to reduce memory usage
    if 'component / anomaly identification' in defects_df.columns:
        # Simplified custom data with just the essentials
        custom_data = np.stack([
            defects_df["joint number"].astype(str),
            defects_df["component / anomaly identification"],
            defects_df["depth [%]"].fillna(0),
        ], axis=-1)
    else:
        custom_data = np.stack([
            defects_df["joint number"].astype(str),
            defects_df["depth [%]"].fillna(0),
        ], axis=-1)
    
    # Create figure with a single trace using depth for color
    fig = go.Figure()
    
    # Simplified hover template
    hover_template = (
        "<b>Distance:</b> %{x:.2f} m<br>"
        "<b>Depth:</b> %{customdata[2]:.1f}%<br>"
        "<b>Joint:</b> %{customdata[0]}<extra></extra>"
    )
    
    # Create a single trace for all defects, colored by depth
    if "depth [%]" in defects_df.columns:
        fig.add_trace(scatter_type(
            x=defects_df["log dist. [m]"],
            y=defects_df["clock_float"],
            mode="markers",
            marker=dict(
                size=5,  # Smaller markers for better performance
                color=defects_df["depth [%]"],
                colorscale="Turbo",
                cmin=0,
                cmax=defects_df["depth [%]"].max(),
                colorbar=dict(
                    title="Depth (%)",
                    thickness=15,
                    len=0.6,
                ),
                opacity=0.7,  # Slight transparency for better visibility when overlapping
            ),
            customdata=custom_data,
            hovertemplate=hover_template,
            name="Defects"
        ))
    else:
        # Fallback if no depth data
        fig.add_trace(scatter_type(
            x=defects_df["log dist. [m]"],
            y=defects_df["clock_float"],
            mode="markers",
            marker=dict(
                size=5,
                color="blue",
                opacity=0.7,
            ),
            customdata=custom_data,
            hovertemplate=hover_template,
            name="Defects"
        ))
    
    # Simplified joint markers - just add vertical lines instead of annotations
    for _, row in joints_df.iterrows():
        x0 = row["log dist. [m]"]
        joint_num = row["joint number"]
    
    # Add a simplified clock position grid (fewer lines)
    for hour in [3, 6, 9, 12]:
        fig.add_shape(
            type="line",
            x0=defects_df["log dist. [m]"].min() - 1,
            x1=defects_df["log dist. [m]"].max() + 1,
            y0=hour,
            y1=hour,
            line=dict(color="lightgray", width=1, dash="dot"),
            layer="below"
        )
    
    # Simplified layout
    fig.update_layout(
        title="Pipeline Defect Map",
        xaxis=dict(
            title="Distance Along Pipeline (m)",
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.2)",
        ),
        yaxis=dict(
            title="Clock Position (hr)",
            tickmode="array",
            tickvals=[3, 6, 9, 12],
            ticktext=["3:00", "6:00", "9:00", "12:00"],
            range=[0.5, 12.5],
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.2)",
        ),
        height=600,
        plot_bgcolor="white",
        hovermode="closest",
    )
    
    # Static color key instead of interactive buttons
    fig.add_annotation(
        text="Color indicates defect depth (%)",
        x=0.01,
        y=-0.1,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="left"
    )
    
    # Remove buttons and interactive elements
    fig.update_layout(
        updatemenus=[],  # No updatemenus
        sliders=[]      # No sliders
    )
    
    return fig


def create_joint_defect_visualization(defects_df, joint_number):
    """
    Create a visualization of defects for a specific joint, representing defects
    as rectangles whose fill color maps to depth (%) between the joint's min & max,
    plus an interactive hover and a matching colorbar.
    """
    # 1) Filter
    joint_defects = defects_df[defects_df['joint number'] == joint_number].copy()
    if joint_defects.empty:
        return go.Figure().update_layout(
            title=f"No defects found for Joint {joint_number}",
            xaxis_title="Distance (m)",
            yaxis_title="Clock Position",
            plot_bgcolor="white"
        )
    
    # 2) Depth range for this joint
    depths = joint_defects['depth [%]'].astype(float)
    min_depth, max_depth = depths.min(), depths.max()
    
    # Ensure we have a valid range (avoid division by zero)
    if min_depth == max_depth:
        min_depth = max(0, min_depth - 1)
        max_depth = max_depth + 1

    # 3) Geometry constants
    min_dist = joint_defects['log dist. [m]'].min()
    max_dist = joint_defects['log dist. [m]'].max()
    pipe_diameter = 1.0  # m
    meters_per_clock_unit = np.pi * pipe_diameter / 12

    fig = go.Figure()
    colorscale_name = "YlOrRd"

    # 4) Draw each defect
    for _, defect in joint_defects.iterrows():
        x_center = defect['log dist. [m]']
        clock_pos = defect['clock_float']
        length_m = defect['length [mm]'] / 1000
        width_m = defect['width [mm]'] / 1000
        depth_pct = float(defect['depth [%]'])

        # rectangle corners
        w_clock = width_m / meters_per_clock_unit
        x0, x1 = x_center - length_m/2, x_center + length_m/2
        y0, y1 = clock_pos - w_clock/2, clock_pos + w_clock/2

        # Calculate normalized depth (0-1) for color mapping
        norm_depth = (depth_pct - min_depth) / (max_depth - min_depth)
        
        # Get color from colorscale using plotly's helper
        color = px.colors.sample_colorscale(colorscale_name, [norm_depth])[0]

        # Create custom data for hover info
        custom_data = [
            defect['clock'],
            depth_pct,
            defect['length [mm]'],
            defect['width [mm]'],
            defect.get('component / anomaly identification', 'Unknown')
        ]
        
        # Add rectangle for each defect with proper hover template
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            mode='lines',
            fill='toself',
            fillcolor=color,  # Apply the color from the colorscale
            line=dict(color='black', width=1),
            hoveron='fills+points',
            hoverinfo='text',
            customdata=[custom_data] * 5,  # Same data for all 5 points
            hovertemplate="<b>Defect Information</b><br>" +
                          "Distance: %{x:.3f} m<br>" +
                          "Clock: %{customdata[0]}<br>" +
                          "Depth: %{customdata[1]:.1f}%<br>" +
                          "Length: %{customdata[2]:.1f} mm<br>" +
                          "Width: %{customdata[3]:.1f} mm<br>" +
                          "Type: %{customdata[4]}<extra></extra>",
            showlegend=False
        ))

    # 5) Invisible scatter for shared colorbar
    fig.add_trace(go.Scatter(
        x=[None]*len(depths),
        y=[None]*len(depths),
        mode='markers',
        marker=dict(
            color=depths,
            colorscale=colorscale_name,
            cmin=min_depth,
            cmax=max_depth,
            showscale=True,
            colorbar=dict(
                title="Depth (%)",
                thickness=15,
                len=0.5,
                tickformat=".1f"
            ),
            opacity=0
        ),
        showlegend=False
    ))

    # 6) Clock‐hour grid lines
    for hr in range(1,13):
        fig.add_shape(
            type="line",
            x0=min_dist - 0.2, x1=max_dist + 0.2,
            y0=hr, y1=hr,
            line=dict(color="lightgray", dash="dot", width=1),
            layer="below"
        )

    # 7) Layout
    fig.update_layout(
        title=f"Defect Map for Joint {joint_number}",
        xaxis_title="Distance Along Pipeline (m)",
        yaxis_title="Clock Position (hr)",
        plot_bgcolor="white",
        xaxis=dict(
            range=[min_dist - 0.2, max_dist + 0.2],
            showgrid=True, gridcolor="rgba(200,200,200,0.2)"
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(1,13)),
            ticktext=[f"{h}:00" for h in range(1,13)],
            range=[0.5,12.5],
            showgrid=True, gridcolor="rgba(200,200,200,0.2)"
        ),
        height=600, width=1200,
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(l=50, r=50, t=80, b=50)
    )

    return fig


def create_negative_growth_plot(comparison_results):
    """
    Create a scatter plot highlighting negative growth defects
    """
    if (not comparison_results['has_depth_data'] or 
        comparison_results['matches_df'].empty):
        fig = go.Figure()
        fig.add_annotation(
            text="No growth rate data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    # Get the matches dataframe
    matches_df = comparison_results['matches_df']
    
    # Split into negative and positive growth
    negative_growth = matches_df[matches_df['is_negative_growth']]
    positive_growth = matches_df[~matches_df['is_negative_growth']]
    
    if negative_growth.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No negative growth anomalies detected",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    # Use mm data if available, otherwise use percentage
    if comparison_results['has_wt_data']:
        old_depth_col = 'old_depth_mm'
        new_depth_col = 'new_depth_mm'
        growth_col = 'growth_rate_mm_per_year'
        y_title = 'Growth Rate (mm/year)'
    else:
        old_depth_col = 'old_depth_pct'
        new_depth_col = 'new_depth_pct'
        growth_col = 'growth_rate_pct_per_year'
        y_title = 'Growth Rate (% points/year)'
    
    # Create scatter plot
    fig = go.Figure()
    
    # Add positive growth defects
    if not positive_growth.empty:
        fig.add_trace(go.Scatter(
            x=positive_growth['log_dist'],
            y=positive_growth[growth_col],
            mode='markers',
            marker=dict(
                size=10,
                color='blue',
                opacity=0.5
            ),
            name='Positive Growth',
            hovertemplate=(
                "<b>Location:</b> %{x:.2f}m<br>"
                f"<b>Growth Rate:</b> %{{y:.3f}}{y_title.split(' ')[1]}<br>"
                f"<b>Old Depth:</b> %{{customdata[0]:.2f}}{' mm' if comparison_results['has_wt_data'] else '%'}<br>"
                f"<b>New Depth:</b> %{{customdata[1]:.2f}}{' mm' if comparison_results['has_wt_data'] else '%'}<br>"
                "<b>Type:</b> %{customdata[2]}"
                "<extra></extra>"
            ),
            customdata=np.column_stack((
                positive_growth[old_depth_col],
                positive_growth[new_depth_col],
                positive_growth['defect_type']
            ))
        ))
    
    # Add negative growth defects
    fig.add_trace(go.Scatter(
        x=negative_growth['log_dist'],
        y=negative_growth[growth_col],
        mode='markers',
        marker=dict(
            size=12,
            color='red',
            opacity=0.7,
            symbol='triangle-down',
            line=dict(width=1, color='black')
        ),
        name='Negative Growth (Anomaly)',
        hovertemplate=(
            "<b>Location:</b> %{x:.2f}m<br>"
            f"<b>Growth Rate:</b> %{{y:.3f}}{y_title.split(' ')[1]}<br>"
            f"<b>Old Depth:</b> %{{customdata[0]:.2f}}{' mm' if comparison_results['has_wt_data'] else '%'}<br>"
            f"<b>New Depth:</b> %{{customdata[1]:.2f}}{' mm' if comparison_results['has_wt_data'] else '%'}<br>"
            "<b>Type:</b> %{customdata[2]}"
            "<extra></extra>"
        ),
        customdata=np.column_stack((
            negative_growth[old_depth_col],
            negative_growth[new_depth_col],
            negative_growth['defect_type']
        ))
    ))
    
    # Add zero line
    fig.add_shape(
        type="line",
        x0=min(matches_df['log_dist']),
        x1=max(matches_df['log_dist']),
        y0=0, y1=0,
        line=dict(color="black", width=1, dash="dash"),
    )
    
    # Layout
    fig.update_layout(
        title='Defect Growth Rate vs Location (Highlighting Negative Growth)',
        xaxis_title='Distance Along Pipeline (m)',
        yaxis_title=y_title,
        height=500,
        hovermode='closest',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )
    
    return fig