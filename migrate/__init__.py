
import os
import sys
import stat
import glob
import subprocess
import sqlite3
import contextlib
from urllib.parse import urlparse
import paramiko


def add(base_dir, step: str):
    files = ['up', 'rollback', 'verify']

    dirname = '%s/scripts/%s' % (base_dir, step)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    for script in files:
        path = '%s/%s' % (dirname, script)
        if not os.path.exists(path):
            with open(path, 'w+') as file:
                file.write('#!/usr/bin/env sh\n\n')
                file.write('echo TODO\n')
                file.write('exit 1\n')
                os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

            print('Created %s' % (path), file=sys.stderr)

    plan_file = '%s/plan.sql' % (base_dir)
    with persisted_plan(plan_file, read_only=False) as plan:
        plan.execute("""
            insert into steps (name, created_at)
                values (?, datetime(?))
        """, [step, 'now'])

    print('Added %s to %s' % (step, plan_file), file=sys.stderr)


def get_current_step(target):
    params = urlparse(target)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(params.hostname, port=params.port, username=params.username, password=params.password)
    stdin, stdout, stderr = client.exec_command('cat %s' % params.path)
    if stdout.channel.recv_exit_status() != 0:
        pass
        #raise Exception
    return stdout.read()


def put_current_step(target, step):
    params = urlparse(target)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(params.hostname, port=params.port, username=params.username, password=params.password)
    stdin, stdout, stderr = client.exec_command('sh -c "cat - > %s"' % params.path)
    stdin.write(step)
    stdin.channel.close()
    if stdout.channel.recv_exit_status() != 0:
        pass
        #raise Exception


def up_to_latest(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id > (select id from steps where name = ?)
                order by id asc
        """, [current])
        execute_missing(target, base_dir, [x[0] for x in steps], verbose)


def up_to(base_dir, target, step, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id >  (select id from steps where name = ?)
                and   id <= (select id from steps where name = ?)
                order by id asc
        """, [current, step])
        execute_missing(target, base_dir, [x[0] for x in steps], verbose)


def rollback_to(base_dir, target, step: str, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id >  (select id from steps where name = ?)
                and   id <= (select id from steps where name = ?)
                order by id desc
        """, [step, current])
        for step in steps:
            execute_step(target, base_dir, step[0], 'rollback', verbose)


def rollback_to_first(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id <= (select id from steps where name = ?)
                order by id desc
        """, [current])
        for step in steps:
            execute_step(target, base_dir, step[0], 'rollback', verbose)


def execute_missing(target, base_dir, steps, verbose):
    executed = []
    for step in steps:
        try:
            execute_step(target, base_dir, step, 'up', verbose)
            execute_step(target, base_dir, step, 'verify', verbose)
            executed.append(step)
        except Exception as e:
            execute_step(target, base_dir, step, 'rollback', verbose)
            for to_rollback in reversed(executed):
                execute_step(target, base_dir, to_rollback, 'rollback', verbose)
            raise e


def execute_step(target, base_dir, step, type, verbose=False):
    pattern = '%s/scripts/%s/*%s*' % (base_dir, step, type)
    scripts = glob.glob(pattern)
    if not scripts:
        raise Exception(
            'missing scripts for step "%s", was searching for "%s"'
            % (step, pattern)
        )

    for script in scripts:
        print('running %s' % script, file=sys.stderr)
        process = subprocess.run(
            script,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if verbose:
            print(process.stdout.decode(), file=sys.stderr)

        if process.returncode != 0:
            raise Exception

    put_current_step(target, step)


@contextlib.contextmanager
def persisted_plan(plan_file, read_only=True):
    with contextlib.closing(sqlite3.connect(':memory:')) as conn:
        with conn as plan:

            if os.path.exists(plan_file):
                with open(plan_file, 'r') as file:
                    plan.executescript(file.read())

            plan.execute("""
                create table if not exists steps (
                    id integer primary key autoincrement,
                    created_at datetime,
                    name string unique
                )
            """)
            yield plan

            if not read_only:
                with open(plan_file, 'w+') as file:
                    for line in plan.iterdump():
                        if 'sqlite_sequence' not in line:
                            file.write('%s\n' % line)

