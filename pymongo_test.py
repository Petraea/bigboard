from pymongo import MongoClient
db = MongoClient().testdb
#db.things.insert({'test':1,'4':[5,7]})
db.things.drop()

print (db.collection_names())
for doc in db.things.find():
    print (doc)
