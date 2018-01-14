
import psycopg2
import contextlib

class Context():
    def __init__(self, cursor):
        self.cursor = cursor
        self.cursor.execute('create table if not exists current_migration (name varchar)')

    def get_current_step(self):
        self.cursor.execute('select name from current_migration union all select null fetch first 1 row only')
        return self.cursor.fetchone()[0]

    def put_current_step(self, step):
        self.cursor.execute('delete from current_migration')
        self.cursor.execute('insert into current_migration values (%s)', [step])

    def supports(self, file):
        return file.endswith('.sql')

    def handle(self, file):
        with open(file, 'r') as file:
            return self.cursor.execute(file.read())


@contextlib.contextmanager
def get_target_context(params):
    with psycopg2.connect(
        dbname=params.path[1:],
        user=params.username,
        password=params.password,
        host=params.hostname,
        port=params.port
    ) as conn:
        with conn.cursor() as cursor:
            yield Context(cursor)
