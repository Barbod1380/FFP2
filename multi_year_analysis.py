# multi_year_analysis.py
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def compare_defects(old_defects_df, new_defects_df, old_year=None, new_year=None, distance_tolerance=0.1):
    """
    Compare defects between two inspection years to identify common and new defects.
    
    Parameters:
    - old_defects_df: DataFrame with defects from the earlier inspection
    - new_defects_df: DataFrame with defects from the newer inspection
    - old_year: Year of the earlier inspection (optional, for growth rate calculation)
    - new_year: Year of the later inspection (optional, for growth rate calculation)
    - distance_tolerance: Maximum distance (in meters) to consider defects at the same location
    
    Returns:
    - results: Dictionary with comparison results and statistics
    """
    # Copy inputs
    old_df = old_defects_df.copy()
    new_df = new_defects_df.copy()
    
    # Check if we can calculate growth rates
    calculate_growth = False
    if old_year is not None and new_year is not None and new_year > old_year:
        calculate_growth = True
        year_diff = new_year - old_year
    
    # Check if depth data is available for growth calculations
    has_depth_data = ('depth [%]' in old_df.columns and 'depth [%]' in new_df.columns)
    has_wt_data = ('wt nom [mm]' in old_df.columns and 'wt nom [mm]' in new_df.columns)
    
    # Check columns
    for col in ['log dist. [m]', 'component / anomaly identification']:
        if col not in old_df.columns or col not in new_df.columns:
            raise ValueError(f"Missing column: {col}")
    
    # Assign IDs
    old_df['defect_id'] = range(len(old_df))
    new_df['defect_id'] = range(len(new_df))
    
    matched_old = set()
    matched_new = set()
    matches = []
    
    for _, new_defect in new_df.iterrows():
        # Filter same‐type, within tolerance, not yet matched
        mask = (
            #(old_df['component / anomaly identification']== new_defect['component / anomaly identification']) & 
            (~old_df['defect_id'].isin(matched_old))
            & (old_df['log dist. [m]']
               .sub(new_defect['log dist. [m]'])
               .abs() <= distance_tolerance)
        )
        potential_matches = old_df[mask]
        
        if not potential_matches.empty:
            # Find the index label of the minimal distance
            dists = (potential_matches['log dist. [m]']
                     - new_defect['log dist. [m]']).abs()
            best_idx = dists.idxmin()
            closest_match = potential_matches.loc[best_idx]
            
            # Basic match data
            match_data = {
                'new_defect_id': new_defect['defect_id'],
                'old_defect_id': closest_match['defect_id'],
                'distance_diff': dists.loc[best_idx],
                'log_dist': new_defect['log dist. [m]'],
                'old_log_dist': closest_match['log dist. [m]'],
                'defect_type': new_defect['component / anomaly identification']
            }
            
            # Add growth data if available
            if calculate_growth and has_depth_data:
                old_depth = closest_match['depth [%]']
                new_depth = new_defect['depth [%]']
                
                # Add depth information
                match_data.update({
                    'old_depth_pct': old_depth,
                    'new_depth_pct': new_depth,
                    'depth_change_pct': new_depth - old_depth,
                    'growth_rate_pct_per_year': (new_depth - old_depth) / year_diff,
                    'is_negative_growth': (new_depth - old_depth) < 0
                })
                
                # If wall thickness data is available, convert to mm/year
                if has_wt_data:
                    old_wt = closest_match['wt nom [mm]']
                    new_wt = new_defect['wt nom [mm]']
                    
                    # Use the average wall thickness for conversion
                    avg_wt = (old_wt + new_wt) / 2
                    
                    old_depth_mm = old_depth * avg_wt / 100
                    new_depth_mm = new_depth * avg_wt / 100
                    
                    match_data.update({
                        'old_depth_mm': old_depth_mm,
                        'new_depth_mm': new_depth_mm,
                        'depth_change_mm': new_depth_mm - old_depth_mm,
                        'growth_rate_mm_per_year': (new_depth_mm - old_depth_mm) / year_diff
                    })
            
            matches.append(match_data)
            matched_old.add(closest_match['defect_id'])
            matched_new.add(new_defect['defect_id'])
    
    # Column list for empty dataframe handling
    columns = ['new_defect_id', 'old_defect_id', 'distance_diff', 
               'log_dist', 'old_log_dist', 'defect_type']
               
    if calculate_growth and has_depth_data:
        columns.extend(['old_depth_pct', 'new_depth_pct', 'depth_change_pct', 
                       'growth_rate_pct_per_year', 'is_negative_growth'])
        if has_wt_data:
            columns.extend(['old_depth_mm', 'new_depth_mm', 'depth_change_mm', 
                           'growth_rate_mm_per_year'])
    
    # Build results
    matches_df = pd.DataFrame(matches, columns=columns) if matches else pd.DataFrame(columns=columns)
    new_defects = new_df.loc[~new_df['defect_id'].isin(matched_new)].copy()
    
    total = len(new_df)
    common = len(matches_df)
    new_cnt = len(new_defects)
    
    # Stats
    pct_common = common/total*100 if total else 0
    pct_new = new_cnt/total*100 if total else 0
    
    # Distribution of "truly new" types
    if new_cnt:
        dist = (new_defects['component / anomaly identification']
                .value_counts()
                .rename_axis('defect_type')
                .reset_index(name='count'))
        dist['percentage'] = dist['count']/new_cnt*100
    else:
        dist = pd.DataFrame(columns=['defect_type', 'count', 'percentage'])
    
    # Calculate growth statistics if depth data is available
    growth_stats = None
    if calculate_growth and has_depth_data and not matches_df.empty:
        # Growth statistics
        negative_growth_count = matches_df['is_negative_growth'].sum()
        pct_negative_growth = (negative_growth_count / len(matches_df)) * 100 if len(matches_df) > 0 else 0
        
        # Filter out negative growth for positive growth stats
        positive_growth = matches_df[~matches_df['is_negative_growth']]
        
        growth_stats = {
            'total_matched_defects': len(matches_df),
            'negative_growth_count': negative_growth_count,
            'pct_negative_growth': pct_negative_growth,
            'avg_growth_rate_pct': matches_df['growth_rate_pct_per_year'].mean(),
            'avg_positive_growth_rate_pct': positive_growth['growth_rate_pct_per_year'].mean() if len(positive_growth) > 0 else 0,
            'max_growth_rate_pct': positive_growth['growth_rate_pct_per_year'].max() if len(positive_growth) > 0 else 0
        }
        
        # Add mm-based stats if available
        if has_wt_data:
            growth_stats.update({
                'avg_growth_rate_mm': matches_df['growth_rate_mm_per_year'].mean(),
                'avg_positive_growth_rate_mm': positive_growth['growth_rate_mm_per_year'].mean() if len(positive_growth) > 0 else 0,
                'max_growth_rate_mm': positive_growth['growth_rate_mm_per_year'].max() if len(positive_growth) > 0 else 0
            })
    
    return {
        'matches_df': matches_df,
        'new_defects': new_defects,
        'common_defects_count': common,
        'new_defects_count': new_cnt,
        'total_defects': total,
        'pct_common': pct_common,
        'pct_new': pct_new,
        'defect_type_distribution': dist,
        'growth_stats': growth_stats,
        'has_depth_data': has_depth_data,
        'has_wt_data': has_wt_data,
        'calculate_growth': calculate_growth
    }

