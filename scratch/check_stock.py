from database.connection import DBContext
from datetime import date

with DBContext() as (_, c):
    c.execute('SELECT COUNT(*) as cnt FROM inventory WHERE received_date = CURDATE()')
    print(f"Today Total Inserted: {c.fetchone()['cnt']}")
    
    c.execute('''
        SELECT r.reagent_name, COUNT(i.inventory_id) as bottles, u.stock_to_count
        FROM reagents r
        LEFT JOIN inventory i ON r.reagent_id = i.reagent_id AND i.status = 0
        LEFT JOIN unit_conversions u ON r.unit_id = u.unit_id
        GROUP BY r.reagent_id
    ''')
    print("\nStock breakdown:")
    for row in c.fetchall():
        bottles = row['bottles']
        s2c = float(row['stock_to_count'] or 1)
        calc_units = bottles * s2c
        print(f"Reagent: {row['reagent_name']}, Bottles (DB): {bottles}, S2C: {s2c}, Calc Units: {calc_units}")
