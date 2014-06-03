import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.utils import six
from django.db import connections, DEFAULT_DB_ALIAS, migrations
from django.db.migrations.loader import AmbiguityError
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.writer import MigrationWriter
from django.db.migrations.optimizer import MigrationOptimizer


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--no-optimize', action='store_true', dest='no_optimize', default=False,
            help='Do not try to optimize the squashed operations.'),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
    )

    help = "Squashes an existing set of migrations (from first until specified) into a single new one."
    usage_str = "Usage: ./manage.py squashmigrations app migration_name"
    args = "app_label migration_name"

    def handle(self, app_label=None, migration_name=None, **options):

        self.verbosity = int(options.get('verbosity'))
        self.interactive = options.get('interactive')

        if app_label is None or migration_name is None:
            self.stderr.write(self.usage_str)
            sys.exit(1)

        # Load the current graph state, check the app and migration they asked for exists
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        if app_label not in executor.loader.migrated_apps:
            raise CommandError("App '%s' does not have migrations (so squashmigrations on it makes no sense)" % app_label)
        try:
            migration = executor.loader.get_migration_by_prefix(app_label, migration_name)
        except AmbiguityError:
            raise CommandError("More than one migration matches '%s' in app '%s'. Please be more specific." % (migration_name, app_label))
        except KeyError:
            raise CommandError("Cannot find a migration matching '%s' from app '%s'." % (migration_name, app_label))

        # Work out the list of predecessor migrations
        migrations_to_squash = [
            executor.loader.get_migration(al, mn)
            for al, mn in executor.loader.graph.forwards_plan((migration.app_label, migration.name))
            if al == migration.app_label
        ]

        # Tell them what we're doing and optionally ask if we should proceed
        if self.verbosity > 0 or self.interactive:
            self.stdout.write(self.style.MIGRATE_HEADING("Will squash the following migrations:"))
            for migration in migrations_to_squash:
                self.stdout.write(" - %s" % migration.name)

            if self.interactive:
                answer = None
                while not answer or answer not in "yn":
                    answer = six.moves.input("Do you wish to proceed? [yN] ")
                    if not answer:
                        answer = "n"
                        break
                    else:
                        answer = answer[0].lower()
                if answer != "y":
                    return

        # Load the operations from all those migrations and concat together
        operations = []
        for smigration in migrations_to_squash:
            operations.extend(smigration.operations)

        if self.verbosity > 0:
            self.stdout.write(self.style.MIGRATE_HEADING("Optimizing..."))

        optimizer = MigrationOptimizer()
        new_operations = optimizer.optimize(operations, migration.app_label)

        if self.verbosity > 0:
            if len(new_operations) == len(operations):
                self.stdout.write("  No optimizations possible.")
            else:
                self.stdout.write("  Optimized from %s operations to %s operations." % (len(operations), len(new_operations)))

        # Work out the value of replaces (any squashed ones we're re-squashing)
        # need to feed their replaces into ours
        replaces = []
        for migration in migrations_to_squash:
            if migration.replaces:
                replaces.extend(migration.replaces)
            else:
                replaces.append((migration.app_label, migration.name))

        # Make a new migration with those operations
        subclass = type("Migration", (migrations.Migration, ), {
            "dependencies": [],
            "operations": new_operations,
            "replaces": replaces,
        })
        new_migration = subclass("0001_squashed_%s" % migration.name, app_label)

        # Write out the new migration file
        writer = MigrationWriter(new_migration)
        with open(writer.path, "wb") as fh:
            fh.write(writer.as_string())

        if self.verbosity > 0:
            self.stdout.write(self.style.MIGRATE_HEADING("Created new squashed migration %s" % writer.path))
            self.stdout.write("  You should commit this migration but leave the old ones in place;")
            self.stdout.write("  the new migration will be used for new installs. Once you are sure")
            self.stdout.write("  all instances of the codebase have applied the migrations you squashed,")
            self.stdout.write("  you can delete them.")
