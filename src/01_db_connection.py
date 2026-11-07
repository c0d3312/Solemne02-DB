import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

#Cargar variables de entorno desde el archivo .env
load_dotenv()

def get_database():
    """Establece la conexión con MongoDB Atlas y retorna la base de datos."""
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise ValueError("No se encontró MONGO_URI en el archivo .env")
    try:
        #Conexión al clúster
        client = MongoClient(uri)
        #Verificar conexión haciendo ping al servidor
        client.admin.command('ping')
        print("Conexión exitosa a MongoDB Atlas.")  
        #Seleccionar/Crear la base de datos del proyecto
        db = client['campus_inteligente']
        return db
    except ConnectionFailure as e:
        print(f"Error de conexión: {e}")
        return None

def setup_schema_validators(db):
    """Aplica validadores de esquema ($jsonSchema) a las colecciones principales."""
    #Validador para Espacios
    espacios_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["nombre", "tipo", "capacidad", "edificio"],
            "properties": {
                "nombre": {"bsonType": "string", "description": "Nombre del espacio (ej: Sala 101)"},
                "tipo": {"bsonType": "string", "enum": ["Aula", "Laboratorio", "Biblioteca", "Espacio Común"]},
                "capacidad": {"bsonType": "int", "minimum": 1, "description": "Capacidad de personas"},
                "edificio": {"bsonType": "string", "description": "Ubicación dentro del campus"}
            }
        }
    }

    #Validador para Dispositivos (Sensores IoT)
    dispositivos_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id_dispositivo", "tipo_sensor", "id_espacio", "estado"],
            "properties": {
                "id_dispositivo": {"bsonType": "string"},
                "tipo_sensor": {"bsonType": "array", "items": {"bsonType": "string"}}, # ej: ["temperatura", "humedad"]
                "id_espacio": {"bsonType": "objectId", "description": "Referencia al espacio asignado"},
                "estado": {"bsonType": "string", "enum": ["Activo", "Inactivo", "Mantenimiento"]}
            }
        }
    }

    #Validador para Mediciones
    mediciones_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id_dispositivo", "fecha_hora"],
            "properties": {
                "id_dispositivo": {"bsonType": "objectId"},
                "fecha_hora": {"bsonType": "date"},
                "lecturas": {
                    "bsonType": "array",
                    "minItems": 1,
                    "items": {
                        "bsonType": "object",
                        "required": ["tipo", "valor", "unidad"],
                        "properties": {
                            "tipo": {"bsonType": "string"},
                            "valor": {"bsonType": ["double", "int", "long", "decimal"]},
                            "unidad": {"bsonType": "string"}
                        }
                    }
                },
                "temperatura": {"bsonType": ["double", "int"]},
                "humedad": {"bsonType": ["double", "int"]},
                "co2": {"bsonType": ["double", "int"]}
            }
        }
    }

    #Aplicar validadores creando o modificando las colecciones
    colecciones = {
        "espacios": espacios_validator,
        "dispositivos": dispositivos_validator,
        "mediciones": mediciones_validator
    }

    for coll_name, validator in colecciones.items():
        try:
            #Intenta crear la colección con el validador
            db.create_collection(coll_name, validator=validator)
            print(f"Colección '{coll_name}' creada con validador.")
        except OperationFailure as e:
            #Si ya existe (código 48), actualiza el validador existente
            if e.code == 48: 
                db.command("collMod", coll_name, validator=validator)
                print(f"Colección '{coll_name}' ya existía. Validador actualizado.")
            else:
                print(f"Error con la colección '{coll_name}': {e}")

if __name__ == "__main__":
    print("Iniciando módulo de conexión y esquemas...")
    db = get_database()
    if db is not None:
        setup_schema_validators(db)
        print("Configuración inicial de la base de datos completada con éxito.")
