import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import dash
import requests
from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc
import json
from dash import ALL, ctx

""" --------------------------------------------------- backend ---------------------------------------------------- """

# ----------------------------------------------------- files ----------------------------------------------------------

# Json files for geo_borders (for the map)
with open("municipalities.geojson", encoding="utf-8") as f:
    geojson_municipal = json.load(f)
with open("districts.geojson", encoding="utf-8") as f:
    geojson_districts = json.load(f)
# Load police stations CSV
df_police = pd.read_csv("police_stations.csv")

# ----------------------------------------------- DB and API connection ------------------------------------------------

url = 'https://data.gov.il/api/3/action/datastore_search?resource_id=64edd0ee-3d5d-43ce-8562-c336c24dbc1f&limit=5000'
response = requests.get(url)
data = response.json()
records = data['result']['records']
df_population = pd.DataFrame.from_records(records)
conn = sqlite3.connect("crime_2024.db") # DB connection
df_population_clean = df_population[["שם_ישוב", "סהכ"]]
df_population_clean.to_sql("population", conn, if_exists="replace", index=False)
socio_df = pd.read_csv("socioeconomic_by_city.csv")
socio_df["יישוב_נקי"] = socio_df["יישוב"].str.strip()
city_coords_df = pd.read_csv("city_coordinates.csv")  # יש להכין קובץ עם עמודות: יישוב_נקי, lat, lon
city_coords_df["יישוב_נקי"] = city_coords_df["יישוב_נקי"].apply(lambda x: str(x).strip())


# ------------------------------------------------- queries ------------------------------------------------------------

crime_filters = pd.read_sql_query(""" SELECT c.Yeshuv as יישוב,  c.PoliceDistrict as מחוז_משטרתי,
           c.StatisticGroup as סוג_עבירה, c.Quarter as רבעון, c.Year as שנה,
           COUNT(*) as כמות_פשעים
           FROM crimes_2024 c
           WHERE c.Yeshuv IS NOT NULL AND c.StatisticGroup IS NOT NULL
           GROUP BY c.Yeshuv, c.PoliceDistrict, c.StatisticGroup, c.Quarter, c.Year """, conn)

conn.close()

# ------------------------------------------------ tables --------------------------------------------------------------

quarter_mapping = {"Q1": "ינואר-מרץ","Q2": "אפריל-יוני","Q3": "יולי-ספטמבר","Q4": "אוקטובר-דצמבר"} # quarter types
crime_filters["תיאור_רבעון"] = crime_filters["רבעון"].map(quarter_mapping)
type_options = ["כלל העבירות"] + sorted(crime_filters["סוג_עבירה"].dropna().unique())
quarter_options = ["כל השנה"] + sorted(crime_filters["תיאור_רבעון"].dropna().unique())

""" ---------------------------------------------------------------------------------------------------------------- """

""" ----------------------------------------------- frontend ------------------------------------------------------- """

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True) # create Dash
app.title = "מפת פשיעה לפי יישובים"

# --------------------------------------------------- Header -----------------------------------------------------------

