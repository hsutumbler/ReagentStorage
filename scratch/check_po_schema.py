from database.connection import DBContext
with DBContext() as (_, c):
    c.execute('DESCRIBE purchase_orders')
    print(c.fetchall())
