import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import dash
import requests
from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc
import json


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
                    min=2021, max=2025, step=1, value=2021,
                    marks={str(y): str(y) for y in range(2021, 2026)}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("בחר קבוצת עבירה:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id="crime-type-dropdown",
                    options=[{"label": t, "value": t} for t in type_options],
                    value="כלל העבירות",
                    style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("בחר רבעון:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id="quarter-dropdown",
                    options=[{"label": q, "value": q} for q in quarter_options],
                    value="כל השנה",
                    style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("הצג לפי:", style={"fontWeight": "bold"}),
                dbc.Checklist(
                    options=[{"label": "הצג לפי מחוזות", "value": "district"}],
                    value=[], id="toggle-switch", switch=True, style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px", "marginBottom": "10px", "boxShadow": "0px 0px 5px lightgray"}),

            html.Div([
                html.Label("הצג תחנות משטרה:", style={"fontWeight": "bold", "textAlign": "right"}),
                dbc.Checklist(
                    options=[{"label": "הצג תחנות", "value": "stations"}],
                    value=[],
                    id="toggle-police",
                    switch=True,
                    style={"textAlign": "right"}
                )
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px", "boxShadow": "0px 0px 5px lightgray"}),

        ] , style={"width": "40%", "padding-left": "10px", "padding-right": "10px"}),

# ------------------------------------------------------- Map ----------------------------------------------------------

        html.Div(children=[
            html.Div("ניתוחים על פי מפה", style={"fontWeight": "bold", "fontSize": "20px", "marginBottom": "10px"}),
            dcc.Graph(id="map-graph", style={"height": "500px"},config={"scrollZoom": True} )
        ], style={
            "width": "100%",
            "backgroundColor": "white",
            "padding": "20px",
            "borderRadius": "10px",
            "marginLeft": "10px",
            "boxShadow": "0px 0px 8px #b3cde0"
        }),


    ]),
         html.Div(id="crime-ratio-container", style={"display": "none"}, children=[
              html.H3("10 הערים המובילות ביחס פשיעה לנפש", style={"textAlign": "center"}),
              dcc.Graph(
                  id="crime-ratio-graph",
                  style={"marginTop": "20px"}
         )
    ])
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
        fig.add_scattermapbox(
            lat=df_police["lat"], lon=df_police["lon"], mode="markers",
            marker=dict(size=8, color="blue"),
            text=df_police["Station"],
            name="תחנת משטרה"
        )

    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        hoverlabel=dict(bgcolor="white", font_size=14),
        title="מפת פשיעה לפי בחירה",
    )

    show_stats_style = {"display": "block"} if selected_year == 2024 else {"display": "none"}
    return fig, show_stats_style

@app.callback(
    Output("crime-ratio-graph", "figure"),
    Input("year-slider", "value")
)
def update_crime_ratio_graph(selected_year):
    if selected_year != 2024:
        return go.Figure()

    conn = sqlite3.connect("crime_2024.db")
    crime_per_yeshuv = pd.read_sql("SELECT Yeshuv as יישוב, COUNT(*) as כמות_פשעים FROM crimes_2024 GROUP BY Yeshuv", conn)
    population = pd.read_sql("SELECT `שם_ישוב` as יישוב, `סהכ` as סהכ_אוכלוסייה FROM population", conn)
    conn.close()
    crime_per_yeshuv['יישוב_נקי'] = crime_per_yeshuv['יישוב'].apply(clean_city_name)
    population['יישוב_נקי'] = population['יישוב'].apply(clean_city_name)

    merged = pd.merge(crime_per_yeshuv, population, left_on='יישוב_נקי', right_on='יישוב_נקי', how='inner')
    merged["פשיעה_לנפש"] = merged["כמות_פשעים"] / merged["סהכ_אוכלוסייה"]
    top10 = merged.sort_values(by="פשיעה_לנפש", ascending=False).head(10)

    fig = go.Figure(go.Bar(
        x=top10["יישוב_נקי"],
        y=top10["פשיעה_לנפש"],
        marker_color="indianred"
    ))

    fig.update_layout(
        title="יחס פשיעה לנפש - 10 ערים מובילות",
        xaxis_title="עיר",
        yaxis_title="פשיעה לנפש",
        template="simple_white"
    )
    return fig

def clean_city_name(name):
    if pd.isna(name):
        return ""
    return str(name).strip().replace('-', ' ').replace('"', '').replace("'", '').replace("־", ' ').replace('״', '').replace('׳', '').replace(" ", " ")

""" ---------------------------------------------------------------------------------------------------------------- """

# ---------------------------------------------------- Main ------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True, port=8050)