import unittest

from sqlParser import DB


class AlterParsingRegressionTests(unittest.TestCase):
    def test_add_constraint_and_primary_key_are_not_treated_as_columns(self):
        db = DB('test3.sql')

        for table in db.tables:
            bad_names = [
                column.name
                for column in table.columns
                if column.name and column.name.upper() in {'PRIMARY', 'CONSTRAINT', 'FOREIGN'}
            ]
            self.assertFalse(bad_names, f"Table {table.name} contains fake constraint columns: {bad_names}")

    def test_foreign_key_reference_is_kept(self):
        db = DB('test3.sql')
        table = next(t for t in db.tables if t.name == 'model_has_permissions')
        permission_id = next(c for c in table.columns if c.name == 'permission_id')
        self.assertEqual(permission_id.referenceTable, 'permissions')
        self.assertEqual(permission_id.referenceColumn, 'id')

    def test_unsigned_not_null_auto_increment_are_split_from_sql_type(self):
        db = DB('test3.sql')
        table = next(t for t in db.tables if t.name == 'failed_jobs')
        column = next(c for c in table.columns if c.name == 'id')
        self.assertEqual(column.dataType, 'bigint(20)')
        self.assertIn('UNSIGNED', column.attributes)
        self.assertIn('NOT', column.attributes)
        self.assertIn('NULL', column.attributes)
        self.assertIn('AUTO_INCREMENT', column.attributes)


if __name__ == '__main__':
    unittest.main()
