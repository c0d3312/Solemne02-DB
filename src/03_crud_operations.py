def run_crud_operations(db):
    """Ejecuta lecturas, actualizaciones y una eliminacion de demostracion."""
    mediciones = db["mediciones"]
    dispositivos = db["dispositivos"]

    # Recupera una muestra reciente sin traer el identificador interno de MongoDB.
    recientes = list(
        mediciones.find(
            {},
            {"_id": 0, "id_medicion": 1, "fecha_hora": 1, "lecturas": 1},
        )
        .sort("fecha_hora", -1)
        .limit(3)
    )
    print(f"find: se encontraron {len(recientes)} mediciones recientes.")
    for medicion in recientes:
        print(medicion)

    # Simula el cambio de estado de un sensor que requiere mantenimiento.
    resultado_estado = dispositivos.update_one(
        {"id_dispositivo": "SEN-TEMP-101"},
        {
            "$set": {"estado": "Mantenimiento"},
            "$currentDate": {"actualizado_en": True},
        },
    )
    print(
        "update_one: "
        f"coincidencias={resultado_estado.matched_count}, "
        f"modificados={resultado_estado.modified_count}."
    )

    # Marca las mediciones con CO2 sobre 1000 ppm para que sean revisadas.
    resultado_revision = mediciones.update_many(
        {
            "lecturas": {
                "$elemMatch": {"tipo": "co2", "valor": {"$gt": 1000}}
            }
        },
        {
            "$set": {"revision_requerida": True},
            "$currentDate": {"marcada_revision_en": True},
        },
    )
    print(
        "update_many: "
        f"coincidencias={resultado_revision.matched_count}, "
        f"modificadas={resultado_revision.modified_count}."
    )

    # El filtro limita la eliminacion a un registro temporal del conjunto de prueba.
    resultado_eliminacion = mediciones.delete_one(
        {
            "id_medicion": "MED-DEMO-DELETE",
            "etiqueta": "registro_temporal_demo",
        }
    )
    print(
        "delete_one: "
        f"mediciones de demostracion eliminadas={resultado_eliminacion.deleted_count}."
    )


if __name__ == "__main__":
    from importlib import import_module

    db = import_module("01_db_connection").get_database()
    if db is None:
        raise ConnectionError("No fue posible conectarse a MongoDB.")
    try:
        run_crud_operations(db)
    finally:
        db.client.close()
