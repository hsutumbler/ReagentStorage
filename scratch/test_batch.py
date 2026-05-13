from database.models.inventory import InventoryModel
from database.models.purchase_order import PurchaseOrderModel
from services.rid_generator import generate_rid
from datetime import date

def test_batch():
    try:
        # Simulate what BatchReceivePage._do_batch_receive does
        reagent_id = 1
        qty = 2
        lot = "TEST_BATCH_LOT"
        expiry = date(2026, 12, 31)
        
        print(f"Starting test batch for reagent {reagent_id}, qty {qty}")
        for i in range(qty):
            rid = generate_rid()
            print(f"Generated RID: {rid}")
            InventoryModel.insert(
                rid=rid, reagent_id=reagent_id, lot_number=lot,
                expiry_date=expiry, received_date=date.today(),
                received_by=1
            )
        print("Test Batch Success")
    except Exception as e:
        print(f"Test Batch Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch()
