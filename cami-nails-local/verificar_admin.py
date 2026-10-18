import sqlite3
from pathlib import Path
p=Path(__file__).resolve().parent/'instance'/'studio.sqlite3'
with sqlite3.connect(p) as c:
    exists=bool(c.execute('SELECT 1 FROM usuarios LIMIT 1').fetchone())
raise SystemExit(0 if exists else 10)
