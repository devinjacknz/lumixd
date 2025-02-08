"""
Set up MongoDB collections for order tracking
"""
import pymongo
from termcolor import cprint

def setup_mongodb():
    """Set up MongoDB collections and verify connection"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["lumixd"]
        
        # Create collections with indexes
        orders = db["orders"]
        orders.create_index([("status", 1)])
        orders.create_index([("execute_at", 1)])
        orders.create_index([("instance_id", 1)])
        
        positions = db["positions"]
        positions.create_index([("instance_id", 1)])
        positions.create_index([("token_address", 1)])
        
        # Verify connection
        client.admin.command("ping")
        cprint("✅ MongoDB setup complete", "green")
        cprint(f"✅ Collections created: {db.list_collection_names()}", "green")
        return True
    except Exception as e:
        cprint(f"❌ MongoDB setup failed: {str(e)}", "red")
        return False

if __name__ == '__main__':
    setup_mongodb()
