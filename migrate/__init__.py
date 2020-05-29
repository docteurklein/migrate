
import os
import sys
import stat
import glob
import subprocess
import sqlite3
import contextlib
import importlib
from urllib.parse import urlparse
from . import targets


def status(base_dir, target):
    plan_file = '%s/plan.sql' % (base_dir)
    with get_target_context(target) as context:
        current = context.get_current_step()
        print('current step: %s' % (current or 'n/a'))
        with persisted_plan(plan_file) as plan:
            steps = plan.execute("""
                select name from steps
                    where id > (select id from steps where name = ? union all select 0)
                    order by id asc
            """, [current])
            print('missing steps: %s' % [x[0] for x in steps])

def add(base_dir, step: str, type: str):
    files = ['up', 'rollback', 'verify']

    dirname = '%s/scripts/%s' % (base_dir, step)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    for script in files:
        path = '%s/%s.%s' % (dirname, script, type)
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


def get_target_context(target):
    params = urlparse(target)
    try:
        return getattr(targets, params.scheme).get_target_context(params)
    except AttributeError:
        return importlib.import_module(params.scheme).get_target_context(params)


def up_to_latest(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    with get_target_context(target) as context:
        current = context.get_current_step()
        with persisted_plan(plan_file) as plan:
            steps = plan.execute("""
                select name from steps
                    where id > (select id from steps where name = ? union all select 0)
                    order by id asc
            """, [current])
            execute_missing(context, base_dir, [row[0] for row in steps], current, verbose)


def up_to(base_dir, target, step, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    with get_target_context(target) as context:
        current = context.get_current_step()
        with persisted_plan(plan_file) as plan:
            steps = plan.execute("""
                select name from steps
                    where id >  (select id from steps where name = ? union all select 0)
                    and   id <= (select id from steps where name = ? union all select max(id) from steps)
                    order by id asc
            """, [current, step])
            execute_missing(context, base_dir, [row[0] for row in steps], current, verbose)


def rollback_to(base_dir, target, step: str, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    with get_target_context(target) as context:
        current = context.get_current_step()
        if not current:
            return
        with persisted_plan(plan_file) as plan:
            steps = plan.execute("""
                select name from steps
                    where id >  (select id from steps where name = ? union all select 0)
                    and   id <= (select id from steps where name = ? union all select max(id) from steps)
                    order by id desc
            """, [step, current])
            for row in steps:
                execute_step(context, base_dir, row[0], current, 'rollback', verbose)

        context.put_current_step(step, current)


def rollback_to_first(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    with get_target_context(target) as context:
        current = context.get_current_step()
        if not current:
            return
        with persisted_plan(plan_file) as plan:
            steps = plan.execute("""
                select name from steps
                    where id <= (select id from steps where name = ? union all select max(id) from steps)
                    order by id desc
            """, [current])
            for row in steps:
                execute_step(context, base_dir, row[0], current, 'rollback', verbose)

        context.put_current_step(None, current)


def previous(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    with get_target_context(target) as context:
        current = context.get_current_step()
        previous = context.get_previous_step()

        with persisted_plan(plan_file) as plan:
            direction_is_up = plan.execute("""
                select current.id < previous.id
                    from (select * from steps where name = ?) current
                    join (select * from steps where name = ?) previous
            """, [current, previous]).fetchone()

            if direction_is_up is None:
                print('no previous migration', file=sys.stderr)
                return

            print('going to %s (direction %s)' % (previous, 'up' if direction_is_up[0] else 'rollback'), file=sys.stderr)
            if direction_is_up[0]:
                up_to(base_dir, target, previous, verbose)
            else:
                rollback_to(base_dir, target, previous, verbose)


def execute_missing(context, base_dir, steps, current, verbose):
    executed = []
    for step in steps:
        try:
            execute_step(context, base_dir, step, current, 'up', verbose)
            execute_step(context, base_dir, step, current, 'verify', verbose)
            executed.append(step)
        except Exception as e:
            execute_step(context, base_dir, step, current, 'rollback', verbose)
            for to_rollback in reversed(executed):
                execute_step(context, base_dir, to_rollback, current, 'rollback', verbose)
            raise e


def execute_step(context, base_dir, step, current, type, verbose=False):
    pattern = '%s/scripts/%s/*%s*' % (base_dir, step, type)
    scripts = glob.glob(pattern)
    if not scripts:
        raise Exception(
            'missing scripts for step "%s", was searching for "%s"'
            % (step, pattern)
        )

    for script in scripts:
        if context.supports(script):
            print('letting target handle %s' % script, file=sys.stderr)
            context.handle(script)
        else:
            print('executing %s' % script, file=sys.stderr)
            process = subprocess.run(
                script,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if verbose:
                print(process.stdout.decode(), file=sys.stderr)

            if process.returncode != 0:
                raise Exception

    if type in ['verify', 'rollback']:
        context.put_current_step(step, current)

def sql(base_dir, target, query, verbose=False):
    with get_target_context(target) as context:
        return context.sql(query)

def reset(base_dir, target, verbose=False):
    with get_target_context(target) as context:
        context.reset()

def force_state(base_dir, target, step, verbose=False):
    with get_target_context(target) as context:
        context.put_current_step(step, context.get_current_step())

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
