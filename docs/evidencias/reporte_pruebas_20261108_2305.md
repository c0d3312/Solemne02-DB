# Reporte de pruebas integrales - Solemne 02

- Fecha de ejecución: 2026-11-08 23:05:32
- Servidor: MongoDB 8.0.37 (Atlas) - base de prueba `campus_inteligente_test`
- Python 3.11.9 - PyMongo 4.6.1 - Windows
- Resultado: **11 OK, 2 advertencias, 2 fallas**

| Código | Prueba | Resultado | Tiempo (ms) | Detalle |
|---|---|---|---|---|
| P01 | Conexión a MongoDB Atlas | OK | 185 | MongoDB 8.0.37 en Atlas, 3 nodo(s), base 'campus_inteligente_test' |
| P02 | Creación de colecciones con validadores | OK | 1440 | 4 colecciones creadas con $jsonSchema |
| P03 | Carga inicial de datos (seed) | ADVERTENCIA | 13771 | Conteos correctos {'espacios': 12, 'dispositivos': 24, 'mediciones': 5, 'alertas': 1} / Sólo hay pocas mediciones: el set de prueba es chico para demostrar consultas y agregaciones |
| P04 | Re-ejecución de validadores | FALLA | 131 | setup_schema_validators falla al re-ejecutarse (CollectionInvalid: collection espacios already exists). En PyMongo 4.x create_collection lanza CollectionInvalid si la colección existe; capturar CollectionInvalid o usar create_collection(..., check_exists=False) |
| P05 | Carga idempotente (sin duplicados) | OK | 14201 | Segunda carga sin duplicados {'espacios': 12, 'dispositivos': 24, 'mediciones': 5, 'alertas': 1} |
| P06 | Validadores rechazan documentos inválidos | OK | 1325 | 8/8 documentos inválidos rechazados (código 121) |
| P07 | Flexibilidad: sensor y lectura de tipo nuevo | OK | 810 | Sensor y lectura de un tipo nuevo ('ruido', dB) aceptados sin cambiar el esquema |
| P08 | Integridad referencial tras la carga | OK | 779 | 0 referencias huérfanas en 5 relaciones |
| P09 | Coherencia de alertas con umbrales | OK | 614 | 1 alerta(s) coherentes con umbral y severidad |
| P10 | Operaciones CRUD (03_crud_operations) | FALLA | 1726 | update_one no modificó ningún dispositivo (¿el id_dispositivo del filtro existe en sample_data.json?) |
| P11 | Integridad referencial tras CRUD | OK | 688 | 0 referencias huérfanas en 5 relaciones |
| P12 | Consultas de filtrado (04_query_filters) | OK | 685 | Ejecutadas sin error: ['filtros'] |
| P13 | Pipelines de agregación (05_aggregations) | OK | 409 | Ejecutadas sin error: ['agregaciones'] |
| P14 | Cobertura de operadores exigidos por la rúbrica | ADVERTENCIA | 6 | Elementos de la rúbrica que aún no aparecen en el código: {'Filtros': ['$and', '$or', '$lt']} |
| P15 | Índices y plan de ejecución (explain) | OK | 665 | Consulta de alertas activas usa índice: ['FETCH', 'IXSCAN(idx_estado_severidad_fecha)'] |

## Salida capturada de cada prueba

### P01 - Conexión a MongoDB Atlas
```text
(sin salida)
```

### P02 - Creación de colecciones con validadores
```text
Colección 'espacios' creada con validador.
Colección 'dispositivos' creada con validador.
Colección 'mediciones' creada con validador.
Colección 'alertas' creada con validador.
```

### P03 - Carga inicial de datos (seed)
```text
insert_one: espacio 'Aula 101' insertado con id 6af12a70b10457a03ede30c8.
insert_many: 11 espacios insertados.
insert_one: dispositivo 'SEN-TH-001' insertado con id 6af12a74b10457a03ede30d4.
insert_many: 23 dispositivos insertados.
insert_one: medicion 'MED-001' insertada.
insert_many: 4 mediciones insertadas.
insert_many: 1 alerta(s) generada(s) por umbrales superados.

Carga completada:
  - Espacios:     12.
  - Dispositivos: 24.
  - Mediciones:   5.
  - Alertas:      1.
```

### P04 - Re-ejecución de validadores
```text
(sin salida)
```

### P05 - Carga idempotente (sin duplicados)
```text
insert_one: no hay espacios nuevos para insertar.
insert_many: no hay espacios nuevos para insertar.
insert_one: no hay dispositivos nuevos para insertar.
insert_many: no hay dispositivos nuevos para insertar.
insert_one: no hay mediciones nuevas para insertar.
insert_many: no hay mediciones nuevas para insertar.

Carga completada:
  - Espacios:     12.
  - Dispositivos: 24.
  - Mediciones:   5.
  - Alertas:      1.
```

