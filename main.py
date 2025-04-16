import pandas as pd
import sqlite3
import plotly.express as px
import dash
from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc
import json

""" --------------------------------------------------- backend ---------------------------------------------------- """

# Json files for geo_borders (for the map)
with open("municipalities.geojson", encoding="utf-8") as f:
    geojson_municipal = json.load(f)
with open("districts.geojson", encoding="utf-8") as f:
    geojson_districts = json.load(f)

conn = sqlite3.connect("crime_2024.db") # DB connection
query = """ SELECT c.Yeshuv as יישוב,  c.PoliceDistrict as מחוז_משטרתי,
           c.StatisticGroup as סוג_עבירה, c.Quarter as רבעון, c.Year as שנה,
           COUNT(*) as כמות_פשעים
    FROM crimes_2024 c
    WHERE c.Yeshuv IS NOT NULL AND c.StatisticGroup IS NOT NULL
    GROUP BY c.Yeshuv, c.PoliceDistrict, c.StatisticGroup, c.Quarter, c.Year """
df = pd.read_sql_query(query, conn) # making df table for reaching data
conn.close()

quarter_mapping = {"Q1": "ינואר-מרץ","Q2": "אפריל-יוני","Q3": "יולי-ספטמבר","Q4": "אוקטובר-דצמבר"} # quarter types
df["תיאור_רבעון"] = df["רבעון"].map(quarter_mapping)
type_options = ["כלל העבירות"] + sorted(df["סוג_עבירה"].dropna().unique())
quarter_options = ["כל השנה"] + sorted(df["תיאור_רבעון"].dropna().unique())

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
            ], style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px", "boxShadow": "0px 0px 5px lightgray"})

        ] , style={"width": "40%", "padding-left": "10px", "padding-right": "10px"}),

# ------------------------------------------------------- Map ----------------------------------------------------------

        html.Div(children=[
            html.Div("ניתוחים על פי מפה", style={"fontWeight": "bold", "fontSize": "20px", "marginBottom": "10px"}),
            dcc.Graph(id="map-graph", style={"height": "500px"})
        ], style={
            "width": "100%",
            "backgroundColor": "white",
            "padding": "20px",
            "borderRadius": "10px",
            "marginLeft": "10px",
            "boxShadow": "0px 0px 8px #b3cde0"
        }),


    ])
])

# ---------------------------------------------- callbacks (events) ----------------------------------------------------

@app.callback(
    Output("map-graph", "figure"),
    Input("year-slider", "value"),
    Input("crime-type-dropdown", "value"),
    Input("quarter-dropdown", "value"),
    Input("toggle-switch", "value")
)

# --------------------------------------------------- Update -----------------------------------------------------------

def update_map(selected_year, selected_crime, selected_quarter, toggle_value):
    filtered = df[df["שנה"] == selected_year]
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

    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        hoverlabel=dict(bgcolor="white", font_size=14),
        title="מפת פשיעה לפי בחירה"
    )
    return fig

""" ---------------------------------------------------------------------------------------------------------------- """

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=8050)