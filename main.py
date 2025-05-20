import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import dash
import requests
from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc
import json
from rapidfuzz import process

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

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP]) # create Dash
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
                html.Label("בחר שנה:", style={"fontWeight": "bold"}),
                dcc.Slider(
                    id="year-slider",
                    min=2020, max=2024, step=1, value=2024,
                    marks={str(y): str(y) for y in range(2020, 2025)}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "15px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("בחר קבוצת עבירה:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id="crime-type-dropdown",
                    options=[{"label": t, "value": t} for t in type_options],
                    value="כלל העבירות",
                    style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "15px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("בחר רבעון:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id="quarter-dropdown",
                    options=[{"label": q, "value": q} for q in quarter_options],
                    value="כל השנה",
                    style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "15px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("הצג לפי:", style={"fontWeight": "bold"}),
                dbc.Checklist(
                    options=[{"label": "הצג לפי מחוזות", "value": "district"}],
                    value=[], id="toggle-switch", switch=True, style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "15px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("הצג תחנות משטרה:", style={"fontWeight": "bold", "textAlign": "right"}),
                dbc.Checklist(
                    options=[{"label": "הצג תחנות", "value": "stations"}],
                    value=[],
                    id="toggle-police",
                    switch=True,
                    style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "15px", "boxShadow": "0px 0px 5px lightgray"}),

        ] , style={"width": "40%", "padding-left": "10px", "padding-right": "10px"}),

# ------------------------------------------------------- Map ----------------------------------------------------------

        html.Div(children=[
            html.Div("ניתוחים על פי מפה", style={"fontWeight": "bold", "fontSize": "20px", "marginBottom": "10px"}),
            dcc.Graph(id="map-graph", style={"height": "400px"},config={"scrollZoom": True} )
        ], style={
            "width": "100%",
            "backgroundColor": "white",
            "padding": "20px",
            "borderRadius": "10px",
            "marginLeft": "10px",
            "boxShadow": "0px 0px 8px #b3cde0"
        }),


    ]),

# -------------------------------------------interactive graphs -----------------------------------------------------------

            html.Div([
                html.H3("פשיעה לנפש מול דירוג חברתי־כלכלי", style={"textAlign": "right"}),
                dcc.Graph(id="scatter-socio-graph", style={"height": "400px"})
            ], style={
                "width": "100%",
                "marginTop": "40px",
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "10px",
                "boxShadow": "0px 0px 8px #b3cde0"
            }),

# --------------------------------------------------- graphs -----------------------------------------------------------

            html.Div(id="crime-ratio-container", style={
                "display": "block",
                "marginTop": "50px",
            }, children=[
                html.H3("ניתוחים סטטיסטיים", style={
                    "textAlign": "right",
                    "marginBottom": "20px",
                    "marginTop": "10px",
                    "paddingRight": "10px"
                }),

                # הגרף
                dcc.Graph(id="crime-ratio-graph", style={
                    "height": "300px",
                    "width": "420px",
                    "borderRadius": "10px",
                    "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                    "paddingRight": "10px"
                }),

                # הפילטרים – מתחת לגרף
                html.Div([
                    html.Label("בחר סוג עבירה לניתוח:", style={"fontWeight": "bold", "paddingTop": "10px", "display": "block"}),
                    dcc.Dropdown(id="filter-crime-type", placeholder="בחר סוג עבירה", style={"width": "410px","paddingRight": "10px"}),

                    html.Label("חפש יישוב:", style={"fontWeight": "bold", "paddingTop": "10px", "display": "block"}),
                    dcc.Input(id="filter-city", type="text", placeholder="לדוגמה: חיפה", style={"width": "420px","paddingRight": "10px"})
                ])
            ]),

    html.Div([], style={"backgroundColor": "#e6f2ff", "height": "100px"})
])

# ---------------------------------------------- callbacks (events) ----------------------------------------------------

@app.callback(
    Output("map-graph", "figure"),
    Output("crime-ratio-container", "style"),
    Input("year-slider", "value"),
    Input("crime-type-dropdown", "value"),
    Input("quarter-dropdown", "value"),
    Input("toggle-switch", "value"),
    Input("toggle-police", "value"),
)

# --------------------------------------------------- Update -----------------------------------------------------------

def update_map(selected_year, selected_crime, selected_quarter, toggle_value, toggle_police):
    filtered = crime_filters[crime_filters["שנה"] == selected_year]
    if selected_crime != "כלל העבירות":
        filtered = filtered[filtered["סוג_עבירה"] == selected_crime]
    if selected_quarter != "כל השנה":
        filtered = filtered[filtered["תיאור_רבעון"] == selected_quarter]

    if "district" in toggle_value:
        grouped = filtered.groupby("מחוז_משטרתי", as_index=False).agg({"כמות_פשעים": "sum"})
        fig = px.choropleth_mapbox(
            grouped, geojson=geojson_districts, locations="מחוז_משטרתי",
            featureidkey="properties.name", color="כמות_פשעים",
            color_continuous_scale="OrRd", mapbox_style="carto-positron",
            zoom=6.2, center={"lat": 31.5, "lon": 34.75}, opacity=0.5
        )
    else:
        grouped = filtered.groupby("יישוב", as_index=False).agg({"כמות_פשעים": "sum"})
        fig = px.choropleth_mapbox(
            grouped, geojson=geojson_municipal, locations="יישוב",
            featureidkey="properties.MUN_HEB", color="כמות_פשעים",
            color_continuous_scale="OrRd", mapbox_style="carto-positron",
            zoom=6.5, center={"lat": 31.5, "lon": 34.75}, opacity=0.5
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
        mapbox_zoom=6.5,
        mapbox_center={"lat": 31.5, "lon": 34.75},
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        hoverlabel=dict(bgcolor="white", font_size=14)
    )

    show_stats_style = {"display": "block"} if selected_year == 2024 else {"display": "none"}
    return fig, show_stats_style

