
import sqlite3
import contextlib
import os
import sys


class Context():
    def __init__(self, cursor):
        self.cursor = cursor
        self.schema()

    def reset(self):
        self.cursor.execute('drop table if exists migrations_history')
        self.schema()

    def schema(self):
        self.cursor.execute("create table if not exists migrations_history (id serial primary key, name varchar, date timestamp not null default (datetime('now')), previous varchar)")

    def get_current_step(self):
        self.cursor.execute('select name from migrations_history order by id desc limit 1')
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def get_previous_step(self):
        self.cursor.execute('select previous from migrations_history order by id desc limit 1')
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def put_current_step(self, step, previous = None):
        self.cursor.execute('insert into migrations_history(name, previous) values (?, ?)', [step, previous])

    def supports(self, file):
        return file.endswith('.sql')

    def handle(self, file):
        with open(file, 'r') as file:
            return self.cursor.executescript(file.read())

    def sql(self, query, params = []):
        self.cursor.execute(query, params)
        if self.cursor.description is None:
            return []

        print(self.cursor.fetchall())
        return self.cursor.fetchall()


@contextlib.contextmanager
def get_target_context(params):
    with contextlib.closing(sqlite3.connect(params.path)) as conn:
        yield Context(conn.cursor())
        conn.commit()
