from __future__ import unicode_literals

import unittest

try:
    import sqlparse
except ImportError:
    sqlparse = None

from django import test
from django.db import connection, migrations, models, router
from django.db.migrations.migration import Migration
from django.db.migrations.state import ProjectState
from django.db.models.fields import NOT_PROVIDED
from django.db.transaction import atomic
from django.db.utils import IntegrityError, DatabaseError

from .test_base import MigrationTestBase


class OperationTests(MigrationTestBase):
    """
    Tests running the operations and making sure they do what they say they do.
    Each test looks at their state changing, and then their database operation -
    both forwards and backwards.
    """

    def apply_operations(self, app_label, project_state, operations):
        migration = Migration('name', app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.apply(project_state, editor)

    def unapply_operations(self, app_label, project_state, operations):
        migration = Migration('name', app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.unapply(project_state, editor)

    def set_up_test_model(self, app_label, second_model=False, third_model=False, related_model=False, mti_model=False):
        """
        Creates a test model state and database table.
        """
        # Delete the tables if they already exist
        with connection.cursor() as cursor:
            # Start with ManyToMany tables
            try:
                cursor.execute("DROP TABLE %s_pony_stables" % app_label)
            except DatabaseError:
                pass
            try:
                cursor.execute("DROP TABLE %s_pony_vans" % app_label)
            except DatabaseError:
                pass

            # Then standard model tables
            try:
                cursor.execute("DROP TABLE %s_pony" % app_label)
            except DatabaseError:
                pass
            try:
                cursor.execute("DROP TABLE %s_stable" % app_label)
            except DatabaseError:
                pass
            try:
                cursor.execute("DROP TABLE %s_van" % app_label)
            except DatabaseError:
                pass
        # Make the "current" state
        operations = [migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
        )]
        if second_model:
            operations.append(migrations.CreateModel(
                "Stable",
                [
                    ("id", models.AutoField(primary_key=True)),
                ]
            ))
        if third_model:
            operations.append(migrations.CreateModel(
                "Van",
                [
                    ("id", models.AutoField(primary_key=True)),
                ]
            ))
        if related_model:
            operations.append(migrations.CreateModel(
                "Rider",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pony", models.ForeignKey("Pony")),
                ],
            ))
        if mti_model:
            operations.append(migrations.CreateModel(
                "ShetlandPony",
                fields=[
                    ('pony_ptr', models.OneToOneField(
                        auto_created=True,
                        primary_key=True,
                        to_field='id',
                        serialize=False,
                        to='Pony',
                    )),
                    ("cuteness", models.IntegerField(default=1)),
                ],
                bases=['%s.Pony' % app_label],
            ))

        return self.apply_operations(app_label, ProjectState(), operations)

    def test_create_model(self):
        """
        Tests the CreateModel operation.
        Most other tests use this operation as part of setup, so check failures here first.
        """
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
        )
        # Test the state alteration
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        self.assertEqual(new_state.models["test_crmo", "pony"].name, "Pony")
        self.assertEqual(len(new_state.models["test_crmo", "pony"].fields), 2)
        # Test the database alteration
        self.assertTableNotExists("test_crmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableExists("test_crmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(len(definition[1]), 2)
        self.assertEqual(len(definition[2]), 0)
        self.assertEqual(definition[1][0], "Pony")

    def test_create_model_m2m(self):
        """
        Test the creation of a model with a ManyToMany field and the
        auto-created "through" model.
        """
        project_state = self.set_up_test_model("test_crmomm")
        operation = migrations.CreateModel(
            "Stable",
            [
                ("id", models.AutoField(primary_key=True)),
                ("ponies", models.ManyToManyField("Pony", related_name="stables"))
            ]
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_crmomm", new_state)
        # Test the database alteration
        self.assertTableNotExists("test_crmomm_stable_ponies")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmomm", editor, project_state, new_state)
        self.assertTableExists("test_crmomm_stable")
        self.assertTableExists("test_crmomm_stable_ponies")
        self.assertColumnNotExists("test_crmomm_stable", "ponies")
        # Make sure the M2M field actually works
        with atomic():
            new_apps = new_state.render()
            Pony = new_apps.get_model("test_crmomm", "Pony")
            Stable = new_apps.get_model("test_crmomm", "Stable")
            stable = Stable.objects.create()
            p1 = Pony.objects.create(pink=False, weight=4.55)
            p2 = Pony.objects.create(pink=True, weight=5.43)
            stable.ponies.add(p1, p2)
            self.assertEqual(stable.ponies.count(), 2)
            stable.ponies.all().delete()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmomm", editor, new_state, project_state)
        self.assertTableNotExists("test_crmomm_stable")
        self.assertTableNotExists("test_crmomm_stable_ponies")

    def test_create_model_inheritance(self):
        """
        Tests the CreateModel operation on a multi-table inheritance setup.
        """
        project_state = self.set_up_test_model("test_crmoih")
        # Test the state alteration
        operation = migrations.CreateModel(
            "ShetlandPony",
            [
                ('pony_ptr', models.OneToOneField(
                    auto_created=True,
                    primary_key=True,
                    to_field='id',
                    serialize=False,
                    to='test_crmoih.Pony',
                )),
                ("cuteness", models.IntegerField(default=1)),
            ],
        )
        new_state = project_state.clone()
        operation.state_forwards("test_crmoih", new_state)
        self.assertIn(("test_crmoih", "shetlandpony"), new_state.models)
        # Test the database alteration
        self.assertTableNotExists("test_crmoih_shetlandpony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmoih", editor, project_state, new_state)
        self.assertTableExists("test_crmoih_shetlandpony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmoih", editor, new_state, project_state)
        self.assertTableNotExists("test_crmoih_shetlandpony")

    def test_delete_model(self):
        """
        Tests the DeleteModel operation.
        """
        project_state = self.set_up_test_model("test_dlmo")
        # Test the state alteration
        operation = migrations.DeleteModel("Pony")
        new_state = project_state.clone()
        operation.state_forwards("test_dlmo", new_state)
        self.assertNotIn(("test_dlmo", "pony"), new_state.models)
        # Test the database alteration
        self.assertTableExists("test_dlmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_dlmo", editor, project_state, new_state)
        self.assertTableNotExists("test_dlmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_dlmo", editor, new_state, project_state)
        self.assertTableExists("test_dlmo_pony")

    def test_rename_model(self):
        """
        Tests the RenameModel operation.
        """
        project_state = self.set_up_test_model("test_rnmo")
        # Test the state alteration
        operation = migrations.RenameModel("Pony", "Horse")
        new_state = project_state.clone()
        operation.state_forwards("test_rnmo", new_state)
        self.assertNotIn(("test_rnmo", "pony"), new_state.models)
        self.assertIn(("test_rnmo", "horse"), new_state.models)
        # Test the database alteration
        self.assertTableExists("test_rnmo_pony")
        self.assertTableNotExists("test_rnmo_horse")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnmo", editor, project_state, new_state)
        self.assertTableNotExists("test_rnmo_pony")
        self.assertTableExists("test_rnmo_horse")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rnmo", editor, new_state, project_state)
        self.assertTableExists("test_dlmo_pony")
        self.assertTableNotExists("test_rnmo_horse")

    # See #22248 - this will fail until that's fixed.
    #
    # def test_rename_model_with_related(self):
    #     """
    #     Tests the real-world combo of a RenameModel operation with AlterField
    #     for a related field.
    #     """
    #     project_state = self.set_up_test_model(
    #         "test_rnmowr", related_model=True)
    #     # Test the state alterations
    #     model_operation = migrations.RenameModel("Pony", "Horse")
    #     new_state = project_state.clone()
    #     model_operation.state_forwards("test_rnmowr", new_state)
    #     self.assertNotIn(("test_rnmowr", "pony"), new_state.models)
    #     self.assertIn(("test_rnmowr", "horse"), new_state.models)

    #     self.assertEqual(
    #         "Pony",
    #         project_state.render().get_model("test_rnmowr", "rider")
    #         ._meta.get_field_by_name("pony")[0].rel.to._meta.object_name)
    #     field_operation = migrations.AlterField(
    #         "Rider", "pony", models.ForeignKey("Horse"))
    #     field_operation.state_forwards("test_rnmowr", new_state)
    #     self.assertEqual(
    #         "Horse",
    #         new_state.render().get_model("test_rnmowr", "rider")
    #         ._meta.get_field_by_name("pony")[0].rel.to._meta.object_name)

    #     # Test the database alterations
    #     self.assertTableExists("test_rnmowr_pony")
    #     self.assertTableNotExists("test_rnmowr_horse")
    #     with connection.schema_editor() as editor:
    #         model_operation.database_forwards("test_rnmowr", editor, project_state, new_state)
    #         field_operation.database_forwards("test_rnmowr", editor, project_state, new_state)
    #     self.assertTableNotExists("test_rnmowr_pony")
    #     self.assertTableExists("test_rnmowr_horse")
    #     # And test reversal
    #     with connection.schema_editor() as editor:
    #         field_operation.database_backwards("test_rnmowr", editor, new_state, project_state)
    #         model_operation.database_backwards("test_rnmowr", editor, new_state, project_state)
    #     self.assertTableExists("test_rnmowr_pony")
    #     self.assertTableNotExists("test_rnmowr_horse")

    def test_add_field(self):
        """
        Tests the AddField operation.
        """
        project_state = self.set_up_test_model("test_adfl")
        # Test the state alteration
        operation = migrations.AddField(
            "Pony",
            "height",
            models.FloatField(null=True, default=5),
        )
        new_state = project_state.clone()
        operation.state_forwards("test_adfl", new_state)
        self.assertEqual(len(new_state.models["test_adfl", "pony"].fields), 4)
        field = [
            f for n, f in new_state.models["test_adfl", "pony"].fields
            if n == "height"
        ][0]
        self.assertEqual(field.default, 5)
        # Test the database alteration
        self.assertColumnNotExists("test_adfl_pony", "height")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adfl", editor, project_state, new_state)
        self.assertColumnExists("test_adfl_pony", "height")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adfl", editor, new_state, project_state)
        self.assertColumnNotExists("test_adfl_pony", "height")

    def test_add_charfield(self):
        """
        Tests the AddField operation on TextField.
        """
        project_state = self.set_up_test_model("test_adchfl")

        new_apps = project_state.render()
        Pony = new_apps.get_model("test_adchfl", "Pony")
        pony = Pony.objects.create(weight=42)

        new_state = self.apply_operations("test_adchfl", project_state, [
            migrations.AddField(
                "Pony",
                "text",
                models.CharField(max_length=10, default="some text"),
            ),
            migrations.AddField(
                "Pony",
                "empty",
                models.CharField(max_length=10, default=""),
            ),
            # If not properly quoted digits would be interpreted as an int.
            migrations.AddField(
                "Pony",
                "digits",
                models.CharField(max_length=10, default="42"),
            ),
            # Manual quoting is fragile and could trip on quotes. Refs #xyz.
            migrations.AddField(
                "Pony",
                "quotes",
                models.CharField(max_length=10, default='"\'"'),
            ),
        ])

        new_apps = new_state.render()
        Pony = new_apps.get_model("test_adchfl", "Pony")
        pony = Pony.objects.get(pk=pony.pk)
        self.assertEqual(pony.text, "some text")
        self.assertEqual(pony.empty, "")
        self.assertEqual(pony.digits, "42")
        self.assertEqual(pony.quotes, '"\'"')

    def test_add_textfield(self):
        """
        Tests the AddField operation on TextField.
        """
        project_state = self.set_up_test_model("test_adtxtfl")

        new_apps = project_state.render()
        Pony = new_apps.get_model("test_adtxtfl", "Pony")
        pony = Pony.objects.create(weight=42)

        new_state = self.apply_operations("test_adtxtfl", project_state, [
            migrations.AddField(
                "Pony",
                "text",
                models.TextField(default="some text"),
            ),
            migrations.AddField(
                "Pony",
                "empty",
                models.TextField(default=""),
            ),
            # If not properly quoted digits would be interpreted as an int.
            migrations.AddField(
                "Pony",
                "digits",
                models.TextField(default="42"),
            ),
            # Manual quoting is fragile and could trip on quotes. Refs #xyz.
            migrations.AddField(
                "Pony",
                "quotes",
                models.TextField(default='"\'"'),
            ),
        ])

        new_apps = new_state.render()
        Pony = new_apps.get_model("test_adtxtfl", "Pony")
        pony = Pony.objects.get(pk=pony.pk)
        self.assertEqual(pony.text, "some text")
        self.assertEqual(pony.empty, "")
        self.assertEqual(pony.digits, "42")
        self.assertEqual(pony.quotes, '"\'"')

    @test.skipUnlessDBFeature('supports_binary_field')
    def test_add_binaryfield(self):
        """
        Tests the AddField operation on TextField/BinaryField.
        """
        project_state = self.set_up_test_model("test_adbinfl")

        new_apps = project_state.render()
        Pony = new_apps.get_model("test_adbinfl", "Pony")
        pony = Pony.objects.create(weight=42)

        new_state = self.apply_operations("test_adbinfl", project_state, [
            migrations.AddField(
                "Pony",
                "blob",
                models.BinaryField(default=b"some text"),
            ),
            migrations.AddField(
                "Pony",
                "empty",
                models.BinaryField(default=b""),
            ),
            # If not properly quoted digits would be interpreted as an int.
            migrations.AddField(
                "Pony",
                "digits",
                models.BinaryField(default=b"42"),
            ),
            # Manual quoting is fragile and could trip on quotes. Refs #xyz.
            migrations.AddField(
                "Pony",
                "quotes",
                models.BinaryField(default=b'"\'"'),
            ),
        ])

        new_apps = new_state.render()
        Pony = new_apps.get_model("test_adbinfl", "Pony")
        pony = Pony.objects.get(pk=pony.pk)
        # SQLite returns buffer/memoryview, cast to bytes for checking.
        self.assertEqual(bytes(pony.blob), b"some text")
        self.assertEqual(bytes(pony.empty), b"")
        self.assertEqual(bytes(pony.digits), b"42")
        self.assertEqual(bytes(pony.quotes), b'"\'"')

    def test_column_name_quoting(self):
        """
        Column names that are SQL keywords shouldn't cause problems when used
        in migrations (#22168).
        """
        project_state = self.set_up_test_model("test_regr22168")
        operation = migrations.AddField(
            "Pony",
            "order",
            models.IntegerField(default=0),
        )
        new_state = project_state.clone()
        operation.state_forwards("test_regr22168", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_regr22168", editor, project_state, new_state)
        self.assertColumnExists("test_regr22168_pony", "order")

    def test_add_field_preserve_default(self):
        """
        Tests the AddField operation's state alteration
        when preserve_default = False.
        """
        project_state = self.set_up_test_model("test_adflpd")
        # Test the state alteration
        operation = migrations.AddField(
            "Pony",
            "height",
            models.FloatField(null=True, default=4),
            preserve_default=False,
        )
        new_state = project_state.clone()
        operation.state_forwards("test_adflpd", new_state)
        self.assertEqual(len(new_state.models["test_adflpd", "pony"].fields), 4)
        field = [
            f for n, f in new_state.models["test_adflpd", "pony"].fields
            if n == "height"
        ][0]
        self.assertEqual(field.default, NOT_PROVIDED)
        # Test the database alteration
        project_state.render().get_model("test_adflpd", "pony").objects.create(
            weight=4,
        )
        self.assertColumnNotExists("test_adflpd_pony", "height")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adflpd", editor, project_state, new_state)
        self.assertColumnExists("test_adflpd_pony", "height")

    def test_add_field_m2m(self):
        """
        Tests the AddField operation with a ManyToManyField.
        """
        project_state = self.set_up_test_model("test_adflmm", second_model=True)
        # Test the state alteration
        operation = migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies"))
        new_state = project_state.clone()
        operation.state_forwards("test_adflmm", new_state)
        self.assertEqual(len(new_state.models["test_adflmm", "pony"].fields), 4)
        # Test the database alteration
        self.assertTableNotExists("test_adflmm_pony_stables")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adflmm", editor, project_state, new_state)
        self.assertTableExists("test_adflmm_pony_stables")
        self.assertColumnNotExists("test_adflmm_pony", "stables")
        # Make sure the M2M field actually works
        with atomic():
            new_apps = new_state.render()
            Pony = new_apps.get_model("test_adflmm", "Pony")
            p = Pony.objects.create(pink=False, weight=4.55)
            p.stables.create()
            self.assertEqual(p.stables.count(), 1)
            p.stables.all().delete()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adflmm", editor, new_state, project_state)
        self.assertTableNotExists("test_adflmm_pony_stables")

    def test_alter_field_m2m(self):
        project_state = self.set_up_test_model("test_alflmm", second_model=True)

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies"))
        ])
        new_apps = project_state.render()
        Pony = new_apps.get_model("test_alflmm", "Pony")
        self.assertFalse(Pony._meta.get_field('stables').blank)

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AlterField("Pony", "stables", models.ManyToManyField(to="Stable", related_name="ponies", blank=True))
        ])
        new_apps = project_state.render()
        Pony = new_apps.get_model("test_alflmm", "Pony")
        self.assertTrue(Pony._meta.get_field('stables').blank)

    def test_repoint_field_m2m(self):
        project_state = self.set_up_test_model("test_alflmm", second_model=True, third_model=True)

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AddField("Pony", "places", models.ManyToManyField("Stable", related_name="ponies"))
        ])
        new_apps = project_state.render()
        Pony = new_apps.get_model("test_alflmm", "Pony")

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AlterField("Pony", "places", models.ManyToManyField(to="Van", related_name="ponies"))
        ])

        # Ensure the new field actually works
        new_apps = project_state.render()
        Pony = new_apps.get_model("test_alflmm", "Pony")
        p = Pony.objects.create(pink=False, weight=4.55)
        p.places.create()
        self.assertEqual(p.places.count(), 1)
        p.places.all().delete()

    def test_remove_field_m2m(self):
        project_state = self.set_up_test_model("test_rmflmm", second_model=True)

        project_state = self.apply_operations("test_rmflmm", project_state, operations=[
            migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies"))
        ])
        self.assertTableExists("test_rmflmm_pony_stables")

        operations = [migrations.RemoveField("Pony", "stables")]
        self.apply_operations("test_rmflmm", project_state, operations=operations)
        self.assertTableNotExists("test_rmflmm_pony_stables")

        # And test reversal
        self.unapply_operations("test_rmflmm", project_state, operations=operations)
        self.assertTableExists("test_rmflmm_pony_stables")

    def test_remove_field_m2m_with_through(self):
        project_state = self.set_up_test_model("test_rmflmmwt", second_model=True)

        self.assertTableNotExists("test_rmflmmwt_ponystables")
        project_state = self.apply_operations("test_rmflmmwt", project_state, operations=[
            migrations.CreateModel("PonyStables", fields=[
                ("pony", models.ForeignKey('test_rmflmmwt.Pony')),
                ("stable", models.ForeignKey('test_rmflmmwt.Stable')),
            ]),
            migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies", through='test_rmflmmwt.PonyStables'))
        ])
        self.assertTableExists("test_rmflmmwt_ponystables")

        operations = [migrations.RemoveField("Pony", "stables")]
        self.apply_operations("test_rmflmmwt", project_state, operations=operations)

    def test_remove_field(self):
        """
        Tests the RemoveField operation.
        """
        project_state = self.set_up_test_model("test_rmfl")
        # Test the state alteration
        operation = migrations.RemoveField("Pony", "pink")
        new_state = project_state.clone()
        operation.state_forwards("test_rmfl", new_state)
        self.assertEqual(len(new_state.models["test_rmfl", "pony"].fields), 2)
        # Test the database alteration
        self.assertColumnExists("test_rmfl_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rmfl", editor, project_state, new_state)
        self.assertColumnNotExists("test_rmfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rmfl", editor, new_state, project_state)
        self.assertColumnExists("test_rmfl_pony", "pink")

    def test_remove_fk(self):
        """
        Tests the RemoveField operation on a foreign key.
        """
        project_state = self.set_up_test_model("test_rfk", related_model=True)
        self.assertColumnExists("test_rfk_rider", "pony_id")
        operation = migrations.RemoveField("Rider", "pony")
        new_state = project_state.clone()
        operation.state_forwards("test_rfk", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rfk", editor, project_state, new_state)
        self.assertColumnNotExists("test_rfk_rider", "pony_id")
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rfk", editor, new_state, project_state)
        self.assertColumnExists("test_rfk_rider", "pony_id")

    def test_alter_model_table(self):
        """
        Tests the AlterModelTable operation.
        """
        project_state = self.set_up_test_model("test_almota")
        # Test the state alteration
        operation = migrations.AlterModelTable("Pony", "test_almota_pony_2")
        new_state = project_state.clone()
        operation.state_forwards("test_almota", new_state)
        self.assertEqual(new_state.models["test_almota", "pony"].options["db_table"], "test_almota_pony_2")
        # Test the database alteration
        self.assertTableExists("test_almota_pony")
        self.assertTableNotExists("test_almota_pony_2")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_almota", editor, project_state, new_state)
        self.assertTableNotExists("test_almota_pony")
        self.assertTableExists("test_almota_pony_2")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_almota", editor, new_state, project_state)
        self.assertTableExists("test_almota_pony")
        self.assertTableNotExists("test_almota_pony_2")

    def test_alter_field(self):
        """
        Tests the AlterField operation.
        """
        project_state = self.set_up_test_model("test_alfl")
        # Test the state alteration
        operation = migrations.AlterField("Pony", "pink", models.IntegerField(null=True))
        new_state = project_state.clone()
        operation.state_forwards("test_alfl", new_state)
        self.assertEqual(project_state.models["test_alfl", "pony"].get_field_by_name("pink").null, False)
        self.assertEqual(new_state.models["test_alfl", "pony"].get_field_by_name("pink").null, True)
        # Test the database alteration
        self.assertColumnNotNull("test_alfl_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alfl", editor, project_state, new_state)
        self.assertColumnNull("test_alfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alfl", editor, new_state, project_state)
        self.assertColumnNotNull("test_alfl_pony", "pink")

    def test_alter_field_pk(self):
        """
        Tests the AlterField operation on primary keys (for things like PostgreSQL's SERIAL weirdness)
        """
        project_state = self.set_up_test_model("test_alflpk")
        # Test the state alteration
        operation = migrations.AlterField("Pony", "id", models.IntegerField(primary_key=True))
        new_state = project_state.clone()
        operation.state_forwards("test_alflpk", new_state)
        self.assertIsInstance(project_state.models["test_alflpk", "pony"].get_field_by_name("id"), models.AutoField)
        self.assertIsInstance(new_state.models["test_alflpk", "pony"].get_field_by_name("id"), models.IntegerField)
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alflpk", editor, project_state, new_state)
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alflpk", editor, new_state, project_state)

    @unittest.skipUnless(connection.features.supports_foreign_keys, "No FK support")
    def test_alter_field_pk_fk(self):
        """
        Tests the AlterField operation on primary keys changes any FKs pointing to it.
        """
        project_state = self.set_up_test_model("test_alflpkfk", related_model=True)
        # Test the state alteration
        operation = migrations.AlterField("Pony", "id", models.FloatField(primary_key=True))
        new_state = project_state.clone()
        operation.state_forwards("test_alflpkfk", new_state)
        self.assertIsInstance(project_state.models["test_alflpkfk", "pony"].get_field_by_name("id"), models.AutoField)
        self.assertIsInstance(new_state.models["test_alflpkfk", "pony"].get_field_by_name("id"), models.FloatField)

        def assertIdTypeEqualsFkType():
            with connection.cursor() as cursor:
                id_type = [c.type_code for c in connection.introspection.get_table_description(cursor, "test_alflpkfk_pony") if c.name == "id"][0]
                fk_type = [c.type_code for c in connection.introspection.get_table_description(cursor, "test_alflpkfk_rider") if c.name == "pony_id"][0]
            self.assertEqual(id_type, fk_type)

        assertIdTypeEqualsFkType()
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alflpkfk", editor, project_state, new_state)
        assertIdTypeEqualsFkType()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alflpkfk", editor, new_state, project_state)
        assertIdTypeEqualsFkType()

    def test_rename_field(self):
        """
        Tests the RenameField operation.
        """
        project_state = self.set_up_test_model("test_rnfl")
        # Test the state alteration
        operation = migrations.RenameField("Pony", "pink", "blue")
        new_state = project_state.clone()
        operation.state_forwards("test_rnfl", new_state)
        self.assertIn("blue", [n for n, f in new_state.models["test_rnfl", "pony"].fields])
        self.assertNotIn("pink", [n for n, f in new_state.models["test_rnfl", "pony"].fields])
        # Test the database alteration
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnfl", editor, project_state, new_state)
        self.assertColumnExists("test_rnfl_pony", "blue")
        self.assertColumnNotExists("test_rnfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rnfl", editor, new_state, project_state)
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")

    def test_alter_unique_together(self):
        """
        Tests the AlterUniqueTogether operation.
        """
        project_state = self.set_up_test_model("test_alunto")
        # Test the state alteration
        operation = migrations.AlterUniqueTogether("Pony", [("pink", "weight")])
        new_state = project_state.clone()
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(len(project_state.models["test_alunto", "pony"].options.get("unique_together", set())), 0)
        self.assertEqual(len(new_state.models["test_alunto", "pony"].options.get("unique_together", set())), 1)
        # Make sure we can insert duplicate rows
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
            # Test the database alteration
            with connection.schema_editor() as editor:
                operation.database_forwards("test_alunto", editor, project_state, new_state)
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            with self.assertRaises(IntegrityError):
                with atomic():
                    cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
            # And test reversal
            with connection.schema_editor() as editor:
                operation.database_backwards("test_alunto", editor, new_state, project_state)
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
        # Test flat unique_together
        operation = migrations.AlterUniqueTogether("Pony", ("pink", "weight"))
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(len(new_state.models["test_alunto", "pony"].options.get("unique_together", set())), 1)

    def test_alter_index_together(self):
        """
        Tests the AlterIndexTogether operation.
        """
        project_state = self.set_up_test_model("test_alinto")
        # Test the state alteration
        operation = migrations.AlterIndexTogether("Pony", [("pink", "weight")])
        new_state = project_state.clone()
        operation.state_forwards("test_alinto", new_state)
        self.assertEqual(len(project_state.models["test_alinto", "pony"].options.get("index_together", set())), 0)
        self.assertEqual(len(new_state.models["test_alinto", "pony"].options.get("index_together", set())), 1)
        # Make sure there's no matching index
        self.assertIndexNotExists("test_alinto_pony", ["pink", "weight"])
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alinto", editor, project_state, new_state)
        self.assertIndexExists("test_alinto_pony", ["pink", "weight"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alinto", editor, new_state, project_state)
        self.assertIndexNotExists("test_alinto_pony", ["pink", "weight"])

    @unittest.skipIf(sqlparse is None and connection.features.requires_sqlparse_for_splitting, "Missing sqlparse")
    def test_run_sql(self):
        """
        Tests the RunSQL operation.
        """
        project_state = self.set_up_test_model("test_runsql")
        # Create the operation
        operation = migrations.RunSQL(
            # Use a multi-line string with a commment to test splitting on SQLite and MySQL respectively
            "CREATE TABLE i_love_ponies (id int, special_thing int);\n"
            "INSERT INTO i_love_ponies (id, special_thing) VALUES (1, 42); -- this is magic!\n"
            "INSERT INTO i_love_ponies (id, special_thing) VALUES (2, 51);\n",
            "DROP TABLE i_love_ponies",
            state_operations=[migrations.CreateModel("SomethingElse", [("id", models.AutoField(primary_key=True))])],
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_runsql", new_state)
        self.assertEqual(len(new_state.models["test_runsql", "somethingelse"].fields), 1)
        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)
        self.assertTableExists("i_love_ponies")
        # Make sure all the SQL was processed
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 2)
        # And test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards("test_runsql", editor, new_state, project_state)
        self.assertTableNotExists("i_love_ponies")

    def test_run_python(self):
        """
        Tests the RunPython operation
        """

        project_state = self.set_up_test_model("test_runpython", mti_model=True)

        # Create the operation
        def inner_method(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            Pony.objects.create(pink=1, weight=3.55)
            Pony.objects.create(weight=5)

        def inner_method_reverse(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            Pony.objects.filter(pink=1, weight=3.55).delete()
            Pony.objects.filter(weight=5).delete()
        operation = migrations.RunPython(inner_method, reverse_code=inner_method_reverse)
        # Test the state alteration does nothing
        new_state = project_state.clone()
        operation.state_forwards("test_runpython", new_state)
        self.assertEqual(new_state, project_state)
        # Test the database alteration
        self.assertEqual(project_state.render().get_model("test_runpython", "Pony").objects.count(), 0)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.render().get_model("test_runpython", "Pony").objects.count(), 2)
        # Now test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.render().get_model("test_runpython", "Pony").objects.count(), 0)
        # Now test we can't use a string
        with self.assertRaises(ValueError):
            operation = migrations.RunPython("print 'ahahaha'")

        # Also test reversal fails, with an operation identical to above but without reverse_code set
        no_reverse_operation = migrations.RunPython(inner_method)
        self.assertFalse(no_reverse_operation.reversible)
        with connection.schema_editor() as editor:
            no_reverse_operation.database_forwards("test_runpython", editor, project_state, new_state)
            with self.assertRaises(NotImplementedError):
                no_reverse_operation.database_backwards("test_runpython", editor, new_state, project_state)
        self.assertEqual(project_state.render().get_model("test_runpython", "Pony").objects.count(), 2)

        def create_ponies(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            pony1 = Pony.objects.create(pink=1, weight=3.55)
            self.assertIsNot(pony1.pk, None)
            pony2 = Pony.objects.create(weight=5)
            self.assertIsNot(pony2.pk, None)
            self.assertNotEqual(pony1.pk, pony2.pk)

        operation = migrations.RunPython(create_ponies)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.render().get_model("test_runpython", "Pony").objects.count(), 4)

        def create_shetlandponies(models, schema_editor):
            ShetlandPony = models.get_model("test_runpython", "ShetlandPony")
            pony1 = ShetlandPony.objects.create(weight=4.0)
            self.assertIsNot(pony1.pk, None)
            pony2 = ShetlandPony.objects.create(weight=5.0)
            self.assertIsNot(pony2.pk, None)
            self.assertNotEqual(pony1.pk, pony2.pk)

        operation = migrations.RunPython(create_shetlandponies)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.render().get_model("test_runpython", "Pony").objects.count(), 6)
        self.assertEqual(project_state.render().get_model("test_runpython", "ShetlandPony").objects.count(), 2)

    def test_run_python_atomic(self):
        """
        Tests the RunPython operation correctly handles the "atomic" keyword
        """
        project_state = self.set_up_test_model("test_runpythonatomic", mti_model=True)

        def inner_method(models, schema_editor):
            Pony = models.get_model("test_runpythonatomic", "Pony")
            Pony.objects.create(pink=1, weight=3.55)
            raise ValueError("Adrian hates ponies.")

        atomic_migration = Migration("test", "test_runpythonatomic")
        atomic_migration.operations = [migrations.RunPython(inner_method)]
        non_atomic_migration = Migration("test", "test_runpythonatomic")
        non_atomic_migration.operations = [migrations.RunPython(inner_method, atomic=False)]
        # If we're a fully-transactional database, both versions should rollback
        if connection.features.can_rollback_ddl:
            self.assertEqual(project_state.render().get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.render().get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.render().get_model("test_runpythonatomic", "Pony").objects.count(), 0)
        # Otherwise, the non-atomic operation should leave a row there
        else:
            self.assertEqual(project_state.render().get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.render().get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.render().get_model("test_runpythonatomic", "Pony").objects.count(), 1)


class MigrateNothingRouter(object):
    """
    A router that sends all writes to the other database.
    """
    def allow_migrate(self, db, model):
        return False


class MultiDBOperationTests(MigrationTestBase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [MigrateNothingRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_create_model(self):
        """
        Tests that CreateModel honours multi-db settings.
        """
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
        )
        # Test the state alteration
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        # Test the database alteration
        self.assertTableNotExists("test_crmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableNotExists("test_crmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
