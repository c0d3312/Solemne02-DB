def agregaciones(db):
	# promedio y maximo de cada variable ambiental ($match + $group)
	print("PROMEDIO POR VARIABLE: ")
	mediciones = db["mediciones"].aggregate([
		{"$unwind": "$lecturas"},
		{"$match": {"lecturas.tipo": {"$in": ["temperatura", "humedad", "co2", "luminosidad"]}}},
		{"$group": {"_id": "$lecturas.tipo", "promedio": {"$avg": "$lecturas.valor"}, "maximo": {"$max": "$lecturas.valor"}}}
		])
	for i in mediciones:
		print(i)

	# cantidad de variables que mide cada dispositivo activo ($project con campo calculado)
	print("VARIABLES POR DISPOSITIVO: ")
	mide = db["dispositivos"].aggregate([
		{"$match": {"estado": "Activo"}},
		{"$project": {"_id": 0, "id_dispositivo": 1, "cantidad_variables": {"$size": "$tipo_sensor"}}}
		])
	for i in mide:
		print(i)

	# top 3 variables mas monitoreadas ($sort + $limit)
	print("TOP 3 VARIABLES: ")
	variables = db["dispositivos"].aggregate([
		{"$unwind": "$tipo_sensor"},
		{"$group": {"_id": "$tipo_sensor", "dispositivos": {"$sum": 1}}},
		{"$sort": {"dispositivos": -1}},
		{"$limit": 3}
		])
	for i in variables:
		print(i)

if __name__ == "__main__":
	from importlib import import_module
	db = import_module("01_db_connection").get_database()
	if db is None:
		raise ConnectionError("No fue posible conectarse a MongoDB.")
	try:
		agregaciones(db)
	finally:
		db.client.close()