from pymongo import MongoClient
import certifi
import sys

# MongoDB Atlas Configuration
MONGO_URI = "mongodb+srv://u24dsc119_db_user:aC3Ls9HDZDqnHLzl@cluster0.6vdunga.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "nmc_gatepass"

print(f"--- Testing MongoDB Atlas Connection with SSL Fix ---")
try:
    # Adding tlsCAFile=certifi.where() to fix SSL Certificate errors
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    
    # Trigger a server selection
    client.admin.command('ismaster')
    print("Success! Connected to MongoDB Atlas correctly.")
    
    db = client[DB_NAME]
    count = db.visitors.count_documents({})
    print(f"Total visitors in database: {count}")
    
    client.close()
except Exception as e:
    print(f"Failed to connect to MongoDB Atlas: {e}")
    print("\nPRO TIP: If you still see 'certificate is not yet valid', please check if your computer's date and time are correct.")
    sys.exit(1)
