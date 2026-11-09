"""
07_integration_tests.py - Pruebas integrales y verificación de ejecución en MongoDB Atlas.
Responsable: Iván Herrera.

Ejecuta el flujo completo del proyecto contra una base de PRUEBA en Atlas
(validadores -> carga -> CRUD -> consultas -> agregaciones) y verifica que:
  - la conexión es realmente a un clúster de Atlas,
  - los validadores $jsonSchema existen y rechazan documentos inválidos,
  - el esquema acepta sensores/lecturas nuevas (flexibilidad),
  - la carga es idempotente (re-ejecutar no duplica datos),
  - no hay referencias huérfanas entre colecciones,
  - las alertas son coherentes con los umbrales del espacio,
  - las operaciones CRUD producen el efecto esperado,
  - los scripts de consultas y agregaciones se ejecutan sin errores,
  - los índices se usan (explain),
  - el código cubre los operadores que exige la rúbrica.

Al final genera docs/evidencias/reporte_pruebas_<fecha>.md (evidencia para el informe).

Uso (desde la raíz del repositorio, con el .env configurado):
    python src/07_integration_tests.py              # base de prueba: campus_inteligente_test
    python src/07_integration_tests.py --mantener   # no borra la base de prueba al terminar
    python src/07_integration_tests.py --db otra_base_de_prueba
"""
import argparse
import contextlib
import inspect
import io
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src"
sys.path.insert(0, str(SRC))

BASE_PRINCIPAL = "campus_inteligente"
COLECCIONES = ["espacios", "dispositivos", "mediciones", "alertas"]

parser = argparse.ArgumentParser(description="Pruebas integrales Solemne 02 (MongoDB Atlas)")
parser.add_argument("--db", default="campus_inteligente_test", help="base de datos de prueba")
parser.add_argument("--mantener", action="store_true", help="no borrar la base de prueba al final")
parser.add_argument("--permitir-principal", action="store_true",
                    help="permite usar la base principal (se BORRARÁ su contenido)")
ARGS = parser.parse_args()

if ARGS.db == BASE_PRINCIPAL and not ARGS.permitir_principal:
    sys.exit(f"Por seguridad no se ejecutan pruebas sobre '{BASE_PRINCIPAL}' "
             "(se borran sus colecciones). Use otra base o --permitir-principal.")

# Se fija la base ANTES de importar 01_db_connection: load_dotenv no sobrescribe variables existentes.
os.environ["MONGO_DB"] = ARGS.db

import pymongo  # noqa: E402
from pymongo.errors import WriteError  # noqa: E402

conexion = import_module("01_db_connection")
seed = import_module("02_seed_data")
crud = import_module("03_crud_operations")

SAMPLE = json.loads((RAIZ / "data" / "sample_data.json").read_text(encoding="utf-8"))
RESULTADOS = []


# --------------------------------------------------------------------------- utilidades
def ejecutar(codigo, descripcion, fn):
    """Ejecuta una prueba, captura su salida por consola y registra el resultado.
    La función devuelve (estado, detalle) con estado OK | ADVERTENCIA | FALLA."""
    buffer = io.StringIO()
    inicio = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buffer):
            estado, detalle = fn()
    except AssertionError as e:
        estado, detalle = "FALLA", str(e)
    except Exception as e:  # cualquier error inesperado también es evidencia
        estado, detalle = "FALLA", f"{type(e).__name__}: {e}"
    ms = (time.perf_counter() - inicio) * 1000
    RESULTADOS.append({"codigo": codigo, "descripcion": descripcion, "estado": estado,
                       "detalle": detalle, "ms": round(ms), "salida": buffer.getvalue()})
    etiqueta = {"OK": "[OK]   ", "ADVERTENCIA": "[ADV]  ", "FALLA": "[FALLA]"}[estado]
    print(f"{etiqueta} {codigo} {descripcion} ({ms:.0f} ms)\n          -> {detalle}")


def conteos():
    return {c: db[c].count_documents({}) for c in COLECCIONES}


def huerfanos(coleccion, campo, destino):
    """Cuenta documentos cuyo `campo` apunta a un _id inexistente en `destino` ($lookup)."""
    pipeline = [
        {"$match": {campo: {"$exists": True}}},
        {"$lookup": {"from": destino, "localField": campo, "foreignField": "_id", "as": "ref"}},
        {"$match": {"ref": {"$size": 0}}},
        {"$count": "n"},
    ]
    r = list(db[coleccion].aggregate(pipeline))
    return r[0]["n"] if r else 0