def match_names_fuzzy(source_names, target_names, threshold=85):
    mapping = {}
    for name in source_names:
        match, score, _ = process.extractOne(name, target_names)
        if score >= threshold:
            mapping[name] = match
    return mapping

# Callback חדש
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

    def clean_name(name):
        name = str(name).strip().replace('-', ' ').replace('־', ' ').replace("'", '').replace('"', '')
        name = name.replace("תל אביב יפו", "תל אביב")
        name = name.replace("תל אביב -יפו", "תל אביב")
        return name


    # שלב ניקוי
    crime_df["יישוב_נקי"] = crime_df["יישוב"].apply(clean_name)
    population["יישוב_נקי"] = population["יישוב"].apply(clean_name)
    socio_df["יישוב_נקי"] = socio_df["יישוב"].apply(clean_name)
    city_coords_df["יישוב_נקי"] = city_coords_df["יישוב_נקי"].apply(clean_name)

    # תיקון שמות יישובים בעזרת fuzzy matching
    crime_names = crime_df["יישוב_נקי"].unique()
    coords_map = match_names_fuzzy(crime_names, city_coords_df["יישוב_נקי"].unique())
    pop_map = match_names_fuzzy(crime_names, population["יישוב_נקי"].unique())
    socio_map = match_names_fuzzy(crime_names, socio_df["יישוב_נקי"].unique())

    crime_df["יישוב_נקי"] = crime_df["יישוב_נקי"].apply(lambda x: coords_map.get(x, x))
    crime_df["יישוב_נקי"] = crime_df["יישוב_נקי"].apply(lambda x: pop_map.get(x, x))
    crime_df["יישוב_נקי"] = crime_df["יישוב_נקי"].apply(lambda x: socio_map.get(x, x))

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
    Output("crime-ratio-graph", "figure"),
    Input("year-slider", "value"),
    Input("filter-crime-type", "value"),
    Input("filter-city", "value")
)
def update_crime_ratio_graph(selected_year, selected_type, input_city):
    if selected_year != 2024:
        return go.Figure()

    conn = sqlite3.connect("crime_2024.db")
    crime_df = pd.read_sql("SELECT Yeshuv as יישוב, StatisticGroup as סוג_עבירה, COUNT(*) as כמות_פשעים FROM crimes_2024 GROUP BY Yeshuv, StatisticGroup", conn)
    population = pd.read_sql("SELECT `שם_ישוב` as יישוב, `סהכ` as סהכ_אוכלוסייה FROM population", conn)
    conn.close()

    def clean_city_name(name):
        if pd.isna(name):
            return ""
        return str(name).strip().replace('-', ' ').replace('"', '').replace("'", '').replace("־", ' ').replace('״', '').replace('׳', '')

    crime_df["יישוב_נקי"] = crime_df["יישוב"].apply(clean_city_name)
    population["יישוב_נקי"] = population["יישוב"].apply(clean_city_name)

    if selected_type:
        crime_df = crime_df[crime_df["סוג_עבירה"] == selected_type]

    merged = pd.merge(crime_df, population, on="יישוב_נקי", how="inner")
    merged["פשיעה_לנפש"] = merged["כמות_פשעים"] / merged["סהכ_אוכלוסייה"]

    top10 = merged.sort_values(by="פשיעה_לנפש", ascending=False).head(10)

    # הוספת יישוב מחיפוש אם הוא לא בטופ 10
    if input_city:
        input_city_clean = clean_city_name(input_city)
        city_row = merged[merged["יישוב_נקי"].str.contains(input_city_clean, case=False)]
        if not city_row.empty:
            top10 = pd.concat([top10, city_row]).drop_duplicates(subset="יישוב_נקי")

    colors = ["blue" if city == input_city else "indianred" for city in top10["יישוב_נקי"]]

    fig = go.Figure(go.Bar(
        x=top10["יישוב_נקי"],
        y=top10["פשיעה_לנפש"],
        marker_color=colors
    ))

    fig.update_layout(
        xaxis_title="עיר",
        yaxis_title="יחס הפשיעה לנפש",
        template="simple_white",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(tickangle=45)
    )

    return fig

@app.callback(
    Output("filter-crime-type", "options"),
    Input("year-slider", "value")
)
def populate_crime_type_options(year):
    if year != 2024:
        return []

    conn = sqlite3.connect("crime_2024.db")
    types = pd.read_sql("SELECT DISTINCT StatisticGroup as סוג_עבירה FROM crimes_2024", conn)
    conn.close()

    return [{"label": t, "value": t} for t in sorted(types["סוג_עבירה"].dropna().unique())]


""" ---------------------------------------------------------------------------------------------------------------- """

# ---------------------------------------------------- Main ------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True, port=8050)