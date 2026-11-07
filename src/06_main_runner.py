from importlib import import_module


def main():
    connection = import_module("01_db_connection")
    seed = import_module("02_seed_data")
    crud = import_module("03_crud_operations")

    db = connection.get_database()
    if db is None:
        raise ConnectionError("No fue posible conectarse a MongoDB.")

    try:
        connection.setup_schema_validators(db)
        seed.seed_data(db)
        crud.run_crud_operations(db)
    finally:
        db.client.close()


if __name__ == "__main__":
    main()
