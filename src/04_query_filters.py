def filtros(db):
	# espacios que sean un laboratorio (con regex)
	print("ESPACIOS (Laboratorios): ")
	espacios = db["espacios"].find(
		{"tipo": {"$regex":"[Ll]aboratorio"}},
		{"nombre":1,"capacidad":1,"_id":0,"tipo":1,"edificio":1}
		)
	for i in espacios:
		print(i)

	# espacios con capacidad de mas de 30 
	print("ESPACIOS: ")
	espacios = db["espacios"].find(
		{"capacidad": {"$gt": 30}},
		{"nombre":1,"capacidad":1,"_id":0,"tipo":1,"edificio":1}
		)
	for i in espacios:
		print(i)

	# mediciones
	print("MEDICIONES: ")
	medi = db["mediciones"].find({
		"lecturas.tipo": "temperatura"
		})
	for i in medi:
		print(i)

	# dispositivos que no esten activos
	print("DISPOSITIVOS: ")
	disp = db["dispositivos"].find(
		{"estado":{"$not": {"$eq":"Activo"}}},
		{'id_dispositivo':1, 'estado':1,'tipo_sensor':1, "_id":0}
		)
	for i in disp:
		print(i)

	# proyección básica
	print("proyección:")
	medi = db["mediciones"].find({}, ["fecha_hora", "lecturas"])
	for i in medi:
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
