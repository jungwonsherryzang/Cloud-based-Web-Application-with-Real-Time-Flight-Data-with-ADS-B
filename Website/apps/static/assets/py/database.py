import folium
from datetime import datetime
import os
import sys
import pandas as pd
import json
import requests
import math
from signal import signal, SIGINT
from flask import flash
from PIL import Image
from google.cloud import bigquery
bigquery_client = bigquery.Client()

def findLocRange(lat_center,long_center):
    #20km range
    range = 0.09
    lat_min = lat_center - range
    lat_max = lat_center + range
    long_min = long_center - (range/ math.cos(lat_center*math.pi/180))
    long_max = long_center + (range / math.cos(lat_center*math.pi/180))
    return lat_min,lat_max,long_min,long_max

def collectData(lat_min, lat_max, long_min, long_max):
    username = ""
    password = ""
    url_data = (
        f"https://{username}:{password}"
        f"@opensky-network.org/api/states/all?"
        f"&lamin={str(lat_min)}"
        f"&lomin={str(long_min)}"
        f"&lamax={str(lat_max)}"
        f"&lomax={str(long_max)}"
    )
    r = requests.get(url_data)
    r.status_code
    file=r.json()
    
    #Sometimes the api returns 17 columns and sometimes it returns 18
    columns1=['icao24', 'callsign','origin_country','time_position',
            'last_contact','longitude','latitude','baro_altitude',
            'on_ground','velocity','true_track','vertical_rate',
            'sensors','geo_altitude','squawk','spi','position_source']
    columns2=['icao24', 'callsign','origin_country','time_position',
            'last_contact','longitude','latitude','baro_altitude',
            'on_ground','velocity','true_track','vertical_rate',
            'sensors','geo_altitude','squawk','spi','x','y']
    try:
        df=pd.DataFrame(file['states'],columns=columns1)\
                                            .drop(columns=['position_source','sensors','squawk'])\
                                            .assign(obs_time= lambda x: file['time'])
    except:
        df=pd.DataFrame(file['states'],columns=columns2)\
                                            .drop(columns=['x','y','sensors','squawk'])\
                                            .assign(obs_time= lambda x: file['time'])
    df[['time_position','last_contact','obs_time']] = df[['time_position','last_contact','obs_time']].apply(pd.to_datetime, unit='s')
    return df

def cleanDataframe(df):
    df = df.where(pd.notnull(df), None)
    df = df.reset_index(drop=True)
    return df

def connectQuery(df):
    credentials = 'cs540-admin.json'
    os.environ['Google_APPLICATION_CREDENTIALS'] = credentials
    table_id = 'cs540-project.Flights.AllData'
    try:
        df = df.to_gbq(table_id , if_exists='append')
    except:
        flash('There is no new data. Please wait, then try again.')

def main():
    lat_center, long_center = 29.18, -81.05
    lat_min, lat_max, long_min, long_max = findLocRange(lat_center, long_center)
    df = collectData(str(lat_min), str(lat_max), str(long_min), str(long_max))
    df = cleanDataframe(df)
    connectQuery(df)
    return(df)

def pop_data():
    #Runs the data_vis function, which grabs latest opensky data and builds flight map
    data_vis()

    query_job = bigquery_client.query(
        """
        SELECT
            *
        FROM
            `cs540-project.Flights.AllData`
        """
    )
    # Handle query_job result and return to flask to display
    res = query_job.result().to_dataframe()
    cols={'icao24':'ICAO24', 'callsign':'Callsign','origin_country':'Origin',
            'longitude':'Lon','latitude':'Lat','baro_altitude':'Baro-Alt',
            'velocity':'Velocity','true_track':'True-Track',
            'vertical_rate':'Vert Rate','geo_altitude':'Geo-Alt',
            'time_position':'Time/Pos','last_contact':'Last Contact',
            'obs_time':'OBS Time','on_ground':'On Ground?'}
    df=pd.DataFrame(res).drop(columns=['spi']).rename(cols, axis=1)
    return(df)

def data_vis():
    df=main()
    start_coords = (29.18, -81.05)
    flight_map = folium.Map(location=start_coords, zoom_start=11,min_zoom=9,max_zoom=14)
    plane_url='apps/static/assets/img/plane_icon.png'
    r_plane_url='apps/static/assets/img/r_plane.png'
    plane = Image.open(plane_url)
    for i in range(0,len(df)):
        lat = df.loc[i]['latitude']
        lon = df.loc[i]['longitude']
        callsign = df.loc[i]['callsign']
        plane.rotate(df.loc[i]['true_track']).save(r_plane_url)
        new_icon = folium.features.CustomIcon(r_plane_url, icon_size=(16,16), icon_anchor=('center'))
        folium.Marker([lat, lon], popup=callsign, icon=new_icon).add_to(flight_map)
    flight_map.save('apps/templates/home/map.html')