def etapas_plan(plan):
    """Extrae recursivamente las etapas (IXSCAN, COLLSCAN, ...) de un plan de explain()."""
    salida = []
    if isinstance(plan, dict):
        if "stage" in plan:
            salida.append(plan["stage"] + (f"({plan['indexName']})" if "indexName" in plan else ""))
        for v in plan.values():
            salida += etapas_plan(v)
    elif isinstance(plan, list):
        for v in plan:
            salida += etapas_plan(v)
    return salida


def funciones_publicas(modulo):
    """Funciones definidas en el módulo que reciben un único parámetro (db)."""
    return [f for n, f in inspect.getmembers(modulo, inspect.isfunction)
            if f.__module__ == modulo.__name__ and not n.startswith("_")
            and len(inspect.signature(f).parameters) == 1]


def alertas_esperadas():
    """Calcula, de forma independiente al seed, cuántas alertas deben generarse."""
    disp = {d["id_dispositivo"]: d for d in SAMPLE["dispositivos"]}
    esp = {e["nombre"]: e for e in SAMPLE["espacios"]}
    total = 0
    for m in SAMPLE["mediciones"]:
        umbrales = esp[disp[m["dispositivo"]]["espacio"]].get("umbrales", {})
        for lectura in m["lecturas"]:
            cfg = seed.UMBRAL_MAP.get(lectura["tipo"])
            u = umbrales.get(cfg["clave"]) if cfg else None
            if not u:
                continue
            if "max" in u and lectura["valor"] > u["max"]:
                total += 1
            elif "min" in u and lectura["valor"] < u["min"] and cfg.get("tipo_baja"):
                total += 1
    return total


# --------------------------------------------------------------------------- pruebas
def t01_conexion():
    info = db.client.server_info()
    nodos = sorted(f"{h}:{p}" for h, p in db.client.nodes)
    assert any("mongodb.net" in n for n in nodos), f"La conexión no apunta a Atlas: {nodos}"
    return "OK", f"MongoDB {info['version']} en Atlas, {len(nodos)} nodo(s), base '{db.name}'"


def t02_validadores():
    for c in db.list_collection_names():          # base de prueba limpia
        db.drop_collection(c)
    conexion.setup_schema_validators(db)
    validadores = {c["name"]: c.get("options", {}).get("validator") for c in db.list_collections()}
    faltan = [c for c in COLECCIONES if not validadores.get(c)]
    assert not faltan, f"Colecciones sin validador: {faltan}"
    return "OK", "4 colecciones creadas con $jsonSchema"


def t03_carga():
    seed.seed_data(db)
    c = conteos()
    esperado = {"espacios": len(SAMPLE["espacios"]), "dispositivos": len(SAMPLE["dispositivos"]),
                "mediciones": len(SAMPLE["mediciones"]), "alertas": alertas_esperadas()}
    assert c == esperado, f"Conteos {c} distintos de lo esperado {esperado}"
    estado = "OK"
    detalle = f"Conteos correctos {c}"
    if c["mediciones"] < 50:
        estado = "ADVERTENCIA"
        detalle += (" | Sólo hay pocas mediciones: el set de prueba es chico para "
                    "demostrar consultas y agregaciones")
    return estado, detalle


def t04_setup_reejecutable():
    try:
        conexion.setup_schema_validators(db)
    except Exception as e:
        raise AssertionError(
            f"setup_schema_validators falla al re-ejecutarse ({type(e).__name__}: {e}). "
            "En PyMongo 4.x create_collection lanza CollectionInvalid si la colección existe; "
            "capturar CollectionInvalid o usar create_collection(..., check_exists=False)")
    return "OK", "Los validadores se pueden re-aplicar sin error"


def t05_carga_idempotente():
    antes = conteos()
    seed.seed_data(db)
    despues = conteos()
    assert antes == despues, f"La segunda carga duplicó datos: {antes} -> {despues}"
    return "OK", f"Segunda carga sin duplicados {despues}"


