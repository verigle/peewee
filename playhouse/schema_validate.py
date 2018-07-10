from collections import namedtuple

from playhouse.reflection import Introspector


ValidationResult = namedtuple('ValidationResult', (
    'valid', 'table_exists', 'add_fields', 'remove_fields', 'change_fields'))


def validate_schema(model):
    db = model._meta.database
    table = model._meta.table_name
    if not db.table_exists(table):
        return ValidationResult(False, False, None, None, None)

    introspector = Introspector.from_database(db)
    db_model = introspector.generate_models(table_names=[table])[table]

    columns = set(model._meta.columns)
    db_columns = set(db_model._meta.columns)

    to_remove = [model._meta.columns[c] for c in columns - db_columns]
    to_add = [db_model._meta.columns[c] for c in db_columns - columns]
    to_change = []
    intersect = columns & db_columns  # Take intersection and remove matches.
    for column in intersect:
        field = model._meta.columns[column]
        db_field = db_model._meta.columns[column]
        if field.field_type != db_field.field_type:
            to_change.append((field, db_field))

    is_valid = not any((to_remove, to_add, to_change))
    return ValidationResult(is_valid, True, to_add, to_remove, to_change)
