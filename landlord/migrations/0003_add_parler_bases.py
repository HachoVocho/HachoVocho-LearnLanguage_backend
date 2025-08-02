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
        ("landlord", "0002_alter_landlorddetailsmodel_last_name"),
    ]

    operations = [
        AlterModelBases(
            name="landlordquestionmodel",
            bases=(TranslatableModel, models.Model),
        ),
        AlterModelBases(
            name="landlordoptionmodel",
            bases=(TranslatableModel, models.Model),
        ),
    ]
