# Crime Statistics Dashboard

An interactive GIS-style dashboard for exploring crime data in Israel with maps, filters, city-level analysis, and export tools.

The project is built with `Dash`, `Plotly`, `Pandas`, and `SQLite`, and combines crime records with municipal boundaries, police station locations, population data, and socioeconomic indicators.

## Overview

This application helps users explore crime patterns across Israeli cities and police districts from 2020 to 2024. It provides:

- A choropleth map of crime distribution by city or police district
- Filters for year, crime type, and quarter
- Optional police station markers on the map
- A socioeconomic scatter plot comparing crime-per-capita and city ranking
- A quarterly comparison chart for cities currently in view
- A city details panel with summary statistics and a pie chart
- Export links for datasets used by the dashboard

## Tech Stack

- Python
- Dash
- Dash Bootstrap Components
- Plotly
- Pandas
- SQLite
- Requests

## Project Structure

```text
CrimeProject/
- main.py                      # Main Dash application
- crime_2024.db                # SQLite database with crime tables
- crimes_2020.csv              # Raw/exportable crime data
- crimes_2021.csv
- crimes_2022.csv
- crimes_2023.csv
- city_coordinates.csv         # City coordinates used for spatial filtering
- police_stations.csv          # Police station coordinates
- socioeconomic_by_city.csv    # Socioeconomic ranking by city
- requirements.txt             # Python dependencies
- script.py                    # Small helper to inspect DB tables
```

## Data Sources

The dashboard uses a mix of local files and live data:

- Local crime data stored in `crime_2024.db`
- Police station coordinates from `police_stations.csv`
- City coordinates from `city_coordinates.csv`
- Socioeconomic data from `socioeconomic_by_city.csv`
- Population data fetched at runtime from `data.gov.il`

## Required Files

The app code expects these files to exist in the project root at runtime:

- `crime_2024.db`
- `city_coordinates.csv`
- `police_stations.csv`
- `socioeconomic_by_city.csv`
- `municipalities.geojson`
- `districts.geojson`

Important:

- In the current repo snapshot, `municipalities.geojson` and `districts.geojson` are referenced by `main.py` but are not present in the project folder.
- The app will not start successfully until those two GeoJSON files are added.
- `main.py` also references `/assets/siren.png`. That image is optional for presentation, but if you want the header icon to appear, create an `assets/` folder and place `siren.png` inside it.

## Setup

1. Create and activate a virtual environment.
2. Install the required packages.
3. Make sure the required CSV, DB, and GeoJSON files are present.
4. Run the Dash app.

Example on Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install dash dash-bootstrap-components plotly pandas requests
python main.py
```

The app runs locally at:

```text
http://127.0.0.1:8050
```

## How It Works

When the app starts, it:

1. Loads municipal and district GeoJSON boundaries.
2. Reads local CSV files for police stations, city coordinates, and socioeconomic data.
3. Fetches population data from the Israeli government API.
4. Stores the cleaned population table inside the SQLite database.
5. Builds interactive dashboards and callbacks for filtering and visualization.

## Main Features

### 1. Crime Map

- Shows crime counts by municipality or police district
- Supports filtering by year, crime category, and quarter
- Can overlay police station locations

### 2. Socioeconomic Analysis

- Compares crime per capita with socioeconomic ranking
- Updates based on map viewport and selected filters

### 3. Quarterly Comparison

- Displays grouped bars by quarter for visible cities
- Helps compare seasonal trends across locations

### 4. City Statistics Panel

- Lets the user select a city from the current map view
- Shows total crimes, average crimes by category, and a pie chart

### 5. Data Export

- Users can export crime tables and supporting datasets from the interface

## Notes and Limitations

- The app currently runs in `debug=True` mode in `main.py`.
- Population data is fetched live, so internet access is required during startup.
- Interactive analysis panels are designed around the 2024 database workflow and are only shown when the selected year is `2024`.
- If Hebrew text appears incorrectly on some systems, verify the source file encodings and your environment's UTF-8 support.

## Development

To inspect the tables currently stored in the SQLite database:

```powershell
python script.py
```

In the current database snapshot, the helper script reports:

- `crimes_2024`
- `population`

## Future Improvements

- Add the missing GeoJSON files to the repository
- Move all required data assets into clearly named folders
- Add a proper data preparation pipeline for all years
- Improve dependency management in `requirements.txt`
- Add tests and deployment instructions

## License

Add a license file if you plan to distribute or publish this project.

