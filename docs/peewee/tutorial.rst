.. _tutorial:

Tutorial
========

The purpose of this document is to introduce you to Peewee's commonly-used APIs
and suggested workflows.

Configuring database
^^^^^^^^^^^^^^^^^^^^

To get started using Peewee, the first step is to configure your database and
declare models for the tables your application will be using. Peewee supports
the following databases by default:

* :py:class:`SqliteDatabase`, using the standard library ``sqlite3``.
* :py:class:`MySQLDatabase`, using ``pymysql`` or ``mysql-python``.
* :py:class:`PostgresqlDatabase`, using ``psycopg2``.

Configure your database by passing the database name (or filename) along with
any driver-specific details, which may include the user, password and host.

Examples:

.. code-block:: python

    # Connect to a Sqlite database using write-ahead log journalling mode.
    db = SqliteDatabase('my-app.db', pragmas={'journal_mode': 'wal'})

    # Connect to a Postgresql database on a different server.
    db = PostgresqlDatabase('my_app', user='postgres', host='10.1.0.3')

Declaring models
^^^^^^^^^^^^^^^^

Before declaring the models our application will use, it is a best practice to
declare a base model class bound to our database. This saves us having to bind
each model to the database individually.

.. code-block:: python

    class BaseModel(Model):
        class Meta:
            database = db

Now we can define any number of models, which will extend our ``BaseModel``
class:

.. code-block:: python

    class User(BaseModel):
        username = CharField(unique=True)

    class Tweet(BaseModel):
        content = TextField()
        timestamp = DateTimeField(default=datetime.datetime.now)
        user = ForeignKeyField(User, backref='tweets')

.. note::

    Peewee assumes that the table-name for a model is the lower-case class
    name. To explicitly tell Peewee which table a model maps to, you can
    specify the following ``Meta`` option:

    .. code-block:: python

        class User(BaseModel):
            username = CharField(unique=True)

            class Meta:
                table_name = 'users'

The :py:class:`Model` classes we have declared are normal Python classes, and
you can implement methods, properties and attributes on them as you would any
other Python class.

Creating the schema
^^^^^^^^^^^^^^^^^^^

In order to begin working with our models, we should create the schema in our
database. We will use the :py:meth:`Database.create_tables` method, which
accepts a list of one or more model classes. This method is responsible for:

* Resolving inter-model dependencies to ensure tables are created in order.
* Creating tables and constraints for the given models.
* Creating the appropriate indexes for any fields that were initialized as
  ``index=True`` or ``unique=True``, as well as any special indexes declared as
  part of the ``Model.Meta.indexes`` attribute.
* Create any sequences for fields that declare a ``sequence`` parameter.

Connecting to the database and creating the schema:

.. code-block:: python

    # Use the database as a context-manager, which will wrap the subsequent
    # code in a transaction and commit, then close the connection, at the end.
    with db:
        db.create_tables([User, Tweet])

This will cause the following SQL to be executed:

.. code-block:: sql

    BEGIN;
    CREATE TABLE IF NOT EXISTS "user" (
        "id" INTEGER NOT NULL PRIMARY KEY,
        "username" VARCHAR(255) NOT NULL);
    CREATE UNIQUE INDEX IF NOT EXISTS "user_username" ON "user" ("username");

    CREATE TABLE IF NOT EXISTS "tweet" (
        "id" INTEGER NOT NULL PRIMARY KEY,
        "content" TEXT NOT NULL,
        "timestamp" DATETIME NOT NULL,
        "user_id" INTEGER NOT NULL,
        FOREIGN KEY ("user_id") REFERENCES "user" ("id"));
    CREATE INDEX IF NOT EXISTS "tweet_user_id" ON "tweet" ("user_id");
    COMMIT;