app.layout = html.Div(style={"backgroundColor": "#e6f2ff", "direction": "rtl"}, children=[
    html.Div([
        html.Div([
            html.H1("ניתוחי פשיעה - מדינת ישראל", style={
                "margin": "0", "fontSize": "28px", "color": "white",
                "flex": "1", "textAlign": "center"
            }),
            html.Img(src="/assets/siren.png", style={
                "height": "40px", "marginRight": "15px"
            })
        ], style={
            "display": "flex", "alignItems": "center",
            "justifyContent": "flex-end", "gap": "15px"
        })
    ], style={
        "backgroundColor": "#0d1a33",
        "padding": "15px",
        "marginBottom": "15px"
    }),
    html.Div(style={"display": "flex"}, children=[

# ------------------------------------------------ Maps filters --------------------------------------------------------

        html.Div(children=[
            html.Div([
                html.H3("פילטרים של המפה", style={"textAlign": "right", "marginBottom": "15px"}),

                html.Div([  # שנה ורבעון
                    html.Label("בחר שנה:", style={"fontWeight": "bold", "display": "block"}),
                    dcc.Slider(
                        id="year-slider",
                        min=2020, max=2024, step=1, value=2024,
                        marks={str(y): str(y) for y in range(2020, 2025)}
                    ),
                    html.Br(),
                    html.Label("בחר רבעון:", style={"fontWeight": "bold", "display": "block"}),
                    dcc.Dropdown(
                        id="quarter-dropdown",
                        options=[{"label": q, "value": q} for q in quarter_options],
                        value="כל השנה",
                        style={"textAlign": "right"}
                    )
                ], style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px",
                          "marginBottom": "15px", "boxShadow": "0 2px 5px rgba(0,0,0,0.1)"}),

                html.Div([  # סוג עבירה
                    html.Label("בחר סוג עבירה:", style={"fontWeight": "bold", "display": "block"}),
                    dcc.Dropdown(
                        id="crime-type-dropdown",
                        options=[{"label": t, "value": t} for t in type_options],
                        value="כלל העבירות",
                        style={"textAlign": "right"}
                    )
                ], style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px",
                          "marginBottom": "15px", "boxShadow": "0 2px 5px rgba(0,0,0,0.1)"}),

                html.Div([  # שכבות
                    html.Label("שכבות:", style={"fontWeight": "bold", "display": "block"}),
                    dbc.Checklist(
                        options=[{"label": "מחוזות", "value": "district"}],
                        value=[], id="toggle-switch", switch=True, style={"textAlign": "right", "marginBottom": "10px"}
                    ),
                    dbc.Checklist(
                        options=[{"label": "תחנות משטרה", "value": "stations"}],
                        value=[],
                        id="toggle-police",
                        switch=True,
                        style={"textAlign": "right"}
                    )
                ], style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px",
                          "marginBottom": "15px", "boxShadow": "0 2px 5px rgba(0,0,0,0.1)"})
            ],  style={"backgroundColor": "#e6f2ff", "padding": "20px", "borderRadius": "12px", "boxShadow": "0 0 6px #99badd", "border": "3px solid #99badd"})

        ], style={"width": "40%","padding-right":"35px"}),

# ------------------------------------------------------- Map ----------------------------------------------------------

        html.Div(children=[
            html.Div("ניתוחים על פי מפה", style={"fontWeight": "bold", "fontSize": "20px", "marginBottom": "10px"}),
            dcc.Graph(id="map-graph", style={"height": "470px","border": "3px solid #99badd"},config={"scrollZoom": True} )
        ], style={
            "width": "100%",
            "backgroundColor": "#e6f2ff",
            "padding": "20px",
            "borderRadius": "10px",
            "marginLeft": "35px",
            "boxShadow": "0px 0px 8px #b3cde0",
        }),
    ]),

# -------------------------------------------interactive graphs -----------------------------------------------------------

    html.Div(id="analysis-container", children=[
        html.H3("גרפים אינטראקטיביים", style={"textAlign": "right", "marginBottom": "20px"}),

        html.Div(style={"display": "flex", "gap": "20px"}, children=[
            html.Div([
                html.H5("פשיעה לנפש מול דירוג חברתי־כלכלי", style={"textAlign": "right"}),
                dcc.Graph(id="scatter-socio-graph", style={"height": "400px"})
            ], style={"width": "50%"}),

            html.Div([
                html.H5("פשיעה לפי רבעונים ביישובים נוכחיים", style={"textAlign": "right"}),
                dcc.Graph(id="quarterly-crime-graph", style={"height": "400px"})
            ], style={"width": "50%"})
        ]),
        html.Div(style={"display": "flex", "gap": "20px","padding-top" : "20px"}, children=[
            html.Div([
                html.H5("בחר יישוב להצגת נתונים סטטיסטיים", style={"textAlign": "right"}),
                dcc.Dropdown(id="city-scope-dropdown", placeholder="בחר יישוב מהתצוגה במפה"),
                html.Div(id="city-details-panel")
            ], style={"width": "50%"}),

            html.Div([
                html.Button("📤 ייצוא נתונים", id="toggle-export-list", n_clicks=0, style={
                    "backgroundColor": "#0d1a33",
                    "color": "white",
                    "padding": "10px 20px",
                    "fontSize": "18px",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                    "marginBottom": "10px"
                }),
                html.Div(id="export-list-wrapper", style={"marginTop": "10px", "textAlign": "right"})
            ], style={"width": "50%", "display": "flex", "flexDirection": "column", "justifyContent": "flex-start",
                      "alignItems": "flex-end"})
        ])
    ], style={
        "width": "96%",
        "margin": "40px auto 0",
        "backgroundColor": "#e6f2ff",
        "padding": "20px",
        "borderRadius": "12px",
        "boxShadow": "0 0 6px #99badd",
        "border": "3px solid #99badd"
    }),
    html.Div([], style={"backgroundColor": "#e6f2ff", "height": "100px"})
])

