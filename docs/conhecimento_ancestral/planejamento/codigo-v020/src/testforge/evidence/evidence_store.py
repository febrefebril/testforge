import json,sqlite3,time
from pathlib import Path
SCHEMA="""
CREATE TABLE IF NOT EXISTS healing_suggestion(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at INTEGER NOT NULL,run_id TEXT NOT NULL,application TEXT NOT NULL,page_signature TEXT NOT NULL,action_id TEXT NOT NULL,technology_family TEXT,taxonomy_code TEXT NOT NULL,original_locator TEXT NOT NULL,suggested_locator TEXT NOT NULL,total_score REAL NOT NULL,mode TEXT NOT NULL,status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence_package(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at INTEGER NOT NULL,healing_suggestion_id INTEGER NOT NULL,manifest_json TEXT,FOREIGN KEY(healing_suggestion_id)REFERENCES healing_suggestion(id));
CREATE TABLE IF NOT EXISTS oracle_observation(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at INTEGER NOT NULL,healing_suggestion_id INTEGER NOT NULL,oracle_type TEXT NOT NULL,expected TEXT NOT NULL,actual TEXT,result TEXT NOT NULL,reviewed_label TEXT,FOREIGN KEY(healing_suggestion_id)REFERENCES healing_suggestion(id));
CREATE TABLE IF NOT EXISTS review_decision(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at INTEGER NOT NULL,healing_suggestion_id INTEGER NOT NULL,reviewer TEXT,label TEXT NOT NULL,notes TEXT,FOREIGN KEY(healing_suggestion_id)REFERENCES healing_suggestion(id));
CREATE TABLE IF NOT EXISTS promotion_decision(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at INTEGER NOT NULL,healing_suggestion_id INTEGER NOT NULL,from_state TEXT NOT NULL,to_state TEXT NOT NULL,allowed INTEGER NOT NULL,reasons_json TEXT NOT NULL,FOREIGN KEY(healing_suggestion_id)REFERENCES healing_suggestion(id));
"""
class EvidenceStore:
    def __init__(self,db_path="testforge_healing.sqlite"):
        self.db_path=str(db_path); self._init_db()
    def _conn(self):
        c=sqlite3.connect(self.db_path);c.row_factory=sqlite3.Row;return c
    def _init_db(self):
        with self._conn() as c: c.executescript(SCHEMA)
    def insert_healing_suggestion(self,**kw):
        with self._conn() as c:
            cur=c.execute("INSERT INTO healing_suggestion(created_at,run_id,application,page_signature,action_id,technology_family,taxonomy_code,original_locator,suggested_locator,total_score,mode,status)VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(int(time.time()),kw["run_id"],kw["application"],kw["page_signature"],kw["action_id"],kw.get("technology_family"),kw["taxonomy_code"],kw["original_locator"],kw["suggested_locator"],kw["total_score"],kw.get("mode","shadow"),kw.get("status","suggested")))
            return int(cur.lastrowid)
    def insert_evidence_package(self,hid,manifest):
        with self._conn() as c:
            return int(c.execute("INSERT INTO evidence_package(created_at,healing_suggestion_id,manifest_json)VALUES(?,?,?)",(int(time.time()),hid,json.dumps(manifest,ensure_ascii=False))).lastrowid)
    def insert_oracle_observation(self,**kw):
        with self._conn() as c:
            return int(c.execute("INSERT INTO oracle_observation(created_at,healing_suggestion_id,oracle_type,expected,actual,result,reviewed_label)VALUES(?,?,?,?,?,?,?)",(int(time.time()),kw["healing_suggestion_id"],kw["oracle_type"],kw["expected"],kw.get("actual"),kw["result"],kw.get("reviewed_label"))).lastrowid)
    def insert_review_decision(self,**kw):
        with self._conn() as c:
            return int(c.execute("INSERT INTO review_decision(created_at,healing_suggestion_id,reviewer,label,notes)VALUES(?,?,?,?,?)",(int(time.time()),kw["healing_suggestion_id"],kw.get("reviewer"),kw["label"],kw.get("notes"))).lastrowid)
    def insert_promotion_decision(self,**kw):
        with self._conn() as c:
            return int(c.execute("INSERT INTO promotion_decision(created_at,healing_suggestion_id,from_state,to_state,allowed,reasons_json)VALUES(?,?,?,?,?,?)",(int(time.time()),kw["healing_suggestion_id"],kw["from_state"],kw["to_state"],1 if kw["allowed"] else 0,json.dumps(kw.get("reasons",[]),ensure_ascii=False))).lastrowid)
    def list_pending_reviews(self,limit=50):
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT hs.* FROM healing_suggestion hs LEFT JOIN review_decision rd ON rd.healing_suggestion_id=hs.id WHERE hs.mode='shadow' AND hs.status IN('suggested','pending_review') AND rd.id IS NULL ORDER BY hs.created_at DESC LIMIT ?",(limit,)).fetchall()]
    def get_metrics(self,application=None):
        with self._conn() as c:
            w="WHERE h.application=?" if application else ""
            p=(application,) if application else ()
            reviewed=c.execute(f"SELECT COUNT(*)FROM review_decision rd JOIN healing_suggestion h ON h.id=rd.healing_suggestion_id {w}",p).fetchone()[0]
            fh=c.execute(f"SELECT COUNT(*)FROM review_decision rd JOIN healing_suggestion h ON h.id=rd.healing_suggestion_id {w} {'AND' if w else 'WHERE'} rd.label='FALSE_HEAL'",p).fetchone()[0]
            tp=c.execute(f"SELECT COUNT(*)FROM review_decision rd JOIN healing_suggestion h ON h.id=rd.healing_suggestion_id {w} {'AND' if w else 'WHERE'} rd.label='TRUE_POSITIVE_HEAL'",p).fetchone()[0]
        return {"reviewed":reviewed,"false_heals":fh,"true_positives":tp,"false_heal_rate":fh/reviewed if reviewed else 0.0,"precision":tp/reviewed if reviewed else 0.0}
