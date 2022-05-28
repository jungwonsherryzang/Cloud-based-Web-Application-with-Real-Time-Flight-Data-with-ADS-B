# -*- coding: utf-8 -*-
"""

By Michael Fornito, Kyrsh Rejendran, Thomas Fiello

"""
#!pip3 install flightradar24
#import mysql.connector
#!pip3 install --upgrade google-cloud
#!pip3 install --upgrade google-cloud-storage
#!pip3 install --upgrade google-cloud-bigquery
#!pip install --upgrade pandas_gbq
#!pip install pyarrow
from google.cloud import bigquery
import pandas as pd
import flightradar24
import requests
import math
import os
from datetime import datetime
fr = fr = flightradar24.Api()

def findAirportLoc(name):
    #FlightRadar24
    dataAirport = fr.get_airports()
    listAirport= dataAirport['rows']
    for airport in listAirport:
        if(name in airport['name']):
            return airport['lat'], airport['lon']
        
def findLocRange(lat_center,long_center):
    #20km range
    range = 0.09
    lat_min = lat_center - range
    lat_max = lat_center + range
    long_min = long_center - (range/ math.cos(lat_center*math.pi/180))
    long_max = long_center + (range / math.cos(lat_center*math.pi/180))
    return lat_min,lat_max,long_min,long_max

def collectData(lat_min, lat_max, long_min, long_max):
    r = requests.get('https://opensky-network.org/api/states/all?lamin='+lat_min+'&lomin='+long_min+'&lamax='+lat_max+'&lomax='+long_max)
    r.status_code
    file=r.json()
    df=pd.DataFrame(file['states'],columns=['icao24', 'callsign','origin_country','time_position','last_contact',
                                            'longitude','latitude','baro_altitude','on_ground','velocity',
                                            'true_track','vertical_rate','sensors','geo_altitude','squawk','spi','x','y']).drop(columns=['x','y']).assign(obs_time= lambda x: file['time'])
    df[['time_position','last_contact','obs_time']] = df[['time_position','last_contact','obs_time']].apply(pd.to_datetime, unit='s')
    #df.set_index(['obs_time', 'callsign'],inplace=True)
    return df

def cleanDataframe(df):
    df = df.drop(columns=['sensors','squawk'])
    df = df.where(pd.notnull(df), None)
    df = df.reset_index(drop=True)
    return df

def connectQuery(df):
    credentials = 'P:\GitHub\ERAU_CS540_Team4\cs540-admin.json'
    os.environ['Google_APPLICATION_CREDENTIALS'] = credentials
    client = bigquery.Client()
    table_id = 'cs540-project.Flights.AllData'
    df = df.to_gbq(table_id , if_exists='append')
    
def createTest(): #Test the database on the test table
    credentials = 'P:\GitHub\ERAU_CS540_Team4\cs540-admin.json'
    os.environ['Google_APPLICATION_CREDENTIALS'] = credentials
    client = bigquery.Client()
    table_id = 'cs540-project.Flights.Test'
    rows_to_insert = [
        {u'Name' : 'Mike', u'Age': 23},
        {u'Name' : 'DummyData', u'Age': 24},
        ]
    errors = client.insert_rows_json(table_id,rows_to_insert)  

def main():
    
    lat_center, long_center = findAirportLoc('Daytona')
    lat_min, lat_max, long_min, long_max = findLocRange(lat_center, long_center)
    df = collectData(str(lat_min), str(lat_max), str(long_min), str(long_max))
    df = cleanDataframe(df)
    connectQuery(df)
    
main()


