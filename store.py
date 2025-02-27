
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import sys
import pandas as pd
from dotenv import load_dotenv

class StoreController:
    def __init__(self):
        try:
            uri = "mongodb+srv://rjongco:iapplegog@cluster0.o5y7d.mongodb.net/?retryWrites=true&w=majority&appName=cluster0"
            # Create a new client and connect to the server
            client = MongoClient(uri, server_api=ServerApi('1'))
            # Send a ping to confirm a successful connection
            db = client['fbps']
            self.client =client
            self.db=db
            self.session = db['session']
            self.job = db['job']
            self.queue = db['queue']
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
            
        except Exception as e:
            print(e)
            sys.exit(1)
