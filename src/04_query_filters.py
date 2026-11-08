def filtros(db):
	# espacios con capacidad de mas de 30 
	espacios = db["espacios"].find({"capacidad": {"$gt": 30}})
	for i in espacios:
		print(i)

	# mediciones
	medi = db["mediciones"].find({
		"lecturas.tipo": "temperatura"
		})
	for i in medi:
		print(i)

	# dispositivos que no esten activos
	disp = db["dispositivos"].find({"estado":{"$ne":"Activo"}})
	for i in disp:
		print(i)

if __name__ == "__main__":
	from importlib import import_module # ?????
	db = import_module("01_db_connection").get_database()
	if db is None:
		raise ConnectionError("yorlem")
	try:
		filtros(db)
	finally:
		db.client.close()