def t06_validadores_rechazan():
    esp_id = db.espacios.find_one()["_id"]
    disp_id = db.dispositivos.find_one()["_id"]
    ahora = datetime.now(timezone.utc)
    casos = [
        ("espacios", {"nombre": "TEST tipo invalido", "tipo": "Cocina", "capacidad": 10, "edificio": "X"},
         "tipo fuera del enum"),
        ("espacios", {"nombre": "TEST sin capacidad", "tipo": "Aula", "edificio": "X"}, "falta capacidad"),
        ("dispositivos", {"id_dispositivo": "TEST-1", "tipo_sensor": ["ruido"], "id_espacio": esp_id,
                          "estado": "Roto"}, "estado fuera del enum"),
        ("dispositivos", {"id_dispositivo": "TEST-2", "tipo_sensor": ["ruido"], "id_espacio": "Aula 101",
                          "estado": "Activo"}, "id_espacio no es ObjectId"),
        ("mediciones", {"id_dispositivo": disp_id,
                        "lecturas": [{"tipo": "co2", "valor": 500, "unidad": "ppm"}]}, "sin fecha_hora"),
        ("mediciones", {"id_dispositivo": disp_id, "fecha_hora": ahora, "lecturas": []}, "lecturas vacía"),
        ("mediciones", {"id_dispositivo": disp_id, "fecha_hora": ahora,
                        "lecturas": [{"tipo": "temperatura", "valor": "22"}]}, "valor texto y sin unidad"),
        ("alertas", {"id_espacio": esp_id, "id_dispositivo": disp_id, "tipo": "co2_alto",
                     "severidad": "Extrema", "estado": "Activa", "fecha_generacion": ahora,
                     "mensaje": "test"}, "severidad fuera del enum"),
    ]
    aceptados = []
    for coleccion, doc, motivo in casos:
        try:
            r = db[coleccion].insert_one(doc)
            aceptados.append(f"{coleccion}: {motivo}")
            db[coleccion].delete_one({"_id": r.inserted_id})      # limpieza controlada
        except WriteError as e:
            print(f"rechazado ({coleccion}, {motivo}) -> código {e.code}")
            assert e.code == 121, f"Error inesperado {e.code} en {coleccion}"
    assert not aceptados, f"El validador ACEPTÓ documentos inválidos: {aceptados}"
    return "OK", f"{len(casos)}/{len(casos)} documentos inválidos rechazados (código 121)"


def t07_flexibilidad():
    esp_id = db.espacios.find_one({"tipo": "Biblioteca"}) or db.espacios.find_one()
    nuevo = db.dispositivos.insert_one({
        "id_dispositivo": "TEST-RUIDO-01", "tipo_sensor": ["ruido"], "id_espacio": esp_id["_id"],
        "estado": "Activo", "especificaciones": {"modelo": "WS302", "rango_db": [30, 130], "ponderacion": "A"}})
    med = db.mediciones.insert_one({
        "id_medicion": "TEST-MED-RUIDO", "id_dispositivo": nuevo.inserted_id,
        "fecha_hora": datetime.now(timezone.utc),
        "lecturas": [{"tipo": "ruido", "valor": 48.5, "unidad": "dB"}]})
    encontrado = db.mediciones.count_documents({"lecturas.tipo": "ruido"})
    db.mediciones.delete_one({"_id": med.inserted_id})
    db.dispositivos.delete_one({"_id": nuevo.inserted_id})
    assert encontrado == 1, "No se pudo consultar la lectura nueva"
    return "OK", "Sensor y lectura de un tipo nuevo ('ruido', dB) aceptados sin cambiar el esquema"


def _integridad():
    checks = {
        "dispositivos.id_espacio -> espacios": huerfanos("dispositivos", "id_espacio", "espacios"),
        "mediciones.id_dispositivo -> dispositivos": huerfanos("mediciones", "id_dispositivo", "dispositivos"),
        "alertas.id_espacio -> espacios": huerfanos("alertas", "id_espacio", "espacios"),
        "alertas.id_dispositivo -> dispositivos": huerfanos("alertas", "id_dispositivo", "dispositivos"),
        "alertas.id_medicion -> mediciones": huerfanos("alertas", "id_medicion", "mediciones"),
    }
    for k, v in checks.items():
        print(f"{k}: {v} huérfano(s)")
    malos = {k: v for k, v in checks.items() if v}
    assert not malos, f"Referencias huérfanas: {malos}"
    return "OK", "0 referencias huérfanas en 5 relaciones"


