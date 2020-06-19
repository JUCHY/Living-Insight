CREATE TABLE num_mh_service_building AS (SELECT house_id, COUNT(*) AS num_mental_services FROM house_id_mental_health GROUP BY house_id);
CREATE TABLE total_subway_entrances_building AS (SELECT house_id, COUNT(*) AS subway_entrances FROM building_to_subway GROUP BY house_id);
SELECT house_id, COUNT(*) AS total_collissions, SUM(num_injured) AS total_injured, SUM(num_killed) AS total_killed FROM vehicle_collissions NATURAL JOIN building_to_collissions GROUP BY house_id;
CREATE TABLE vehicle_collission_total_data_building AS (SELECT house_id, COUNT(*) AS total_collissions, SUM(num_injured) AS total_injured, SUM(num_killed) AS total_killed FROM vehicle_collissions NATURAL JOIN building_to_collissions GROUP by house_id);

living_insight=# DELETE FROM vehicle_collissions WHERE collision_id ISNULL;
DELETE 2
living_insight=# ALTER TABLE vehicle_collissions ALTER COLUMN num_injured TYPE INT USING num_injured::integer;
ALTER TABLE