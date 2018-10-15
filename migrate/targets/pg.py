
import psycopg2
import contextlib
import os
import sys


class Context():
    def __init__(self, cursor):
        self.cursor = cursor
        self.schema()

    def reset(self):
        self.cursor.execute('drop table if exists migrations.history')
        self.schema()

    def schema(self):
        self.cursor.execute('create schema if not exists migrations')
        self.cursor.execute('create table if not exists migrations.history (id serial primary key, name varchar, date timestamp not null default now(), previous varchar)')

    def get_current_step(self):
        self.cursor.execute('select name from migrations.history order by id desc limit 1')
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def get_previous_step(self):
        self.cursor.execute('select previous from migrations.history order by id desc limit 1')
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def put_current_step(self, step, previous = None):
        self.cursor.execute('insert into migrations.history(name, previous) values (%s, %s)', [step, previous])

    def supports(self, file):
        return file.endswith('.sql')

    def handle(self, file):
        with open(file, 'r') as file:
            return self.cursor.execute(file.read())

    def sql(self, query):
        self.cursor.execute(query)
        if self.cursor.description is None:
            return []
        return self.cursor.fetchall()


@contextlib.contextmanager
def get_target_context(params):
    password = os.environ.get('POSTGRES_PASSWORD', params.password)
    if os.path.exists(os.environ.get('POSTGRES_PASSWORD_FILE', '')):
        with open(os.environ.get('POSTGRES_PASSWORD_FILE'), 'r') as file:
            password = file.read()

    with psycopg2.connect(
        dbname=os.environ.get('POSTGRES_DBNAME', params.path[1:]),
        user=os.environ.get('POSTGRES_USER', params.username),
        password=password,
        host=os.environ.get('POSTGRES_HOST', params.hostname),
        port=os.environ.get('POSTGRES_PORT', params.port)
    ) as conn:
        with conn.cursor() as cursor:
            yield Context(cursor)
