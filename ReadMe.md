# Pipeline Inspection Multi-Year Analysis

This Dash-Plotly application provides tools for analyzing pipeline inspection data, particularly for fitness-for-service assessments by analyzing pipeline defects over time.

## Features

- **CSV File Upload**: Upload inspection data from multiple years with robust column mapping
- **Single Year Analysis**: Analyze defects from a specific inspection
  - Data preview
  - Defect dimension statistics and visualizations
  - Pipeline visualizations (complete pipeline and joint-by-joint)
- **Multi-Year Comparison**: Compare defects between two inspection years
  - Identify new vs. common defects
  - Analyze defect growth rates
  - Identify anomalies like negative growth

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Directory Structure

```
pipeline-analysis/
├── app.py                   # Main application file
├── analysis_callbacks.py    # Callbacks for analysis functionality
├── analysis_layout.py       # Layout components for analysis
├── column_mapping.py        # Column mapping functionality
├── column_mapping_ui.py     # UI for column mapping
├── data_processing.py       # Data processing functions
├── defect_analysis.py       # Defect analysis functions
├── file_handling.py         # File upload and handling
├── file_processing.py       # File processing functionality
├── multi_year_analysis.py   # Multi-year comparison functions
├── utils.py                 # Utility functions
├── visualizations.py        # Visualization functions
├── assets/                  # CSS and other static files
│   └── custom.css           # Custom styling
└── requirements.txt         # Python dependencies
```

## Usage

1. Run the application:

```bash
python app.py
```

2. Open your web browser and navigate to http://127.0.0.1:8050/

3. Use the sidebar to upload CSV files with pipeline inspection data

4. Map columns in your CSV to the standard column format

5. Process the data and switch to the Analysis tab for visualizations and insights

## Data Format

The application works with CSV files containing pipeline inspection data. Required columns include:

- `log dist. [m]`: Distance along the pipeline
- `joint number`: Joint identifier
- `joint length [m]`: Length of joint
- `wt nom [mm]`: Nominal wall thickness
- `component / anomaly identification`: Defect type
- `depth [%]`: Defect depth as percentage of wall thickness
- `length [mm]`: Defect length
- `width [mm]`: Defect width
- `clock`: Clock position (HH:MM format)

## License

[MIT License](LICENSE)