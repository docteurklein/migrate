# migrate

## What ?

A migration runner, not especially targeting sql databases.

## How ?

    docker run -v $PWD:/usr/src/app -u 1000:1000 docteurklein/migrate

### Add a new migration step

    migrate add 'create_missing_indexes' sh

### Execute migrations

    migrate pg://prod up-to 'some_next_step'
    migrate pg://prod up-to --latest

### Rollback migrations

    migrate pg://prod rollback-to 'some_previous_step'
    migrate pg://prod rollback-to --zero


### Go back to previous state (either up or rollback)

    migrate pg: previous

> Note: executing this twice would end up to where you started.


## verifying side-effects before executing them

All commands having side effects have the `--dry-run` and `--verbose` option. If you use them both, you'll see exactly what would be executed.

## File structure


You can specify many scripts per step that matches the glob pattern:

    migrations/*/*up*
    migrations/*/*rollback*
    migrations/*/*verify*

Use numeric prefixes to guarantee the order of execution, for example:

 - `migrations/create_missing_indexes/1-up.sh`
 - `migrations/create_missing_indexes/2-up.sh`


## Planning

A local plan file is compared to the target's state and decides which steps are yet to be executed.

Steps are executed sequentially.

After each step execution, the `verify` script is invoked.

If `verify` exits with a status code different than `0`, all rollback scripts from impacted steps are executed, and the whole migration stops.


## Targets

The target is represented by an URL (containing credentials and configuration).
The target is the thing we want to mutate.
The target stores the history of all executed steps.

Currently supported targets are:

### postgres target
    
example: `migrate pg://user:password@hostname/db_name status`

#### Environment variables

Those variables take precedence over the values passed in URL.

 - `POSTGRES_DBNAME`
 - `POSTGRES_USER`
 - `POSTGRES_PASSWORD`
 - `POSTGRES_PASSWORD_FILE` (wins over `POSTGRES_PASSWORD`)
 - `POSTGRES_HOST`
 - `POSTGRES_PORT`
 
### sqlite target

example: `migrate sqlite:path/to/some_file.sqlite status`


### arbitray python module target

You can write your own python module that respects the [`Context` interface](./migrate/targets/sqlite.py#L8),
and use it like this:

    migrate some.python.module:some-host/some/param status`

### SQL scripts

Files ending with `.sql` are treated differently than others if the target supports it:
their contents are passed to the current transaction opened on the target.


## Examples

 - `migrations/create_missing_indexes/up`

```sh
#!/usr/bin/env sh

curl -X POST http://elasticsearch.local:9200/_reindex -d@- <<JSON
    {
      "source": {
        "index": "twitter"
      },
      "dest": {
        "index": "new_twitter"
      }
    }
JSON
```

 - `migrations/create_missing_indexes/rollback`

```sh
#!/usr/bin/env sh

curl -X POST http://elasticsearch.local:9200/_reindex -d@- <<JSON
    {
      "source": {
        "index": "new_twitter"
      },
      "dest": {
        "index": "twitter"
      }
    }
JSON
```

 - `migrations/create_missing_indexes/verify`

```sh
#!/usr/bin/env sh

curl -f -X GET http://elasticsearch.local:9200/twitter
```


### shebang


Each step uses executable files with shebang (except `.sql` files) for a maximum flexibility.


## Contributing

### Running tests

    ./bin/tests