# ---------------------------------------------- callbacks (events) ----------------------------------------------------

@app.callback(
    Output("map-graph", "figure"),
    Input("year-slider", "value"),
    Input("crime-type-dropdown", "value"),
    Input("quarter-dropdown", "value"),
    Input("toggle-switch", "value"),
    Input("toggle-police", "value"),
)

# --------------------------------------------------- Update -----------------------------------------------------------

def update_map(selected_year, selected_crime, selected_quarter, toggle_value, toggle_police, relayoutData=None):
    filtered = load_crime_data_for_year(selected_year)
    if selected_crime != "כלל העבירות":
        filtered = filtered[filtered["סוג_עבירה"] == selected_crime]
    if selected_quarter != "כל השנה":
        filtered = filtered[filtered["תיאור_רבעון"] == selected_quarter]


    zoom = 6.5
    center = {"lat": 31.5, "lon": 34.75}
    if relayoutData and "mapbox.center" in relayoutData and "mapbox.zoom" in relayoutData:
        center = relayoutData.get("mapbox.center", center)
        zoom = relayoutData.get("mapbox.zoom", zoom)

    if "district" in toggle_value:
        grouped = filtered.groupby("מחוז_משטרתי", as_index=False).agg({"כמות_פשעים": "sum"})
        fig = px.choropleth_mapbox(
            grouped, geojson=geojson_districts, locations="מחוז_משטרתי",
            featureidkey="properties.name", color="כמות_פשעים",
            color_continuous_scale="OrRd", mapbox_style="carto-positron",
            opacity=0.5
        )
    else:
        grouped = filtered.groupby("יישוב", as_index=False).agg({"כמות_פשעים": "sum"})
        fig = px.choropleth_mapbox(
            grouped, geojson=geojson_municipal, locations="יישוב",
            featureidkey="properties.MUN_HEB", color="כמות_פשעים",
            color_continuous_scale="OrRd", mapbox_style="carto-positron",
            opacity=0.5
        )

    if "stations" in toggle_police:
        fig.add_trace(go.Scattermapbox(
            lat=df_police["lat"],
            lon=df_police["lon"],
            marker=dict(size=7, color="blue", symbol="circle"),
            text=["🚓 תחנה"] * len(df_police),
            mode="markers+text",
            name="תחנות משטרה"
        ))

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=zoom,
        mapbox_center=center,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        hoverlabel=dict(bgcolor="#e6f2ff", font_size=14)
    )

    return fig


