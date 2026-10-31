import tempfile, unittest, sqlite3
from pathlib import Path
from voodoosql import Catalog, QueryPack, execute_checked, save_catalog, seed

class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.db=Path(cls.tmp.name)/'demo.sqlite'; seed(cls.db)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def test_composite_primary_key_order(self):
        c=Catalog.from_sqlite(self.db); t=next(x for x in c.tables if x['name']=='customers')
        self.assertEqual([x['name'] for x in sorted((x for x in t['columns'] if x['primary_key_position']),key=lambda z:z['primary_key_position'])],['tenant_id','customer_id'])
        fk=next(x for x in c.relations if x['from']=='order_lines')
        self.assertEqual((fk['from_columns'],fk['to_columns']),(['tenant_id','order_id'],['tenant_id','order_id']))
    def test_declared_and_inferred_evidence_separate(self):
        c=Catalog.from_sqlite(self.db); self.assertTrue(any(r['evidence']=='declared' and r['enforced'] is None and r['enforcement_status']=='unknown' for r in c.relations)); self.assertTrue(any(r['evidence']=='inferred' and r['enforced'] is None for r in c.relations))
    def test_permission_completeness_disclosed(self):
        self.assertIn('permission',Catalog.from_sqlite(self.db).completeness['note'])
    def test_parameterized_composite_lookup(self):
        r=QueryPack(self.db).execute('customer-orders',{'tenant_id':'t1','customer_id':"c1' OR 1=1 --"}); self.assertEqual(r['rows'],[])
    def test_fanout_safe_payment_result(self):
        r=QueryPack(self.db).execute('paid-by-order'); self.assertEqual(r['rows'][0],['o1',3000,3000])
    def test_temporal_latest_row(self):
        r=QueryPack(self.db).execute('history-current'); self.assertEqual(r['rows'][0],['o1','paid','2026-02-01T11:00:00'])
    def test_as_of_history_excludes_future_state(self):
        r=QueryPack(self.db).execute('history-as-of-order',{'as_of':'2026-02-01T10:30:00'}); self.assertEqual(r['rows'],[['o1','paid','open','2026-02-01T10:00:00'],['o2','paid',None,None],['o3','open',None,None]])
    def test_undefined_metric_clarifies(self):
        self.assertEqual(QueryPack(self.db).retrieve('net revenue')['status'],'clarification_required')
    def test_unknown_question_clarifies(self):
        self.assertEqual(QueryPack(self.db).retrieve('tell me something interesting')['status'],'clarification_required')
    def test_write_rejected(self):
        with self.assertRaises(ValueError): execute_checked("DELETE FROM orders",path=self.db)
    def test_attach_rejected(self):
        with self.assertRaisesRegex(sqlite3.DatabaseError, 'not authorized'):
            execute_checked("SELECT load_extension('x')",path=self.db)
    def test_multi_statement_rejected(self):
        with self.assertRaises(ValueError): execute_checked("SELECT 1; SELECT 2",path=self.db)
    def test_schema_change_stales_recipe(self):
        pack=QueryPack(self.db); import sqlite3
        c=sqlite3.connect(self.db); c.execute('CREATE TABLE added(id TEXT)'); c.commit(); c.close()
        self.assertEqual(pack.execute('paid-by-order')['status'],'stale')
    def test_external_catalog_has_no_fabricated_edges_and_unknown_enforcement(self):
        import sqlite3
        path=Path(self.tmp.name)/'external.sqlite'; c=sqlite3.connect(path); c.execute('CREATE TABLE ledger(id TEXT PRIMARY KEY)'); c.commit(); c.close()
        snap=Catalog.from_sqlite(path); self.assertEqual(snap.relations,[]); self.assertEqual([x['name'] for x in snap.tables],['ledger'])
    def test_schema_allowlist_reports_incomplete(self):
        snap=Catalog.from_sqlite(self.db,allowed_schemas=['restricted']); self.assertFalse(snap.completeness['complete']); self.assertEqual(snap.tables,[]); self.assertEqual(snap.relations,[])
        self.assertFalse(Catalog.from_sqlite(self.db,allowed_schemas=[]).completeness['complete'])
    def test_graphify_export_and_persistent_metadata_catalog(self):
        snap=Catalog.from_sqlite(self.db); g=snap.to_graph(); self.assertTrue(any(n['type']=='table' for n in g['nodes'])); self.assertTrue(any(e['type']=='RELATES_TO' for e in g['edges']))
        p=Path(self.tmp.name)/'metadata.sqlite'; save_catalog(snap,p); import sqlite3; c=sqlite3.connect(p); self.assertGreater(c.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0); c.close()
    def test_read_executes_without_explicit_parameters(self):
        self.assertEqual(execute_checked('SELECT 42 AS answer',path=self.db)['rows'], [[42]])
    def test_view_definition_change_invalidates_fingerprint(self):
        path=Path(self.tmp.name)/'views.sqlite'
        c=sqlite3.connect(path); c.execute('CREATE VIEW v AS SELECT 1 AS result'); c.commit(); c.close()
        first=Catalog.from_sqlite(path).fingerprint
        c=sqlite3.connect(path); c.execute('DROP VIEW v'); c.execute('CREATE VIEW v AS SELECT 2 AS result'); c.commit(); c.close()
        self.assertNotEqual(first,Catalog.from_sqlite(path).fingerprint)
    def test_result_limit(self):
        with self.assertRaises(ValueError): execute_checked('SELECT order_id FROM orders',path=self.db,row_limit=1)
    def test_instruction_budget(self):
        sql='SELECT count(*) FROM customers a, customers b, customers c, customers d, customers e, customers f, customers g, customers h'
        with self.assertRaisesRegex(sqlite3.OperationalError, 'interrupted'):
            execute_checked(sql,path=self.db,instruction_budget=0)

if __name__=='__main__': unittest.main()