def create_comparison_stats_plot(comparison_results):
    """
    Create a pie chart showing new vs. common defects
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    
    Returns:
    - Plotly figure object
    """
    labels = ['Common Defects', 'New Defects']
    values = [
        comparison_results['common_defects_count'],
        comparison_results['new_defects_count']
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=['#2E86C1', '#EC7063'])
    )])
    
    fig.update_layout(
        title='Distribution of Common vs. New Defects',
        font=dict(size=14),
        height=400
    )
    
    return fig

def create_new_defect_types_plot(comparison_results):
    """
    Create a bar chart showing distribution of new defect types
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    
    Returns:
    - Plotly figure object
    """
    type_dist = comparison_results['defect_type_distribution']
    
    if type_dist.empty:
        # Create an empty figure with a message if there are no new defects
        fig = go.Figure()
        fig.add_annotation(
            text="No new defects found",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    # Sort by count descending
    type_dist = type_dist.sort_values('count', ascending=False)
    
    fig = go.Figure(data=[
        go.Bar(
            x=type_dist['defect_type'],
            y=type_dist['count'],
            text=type_dist['percentage'].apply(lambda x: f"{x:.1f}%"),
            textposition='auto',
            marker_color='#EC7063'
        )
    ])
    
    fig.update_layout(
        title='Distribution of New Defect Types',
        xaxis_title='Defect Type',
        yaxis_title='Count',
        font=dict(size=14),
        height=500,
        xaxis=dict(tickangle=-45)  # Rotate x labels for better readability
    )
    
    return fig

def create_defect_location_plot(comparison_results, old_defects_df, new_defects_df):
    """
    Create a scatter plot showing the location of defects along the pipeline
    Highlighting common and new defects
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    - old_defects_df: DataFrame with defects from the earlier inspection
    - new_defects_df: DataFrame with defects from the newer inspection
    
    Returns:
    - Plotly figure object
    """
    # Get matched and new defect IDs
    matched_new_ids = set(comparison_results['matches_df']['new_defect_id']) if not comparison_results['matches_df'].empty else set()
    
    # Prepare data for plotting
    common_defects = new_defects_df[new_defects_df['defect_id'].isin(matched_new_ids)].copy()
    new_defects = comparison_results['new_defects']
    
    # Create plot
    fig = go.Figure()
    
    # Add common defects
    if not common_defects.empty:
        fig.add_trace(go.Scatter(
            x=common_defects['log dist. [m]'],
            y=common_defects['clock_float'] if 'clock_float' in common_defects.columns else [1] * len(common_defects),
            mode='markers',
            name='Common Defects',
            marker=dict(
                color='#2E86C1',
                size=10,
                opacity=0.7
            ),
            hovertemplate=(
                "<b>Common Defect</b><br>"
                "Distance: %{x:.2f} m<br>"
                "Type: %{customdata[0]}<br>"
                "Depth: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=np.column_stack((
                common_defects['component / anomaly identification'],
                common_defects['depth [%]'].fillna(0)
            ))
        ))
    
    # Add new defects
    if not new_defects.empty:
        fig.add_trace(go.Scatter(
            x=new_defects['log dist. [m]'],
            y=new_defects['clock_float'] if 'clock_float' in new_defects.columns else [1] * len(new_defects),
            mode='markers',
            name='New Defects',
            marker=dict(
                color='#EC7063',
                size=10,
                opacity=0.7
            ),
            hovertemplate=(
                "<b>New Defect</b><br>"
                "Distance: %{x:.2f} m<br>"
                "Type: %{customdata[0]}<br>"
                "Depth: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=np.column_stack((
                new_defects['component / anomaly identification'],
                new_defects['depth [%]'].fillna(0)
            ))
        ))
    
    # Update layout
    fig.update_layout(
        title='Location of Common and New Defects Along Pipeline',
        xaxis_title='Distance Along Pipeline (m)',
        yaxis_title='Clock Position' if 'clock_float' in new_defects_df.columns else 'Position',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        hovermode='closest',
        height=500
    )
    
    return fig

