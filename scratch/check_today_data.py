from database.connection import DBContext
with DBContext() as (_, c):
    c.execute('SELECT * FROM purchase_orders')
    print(f"Total POs: {c.fetchall()}")
    
    c.execute('SELECT * FROM inventory WHERE received_date = CURDATE()')
    print(f"Inventory today: {c.fetchall()}")
