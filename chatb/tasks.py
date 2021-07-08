from background_task import background

from .models import chatb_collection

@background(schedule=0)
def match():
    inQueue = chatb_collection.count_documents({"state": "queued"})
    print("welp")

@background(schedule=0)
def dots():
    print("TODO")