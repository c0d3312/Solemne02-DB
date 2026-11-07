import json
from datetime import datetime
from pathlib import Path


def seed_data(db, sample_data_path=None):
    """Carga espacios, dispositivos y mediciones de ejemplo sin duplicarlos."""
    data_path = sample_data_path or (
        Path(__file__).resolve().parents[1] / "data" / "sample_data.json"
    )
    with open(data_path, encoding="utf-8") as sample_file:
        sample_data = json.load(sample_file)

    espacios = db["espacios"]
    dispositivos = db["dispositivos"]
    mediciones = db["mediciones"]

    espacios.create_index("nombre", unique=True)
    dispositivos.create_index("id_dispositivo", unique=True)
    mediciones.create_index(
        "id_medicion",
        unique=True,
        partialFilterExpression={"id_medicion": {"$type": "string"}},
    )

    for espacio in sample_data["espacios"]:
        espacios.update_one(
            {"nombre": espacio["nombre"]},
            {"$set": espacio},
            upsert=True,
        )

    espacio_ids = {
        espacio["nombre"]: espacios.find_one(
            {"nombre": espacio["nombre"]}, {"_id": 1}
        )["_id"]
        for espacio in sample_data["espacios"]
    }

    for dispositivo in sample_data["dispositivos"]:
        documento = {
            key: value
            for key, value in dispositivo.items()
            if key != "espacio"
        }
        documento["id_espacio"] = espacio_ids[dispositivo["espacio"]]
        dispositivos.update_one(
            {"id_dispositivo": documento["id_dispositivo"]},
            {"$set": documento},
            upsert=True,
        )

    dispositivo_ids = {
        dispositivo["id_dispositivo"]: dispositivos.find_one(
            {"id_dispositivo": dispositivo["id_dispositivo"]}, {"_id": 1}
        )["_id"]
        for dispositivo in sample_data["dispositivos"]
    }

    documentos_medicion = []
    for medicion in sample_data["mediciones"]:
        documento = {
            **medicion,
            "id_dispositivo": dispositivo_ids[medicion["dispositivo"]],
            "fecha_hora": datetime.fromisoformat(
                medicion["fecha_hora"].replace("Z", "+00:00")
            ),
        }
        documento.pop("dispositivo")
        documentos_medicion.append(documento)

    ids_medicion = [documento["id_medicion"] for documento in documentos_medicion]
    ids_existentes = {
        documento["id_medicion"]
        for documento in mediciones.find(
            {"id_medicion": {"$in": ids_medicion}},
            {"id_medicion": 1, "_id": 0},
        )
    }
    pendientes = [
        documento
        for documento in documentos_medicion
        if documento["id_medicion"] not in ids_existentes
    ]

    # Demuestra la insercion individual antes de insertar el resto en lote.
    if pendientes:
        mediciones.insert_one(pendientes[0])
        print(f"insert_one: medicion {pendientes[0]['id_medicion']} insertada.")
        pendientes = pendientes[1:]
    else:
        print("insert_one: no hay mediciones nuevas para insertar.")

    # El lote reduce los viajes a MongoDB para las mediciones restantes.
    if pendientes:
        resultado_masivo = mediciones.insert_many(pendientes)
        print(f"insert_many: {len(resultado_masivo.inserted_ids)} mediciones insertadas.")
    else:
        print("insert_many: no hay mediciones nuevas para insertar.")

    print(
        "Carga completada: "
        f"{espacios.count_documents({})} espacios, "
        f"{dispositivos.count_documents({})} dispositivos y "
        f"{mediciones.count_documents({})} mediciones."
    )


if __name__ == "__main__":
    from importlib import import_module

    db = import_module("01_db_connection").get_database()
    if db is None:
        raise ConnectionError("No fue posible conectarse a MongoDB.")
    try:
        seed_data(db)
    finally:
        db.client.close()
