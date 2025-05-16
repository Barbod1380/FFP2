import pandas as pd
import numpy as np

def process_pipeline_data(df):
    """
    Process the pipeline inspection data into two separate tables:
    1. joints_df: Contains unique joint information
    2. defects_df: Contains defect information with joint associations
    
    Parameters:
    - df: DataFrame with the raw pipeline data
    
    Returns:
    - joints_df: DataFrame with joint information
    - defects_df: DataFrame with defect information
    """
    # Make a copy to avoid modifying the original
    df_copy = df.copy()
    
    # 1. Replace empty strings with NaN for proper handling
    df_copy = df_copy.replace(r'^\s*$', np.nan, regex=True)
    
    # 2. Convert numeric columns to appropriate types
    numeric_columns = [
        'joint number', 
        'joint length [m]', 
        'wt nom [mm]', 
        'up weld dist. [m]', 
        'depth [%]', 
        'length [mm]', 
        'width [mm]'
    ]
    
    for col in numeric_columns:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    
    # 4. Sort by log distance to ensure proper order for forward fill
    if 'log dist. [m]' in df_copy.columns:
        df_copy = df_copy.sort_values('log dist. [m]')
    
    # 5. Create joints_df with only the specified columns
    joints_df = df_copy[df_copy['joint number'].notna()][['log dist. [m]', 'joint number', 'joint length [m]', 'wt nom [mm]']].copy()
    
    # 6. Drop duplicate joint numbers if any
    joints_df = joints_df.drop_duplicates(subset=['joint number'])
    joints_df = joints_df.reset_index().drop(columns = ['index'])
    
    # 7. Create defects_df - records with length and width values
    # First, forward fill joint number to associate defects with joints
    df_copy['joint number'] = df_copy['joint number'].fillna(method='ffill')
    
    # Filter for records that have both length and width values
    defects_df = df_copy[
        df_copy['length [mm]'].notna() & 
        df_copy['width [mm]'].notna()
    ].copy()
    
    # Select only the specified columns
    defect_columns = [
        'log dist. [m]',
        'component / anomaly identification',
        'joint number',
        'up weld dist. [m]',
        'clock',
        'depth [%]',
        'length [mm]',
        'width [mm]',
        'surface location'
    ]
    
    # Check which columns exist in the data
    available_columns = [col for col in defect_columns if col in df_copy.columns]
    
    # Select only available columns
    defects_df = defects_df[available_columns]
    defects_df = defects_df.reset_index().drop(columns = ['index'])

    # NEW CODE: Standardize surface location if the column exists
    from utils import standardize_surface_location
    if 'surface location' in defects_df.columns:
        defects_df['surface location'] = defects_df['surface location'].apply(standardize_surface_location)
    
    return joints_df, defects_df