def create_growth_rate_histogram(comparison_results):
    """
    Create a histogram showing the distribution of positive corrosion growth rates
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    
    Returns:
    - Plotly figure object
    """
    if (not comparison_results.get('has_depth_data', False) or 
        comparison_results['matches_df'].empty or
        not comparison_results.get('calculate_growth', False)):
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
    
    # Filter for positive growth only
    positive_growth = matches_df[~matches_df['is_negative_growth']]
    
    if positive_growth.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No positive growth data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    # Use mm data if available, otherwise use percentage
    if comparison_results.get('has_wt_data', False):
        growth_col = 'growth_rate_mm_per_year'
        x_title = 'Growth Rate (mm/year)'
    else:
        growth_col = 'growth_rate_pct_per_year'
        x_title = 'Growth Rate (% points/year)'
    
    # Create histogram
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=positive_growth[growth_col],
        nbinsx=20,
        marker=dict(
            color='rgba(255, 100, 102, 0.7)',
            line=dict(color='rgba(255, 100, 102, 1)', width=1)
        ),
        name='Positive Growth Rates'
    ))
    
    # Add vertical line at average growth rate
    mean_growth = positive_growth[growth_col].mean()
    
    fig.add_shape(
        type="line",
        x0=mean_growth, x1=mean_growth,
        y0=0, y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash"),
    )
    
    fig.add_annotation(
        x=mean_growth,
        y=1,
        yref="paper",
        text=f"Mean: {mean_growth:.3f}",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-30
    )
    
    # Layout
    fig.update_layout(
        title='Distribution of Positive Defect Growth Rates',
        xaxis_title=x_title,
        yaxis_title='Count',
        bargap=0.1,
        bargroupgap=0.1,
        height=500
    )
    
    return fig

