# landlord/migrations/0004_add_parler_bases.py
from django.db import migrations, models
from parler.models import TranslatableModel

class AlterModelBases(migrations.operations.base.Operation):
    """
    A back-port of the internal AlterModelBases operation.
    It only mutates Django’s in-memory model state: no real DB SQL.
    """
    reduces_to_sql = False
    reversible = True

    def __init__(self, name, bases):
        self.name = name
        self.bases = bases

    def state_forwards(self, app_label, state):
        # teach the migration state that Model(name) now has these Python bases
        state.models[(app_label, self.name)].bases = self.bases

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # nothing to do at the database level
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # nothing to undo
        pass

    def describe(self):
        return f"Altering bases of {self.name}"

class Migration(migrations.Migration):

    dependencies = [
        ("landlord", "0005_rename_option_text_landlordoptionmodeltranslation_title_and_more"),
    ]

    operations = [
        AlterModelBases(
            name="landlordpropertytypemodel",
            bases=(TranslatableModel, models.Model),
        ),
        AlterModelBases(
            name="landlordpropertyamenitymodel",
            bases=(TranslatableModel, models.Model),
        ),
    ]
