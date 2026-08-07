import os
from dotenv import load_dotenv
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
MONGODB_DB = os.getenv("MONGODB_DB") or os.getenv("MONGO_DB")