def t09_coherencia_alertas():
    dispositivos = {d["_id"]: d for d in db.dispositivos.find({}, {"id_espacio": 1})}
    problemas = []
    for a in db.alertas.find():
        u, v = a.get("umbral_superado", {}), a.get("valor_registrado")
        if "max" in u and v > u["max"]:
            desvio = (v - u["max"]) / u["max"] * 100
        elif "min" in u and v < u["min"]:
            desvio = (u["min"] - v) / u["min"] * 100
        else:
            problemas.append(f"{a['_id']}: valor {v} no supera {u}")
            continue
        sev = "Alta" if desvio >= 20 else "Media"
        if a["severidad"] != sev:
            problemas.append(f"{a['_id']}: severidad {a['severidad']} pero desvío {desvio:.1f}% -> {sev}")
        if dispositivos.get(a["id_dispositivo"], {}).get("id_espacio") != a["id_espacio"]:
            problemas.append(f"{a['_id']}: id_espacio no coincide con el del dispositivo")
        print(f"{a['tipo']}: valor {v}, umbral {u}, desvío {desvio:.1f}% -> {a['severidad']}")
    assert not problemas, "; ".join(problemas)
    return "OK", f"{db.alertas.count_documents({})} alerta(s) coherentes con umbral y severidad"


def t10_crud():
    filtro_co2 = {"lecturas": {"$elemMatch": {"tipo": "co2", "valor": {"$gt": 1000}}}}
    co2_alto = db.mediciones.count_documents(filtro_co2)
    total_antes = db.mediciones.count_documents({})
    demo_antes = db.mediciones.count_documents({"id_medicion": "MED-DEMO-DELETE"})

    crud.run_crud_operations(db)

    problemas = []
    if db.dispositivos.count_documents({"actualizado_en": {"$exists": True}}) == 0:
        problemas.append("update_one no modificó ningún dispositivo (¿el id_dispositivo del filtro "
                         "existe en sample_data.json?)")
    marcadas = db.mediciones.count_documents({"revision_requerida": True})
    if marcadas != co2_alto:
        problemas.append(f"update_many marcó {marcadas} mediciones, se esperaban {co2_alto}")
    if db.mediciones.count_documents({"id_medicion": "MED-DEMO-DELETE"}) != 0:
        problemas.append("delete_one no eliminó MED-DEMO-DELETE")
    if db.mediciones.count_documents({}) != total_antes - demo_antes:
        problemas.append("delete_one eliminó más documentos de los esperados")
    if problemas:
        return "FALLA", "; ".join(problemas)
    return "OK", (f"update_one OK, update_many marcó {marcadas} medición(es) con CO2>1000, "
                  f"delete_one eliminó {demo_antes} registro demo")


def t12_modulo(nombre_modulo):
    def prueba():
        try:
            modulo = import_module(nombre_modulo)
        except Exception as e:
            raise AssertionError(f"No se pudo importar {nombre_modulo}.py: {e}")
        funciones = funciones_publicas(modulo)
        if not funciones:
            return "ADVERTENCIA", f"{nombre_modulo}.py no tiene funciones ejecutables (¿aún vacío?)"
        for f in funciones:
            print(f"### {f.__name__}(db)")
            f(db)
        return "OK", f"Ejecutadas sin error: {[f.__name__ for f in funciones]}"
    return prueba


def t14_cobertura():
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in sorted(SRC.glob("0[1-6]_*.py")))
    requisitos = {
        "CRUD": ["insert_one", "insert_many", ".find(", "update_one", "update_many", "delete_"],
        "Filtros": ["$and", "$or", "$not", "$gt", "$lt", "$eq", "$regex", ".sort("],
        "Agregación": [".aggregate(", "$match", "$group", "$project", "$sort", "$limit"],
    }
    faltan = {g: [t for t in toks if t not in codigo] for g, toks in requisitos.items()}
    faltan = {g: v for g, v in faltan.items() if v}
    ops_update = sorted(set(re.findall(r'"(\$(?:set|unset|inc|push|pull|addToSet|currentDate|mul|rename))"',
                                       (SRC / "03_crud_operations.py").read_text(encoding="utf-8"))))
    print("Operadores de actualización en 03:", ops_update)
    if len(ops_update) < 2:
        faltan["Operadores update (>=2)"] = ops_update
    if faltan:
        return "ADVERTENCIA", f"Elementos de la rúbrica que aún no aparecen en el código: {faltan}"
    return "OK", "Todos los operadores exigidos por la rúbrica aparecen en src/"


