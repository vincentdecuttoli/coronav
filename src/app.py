import datetime
import os
import yaml

import numpy as np
import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


# Lecture du fichier d'environnement
ENV_FILE = '../env.yaml'
with open(ENV_FILE) as f:
    params = yaml.load(f, Loader=yaml.FullLoader)

# Initialisation des chemins vers les fichiers
ROOT_DIR = os.path.dirname(os.path.abspath(ENV_FILE))
DATA_FILE = os.path.join(ROOT_DIR,
                         params['directories']['processed'],
                         params['files']['all_data'])

# Lecture du fichier de données
epidemie_df = (pd.read_csv(DATA_FILE, parse_dates=['Last Update'])
               .assign(day=lambda _df: _df['Last Update'].dt.date)
               .drop_duplicates(subset=['Country/Region', 'Province/State', 'day'])
               [lambda df: df['day'] <= datetime.date(2020, 3, 21)]
              )

countries = [{'label': c, 'value': c} for c in sorted(epidemie_df['Country/Region'].unique())]
betagamma = [{'beta' : 0.001, 'gamma' : 0.1}]

korea_df = (epidemie_df[epidemie_df['Country/Region']=='South Korea']
             .groupby(['Country/Region','day'])
             .agg({'Confirmed':'sum', 'Deaths':'sum', 'Recovered':'sum'})
             .reset_index()
            )

korea_df['infected']=korea_df['Confirmed'].diff()


app = dash.Dash('Corona Virus Explorer')
app.layout = html.Div([
    html.H1(['Corona Virus Explorer'], style={'textAlign': 'center'}),
    dcc.Tabs([
        dcc.Tab(label='Time', children=[
            html.Div([
                dcc.Dropdown(
                    id='country',
                    options=countries
                )
            ]),
            html.Div([
                dcc.Dropdown(
                    id='country2',
                    options=countries
                )
            ]),
            html.Div([
                dcc.RadioItems(
                    id='variable',
                    options=[
                        {'label': 'Confirmed', 'value': 'Confirmed'},
                        {'label': 'Deaths', 'value': 'Deaths'},
                        {'label': 'Recovered', 'value': 'Recovered'}
                    ],
                    value='Confirmed',
                    labelStyle={'display': 'inline-block'}
                )
            ]),
            html.Div([
                dcc.Graph(id='graph1')
            ]),   
        ]),
        dcc.Tab(label='Map', children=[
            dcc.Graph(id='map1'),
            dcc.Slider(
                id='map_day',
                min=0,
                max=(epidemie_df['day'].max() - epidemie_df['day'].min()).days,
                value=0,
                #marks={i:str(date) for i, date in enumerate(epidemie_df['day'].unique())}
                marks={i:str(i) for i, date in enumerate(epidemie_df['day'].unique())}
            )  
        ]),
        dcc.Tab(label='Time', children = [
            html.Div([
                dcc.Dropdown(
                id = "parameters",
                options=betagamma)
            ])
        ])
    ]),
])

@app.callback(
    Output('graph1', 'figure'),
    [
        Input('country', 'value'),
        Input('country2', 'value'),
        Input('variable', 'value'),        
    ]
)
def update_graph(country, country2, variable):
    print(country)
    if country is None:
        graph_df = epidemie_df.groupby('day').agg({variable: 'sum'}).reset_index()
    else:
        graph_df = (epidemie_df[epidemie_df['Country/Region'] == country]
                    .groupby(['Country/Region', 'day'])
                    .agg({variable: 'sum'})
                    .reset_index()
                   )
    if country2 is not None:
        graph2_df = (epidemie_df[epidemie_df['Country/Region'] == country2]
                     .groupby(['Country/Region', 'day'])
                     .agg({variable: 'sum'})
                     .reset_index()
                    )

        
    #data : [dict(...graph_df...)] + ([dict(...graph2_df)] if country2 is not None else [])
        
    return {
        'data': [
            dict(
                x=graph_df['day'],
                y=graph_df[variable],
                type='line',
                name=country if country is not None else 'Total'
            )
        ] + ([
            dict(
                x=graph2_df['day'],
                y=graph2_df[variable],
                type='line',
                name=country2
            )            
        ] if country2 is not None else [])
    }

@app.callback(
    Output('map1', 'figure'),
    [
        Input('map_day', 'value'),
    ]
)
def update_map(map_day):
    day = epidemie_df['day'].unique()[map_day]
    map_df = (epidemie_df[epidemie_df['day'] == day]
              .groupby(['Country/Region'])
              .agg({'Confirmed': 'sum', 'Latitude': 'mean', 'Longitude': 'mean'})
              .reset_index()
             )
    print(map_day)
    print(day)
    print(map_df.head())
    return {
        'data': [
            dict(
                type='scattergeo',
                lon=map_df['Longitude'],
                lat=map_df['Latitude'],
                text=map_df.apply(lambda r: r['Country/Region'] + ' (' + str(r['Confirmed']) + ')', axis=1),
                mode='markers',
                marker=dict(
                    size=np.maximum(map_df['Confirmed'] / 1_000, 5)
                )
            )
        ],
        'layout': dict(
            title=str(day),
            geo=dict(showland=True),
        )
    }
##ne marche pas
@app.callback(
    Output('graph1', 'figure'),
    [
        Input('parameters', 'beta'),
        Input('parameters', 'gamma'),
        Input('Population', 51_470_000),
    ]
)

def sumsq_error(parameters):
    beta, gamma = parameters
    print(parameters)
    print(beta)
    print(gamma)
    
def SIR(t, y):
    S = y[0]
    I = y[1]
    R = y[2]
    print(S)
    print(I)
    print(R)
    return([-beta*S*I, beta*S*I-gamma*I, gamma*I])

    solution_korea = solve_ivp(SIR, [0, 40], [Population, 1, 0], t_eval=np.arange(0, 41, 1))

    return(sum((solution.y[1]-korea_df.loc[2:]['infected'])**2))

if __name__ == '__main__':
    app.run_server(debug=True)