### P06 - Validadores rechazan documentos inválidos
```text
rechazado (espacios, tipo fuera del enum) -> código 121
rechazado (espacios, falta capacidad) -> código 121
rechazado (dispositivos, estado fuera del enum) -> código 121
rechazado (dispositivos, id_espacio no es ObjectId) -> código 121
rechazado (mediciones, sin fecha_hora) -> código 121
rechazado (mediciones, lecturas vacía) -> código 121
rechazado (mediciones, valor texto y sin unidad) -> código 121
rechazado (alertas, severidad fuera del enum) -> código 121
```

### P07 - Flexibilidad: sensor y lectura de tipo nuevo
```text
(sin salida)
```

### P08 - Integridad referencial tras la carga
```text
dispositivos.id_espacio -> espacios: 0 huérfano(s)
mediciones.id_dispositivo -> dispositivos: 0 huérfano(s)
alertas.id_espacio -> espacios: 0 huérfano(s)
alertas.id_dispositivo -> dispositivos: 0 huérfano(s)
alertas.id_medicion -> mediciones: 0 huérfano(s)
```

### P09 - Coherencia de alertas con umbrales
```text
co2_alto: valor 1180, umbral {'max': 1000}, desvío 18.0% -> Media
```

### P10 - Operaciones CRUD (03_crud_operations)
```text
find: se encontraron 3 mediciones recientes.
{'id_medicion': 'MED-DEMO-DELETE', 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 20), 'lecturas': [{'tipo': 'luminosidad', 'valor': 410, 'unidad': 'lux'}]}
{'id_medicion': 'MED-004', 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 15), 'lecturas': [{'tipo': 'temperatura', 'valor': 23.0, 'unidad': 'C'}, {'tipo': 'humedad', 'valor': 51, 'unidad': '%'}]}
{'id_medicion': 'MED-003', 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 10), 'lecturas': [{'tipo': 'luminosidad', 'valor': 360, 'unidad': 'lux'}]}
update_one: coincidencias=0, modificados=0.
update_many: coincidencias=1, modificadas=1.
delete_one: mediciones de demostracion eliminadas=1.
```

### P11 - Integridad referencial tras CRUD
```text
dispositivos.id_espacio -> espacios: 0 huérfano(s)
mediciones.id_dispositivo -> dispositivos: 0 huérfano(s)
alertas.id_espacio -> espacios: 0 huérfano(s)
alertas.id_dispositivo -> dispositivos: 0 huérfano(s)
alertas.id_medicion -> mediciones: 0 huérfano(s)
```

