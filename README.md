# Solemne02-DB

Este repositorio contiene el código fuente y la documentación para el diseño e implementación de un sistema de gestión de datos NoSQL basado en MongoDB. El objetivo es centralizar la información de espacios académicos, dispositivos IoT, mediciones ambientales heterogéneas y alertas de un campus universitario.

# Distribución de equipo:
- Adrián Mancilla Carter: Arquitectura del proyecto, conexión a MongoDB y fundamentación teórico. (SCRUM MASTER)
- Ignacio Ampuero: Modelado de datos, seeding masivo de espacio y dispositivos.
- Felipe González: Ingesta de mediciones ambientales y operaciones CRUD (Update/Delete).
- Matías Catalán: Consulta avanzadas y filtros operativos ($and, $or, $regex, operadores relacionales).
- Benjamín Lagos: Analítica de datos mediante pipelines de agregación ($match, $group, $project).
- Iván Herrera: Orquestación de pruebas, validación integral y discusión de resultados.

# Estructura del repositorio:
```text
/
├── .gitignore                 # Archivos ignorados por git (entornos virtuales, credenciales)
├── requirements.txt           # Dependencias del proyecto
├── README.md                  # Documentación principal del repositorio
├── docs/
│   └── informe_tecnico.ipynb  # Informe técnico consolidado (Jupyter Notebook / PDF)
└── src/
    ├── 01_db_connection.py    # Conexión a MongoDB Atlas
    ├── 02_seed_data.py        # Poblamiento de datos iniciales
    ├── 03_crud_operations.py  # Operaciones CRUD y actualizaciones
    ├── 04_query_filters.py    # Consultas avanzadas
    ├── 05_aggregations.py     # Pipelines de agregación
    └── 06_main_runner.py      # Orquestador de ejecución

# Requisitos:
- Python 3.11.+

# Instrucciones de instalación y ejecución:
1. Clonar el repositorio:
  git clone https://github.com/c0d3312/Solemne02-DB.git
  cd Solemne02-DB
2. Crear y activar un entorno virtual:
   python -m venv venv
   venv\Scripts\activate
3. Instalar dependencias
   pip install -r rquirements.txt
4. Configurar variables de entorno:
   Crear un archivo llamado ".env" en la raíz del proyecto (este archivo debe estar ignorado en Git por seguridad) y agregar la cadena de conexión a MongoDB Atlas:
      '''env
       mongosh "mongodb+srv://clustersolemne02db.ebgilud.mongodb.net/" --apiVersion 1 --username <db_username>
5. Ejecutar los scripts
   python src/06_main_runner.py