def t15_indices():
    indices = {c: [i["name"] for i in db[c].list_indexes()] for c in COLECCIONES}
    print(json.dumps(indices, indent=2))
    plan = (db.alertas.find({"estado": "Activa", "severidad": "Alta"})
            .sort("fecha_generacion", -1).explain())
    etapas = etapas_plan(plan["queryPlanner"]["winningPlan"])
    print("Plan alertas:", etapas)
    if not any(e.startswith("IXSCAN") for e in etapas):
        return "ADVERTENCIA", f"La consulta de alertas no usa índice: {etapas}"
    return "OK", f"Consulta de alertas activas usa índice: {etapas}"


# --------------------------------------------------------------------------- reporte
def escribir_reporte(inicio, servidor):
    carpeta = RAIZ / "docs" / "evidencias"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"reporte_pruebas_{inicio:%Y%m%d_%H%M}.md"
    resumen = {e: sum(r["estado"] == e for r in RESULTADOS) for e in ("OK", "ADVERTENCIA", "FALLA")}
    lineas = [
        "# Reporte de pruebas integrales - Solemne 02",
        "",
        f"- Fecha de ejecución: {inicio:%Y-%m-%d %H:%M:%S}",
        f"- Servidor: MongoDB {servidor} (Atlas) - base de prueba `{db.name}`",
        f"- Python {platform.python_version()} - PyMongo {pymongo.version} - {platform.system()}",
        f"- Resultado: **{resumen['OK']} OK, {resumen['ADVERTENCIA']} advertencias, {resumen['FALLA']} fallas**",
        "",
        "| Código | Prueba | Resultado | Tiempo (ms) | Detalle |",
        "|---|---|---|---|---|",
    ]
    for r in RESULTADOS:
        detalle = r["detalle"].replace("|", "/").replace("\n", " ")
        lineas.append(f"| {r['codigo']} | {r['descripcion']} | {r['estado']} | {r['ms']} | {detalle} |")
    lineas += ["", "## Salida capturada de cada prueba", ""]
    for r in RESULTADOS:
        salida = r["salida"].strip().splitlines()
        if len(salida) > 60:
            salida = salida[:60] + [f"... ({len(salida) - 60} líneas más)"]
        lineas += [f"### {r['codigo']} - {r['descripcion']}", "```text", *(salida or ["(sin salida)"]), "```", ""]
    archivo.write_text("\n".join(lineas), encoding="utf-8")
    return archivo, resumen


# --------------------------------------------------------------------------- main
if __name__ == "__main__":
    inicio = datetime.now()
    db = conexion.get_database()
    if db is None:
        sys.exit("No fue posible conectarse a MongoDB Atlas (revise MONGO_URI y Network Access).")
    servidor = db.client.server_info()["version"]
    print(f"\nPruebas integrales sobre la base '{db.name}'\n")
    try:
        ejecutar("P01", "Conexión a MongoDB Atlas", t01_conexion)
        ejecutar("P02", "Creación de colecciones con validadores", t02_validadores)
        ejecutar("P03", "Carga inicial de datos (seed)", t03_carga)
        ejecutar("P04", "Re-ejecución de validadores", t04_setup_reejecutable)
        ejecutar("P05", "Carga idempotente (sin duplicados)", t05_carga_idempotente)
        ejecutar("P06", "Validadores rechazan documentos inválidos", t06_validadores_rechazan)
        ejecutar("P07", "Flexibilidad: sensor y lectura de tipo nuevo", t07_flexibilidad)
        ejecutar("P08", "Integridad referencial tras la carga", _integridad)
        ejecutar("P09", "Coherencia de alertas con umbrales", t09_coherencia_alertas)
        ejecutar("P10", "Operaciones CRUD (03_crud_operations)", t10_crud)
        ejecutar("P11", "Integridad referencial tras CRUD", _integridad)
        ejecutar("P12", "Consultas de filtrado (04_query_filters)", t12_modulo("04_query_filters"))
        ejecutar("P13", "Pipelines de agregación (05_aggregations)", t12_modulo("05_aggregations"))
        ejecutar("P14", "Cobertura de operadores exigidos por la rúbrica", t14_cobertura)
        ejecutar("P15", "Índices y plan de ejecución (explain)", t15_indices)
    finally:
        archivo, resumen = escribir_reporte(inicio, servidor)
        if not ARGS.mantener:
            for c in db.list_collection_names():
                db.drop_collection(c)
        db.client.close()
    print(f"\nResumen: {resumen['OK']} OK, {resumen['ADVERTENCIA']} advertencias, {resumen['FALLA']} fallas")
    print(f"Reporte: {archivo.relative_to(RAIZ)}")
    sys.exit(1 if resumen["FALLA"] else 0)
