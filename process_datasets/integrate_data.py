
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 06:54:46 2020

@author: joshua
"""

from pyspark.sql import SparkSession
from pyspark.sql import Row
import randomdistribution
from pyspark.sql.functions import udf, struct, asc
from pyspark.sql.types import BooleanType, IntegerType
import computedistance
from pyspark import SparkContext
from pyspark.sql import SQLContext
import sys
import uuid 


sc = SparkContext("local", "SparkFile App")
sqlContext = SQLContext(sc)
sc.addFile("/home/ubuntu/Housing-Insight/process_datasets/computedistance.py")
sc.addFile("/home/ubuntu/Housing-Insight/process_datasets/randomdistribution.py")
address = '11 crooke avenue brooklyn new york'
latlng = computedistance.getLatLong(address)

def handle_building(lat, lng,latlng=latlng):
    latlong2 = [lng, lat ]
    if computedistance.computeDistance(latlng,latlong2) < 3:
        return True
    else:   
        return False

def handle_distance(lat, lng, latlng=latlng):
    latlong2 = [ lng, lat ]
    if computedistance.computeDistance(latlng, latlong2) <1.5:
        return True
    else:
        return False

def find_building_distance(row,latlng=latlng):
    latlong2 = [row['longitude'], row['latitude'] ]
    dist = computedistance.computeDistance(latlng,latlong2)
    newrow = row.asDict()
    newrow["distance"] = dist
    return Row(**newrow)



#removes unneccessary columns from dataset and provides an extra column to keep a unique index

spark = SparkSession \
    .builder \
    .appName("Process to pSqL") \
    .getOrCreate()


buildings = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","final_buildings_set") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()


""" mental_health = spark.read.format("csv") \
    .option("header","true") \
    .option("inferSchema","true") \
    .load("s3a://living-insight-data/Mental_Health_Service_Finder_Data.csv")
    
     """

#define custom functions
_building_udf = udf(handle_building,BooleanType())
_distance_udf = udf(handle_distance, BooleanType())

#filter for buildings within 3 miles of address
buildings = buildings.filter(_building_udf('latitude','longitude'))
buildings.show()
#precinct and community district
buildings_rdd = buildings.rdd.map(find_building_distance)
buildings = buildings_rdd.toDF()
buildings.show()
precinctrow = buildings.orderBy(asc("distance")).take(1)
buildings.orderBy(asc("distance")).limit(1).first()
print("Precinct is")
print()
print(precinctrow[0].precinct)
precinctrow = precinctrow[0]

#mental_health
mh = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","mental_health") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()
id_mh = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","house_id_mental_health") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()


#creates view for buildling, mental health, and link of house_id to mentalhealth_ids
buildings.createOrReplaceTempView("building_view")
mh.createOrReplaceTempView("mental_health")
id_mh.createOrReplaceTempView("housing_id_mental_health")
#query string to join house_ids to mental health institution ids
get_query_ids = 'WITH upd AS ( SELECT * FROM building_view NATURAL JOIN housing_id_mental_health ) SELECT query_id FROM upd'
sqlDF = spark.sql(get_query_ids)
#create view that consists of ids of mental health institutions that pass the criteria
sqlDF.createOrReplaceTempView("query_identifications")
#query string to select all mental health institutions from mental health dataset that much the query_id
get_mh = 'WITH upd AS ( SELECT * FROM mental_health NATURAL JOIN query_identifications) SELECT DISTINCT * FROM upd'
potentialmh = spark.sql(get_mh)
#checks if the chosen mental_health institutions fit the condition
potentialmh.filter(_distance_udf('latitude','longitude'))
#creates house_id for house being added
building_id = uuid.uuid1()
building_id = building_id.hex
#create view from potentialmh and selects queries from it, pairing it with the house_id
potentialmh.createOrReplaceTempView("house_mh")
results = spark.sql("SELECT query_id, '"+building_id+"' AS house_id FROM house_mh")
results.show()
print(building_id)
#subway_entrances
subway_entrances = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","subway_entrances") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

subway = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","building_to_subway") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

subway.createOrReplaceTempView("building_to_subway")
subway_entrances.createOrReplaceTempView("subway_entrances")
#query string to join house_ids to mental health institution ids
get_object_ids = 'WITH upd AS ( SELECT * FROM building_view NATURAL JOIN building_to_subway ) SELECT object_id FROM upd'
sqlDF = spark.sql(get_object_ids)
#create view that consists of ids of subway_entrances institutions that pass the criteria
sqlDF.createOrReplaceTempView("subway_identifications")
#query string to select all mental health institutions from mental health dataset that much the query_id
get_sub = 'WITH upd AS ( SELECT * FROM subway_entrances NATURAL JOIN subway_identifications) SELECT DISTINCT * FROM upd'
potentialsub = spark.sql(get_sub)
#checks if the chosen mental_health institutions fit the condition
potentialsub.filter(_distance_udf('lat','long'))
potentialsub.createOrReplaceTempView("house_sub")
results = spark.sql("SELECT object_id, '"+building_id+"' AS house_id FROM house_sub")
results.show()

#crime

crimes = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","nypd_crime_data") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

crime_ids = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","building_id_to_crime_id") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

crime_ids.createOrReplaceTempView("building_to_crimes")
crimes.createOrReplaceTempView("crime_data")
crime_ids.show()
crimes.show()
#query string to join house_ids to mental health institution ids
get_crime_ids = 'WITH upd AS ( SELECT * FROM building_view NATURAL JOIN building_to_crimes ) SELECT "CMPLNT_NUM" FROM upd'
sqlDF = spark.sql(get_crime_ids)
#create view that consists of ids of mental health institutions that pass the criteria
sqlDF.createOrReplaceTempView("crime_identifications")
sqlDF.show()
#query string to select all mental health institutions from mental health dataset that much the query_id
get_crimes = 'WITH upd AS ( SELECT * FROM crime_data NATURAL JOIN crime_identifications) SELECT DISTINCT * FROM upd'
potentialcrimes = spark.sql(get_crimes)
#checks if the chosen mental_health institutions fit the condition
potentialcrimes.show()
potentialcrimes.filter(_distance_udf('Latitude','Longitude'))
potentialcrimes.createOrReplaceTempView("house_crime")
results = spark.sql("""SELECT "CMPLNT_NUM", '"""+building_id+"""' AS house_id FROM house_crime""")
results.show()


#collissions


vehicle_collissions = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","vehicle_collissions") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

collissions = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","building_to_collissions") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

collissions.createOrReplaceTempView("building_to_collissions")
vehicle_collissions.createOrReplaceTempView("vehicle_collissions")
#query string to join house_ids to vehicle_collissions institution ids
get_collission_ids = 'WITH upd AS ( SELECT * FROM building_view NATURAL JOIN building_to_collissions ) SELECT collision_id FROM upd'
sqlDF = spark.sql(get_collission_ids)
#create view that consists of ids of mental health institutions that pass the criteria
sqlDF.createOrReplaceTempView("collission_ids")
#query string to select all collissions that match the query_id
get_col = 'WITH upd AS ( SELECT * FROM vehicle_collissions NATURAL JOIN collission_ids) SELECT DISTINCT * FROM upd'
potentialcol = spark.sql(get_col)
#checks if the chosen vehicle_collissions fit the condition
potentialcol.filter(_distance_udf('lat','long'))
potentialcol.createOrReplaceTempView("house_collission")
results = spark.sql("SELECT collision_id, '"+building_id+"' AS house_id FROM house_collission")
results.show()






#air_quality
def handle_air(geo_type_name, geo_entity_name, entity_id, building=precinctrow):
    if geo_type_name == "Borough":
        if building.borough.lower() == geo_entity_name.lower():
            return True 
        else:
            return False
    if building.community_district == geo_entity_id:
        print("worked")
        return True
    else:
        return False

_air_udf = udf(handle_air, BooleanType())


air_quality = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","air_quality") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

building_air = spark.read \
    .format("jdbc") \
    .option("url","jdbc:postgresql://localhost:5432/living_insight") \
    .option("dbtable","building_to_air_quality") \
    .option("user","postgres") \
    .option("password", "postgres") \
    .load()

building_air.createOrReplaceTempView("building_to_air_quality")
air_quality.createOrReplaceTempView("air_quality")
#query string to join house_ids to mental health institution ids
get_data_ids = 'WITH upd AS ( SELECT * FROM building_view NATURAL JOIN building_to_air_quality ) SELECT indicator_data_id FROM upd'
sqlDF = spark.sql(get_data_ids)
#create view that consists of ids of mental health institutions that pass the criteria
sqlDF.createOrReplaceTempView("data_ids")
#query string to select all mental health institutions from mental health dataset that much the query_id
get_data = 'WITH upd AS ( SELECT * FROM air_quality NATURAL JOIN data_ids) SELECT DISTINCT * FROM upd'
potential_datapoints = spark.sql(get_data)
#checks if the chosen mental_health institutions fit the condition
potential_datapoints.filter(_air_udf('geo_type_name','geo_entity_name','geo_entity_id'))
potential_datapoints.createOrReplaceTempView("house_air")
results = spark.sql("SELECT indicator_data_id, '"+building_id+"' AS house_id FROM house_air")
results.show()


spark.stop()
