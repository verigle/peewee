from peewee import *
from playhouse.migrate import SchemaMigrator
from playhouse.migrate import migrate
from playhouse.schema_validate import validate_schema

from .base import ModelTestCase
from .base import TestModel
from .base import db
from .base import requires_sqlite
from .base_models import Tweet
from .base_models import User


class TestSchemaValidate(ModelTestCase):
    requires = [User, Tweet]

    def setUp(self):
        super(TestSchemaValidate, self).setUp()
        self.migrator = SchemaMigrator.from_database(self.database)

    def test_simple_validate(self):
        result = validate_schema(User)
        self.assertTrue(result.valid)

        result = validate_schema(Tweet)
        self.assertTrue(result.valid)

    def test_add_remove(self):
        migrate(
            self.migrator.add_column('users', 'name', TextField(default='')),
            self.migrator.drop_column('users', 'username'))
        result = validate_schema(User)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.add_fields), 1)
        new_field = result.add_fields[0]
        self.assertTrue(isinstance(new_field, TextField))
        self.assertEqual(new_field.name, 'name')

        self.assertEqual(len(result.remove_fields), 1)
        old_field = result.remove_fields[0]
        self.assertTrue(old_field is User.username)

    def test_change(self):
        migrate(
            self.migrator.drop_column('users', 'username'),
            self.migrator.add_column('users', 'username',
                                     TextField(default='')),
            self.migrator.drop_column('tweet', 'user_id'),
            self.migrator.add_column('tweet', 'user_id',
                                     IntegerField(null=True)))

        r = validate_schema(User)
        self.assertFalse(r.valid)
        self.assertTrue(len(r.add_fields) == len(r.remove_fields) == 0)
        self.assertTrue(len(r.change_fields), 1)
        old, new = r.change_fields[0]
        self.assertTrue(old is User.username)
        self.assertTrue(isinstance(new, TextField))

        # Although we changed from a foreign-key to an integerfield, we're only
        # comparing column names and field types.
        r = validate_schema(Tweet)
        self.assertTrue(r.valid)

    def test_missing_table(self):
        class FooBar(TestModel):
            pass
        result = validate_schema(FooBar)
        self.assertFalse(result.valid)
        self.assertFalse(result.table_exists)