@app.callback(
    Output("scatter-socio-graph", "figure"),
    Input("year-slider", "value"),
    Input("crime-type-dropdown", "value"),
    Input("quarter-dropdown", "value"),
    Input("map-graph", "relayoutData")
)
def update_scatter_graph(year, crime_type, quarter, relayoutData):
    conn = sqlite3.connect("crime_2024.db")
    crime_df = pd.read_sql("SELECT Yeshuv as יישוב, StatisticGroup as סוג_עבירה, Quarter as רבעון, Year as שנה, COUNT(*) as כמות_פשעים FROM crimes_2024 GROUP BY Yeshuv, StatisticGroup, Quarter, Year", conn)
    population = pd.read_sql("SELECT `שם_ישוב` as יישוב, `סהכ` as סהכ_אוכלוסייה FROM population", conn)
    conn.close()

    socio_df = pd.read_csv("socioeconomic_by_city.csv")
    city_coords_df = pd.read_csv("city_coordinates.csv")

    crime_df = apply_city_name_normalization(crime_df, "יישוב")
    population = apply_city_name_normalization(population, "יישוב")
    socio_df = apply_city_name_normalization(socio_df, "יישוב")
    city_coords_df = apply_city_name_normalization(city_coords_df, "יישוב_נקי")

    crime_df.rename(columns={"יישוב": "יישוב_נקי"}, inplace=True)
    population.rename(columns={"יישוב": "יישוב_נקי"}, inplace=True)
    socio_df.rename(columns={"יישוב": "יישוב_נקי"}, inplace=True)

    df_filtered = crime_df[crime_df["שנה"] == year]
    if crime_type != "כלל העבירות":
        df_filtered = df_filtered[df_filtered["סוג_עבירה"] == crime_type]
    if quarter != "כל השנה":
        quarter_map = {"ינואר-מרץ": "Q1", "אפריל-יוני": "Q2", "יולי-ספטמבר": "Q3", "אוקטובר-דצמבר": "Q4"}
        df_filtered = df_filtered[df_filtered["רבעון"] == quarter_map.get(quarter, "")]

    merged = pd.merge(df_filtered, population, on="יישוב_נקי", how="inner")
    merged = pd.merge(merged, socio_df, on="יישוב_נקי", how="inner")
    merged = pd.merge(merged, city_coords_df, on="יישוב_נקי", how="inner")
    merged = merged.dropna(subset=["lat", "lon", "דירוג_חברתי_כלכלי", "סהכ_אוכלוסייה"])
    merged["דירוג_חברתי_כלכלי"] = pd.to_numeric(merged["דירוג_חברתי_כלכלי"], errors="coerce")

    if relayoutData and "mapbox._derived" in relayoutData:
        bounds = relayoutData["mapbox._derived"].get("coordinates", [])
        if bounds and isinstance(bounds, list):
            lons = [pt[0] for pt in bounds]
            lats = [pt[1] for pt in bounds]
            lon_min, lon_max = min(lons), max(lons)
            lat_min, lat_max = min(lats), max(lats)
            merged = merged[(merged["lon"] >= lon_min) & (merged["lon"] <= lon_max) &
                            (merged["lat"] >= lat_min) & (merged["lat"] <= lat_max)]

    grouped = merged.groupby(["יישוב_נקי", "דירוג_חברתי_כלכלי"], as_index=False).agg({
        "כמות_פשעים": "sum",
        "סהכ_אוכלוסייה": "first"
    })
    grouped["פשיעה_לנפש"] = grouped["כמות_פשעים"] / grouped["סהכ_אוכלוסייה"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grouped["דירוג_חברתי_כלכלי"],
        y=grouped["פשיעה_לנפש"],
        mode="markers",
        text=grouped["יישוב_נקי"],
        marker=dict(
            size=10,
            color=grouped["דירוג_חברתי_כלכלי"],
            colorscale="Viridis",
            showscale=True
        )
    ))
    top_points = grouped.loc[grouped.groupby("דירוג_חברתי_כלכלי")["פשיעה_לנפש"].idxmax()]
    top_points = top_points.sort_values("דירוג_חברתי_כלכלי")
    fig.add_trace(go.Scatter(
        x=top_points["דירוג_חברתי_כלכלי"],
        y=top_points["פשיעה_לנפש"],
        mode="lines+markers",
        name="קו עליון",
        line=dict(color="red", width=2, dash="dash")
    ))
    fig.update_layout(
        xaxis_title="דירוג חברתי-כלכלי (1=נמוך, 10=גבוה)",
        yaxis_title="פשיעה לנפש",
        template="simple_white",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig



@app.callback(
    Output("quarterly-crime-graph", "figure"),
    Input("year-slider", "value"),
    Input("crime-type-dropdown", "value"),
    Input("map-graph", "relayoutData")
)
def update_quarterly_graph(year, crime_type, relayoutData):
    conn = sqlite3.connect("crime_2024.db")
    crime_df = pd.read_sql("""
        SELECT Yeshuv as יישוב, StatisticGroup as סוג_עבירה,
               Quarter as רבעון, Year as שנה, COUNT(*) as כמות_פשעים
        FROM crimes_2024
        GROUP BY Yeshuv, StatisticGroup, Quarter, Year
    """, conn)
    conn.close()

    city_coords_df = pd.read_csv("city_coordinates.csv")
    crime_df = apply_city_name_normalization(crime_df, "יישוב")
    city_coords_df = apply_city_name_normalization(city_coords_df, "יישוב_נקי")

    crime_df.rename(columns={"יישוב": "יישוב_נקי"}, inplace=True)

    if crime_type != "כלל העבירות":
        crime_df = crime_df[crime_df["סוג_עבירה"] == crime_type]

    crime_df = crime_df[crime_df["שנה"] == year]

    merged = pd.merge(crime_df, city_coords_df, on="יישוב_נקי", how="inner")
    merged = merged.dropna(subset=["lat", "lon"])

    if relayoutData and "mapbox._derived" in relayoutData:
        bounds = relayoutData["mapbox._derived"].get("coordinates", [])
        if bounds and isinstance(bounds, list):
            lons = [pt[0] for pt in bounds]
            lats = [pt[1] for pt in bounds]
            lon_min, lon_max = min(lons), max(lons)
            lat_min, lat_max = min(lats), max(lats)
            merged = merged[(merged["lon"] >= lon_min) & (merged["lon"] <= lon_max) &
                            (merged["lat"] >= lat_min) & (merged["lat"] <= lat_max)]

    pivot = merged.pivot_table(
        index="יישוב_נקי",
        columns="רבעון",
        values="כמות_פשעים",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    fig = go.Figure()
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    quarter_labels = {
        "Q1": "ינואר-מרץ",
        "Q2": "אפריל-יוני",
        "Q3": "יולי-ספטמבר",
        "Q4": "אוקטובר-דצמבר"
    }

    for i, q in enumerate(quarters):
        if q in pivot.columns:
            fig.add_trace(go.Bar(
                x=pivot["יישוב_נקי"],
                y=pivot[q],
                name=quarter_labels.get(q, q),
                marker_color=colors[i]
            ))

    fig.update_layout(
        barmode="group",
        xaxis_title="יישוב",
        yaxis_title="מספר עבירות",
        template="simple_white",
        margin=dict(l=20, r=20, t=40, b=80)
    )
    return fig


def normalize_city_name(name):
    if not isinstance(name, str):
        return ""
    name = name.strip()
    name = name.replace("־", "-").replace("–", "-").replace("'", "").replace('"', "")
    name = name.replace("-", " ")
    name = " ".join(name.split())  # remove double spaces
    return name

def apply_city_name_normalization(df, column):
    df[column] = df[column].astype(str).apply(normalize_city_name)
    return df

@app.callback(
    Output("city-scope-dropdown", "options"),
    Input("map-graph", "relayoutData"),
)
def update_city_dropdown(relayoutData):
    city_df = pd.read_csv("city_coordinates.csv")
    city_df = apply_city_name_normalization(city_df, "יישוב_נקי")

    if relayoutData and "mapbox._derived" in relayoutData:
        bounds = relayoutData["mapbox._derived"].get("coordinates", [])
        if bounds and isinstance(bounds, list):
            lons = [pt[0] for pt in bounds]
            lats = [pt[1] for pt in bounds]
            lon_min, lon_max = min(lons), max(lons)
            lat_min, lat_max = min(lats), max(lats)
            city_df = city_df[(city_df["lon"] >= lon_min) & (city_df["lon"] <= lon_max) &
                              (city_df["lat"] >= lat_min) & (city_df["lat"] <= lat_max)]

    city_names = [city for city in city_df["יישוב_נקי"].unique() if pd.notna(city)]
    return [{"label": city, "value": city} for city in sorted(set(city_names))]


@app.callback(
    Output("city-details-panel", "children"),
    Input("city-scope-dropdown", "value"),
    Input("year-slider", "value")
)
def display_city_statistics(selected_city, year):
    if not selected_city:
        return html.Div()

    clean_city = normalize_city_name(selected_city)

    conn = sqlite3.connect("crime_2024.db")
    crimes_raw = pd.read_sql("SELECT Yeshuv, StatisticGroup as סוג_עבירה FROM crimes_2024 WHERE Year = ?", conn, params=(year,))
    conn.close()

    crimes_raw = apply_city_name_normalization(crimes_raw, "Yeshuv")
    crimes_raw.rename(columns={"Yeshuv": "יישוב_נקי"}, inplace=True)

    crime_df = crimes_raw[crimes_raw["יישוב_נקי"] == clean_city]

    if crime_df.empty:
        return html.Div([html.P("לא נמצאו נתוני פשיעה עבור היישוב שבחרת.", style={"textAlign": "right", "color": "red"})])

    crime_summary = crime_df.groupby("סוג_עבירה").size().reset_index(name="כמות")
    total_crimes = crime_summary["כמות"].sum()
    avg_per_type = crime_summary["כמות"].mean()

    fig = go.Figure(data=[
        go.Pie(labels=crime_summary["סוג_עבירה"], values=crime_summary["כמות"], hole=0.3)
    ])
    fig.update_layout(title=f"התפלגות סוגי פשיעה - {selected_city}")

    return html.Div([
        html.H6(f"נתונים עבור יישוב: {selected_city}", style={"textAlign": "right"}),
        html.Div([
            html.Div([
                html.P("סך כל מקרי הפשיעה", style={"fontWeight": "bold", "fontSize": "25px", "margin": "0 5px","textAlign": "center"}),
                html.Br(),
                html.P(f"{total_crimes}", style={"fontWeight": "bold","fontSize": "35px", "color": "#0d1a33", "margin": "0 5px","textAlign": "center"})
            ], style={"alignItems": "center", "gap": "5px"}),

            html.Div([
                html.P("ממוצע עבירות לכל סוג", style={"fontWeight": "bold", "fontSize": "25px", "margin": "0 5px","textAlign": "center"}),
                html.Br(),
                html.P(f"{avg_per_type:.2f}", style={"fontWeight": "bold","fontSize": "35px", "color": "#0d1a33", "margin": "0 5px","textAlign": "center"})
            ], style={"alignItems": "center", "gap": "5px"})
        ], style={"display": "flex", "justifyContent": "space-between", "margin": "20px 0"}),
        dcc.Graph(figure=fig)
    ])

def load_crime_data_for_year(year):
    table_name = f"crimes_{year}"
    conn = sqlite3.connect("crime_2024.db")

    query = f"""
        SELECT 
            Yeshuv as יישוב,
            PoliceDistrict as מחוז_משטרתי,
            StatisticGroup as סוג_עבירה,
            Quarter as רבעון,
            Year as שנה
        FROM {table_name}
        WHERE Yeshuv IS NOT NULL AND StatisticGroup IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["כמות_פשעים"] = 1
    df["תיאור_רבעון"] = df["רבעון"].map({
        "Q1": "ינואר-מרץ",
        "Q2": "אפריל-יוני",
        "Q3": "יולי-ספטמבר",
        "Q4": "אוקטובר-דצמבר"
    })
    return df

@app.callback(
    Output("analysis-container", "style"),
    Input("year-slider", "value")
)
def toggle_analysis_visibility(selected_year):
    if selected_year == 2024:
        return {
            "width": "96%",
            "margin": "40px auto 0",
            "backgroundColor": "#e6f2ff",
            "padding": "20px",
            "borderRadius": "12px",
            "boxShadow": "0 0 6px #99badd",
            "border": "3px solid #99badd",
            "display": "block"
        }
    else:
        return {"display": "none"}

from dash import ctx

@app.callback(
    Output("export-list-wrapper", "children"),
    Input("toggle-export-list", "n_clicks"),
    prevent_initial_call=True
)
def toggle_export_list(n_clicks):
    # Toggle פתיחה/סגירה לפי מספר זוגי/אי זוגי של לחיצות
    if n_clicks % 2 == 0:
        return None

    file_labels = [
        ("crimes_2020", "📄 פשיעה 2020"),
        ("crimes_2021", "📄 פשיעה 2021"),
        ("crimes_2022", "📄 פשיעה 2022"),
        ("crimes_2023", "📄 פשיעה 2023"),
        ("crimes_2024", "📄 פשיעה 2024"),
        ("police_stations", "📄 תחנות משטרה"),
        ("socioeconomic_by_city", "📄 נתונים סוציו־אקונומיים"),
        ("city_coordinates", "📄 קואורדינטות יישובים"),
        ("municipalities", "🗺️ גבולות יישובים (GeoJSON)"),
        ("districts", "🗺️ גבולות מחוזות (GeoJSON)")
    ]

    return html.Div([
        html.Ul([
            html.Li(
                html.A(label, href="#", id={"type": "export-link", "index": key}, style={
                    "fontSize": "16px", "color": "#0d1a33", "textDecoration": "underline", "cursor": "pointer"
                })
            ) for key, label in file_labels
        ], style={"listStyleType": "none", "padding": "0"}),
        dcc.Download(id="download-any")
    ])

@app.callback(
    Output("download-any", "data"),
    Input({"type": "export-link", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_download(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered:
        return None

    file_key = triggered["index"]

    if file_key.startswith("crimes_"):
        year = file_key.split("_")[1]
        conn = sqlite3.connect("crime_2024.db")
        df = pd.read_sql(f"SELECT * FROM crimes_{year}", conn)
        conn.close()
        return dcc.send_data_frame(df.to_csv, f"{file_key}.csv", index=False)

    elif file_key in ["police_stations", "socioeconomic_by_city", "city_coordinates"]:
        df = pd.read_csv(f"{file_key}.csv")
        return dcc.send_data_frame(df.to_csv, f"{file_key}.csv", index=False)

    elif file_key in ["municipalities", "districts"]:
        with open(f"{file_key}.geojson", "r", encoding="utf-8") as f:
            return dict(content=f.read(), filename=f"{file_key}.geojson", type="text/geojson")

    return None

""" ---------------------------------------------------------------------------------------------------------------- """

# ---------------------------------------------------- Main ------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True, port=8050)