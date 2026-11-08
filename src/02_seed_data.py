import json
from datetime import datetime
from pathlib import Path

# Mapeo entre tipo de lectura y la clave de umbral definida en los espacios
UMBRAL_MAP = {
    "temperatura": {
        "clave": "temperatura_c",
        "tipo_alta": "temperatura_alta",
        "tipo_baja": "temperatura_baja",
        "unidad": "°C",
    },
    "humedad": {
        "clave": "humedad_pct",
        "tipo_alta": "humedad_alta",
        "tipo_baja": "humedad_baja",
        "unidad": "%",
    },
    "co2": {
        "clave": "co2_ppm",
        "tipo_alta": "co2_alto",
        "tipo_baja": None,
        "unidad": "ppm",
    },
    "luminosidad": {
        "clave": "luminosidad_lux",
        "tipo_alta": "luminosidad_alta",
        "tipo_baja": "luminosidad_baja",
        "unidad": "lux",
    },
}


def _calcular_severidad(valor, umbral):
    if "max" in umbral and valor > umbral["max"]:
        exceso_pct = ((valor - umbral["max"]) / umbral["max"]) * 100
        return "Alta" if exceso_pct >= 20 else "Media"

    if "min" in umbral and valor < umbral["min"]:
        defecto_pct = ((umbral["min"] - valor) / umbral["min"]) * 100
        return "Alta" if defecto_pct >= 20 else "Media"

    return "Baja"


def _generar_alertas_medicion(medicion, id_dispositivo, id_espacio, nombre_espacio, umbrales):
    if not umbrales:
        return []

    alertas = []
    for lectura in medicion.get("lecturas", []):
        tipo_sensor = lectura.get("tipo")
        valor = lectura.get("valor")
        config = UMBRAL_MAP.get(tipo_sensor)

        if not config:
            continue

        umbral = umbrales.get(config["clave"])
        if not umbral:
            continue

        tipo_alerta = None
        mensaje = ""

        # Evaluar si supera el límite superior
        if "max" in umbral and valor > umbral["max"]:
            tipo_alerta = config["tipo_alta"]
            mensaje = (
                f"{tipo_sensor.capitalize()} ({valor} {config['unidad']}) "
                f"supera el máximo de {umbral['max']} {config['unidad']} "
                f"en {nombre_espacio}."
            )
        # Evaluar si está por debajo del límite inferior
        elif "min" in umbral and valor < umbral["min"] and config.get("tipo_baja"):
            tipo_alerta = config["tipo_baja"]
            mensaje = (
                f"{tipo_sensor.capitalize()} ({valor} {config['unidad']}) "
                f"está bajo el mínimo de {umbral['min']} {config['unidad']} "
                f"en {nombre_espacio}."
            )

        if tipo_alerta:
            severidad = _calcular_severidad(valor, umbral)
            alertas.append({
                "id_espacio": id_espacio,
                "id_dispositivo": id_dispositivo,
                "id_medicion": medicion["_id"],
                "tipo": tipo_alerta,
                "severidad": severidad,
                "estado": "Activa",
                "fecha_generacion": medicion["fecha_hora"],
                "mensaje": mensaje,
                "valor_registrado": valor,
                "umbral_superado": umbral,
            })

    return alertas