### P12 - Consultas de filtrado (04_query_filters)
```text
### filtros(db)
ESPACIOS (Laboratorios): 
{'nombre': 'Laboratorio de Redes', 'tipo': 'Laboratorio', 'capacidad': 30, 'edificio': 'Edificio A'}
{'nombre': 'Laboratorio IoT', 'tipo': 'Laboratorio', 'capacidad': 24, 'edificio': 'Edificio B'}
{'nombre': 'Laboratorio de Electronica', 'tipo': 'Laboratorio', 'capacidad': 20, 'edificio': 'Edificio B'}
{'nombre': 'Taller de Mecatronica', 'tipo': 'Laboratorio', 'capacidad': 18, 'edificio': 'Edificio B'}
ESPACIOS: 
{'nombre': 'Aula 101', 'tipo': 'Aula', 'capacidad': 40, 'edificio': 'Edificio A'}
{'nombre': 'Aula 201', 'tipo': 'Aula', 'capacidad': 40, 'edificio': 'Edificio A'}
{'nombre': 'Biblioteca Central', 'tipo': 'Biblioteca', 'capacidad': 120, 'edificio': 'Edificio Central'}
{'nombre': 'Sala de Estudio 201', 'tipo': 'Espacio Común', 'capacidad': 60, 'edificio': 'Edificio Central'}
{'nombre': 'Auditorio Principal', 'tipo': 'Espacio Común', 'capacidad': 150, 'edificio': 'Edificio D'}
{'nombre': 'Aula 102', 'tipo': 'Aula', 'capacidad': 35, 'edificio': 'Edificio A'}
{'nombre': 'Centro de Computo', 'tipo': 'Espacio Común', 'capacidad': 40, 'edificio': 'Edificio Central'}
MEDICIONES: 
{'_id': ObjectId('6af12a7bb10457a03ede30ec'), 'id_medicion': 'MED-001', 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 0), 'lecturas': [{'tipo': 'temperatura', 'valor': 22.4, 'unidad': 'C'}, {'tipo': 'humedad', 'valor': 48, 'unidad': '%'}], 'id_dispositivo': ObjectId('6af12a74b10457a03ede30d4')}
{'_id': ObjectId('6af12a7bb10457a03ede30ed'), 'id_medicion': 'MED-002', 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 5), 'lecturas': [{'tipo': 'co2', 'valor': 1180, 'unidad': 'ppm'}, {'tipo': 'temperatura', 'valor': 24.1, 'unidad': 'C'}], 'id_dispositivo': ObjectId('6af12a74b10457a03ede30d5'), 'marcada_revision_en': datetime.datetime(2026, 11, 9, 2, 6, 7, 514000), 'revision_requerida': True}
{'_id': ObjectId('6af12a7bb10457a03ede30ef'), 'id_medicion': 'MED-004', 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 15), 'lecturas': [{'tipo': 'temperatura', 'valor': 23.0, 'unidad': 'C'}, {'tipo': 'humedad', 'valor': 51, 'unidad': '%'}], 'id_dispositivo': ObjectId('6af12a74b10457a03ede30d4')}
DISPOSITIVOS: 
{'id_dispositivo': 'SEN-LUX-001', 'tipo_sensor': ['luminosidad'], 'estado': 'Mantenimiento'}
{'id_dispositivo': 'SEN-LUX-003', 'tipo_sensor': ['luminosidad'], 'estado': 'Inactivo'}
{'id_dispositivo': 'SEN-CA-002', 'tipo_sensor': ['pm25', 'pm10'], 'estado': 'Mantenimiento'}
proyección:
{'_id': ObjectId('6af12a7bb10457a03ede30ec'), 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 0), 'lecturas': [{'tipo': 'temperatura', 'valor': 22.4, 'unidad': 'C'}, {'tipo': 'humedad', 'valor': 48, 'unidad': '%'}]}
{'_id': ObjectId('6af12a7bb10457a03ede30ed'), 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 5), 'lecturas': [{'tipo': 'co2', 'valor': 1180, 'unidad': 'ppm'}, {'tipo': 'temperatura', 'valor': 24.1, 'unidad': 'C'}]}
{'_id': ObjectId('6af12a7bb10457a03ede30ee'), 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 10), 'lecturas': [{'tipo': 'luminosidad', 'valor': 360, 'unidad': 'lux'}]}
{'_id': ObjectId('6af12a7bb10457a03ede30ef'), 'fecha_hora': datetime.datetime(2026, 11, 6, 9, 15), 'lecturas': [{'tipo': 'temperatura', 'valor': 23.0, 'unidad': 'C'}, {'tipo': 'humedad', 'valor': 51, 'unidad': '%'}]}
```

### P13 - Pipelines de agregación (05_aggregations)
```text
### agregaciones(db)
PROMEDIO POR VARIABLE: 
{'_id': 'temperatura', 'promedio': 23.166666666666668, 'maximo': 24.1}
{'_id': 'co2', 'promedio': 1180.0, 'maximo': 1180}
{'_id': 'humedad', 'promedio': 49.5, 'maximo': 51}
{'_id': 'luminosidad', 'promedio': 360.0, 'maximo': 360}
VARIABLES POR DISPOSITIVO: 
{'id_dispositivo': 'SEN-TH-001', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-CO2-001', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-TH-002', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-EA-001', 'cantidad_variables': 4}
{'id_dispositivo': 'SEN-CA-001', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-TH-003', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-CO2-002', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-TH-004', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-LUX-002', 'cantidad_variables': 1}
{'id_dispositivo': 'SEN-TH-005', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-CO2-003', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-EA-002', 'cantidad_variables': 4}
{'id_dispositivo': 'SEN-TH-006', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-CO2-004', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-TH-007', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-TH-008', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-LUX-004', 'cantidad_variables': 1}
{'id_dispositivo': 'SEN-TH-009', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-CO2-005', 'cantidad_variables': 2}
{'id_dispositivo': 'SEN-EA-003', 'cantidad_variables': 4}
{'id_dispositivo': 'SEN-CA-003', 'cantidad_variables': 2}
TOP 3 VARIABLES: 
{'_id': 'temperatura', 'dispositivos': 17}
{'_id': 'humedad', 'dispositivos': 12}
{'_id': 'co2', 'dispositivos': 8}
```

### P14 - Cobertura de operadores exigidos por la rúbrica
```text
Operadores de actualización en 03: ['$currentDate', '$set']
```

### P15 - Índices y plan de ejecución (explain)
```text
{
  "espacios": [
    "_id_",
    "nombre_1"
  ],
  "dispositivos": [
    "_id_",
    "id_dispositivo_1"
  ],
  "mediciones": [
    "_id_",
    "id_medicion_1"
  ],
  "alertas": [
    "_id_",
    "idx_estado_severidad_fecha"
  ]
}
Plan alertas: ['FETCH', 'IXSCAN(idx_estado_severidad_fecha)']
```
