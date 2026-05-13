from database.connection import DBContext
with DBContext() as (_, c):
    c.execute('SELECT rid, reagent_id, status, received_date FROM inventory')
    rows = c.fetchall()
    print(f"Total rows in inventory: {len(rows)}")
    for r in rows:
        print(r)
