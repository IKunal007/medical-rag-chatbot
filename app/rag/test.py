import pickle

with open("app/store/docs.pkl", "rb") as f:
    docs = pickle.load(f)

print(docs[0])
