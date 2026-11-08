"""Explicit Phase 12 tests using a newly provisioned real local PostgreSQL DB.

Run directly, not through default unittest discovery. Never targets founddesk.
The isolated DB is retained for browser evidence; rerun setup for a fresh run.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import sys
from threading import Barrier
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from db import get_connection
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from werkzeug.security import check_password_hash

EVIDENCE = ROOT / "docs/evidence/phase12"
metadata = json.loads((EVIDENCE / "environment.json").read_text())
settings = conninfo_to_dict(os.environ["DATABASE_URL"])
if settings.get("host") not in ("localhost", "127.0.0.1", "::1"):
    raise RuntimeError("Local server only")
test_database = metadata["test_database"]
if not re.fullmatch(r"founddesk_phase12_[0-9a-f]{10}", test_database):
    raise RuntimeError("Refusing a database outside the isolated test-name pattern")
settings.update(dbname=test_database, options="-c lock_timeout=5000 -c statement_timeout=15000")
os.environ["DATABASE_URL"] = make_conninfo(**settings)
os.environ["SECRET_KEY"] = secrets.token_hex(32)
from app import app
app.config["TESTING"] = True
PASSWORD = "Phase12-test-only-Password!"


def rows(query, values=()):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            return cursor.fetchall() if cursor.description else []


def token(client, path="/login"):
    page = client.get(path, follow_redirects=True)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
    if match is None:
        raise AssertionError("No CSRF token in actual HTML")
    return match.group(1).decode()


def login(email, password=PASSWORD):
    client = app.test_client()
    response = client.post("/login", data=dict(csrf_token=token(client), email=email, password=password))
    if response.status_code != 302:
        raise AssertionError("Real database login failed")
    return client


def post(client, path, **values):
    values.setdefault("csrf_token", token(client))
    return client.post(path, data=values)


class PostgreSQLIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if rows("SELECT COUNT(*) AS n FROM users")[0]["n"]:
            raise RuntimeError("Use phase12_setup.py to provision a fresh isolated DB before rerunning")
        empty_counts = rows("SELECT (SELECT COUNT(*) FROM users) AS users, (SELECT COUNT(*) FROM lost_items) AS lost, (SELECT COUNT(*) FROM found_items) AS found, (SELECT COUNT(*) FROM claims) AS claims")[0]
        if any(empty_counts.values()):
            raise AssertionError("Fresh DB was not empty")
        (EVIDENCE / "initial_counts.json").write_text(json.dumps(empty_counts, indent=2), encoding="utf-8")
        for name in ("a", "b", "c", "admin"):
            client = app.test_client()
            response = post(client, "/register", full_name="Test Student " + name,
                            email=name + "@phase12.example.test", password=PASSWORD,
                            confirm_password=PASSWORD, role="admin")
            if response.status_code != 302:
                raise AssertionError("Registration failed")
        rows("UPDATE users SET role = 'admin' WHERE email = %s", ("admin@phase12.example.test",))
        cls.users = {name: rows("SELECT user_id FROM users WHERE email = %s", (name + "@phase12.example.test",))[0]["user_id"] for name in ("a", "b", "c", "admin")}
        cls.category = rows("SELECT category_id FROM categories WHERE category_name = 'Keys'")[0]["category_id"]

    def setUp(self):
        self.label = self._testMethodName[:35] + "_" + uuid4().hex[:6]
        self.clients = {name: login(name + "@phase12.example.test") for name in self.users}

    def item(self, owner, kind, name=None, **extra):
        data = dict(item_name=name or self.label + kind, category_id=str(self.category),
                    description="Blue keyring <script>test</script>", location="Library",
                    **{kind + "_date": "2026-01-02"})
        data.update(extra)
        response = post(self.clients[owner], "/report-" + kind, **data)
        self.assertEqual(response.status_code, 302)
        query = "SELECT lost_id AS id FROM lost_items WHERE item_name = %s ORDER BY lost_id DESC" if kind == "lost" else "SELECT found_id AS id FROM found_items WHERE item_name = %s ORDER BY found_id DESC"
        return rows(query, (data["item_name"],))[0]["id"]

    def claim(self, lost, found, owner="a"):
        response = post(self.clients[owner], f"/found-items/{found}/claim", lost_id=str(lost),
                        claim_reason="PRIVATE ownership <b>initials</b>", claimant_id=self.users["b"],
                        claim_date="2000-01-01", status="Approved")
        self.assertEqual(response.status_code, 302)
        return rows("SELECT claim_id FROM claims WHERE lost_id = %s AND found_id = %s", (lost, found))[0]["claim_id"]

    def decide(self, claim, action="approve", client=None):
        return post(client or self.clients["admin"], f"/admin/claims/{claim}/{action}")

    def test_01_schema_seed_and_constraints(self):
        self.assertEqual({r["tablename"] for r in rows("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}, {"users", "categories", "lost_items", "found_items", "claims"})
        with get_connection() as connection:
            connection.execute((ROOT / "database/sample_data.sql").read_text())
        self.assertEqual(rows("SELECT COUNT(*) AS n FROM categories")[0]["n"], 6)
        constraints = rows("SELECT contype, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace = 'public'::regnamespace")
        self.assertEqual(sum(r["contype"] == "p" for r in constraints), 5)
        self.assertEqual(sum(r["contype"] == "f" for r in constraints), 7)
        self.assertEqual(sum(r["contype"] == "u" for r in constraints), 3)
        self.assertEqual(sum(r["contype"] == "c" for r in constraints), 4)
        (EVIDENCE / "test_constraints.json").write_text(json.dumps(constraints, indent=2), encoding="utf-8")
        for query, params, error in (
            ("INSERT INTO categories(category_name) VALUES (%s)", ("Keys",), psycopg.errors.UniqueViolation),
            ("INSERT INTO categories(category_name) VALUES (NULL)", (), psycopg.errors.NotNullViolation),
            ("UPDATE users SET role = 'root' WHERE user_id = %s", (self.users["a"],), psycopg.errors.CheckViolation),
            ("INSERT INTO lost_items(user_id,category_id,item_name,description,location,lost_date) VALUES (%s,999999,'x','x','x',CURRENT_DATE)", (self.users["a"],), psycopg.errors.ForeignKeyViolation),
        ):
            with self.assertRaises(error):
                rows(query, params)

    def test_02_authentication_persistence_and_duplicates(self):
        user = rows("SELECT full_name, email, password_hash, role FROM users WHERE user_id = %s", (self.users["a"],))[0]
        self.assertTrue(check_password_hash(user["password_hash"], PASSWORD))
        self.assertEqual(user["role"], "student")
        client = app.test_client()
        response = post(client, "/login", email="a@phase12.example.test", password="wrong")
        self.assertIn(b"Incorrect email or password", response.data)
        self.assertEqual(client.get("/my-reports").location, "/login")
        response = post(client, "/register", full_name="Duplicate", email=" A@PHASE12.EXAMPLE.TEST ", password=PASSWORD, confirm_password=PASSWORD)
        self.assertIn(b"already exists", response.data)
        self.assertEqual(rows("SELECT COUNT(*) AS n FROM users WHERE email = 'a@phase12.example.test'")[0]["n"], 1)
        post(self.clients["a"], "/logout")
        self.assertEqual(self.clients["a"].get("/my-claims").location, "/login")

    def test_03_crud_owner_validation_and_status(self):
        for kind, table, key in (("lost", "lost_items", "lost_id"), ("found", "found_items", "found_id")):
            identifier = self.item("a", kind)
            path = f"/{kind}-items/{identifier}"
            self.assertEqual(self.clients["b"].get(path + "/edit").status_code, 302)
            data = dict(item_name="Changed " + self.label + kind, category_id=str(self.category), description="Updated", location="Canteen", **{kind + "_date": "2026-01-03"}, user_id=self.users["b"], status="Resolved")
            post(self.clients["b"], path + "/edit", **data)
            post(self.clients["b"], path + "/delete")
            # Identifiers below are fixed test constants, never request input.
            current = rows(f"SELECT * FROM {table} WHERE {key} = %s", (identifier,))[0]
            self.assertEqual(current["location"], "Library")
            post(self.clients["a"], path + "/edit", **data)
            current = rows(f"SELECT * FROM {table} WHERE {key} = %s", (identifier,))[0]
            self.assertEqual(current["location"], "Canteen")
            self.assertEqual(current["user_id"], self.users["a"])
            self.assertEqual(current["status"], "Lost" if kind == "lost" else "Available")
            for field, value in (("item_name", " "), ("category_id", "999999"), (kind + "_date", "2026-02-30"), (kind + "_date", (date.today() + timedelta(days=1)).isoformat())):
                bad = dict(data, **{field: value})
                response = post(self.clients["a"], path + "/edit", **bad)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(rows(f"SELECT location FROM {table} WHERE {key} = %s", (identifier,))[0]["location"], "Canteen")
            post(self.clients["a"], path + "/delete")
            self.assertEqual(rows(f"SELECT * FROM {table} WHERE {key} = %s", (identifier,)), [])

    def test_04_search_and_detail(self):
        name = "Search Keys " + self.label
        lost = self.item("a", "lost", name=name, lost_date="2026-01-01")
        found = self.item("b", "found", name=name, found_date="2026-01-03")
        client = self.clients["a"]
        response = client.get("/browse-items", query_string=dict(keyword=name.lower(), category_id=self.category, location="LIB", type="All"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2 result(s)", response.data)
        self.assertLess(response.data.index(f"/items/Found/{found}".encode()), response.data.index(f"/items/Lost/{lost}".encode()))
        for kind in ("Lost", "Found"):
            page = client.get("/browse-items", query_string=dict(keyword=name, type=kind))
            self.assertIn(b"1 result(s)", page.data)
        self.assertIn(b"No items match", client.get("/browse-items?keyword=nonexistent-" + self.label).data)
        self.assertIn(b"No items match", client.get("/browse-items", query_string={"keyword": "' OR 1=1 --"}).data)
        self.assertEqual(client.get("/browse-items?category_id=999999").status_code, 400)
        self.assertEqual(client.get("/items/Lost/2147483647").status_code, 404)
        page = client.get(f"/items/Found/{found}")
        self.assertIn(b"&lt;script&gt;test&lt;/script&gt;", page.data)
        self.assertNotIn(b"PRIVATE ownership", page.data)

    def test_05_claim_privacy_duplicates_and_deletion(self):
        lost = self.item("a", "lost")
        found = self.item("b", "found")
        claim = self.claim(lost, found)
        actual = rows("SELECT * FROM claims WHERE claim_id = %s", (claim,))[0]
        self.assertEqual(actual["claimant_id"], self.users["a"])
        self.assertEqual(actual["status"], "Pending")
        self.assertEqual(actual["claim_date"], rows("SELECT CURRENT_DATE AS d")[0]["d"])
        self.assertEqual(post(self.clients["a"], f"/found-items/{found}/claim", lost_id=lost, claim_reason="Repeated").status_code, 409)
        self.assertIn(b"PRIVATE ownership &lt;b&gt;initials&lt;/b&gt;", self.clients["a"].get("/my-claims").data)
        self.assertNotIn(b"PRIVATE ownership", self.clients["b"].get("/my-claims?claimant_id=" + str(self.users["a"])).data)
        self.assertIn(b"PRIVATE ownership", self.clients["admin"].get("/admin").data)
        for page in ("/browse-items", "/my-reports", f"/items/Found/{found}", "/reports"):
            self.assertNotIn(b"PRIVATE ownership", self.clients["admin"].get(page).data)
        for kind, identifier in (("lost", lost), ("found", found)):
            post(self.clients["a" if kind == "lost" else "b"], f"/{kind}-items/{identifier}/delete")
        self.assertEqual(len(rows("SELECT * FROM lost_items WHERE lost_id = %s", (lost,))), 1)
        with self.assertRaises((psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)):
            rows("DELETE FROM found_items WHERE found_id = %s", (found,))

    def test_06_claim_eligibility(self):
        lost = self.item("a", "lost")
        other_lost = self.item("b", "lost")
        found = self.item("b", "found")
        self.assertEqual(self.clients["b"].get(f"/found-items/{found}/claim").status_code, 403)
        self.assertEqual(self.clients["admin"].get(f"/found-items/{found}/claim").status_code, 403)
        for bad in (other_lost, 2147483647):
            self.assertEqual(post(self.clients["a"], f"/found-items/{found}/claim", lost_id=bad, claim_reason="Mine").status_code, 400)
        rows("UPDATE lost_items SET status='Resolved' WHERE lost_id=%s", (lost,))
        self.assertEqual(post(self.clients["a"], f"/found-items/{found}/claim", lost_id=lost, claim_reason="Mine").status_code, 400)
        rows("UPDATE found_items SET status='Returned' WHERE found_id=%s", (found,))
        self.assertEqual(post(self.clients["a"], f"/found-items/{found}/claim", lost_id=lost, claim_reason="Mine").status_code, 409)

    def test_07_admin_approval_and_rejection(self):
        l1, l2, l3 = [self.item(owner, "lost", name=self.label + owner) for owner in ("a", "c", "b")]
        f1, f2, f3 = [self.item(owner, "found", name=self.label + owner) for owner in ("b", "c", "c")]
        first = self.claim(l1, f1)
        same_found = self.claim(l2, f1, "c")
        same_lost = self.claim(l1, f2)
        unrelated = self.claim(l3, f3, "b")
        self.assertEqual(self.decide(first).status_code, 302)
        self.assertEqual(rows("SELECT status FROM found_items WHERE found_id=%s", (f1,))[0]["status"], "Returned")
        self.assertEqual(rows("SELECT status FROM lost_items WHERE lost_id=%s", (l1,))[0]["status"], "Resolved")
        for identifier in (same_found, same_lost):
            self.assertEqual(rows("SELECT status FROM claims WHERE claim_id=%s", (identifier,))[0]["status"], "Rejected")
        self.assertEqual(self.decide(unrelated, "reject").status_code, 302)
        self.assertEqual(rows("SELECT status FROM found_items WHERE found_id=%s", (f3,))[0]["status"], "Available")
        self.assertEqual(rows("SELECT status FROM lost_items WHERE lost_id=%s", (l3,))[0]["status"], "Lost")
        for identifier in (first, unrelated):
            for action in ("approve", "reject"):
                self.assertEqual(self.decide(identifier, action).status_code, 409)
        self.assertEqual(self.clients["a"].get(f"/lost-items/{l1}/edit").status_code, 302)
        self.assertEqual(self.clients["b"].get(f"/found-items/{f1}/edit").status_code, 302)

    def test_08_csrf_access_and_no_writes(self):
        lost, found = self.item("a", "lost"), self.item("b", "found")
        claim = self.claim(lost, found)
        paths = [(self.clients["admin"], f"/admin/claims/{claim}/approve"),
                 (self.clients["admin"], f"/admin/claims/{claim}/reject"),
                 (self.clients["a"], f"/lost-items/{lost}/delete"),
                 (self.clients["b"], f"/found-items/{found}/delete"),
                 (self.clients["a"], f"/found-items/{found}/claim")]
        for client, path in paths:
            for csrf in (None, "wrong"):
                response = client.post(path, data={} if csrf is None else {"csrf_token": csrf})
                self.assertEqual(response.location, "/")
        self.assertEqual(rows("SELECT status FROM claims WHERE claim_id=%s", (claim,))[0]["status"], "Pending")
        for path in ("/admin", "/reports"):
            self.assertEqual(self.clients["a"].get(path).status_code, 403)
            self.assertEqual(app.test_client().get(path).location, "/login")
        self.assertEqual(self.decide(claim, client=self.clients["a"]).status_code, 403)
        self.assertEqual(self.clients["admin"].get(f"/admin/claims/{claim}/approve").status_code, 405)

    def test_09_atomic_rollback(self):
        lost, found = self.item("a", "lost"), self.item("b", "found")
        claim = self.claim(lost, found)
        rows("ALTER TABLE found_items ADD CONSTRAINT phase12_test_failure CHECK (status <> 'Returned') NOT VALID")
        try:
            self.assertEqual(self.decide(claim).status_code, 503)
            self.assertEqual(rows("SELECT status FROM claims WHERE claim_id=%s", (claim,))[0]["status"], "Pending")
            self.assertEqual(rows("SELECT status FROM found_items WHERE found_id=%s", (found,))[0]["status"], "Available")
            self.assertEqual(rows("SELECT status FROM lost_items WHERE lost_id=%s", (lost,))[0]["status"], "Lost")
        finally:
            rows("ALTER TABLE found_items DROP CONSTRAINT phase12_test_failure")
        self.assertEqual(self.decide(claim).status_code, 302)

    def race(self, operations):
        barrier = Barrier(len(operations))
        def run(operation):
            barrier.wait(timeout=10)
            return operation().status_code
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(run, operation) for operation in operations]
            return [future.result(timeout=25) for future in futures]

    def test_10_concurrent_shared_found_approvals(self):
        l1, l2 = self.item("a", "lost"), self.item("c", "lost")
        found = self.item("b", "found")
        c1, c2 = self.claim(l1, found), self.claim(l2, found, "c")
        admin2 = login("admin@phase12.example.test")
        codes = self.race([lambda: self.decide(c1), lambda: self.decide(c2, client=admin2)])
        self.assertEqual(sorted(codes), [302, 409])
        self.assertEqual({r["status"] for r in rows("SELECT status FROM claims WHERE found_id=%s", (found,))}, {"Approved", "Rejected"})

    def test_11_concurrent_shared_lost_approvals(self):
        lost = self.item("a", "lost")
        f1, f2 = self.item("b", "found"), self.item("c", "found")
        c1, c2 = self.claim(lost, f1), self.claim(lost, f2)
        admin2 = login("admin@phase12.example.test")
        codes = self.race([lambda: self.decide(c1), lambda: self.decide(c2, client=admin2)])
        self.assertEqual(sorted(codes), [302, 409])
        self.assertEqual({r["status"] for r in rows("SELECT status FROM found_items WHERE found_id IN (%s,%s)", (f1,f2))}, {"Returned", "Available"})

    def test_12_concurrent_crossing_pairs(self):
        l1, l2 = self.item("a", "lost"), self.item("c", "lost")
        f1, f2 = self.item("b", "found", name=self.label+"1"), self.item("b", "found", name=self.label+"2")
        c1, c2 = self.claim(l1,f1), self.claim(l2,f2,"c")
        x1, x2 = self.claim(l1,f2), self.claim(l2,f1,"c")
        admin2 = login("admin@phase12.example.test")
        self.assertEqual(self.race([lambda:self.decide(c1), lambda:self.decide(c2,client=admin2)]), [302,302])
        self.assertEqual({r["status"] for r in rows("SELECT status FROM claims WHERE claim_id IN (%s,%s)", (x1,x2))}, {"Rejected"})

    def test_13_concurrent_approve_reject_and_duplicate_submission(self):
        lost, found = self.item("a","lost"), self.item("b","found")
        client2 = login("a@phase12.example.test")
        def submit(client):
            return post(client,f"/found-items/{found}/claim",lost_id=lost,claim_reason="Concurrent")
        self.assertEqual(sorted(self.race([lambda:submit(self.clients["a"]),lambda:submit(client2)])), [302,409])
        claim=rows("SELECT claim_id FROM claims WHERE lost_id=%s AND found_id=%s",(lost,found))[0]["claim_id"]
        admin2=login("admin@phase12.example.test")
        self.assertEqual(sorted(self.race([lambda:self.decide(claim),lambda:self.decide(claim,"reject",admin2)])),[302,409])
        state=rows("SELECT c.status, f.status AS found_status FROM claims c JOIN found_items f ON f.found_id=c.found_id WHERE c.claim_id=%s",(claim,))[0]
        self.assertEqual(state["found_status"], "Returned" if state["status"]=="Approved" else "Available")

    def test_14_totals_category_zero_and_status_counts(self):
        category=rows("INSERT INTO categories(category_name) VALUES (%s) RETURNING category_id",(self.label,))[0]["category_id"]
        for i in range(2): self.item("a","lost",name=self.label+"L"+str(i),category_id=category)
        for i in range(3): self.item("b","found",name=self.label+"F"+str(i),category_id=category)
        page=self.clients["admin"].get("/reports")
        self.assertEqual(page.status_code,200)
        self.assertIn(f"<td>{self.label}</td><td>2</td><td>3</td>".encode(),page.data)
        totals=rows("SELECT (SELECT COUNT(*) FROM lost_items) AS lost_count,(SELECT COUNT(*) FROM found_items) AS found_count,(SELECT COUNT(*) FROM claims WHERE status='Pending') AS pending_count,(SELECT COUNT(*) FROM found_items WHERE status='Returned') AS returned_count")[0]
        expected="<tr>"+"".join(f"<td>{totals[key]}</td>" for key in ("lost_count","found_count","pending_count","returned_count"))+"</tr>"
        self.assertIn(expected.encode(),page.data)
        self.assertIn(b"<td>Other</td><td>0</td><td>0</td>",page.data)
        (EVIDENCE/"report_totals.json").write_text(json.dumps(totals,indent=2),encoding="utf-8")

    def test_15_queries_sql_real_results_and_no_mutations(self):
        def counts():
            return {table:rows(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"] for table in ("users","categories","lost_items","found_items","claims")}
        before=counts()
        sequences=rows("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename")
        results=[]
        with psycopg.connect(os.environ["DATABASE_URL"],autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute((ROOT/"database/queries.sql").read_text(),prepare=False)
                while True:
                    if cursor.description:
                        results.append(dict(columns=[column.name for column in cursor.description],rows=cursor.fetchall()))
                    if not cursor.nextset(): break
            self.assertIsNone(connection.execute("SELECT to_regclass('pg_temp.founddesk_unresolved_lost')").fetchone()[0])
            self.assertIsNone(connection.execute("SELECT to_regclass('pg_temp.founddesk_demo_categories')").fetchone()[0])
        self.assertEqual(counts(),before)
        self.assertEqual(rows("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename"),sequences)
        self.assertEqual(len(results),12)
        (EVIDENCE/"query_results.json").write_text(json.dumps(results,default=str,indent=2),encoding="utf-8")

    def test_16_submission_racing_approval(self):
        for shared in ("found", "lost"):
            lost = self.item("a", "lost", name=self.label + shared)
            found = self.item("b", "found", name=self.label + shared)
            selected = self.claim(lost, found)
            if shared == "found":
                other_lost, other_found, owner = self.item("c", "lost"), found, "c"
            else:
                other_lost, other_found, owner = lost, self.item("c", "found"), "a"
            codes = self.race([
                lambda: self.decide(selected),
                lambda: post(self.clients[owner], f"/found-items/{other_found}/claim", lost_id=other_lost, claim_reason="Racing request"),
            ])
            self.assertEqual(codes[0], 302)
            self.assertIn(codes[1], (302, 400, 409))
            competitors = rows("SELECT status FROM claims WHERE lost_id=%s AND found_id=%s", (other_lost, other_found))
            self.assertTrue(not competitors or competitors[0]["status"] == "Rejected")

    def test_17_real_connection_failure_and_recovery(self):
        original = os.environ["DATABASE_URL"]
        failed = dict(settings, port="1", connect_timeout="1")
        try:
            os.environ["DATABASE_URL"] = make_conninfo(**failed)
            for path in ("/browse-items", "/items/Found/1", "/my-claims", "/admin", "/reports"):
                response = self.clients["admin"].get(path)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(b"password=", response.data)
            response = post(app.test_client(), "/login", email="a@phase12.example.test", password=PASSWORD)
            self.assertIn(b"Login is unavailable", response.data)
        finally:
            os.environ["DATABASE_URL"] = original
        self.assertEqual(self.clients["admin"].get("/reports").status_code, 200)

    def test_18_stale_admin_eligibility(self):
        lost, found = self.item("a", "lost"), self.item("b", "found")
        claim = self.claim(lost, found)
        rows("UPDATE found_items SET status='Returned' WHERE found_id=%s", (found,))
        self.assertEqual(self.decide(claim).status_code, 409)
        self.assertEqual(rows("SELECT status FROM claims WHERE claim_id=%s", (claim,))[0]["status"], "Pending")
        rows("UPDATE found_items SET status='Available' WHERE found_id=%s", (found,))
        rows("UPDATE lost_items SET status='Resolved' WHERE lost_id=%s", (lost,))
        self.assertEqual(self.decide(claim).status_code, 409)
        self.assertEqual(self.decide(claim, "reject").status_code, 302)


class EvidenceResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.cases=[]
    def addSuccess(self,test):
        super().addSuccess(test)
        self.cases.append(dict(test=test.id(),status="PASS"))
    def addFailure(self,test,err):
        super().addFailure(test,err)
        self.cases.append(dict(test=test.id(),status="FAIL",exception=str(err[1])))
    def addError(self,test,err):
        super().addError(test,err)
        self.cases.append(dict(test=test.id(),status="ERROR",exception=type(err[1]).__name__))


if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PostgreSQLIntegration)
    result=unittest.TextTestRunner(verbosity=2,resultclass=EvidenceResult).run(suite)
    (EVIDENCE/"integration_results.json").write_text(json.dumps(dict(database=test_database,cases=result.cases,tests_run=result.testsRun,successful=result.wasSuccessful()),indent=2),encoding="utf-8")
    sys.exit(0 if result.wasSuccessful() else 1)