def create_negative_growth_plot(comparison_results):
    """
    Create a scatter plot highlighting negative growth defects
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    
    Returns:
    - Plotly figure object
    """
    if (not comparison_results.get('has_depth_data', False) or 
        comparison_results['matches_df'].empty or
        not comparison_results.get('calculate_growth', False)):
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
    if comparison_results.get('has_wt_data', False):
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
                f"<b>Old Depth:</b> %{{customdata[0]:.2f}}{' mm' if comparison_results.get('has_wt_data', False) else '%'}<br>"
                f"<b>New Depth:</b> %{{customdata[1]:.2f}}{' mm' if comparison_results.get('has_wt_data', False) else '%'}<br>"
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
            f"<b>Old Depth:</b> %{{customdata[0]:.2f}}{' mm' if comparison_results.get('has_wt_data', False) else '%'}<br>"
            f"<b>New Depth:</b> %{{customdata[1]:.2f}}{' mm' if comparison_results.get('has_wt_data', False) else '%'}<br>"
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

def create_growth_summary_table(comparison_results):
    """
    Create a summary table of growth statistics
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    
    Returns:
    - Pandas DataFrame with growth statistics
    """
    if (not comparison_results.get('has_depth_data', False) or 
        comparison_results['matches_df'].empty or
        not comparison_results.get('calculate_growth', False) or
        comparison_results.get('growth_stats') is None):
        return pd.DataFrame()
    
    growth_stats = comparison_results['growth_stats']
    has_wt_data = comparison_results.get('has_wt_data', False)
    
    # Create table rows
    rows = []
    
    # Total matched defects
    rows.append({
        'Statistic': 'Total Matched Defects',
        'Value': growth_stats['total_matched_defects']
    })
    
    # Negative growth anomalies
    rows.append({
        'Statistic': 'Negative Growth Anomalies',
        'Value': f"{growth_stats['negative_growth_count']} ({growth_stats['pct_negative_growth']:.1f}%)"
    })
    
    # Average growth rate
    if has_wt_data:
        rows.append({
            'Statistic': 'Average Growth Rate (All)',
            'Value': f"{growth_stats['avg_growth_rate_mm']:.3f} mm/year"
        })
        rows.append({
            'Statistic': 'Average Positive Growth Rate',
            'Value': f"{growth_stats['avg_positive_growth_rate_mm']:.3f} mm/year"
        })
        rows.append({
            'Statistic': 'Maximum Growth Rate',
            'Value': f"{growth_stats['max_growth_rate_mm']:.3f} mm/year"
        })
    else:
        rows.append({
            'Statistic': 'Average Growth Rate (All)',
            'Value': f"{growth_stats['avg_growth_rate_pct']:.3f} %/year"
        })
        rows.append({
            'Statistic': 'Average Positive Growth Rate',
            'Value': f"{growth_stats['avg_positive_growth_rate_pct']:.3f} %/year"
        })
        rows.append({
            'Statistic': 'Maximum Growth Rate',
            'Value': f"{growth_stats['max_growth_rate_pct']:.3f} %/year"
        })
    
    return pd.DataFrame(rows)

