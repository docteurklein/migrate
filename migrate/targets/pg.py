
import psycopg2
import contextlib
import os


class Context():
    def __init__(self, cursor):
        self.cursor = cursor
        self.cursor.execute('create schema if not exists migrations')
        self.cursor.execute('create table if not exists migrations.current_migration (name varchar)')

    def get_current_step(self):
        self.cursor.execute('select name from migrations.current_migration union all select null fetch first 1 row only')
        return self.cursor.fetchone()[0]

    def put_current_step(self, step):
        self.cursor.execute('delete from migrations.current_migration')
        self.cursor.execute('insert into migrations.current_migration values (%s)', [step])

    def supports(self, file):
        return file.endswith('.sql')

    def handle(self, file):
        with open(file, 'r') as file:
            return self.cursor.execute(file.read())


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