def seed_data(db, sample_data_path=None):
    """Carga espacios, dispositivos y mediciones de ejemplo sin duplicados,

    crea los índices necesarios y genera alertas automáticas cuando una
    medición supera los umbrales ambientales configurados para su espacio.
    """
    data_path = sample_data_path or (
        Path(__file__).resolve().parents[1] / "data" / "sample_data.json"
    )
    with open(data_path, encoding="utf-8") as sample_file:
        sample_data = json.load(sample_file)

    espacios = db["espacios"]
    dispositivos = db["dispositivos"]
    mediciones = db["mediciones"]
    alertas = db["alertas"]

    # Creación de índices
    espacios.create_index("nombre", unique=True)
    dispositivos.create_index("id_dispositivo", unique=True)
    mediciones.create_index(
        "id_medicion",
        unique=True,
        partialFilterExpression={"id_medicion": {"$type": "string"}},
    )

    # Índice compuesto para optimizar consultas de alertas por estado, severidad y fecha
    alertas.create_index(
        [("estado", 1), ("severidad", 1), ("fecha_generacion", -1)],
        name="idx_estado_severidad_fecha",
    )

    # ── 1. Espacios ────────────────────────────────────────────────────────
    nombres_existentes = {
        doc["nombre"] for doc in espacios.find({}, {"nombre": 1, "_id": 0})
    }
    espacios_nuevos = [
        esp for esp in sample_data["espacios"]
        if esp["nombre"] not in nombres_existentes
    ]

    # Demostración de insert_one (primer registro) e insert_many (resto)
    if espacios_nuevos:
        resultado_uno = espacios.insert_one(espacios_nuevos[0])
        print(f"insert_one: espacio '{espacios_nuevos[0]['nombre']}' insertado con id {resultado_uno.inserted_id}.")
        espacios_nuevos = espacios_nuevos[1:]
    else:
        print("insert_one: no hay espacios nuevos para insertar.")

    if espacios_nuevos:
        resultado_masivo = espacios.insert_many(espacios_nuevos)
        print(f"insert_many: {len(resultado_masivo.inserted_ids)} espacios insertados.")
    else:
        print("insert_many: no hay espacios nuevos para insertar.")

    # Mantener atributos al día mediante upsert
    for espacio in sample_data["espacios"]:
        espacios.update_one(
            {"nombre": espacio["nombre"]},
            {"$set": espacio},
            upsert=True,
        )

    # Mapeo de nombres a ObjectIds de espacios
    espacio_ids = {
        esp["nombre"]: espacios.find_one({"nombre": esp["nombre"]}, {"_id": 1})["_id"]
        for esp in sample_data["espacios"]
    }

    # ── 2. Dispositivos ───────────────────────────────────────────────────
    codigos_existentes = {
        doc["id_dispositivo"] for doc in dispositivos.find({}, {"id_dispositivo": 1, "_id": 0})
    }

    documentos_dispositivo = []
    for disp in sample_data["dispositivos"]:
        doc = {k: v for k, v in disp.items() if k != "espacio"}
        doc["id_espacio"] = espacio_ids[disp["espacio"]]
        documentos_dispositivo.append(doc)

    dispositivos_nuevos = [
        doc for doc in documentos_dispositivo
        if doc["id_dispositivo"] not in codigos_existentes
    ]

    if dispositivos_nuevos:
        resultado_uno = dispositivos.insert_one(dispositivos_nuevos[0])
        print(f"insert_one: dispositivo '{dispositivos_nuevos[0]['id_dispositivo']}' insertado con id {resultado_uno.inserted_id}.")
        dispositivos_nuevos = dispositivos_nuevos[1:]
    else:
        print("insert_one: no hay dispositivos nuevos para insertar.")

    if dispositivos_nuevos:
        resultado_masivo = dispositivos.insert_many(dispositivos_nuevos)
        print(f"insert_many: {len(resultado_masivo.inserted_ids)} dispositivos insertados.")
    else:
        print("insert_many: no hay dispositivos nuevos para insertar.")

    for doc in documentos_dispositivo:
        dispositivos.update_one(
            {"id_dispositivo": doc["id_dispositivo"]},
            {"$set": doc},
            upsert=True,
        )

    dispositivo_ids = {
        disp["id_dispositivo"]: dispositivos.find_one({"id_dispositivo": disp["id_dispositivo"]}, {"_id": 1})["_id"]
        for disp in sample_data["dispositivos"]
    }

    # Estructura en memoria para consultar el espacio y umbrales de cada dispositivo rápidamente
    espacios_info = {
        esp["nombre"]: {
            "id": espacio_ids[esp["nombre"]],
            "umbrales": esp.get("umbrales", {}),
        }
        for esp in sample_data["espacios"]
    }

    dispositivos_info = {}
    for disp in sample_data["dispositivos"]:
        d_oid = dispositivo_ids[disp["id_dispositivo"]]
        nombre_esp = disp["espacio"]
        dispositivos_info[d_oid] = {
            "id_espacio": espacios_info[nombre_esp]["id"],
            "espacio_nombre": nombre_esp,
            "umbrales": espacios_info[nombre_esp]["umbrales"],
        }

    # 3. Mediciones y generación de alertas
    documentos_medicion = []
    for med in sample_data["mediciones"]:
        doc = {
            **med,
            "id_dispositivo": dispositivo_ids[med["dispositivo"]],
            "fecha_hora": datetime.fromisoformat(
                med["fecha_hora"].replace("Z", "+00:00")
            ),
        }
        doc.pop("dispositivo")
        documentos_medicion.append(doc)

    ids_medicion = [doc["id_medicion"] for doc in documentos_medicion]
    ids_existentes = {
        doc["id_medicion"]
        for doc in mediciones.find(
            {"id_medicion": {"$in": ids_medicion}},
            {"id_medicion": 1, "_id": 0},
        )
    }

    pendientes = [
        doc for doc in documentos_medicion
        if doc["id_medicion"] not in ids_existentes
    ]

    mediciones_insertadas = []

    # Inserción individual
    if pendientes:
        resultado_uno = mediciones.insert_one(pendientes[0])
        print(f"insert_one: medicion '{pendientes[0]['id_medicion']}' insertada.")
        mediciones_insertadas.append(pendientes[0])
        pendientes = pendientes[1:]
    else:
        print("insert_one: no hay mediciones nuevas para insertar.")

    # Inserción en lote
    if pendientes:
        resultado_masivo = mediciones.insert_many(pendientes)
        print(f"insert_many: {len(resultado_masivo.inserted_ids)} mediciones insertadas.")
        mediciones_insertadas.extend(pendientes)
    else:
        print("insert_many: no hay mediciones nuevas para insertar.")

    # 4. Generación automática de alertas
    # PyMongo asigna automáticamente el campo '_id' a cada documento insertado
    alertas_nuevas = []
    for med in mediciones_insertadas:
        info = dispositivos_info.get(med["id_dispositivo"])
        if not info:
            continue

        alertas_detectadas = _generar_alertas_medicion(
            medicion=med,
            id_dispositivo=med["id_dispositivo"],
            id_espacio=info["id_espacio"],
            nombre_espacio=info["espacio_nombre"],
            umbrales=info["umbrales"],
        )
        alertas_nuevas.extend(alertas_detectadas)

    if alertas_nuevas:
        alertas.insert_many(alertas_nuevas)
        print(f"insert_many: {len(alertas_nuevas)} alerta(s) generada(s) por umbrales superados.")

    # Resumen general de la carga
    print(
        "\nCarga completada:\n"
        f"  - Espacios:     {espacios.count_documents({})}.\n"
        f"  - Dispositivos: {dispositivos.count_documents({})}.\n"
        f"  - Mediciones:   {mediciones.count_documents({})}.\n"
        f"  - Alertas:      {alertas.count_documents({})}.\n"
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