def create_highest_growth_table(comparison_results, top_n=10):
    """
    Create a table showing the defects with the highest growth rates
    
    Parameters:
    - comparison_results: Results dictionary from compare_defects function
    - top_n: Number of top defects to include
    
    Returns:
    - Pandas DataFrame with top growing defects
    """
    if (not comparison_results.get('has_depth_data', False) or 
        comparison_results['matches_df'].empty or
        not comparison_results.get('calculate_growth', False)):
        return pd.DataFrame()
    
    matches_df = comparison_results['matches_df']
    has_wt_data = comparison_results.get('has_wt_data', False)
    
    # Filter out negative growth
    positive_growth = matches_df[~matches_df['is_negative_growth']]
    
    if positive_growth.empty:
        return pd.DataFrame()
    
    # Sort by growth rate
    if has_wt_data:
        sorted_df = positive_growth.sort_values('growth_rate_mm_per_year', ascending=False)
        growth_col = 'growth_rate_mm_per_year'
        unit = 'mm/year'
    else:
        sorted_df = positive_growth.sort_values('growth_rate_pct_per_year', ascending=False)
        growth_col = 'growth_rate_pct_per_year'
        unit = '%/year'
    
    # Take top N
    top_defects = sorted_df.head(top_n)
    
    # Select columns for display
    display_cols = ['log_dist', 'defect_type']
    
    if has_wt_data:
        depth_cols = ['old_depth_mm', 'new_depth_mm']
    else:
        depth_cols = ['old_depth_pct', 'new_depth_pct']
    
    display_cols.extend(depth_cols)
    display_cols.append(growth_col)
    
    # Create display dataframe
    display_df = top_defects[display_cols].copy()
    
    # Rename columns for clarity
    column_map = {
        'log_dist': 'Location (m)',
        'defect_type': 'Defect Type',
        'old_depth_pct': 'Old Depth (%)',
        'new_depth_pct': 'New Depth (%)',
        'old_depth_mm': 'Old Depth (mm)',
        'new_depth_mm': 'New Depth (mm)',
        'growth_rate_pct_per_year': f'Growth Rate ({unit})',
        'growth_rate_mm_per_year': f'Growth Rate ({unit})'
    }
    display_df = display_df.rename(columns=column_map)
    
    # Format numeric columns
    for col in display_df.columns:
        if 'Depth' in col or 'Growth' in col or 'Location' in col:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}")
    
    # Reset index for display
    display_df = display_df.reset_index(drop=True)
    
    return display_df

def create_matching_debug_view(old_defects_df, new_defects_df, distance_tolerance=0.1):
    """
    Create a diagnostic view to debug defect matching issues
    
    Parameters:
    - old_defects_df: DataFrame with defects from the earlier inspection
    - new_defects_df: DataFrame with defects from the newer inspection
    - distance_tolerance: Maximum distance used for matching
    
    Returns:
    - Pandas DataFrame with matching diagnostics
    """
    # Common columns to compare
    columns = ['log dist. [m]', 'component / anomaly identification']
    extra_cols = ['depth [%]', 'clock', 'length [mm]', 'width [mm]'] 
    
    # Add any extra columns that are available in both datasets
    for col in extra_cols:
        if col in old_defects_df.columns and col in new_defects_df.columns:
            columns.append(col)
    
    # Create a merged view of close defects
    merged_view = []
    
    # Loop through each defect in the new dataset
    for _, new_defect in new_defects_df.iterrows():
        # Find old defects of the same type within tolerance
        nearby_old = old_defects_df[
            #(old_defects_df['component / anomaly identification'] == new_defect['component / anomaly identification']) &
            (abs(old_defects_df['log dist. [m]'] - new_defect['log dist. [m]']) <= distance_tolerance * 2)  # Using 2x tolerance for this view
        ]
        
        if not nearby_old.empty:
            for _, old_defect in nearby_old.iterrows():
                row = {
                    'new_dist': new_defect['log dist. [m]'],
                    'old_dist': old_defect['log dist. [m]'],
                    'distance_diff': abs(new_defect['log dist. [m]'] - old_defect['log dist. [m]']),
                    'defect_type': new_defect['component / anomaly identification'],
                    'would_match': abs(new_defect['log dist. [m]'] - old_defect['log dist. [m]']) <= distance_tolerance
                }
                
                # Add additional columns
                for col in columns:
                    if col not in ['log dist. [m]', 'component / anomaly identification']:
                        if col in new_defect and col in old_defect:
                            row[f'new_{col}'] = new_defect[col]
                            row[f'old_{col}'] = old_defect[col]
                
                merged_view.append(row)
    
    return pd.DataFrame(merged_view)