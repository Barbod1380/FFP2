import pandas as pd
import numpy as np

def float_to_clock(time_float):
    if pd.isna(time_float):
        return None  # or return "NaN" or ""

    total_minutes = time_float * 24 * 60
    hours = int(total_minutes // 60)
    minutes = int(round(total_minutes % 60))
    return f"{hours:02d}:{minutes:02d}"


def parse_clock(clock_str):
    """
    Parse clock string format (e.g. "5:30") to decimal hours (e.g. 5.5)
    """
    try:
        hours, minutes = map(int, clock_str.split(":"))
        return hours + minutes / 60
    except Exception:
        return np.nan

def decimal_to_clock_str(decimal_hours):
    """
    Convert decimal hours to clock format string.
    Example: 5.9 → "5:54"
    
    Parameters:
    - decimal_hours: Clock position in decimal format
    
    Returns:
    - String in clock format "H:MM"
    """
    if pd.isna(decimal_hours):
        return "Unknown"
    
    # Ensure the value is between 1 and 12
    if decimal_hours < 1:
        decimal_hours += 12
    elif decimal_hours > 12:
        decimal_hours = decimal_hours % 12
        if decimal_hours == 0:
            decimal_hours = 12
    
    hours = int(decimal_hours)
    minutes = int((decimal_hours - hours) * 60)
    
    return f"{hours}:{minutes:02d}"


def standardize_surface_location(value):
    """
    Standardize different surface location values to INT/NON-INT format.
    
    Parameters:
    - value: The original surface location value
    
    Returns:
    - Standardized value: either "INT" or "NON-INT"
    """
    if pd.isna(value) or value is None:
        return None
    
    # Convert to uppercase string for consistent comparison
    value_str = str(value).strip().upper()
    
    # Map different formats to standard values
    if value_str in ['INT', 'I', 'INTERNAL', 'YES', 'INTERNE']:
        return 'INT'
    elif value_str in ['NON-INT', 'E', 'EXTERNAL', 'NO', 'NON INT', 'EXTERNE']:
        return 'NON-INT'
    else:
        # For unknown values, return as is
        return value