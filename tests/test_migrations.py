import json
import unittest
from sqlalchemy import create_engine, text, inspect
from app.migrations import DIRECTORY, upgrade, require_current


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')

    def tearDown(self):
        self.engine.dispose()

    def test_empty_database_and_repeat_upgrade(self):
        self.assertEqual(upgrade(self.engine), '0002_snapshots')
        self.assertEqual(upgrade(self.engine), '0002_snapshots')
        require_current(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT count(*) FROM feniq_schema_revisions')).scalar(), 2)

    def test_legacy_database_preserves_existing_records(self):
        baseline = json.loads((DIRECTORY / '0001_baseline_sqlite.json').read_text())
        with self.engine.begin() as connection:
            for table in baseline:
                for statement in table['sql']:
                    connection.exec_driver_sql(statement)
            connection.exec_driver_sql("INSERT INTO companies (id,name,invite_code,created_at) VALUES (42,'Preserved company','retained-invite','2026-09-13')")
        upgrade(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT name FROM companies WHERE id=42')).scalar(), 'Preserved company')
            self.assertTrue(inspect(connection).has_table('diagnostic_snapshots'))

    def test_unexpected_legacy_schema_rolls_back(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql('CREATE TABLE companies (id INTEGER PRIMARY KEY)')
        with self.assertRaisesRegex(RuntimeError, 'Unexpected legacy schema'):
            upgrade(self.engine)
        with self.engine.connect() as connection:
            self.assertFalse(inspect(connection).has_table('diagnostic_snapshots'))
            self.assertFalse(inspect(connection).has_table('feniq_schema_revisions'))

    def test_revision_tampering_blocks_startup(self):
        upgrade(self.engine)
        with self.engine.begin() as connection:
            connection.exec_driver_sql("UPDATE feniq_schema_revisions SET checksum='changed' WHERE revision='0001_baseline'")
        with self.assertRaisesRegex(RuntimeError, 'revision mismatch'):
            require_current(self.engine)
        with self.assertRaisesRegex(RuntimeError, 'Applied migration changed'):
            upgrade(self.engine)
