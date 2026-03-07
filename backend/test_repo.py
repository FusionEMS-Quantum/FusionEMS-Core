
from core_app.repositories.domination_repository import DominationRepository

print("DominationRepository loaded successfully")
try:
    repo = DominationRepository(None, table="inventory_items")
    print("Instance created")
except Exception as e:
    print(f"Error creating instance: {e}")
