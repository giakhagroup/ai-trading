import sqlite3
import pprint
conn = sqlite3.connect("data/outbox.db")
c = conn.cursor()
c.execute("SELECT * FROM outbox_events;")
rows = c.fetchall()
print(f"Total events: {len(rows)}")
for r in rows:
    print(r)
