from background_task import background
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

from .models import chatb_collection

import requests
import os

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = os.getenv("TUTORIAL_BOT_TOKEN", "error_token")

count = 0
waitMessage = "Looking for another Eusoffian."
messageDict = {}
chatbot = ChatBot(
        'Herbert',
        # logic_adapters=[
        #     'chatterbot.logic.UnitConversion',
        #     'chatterbot.logic.MathematicalEvaluation',
        #     'chatterbot.logic.TimeLogicAdapter'
        # ]
    )

@background(schedule=0)
def match():
    inQueue = chatb_collection.count_documents({"state": "queued"})
    personsInQueue = chatb_collection.find({"state": "queued"})

    for i in range(0, inQueue - 1, 2):
        person1 = personsInQueue[i]["chat_id"]
        person2 = personsInQueue[i + 1]["chat_id"]

        chatb_collection.update_one(
            queryChatId(person1),
            {"$set": {"match_id": person2}}
        )
        chatb_collection.update_one(
            queryChatId(person2),
            {"$set": {"match_id": person1}}
        )
        chatb_collection.update_one(
            queryChatId(person1),
            {"$set": {"state": "matched"}}
        )
        chatb_collection.update_one(
            queryChatId(person2),
            {"$set": {"state": "matched"}}
        )

        successMessage = "You have been matched! Have fun!"
        send_message(successMessage, person1)
        send_message(successMessage, person2)

    if (inQueue % 2 == 1):
        global count
        global waitMessage
        lastPerson = personsInQueue[inQueue - 1]["chat_id"]
        waitMessageX = waitMessage + count * "."
        sentMessage = send_message(waitMessageX, lastPerson, '', False)
        #debug stmt
        send_message(count, lastPerson, '', False)
        
        # update_message(waitMessageX, lastPerson,
        #                     sentMessage['result']['message_id'])

        count = (count + 1) % 3

        # Handle timeout
        # if count > 20:
        #     terminateMessage = "Sorry, there are no Eusoffians available at the moment."
        #     update_message(
        #         terminateMessage, t_id, sentMessage['result']['message_id'])
        #     chatb_collection.update_one(queryChatId(
        #         t_id), {"$set": {"state": "untethered"}})
        #     break
        
    
    print("welp")

@background(schedule=0)
def dots():
    print("TODO")

@background(schedule=0)
def train():
    global chatbot
    

    trainer = ChatterBotCorpusTrainer(chatbot)

    trainer.train("chatterbot.corpus.english")
    trainer.train("chatterbot.corpus.english.greetings")
    trainer.train("chatterbot.corpus.english.conversations")

def chatwAI(input):
    return chatbot.get_response(input).text

def send_message(message, chat_id, reply_markup='', notif=True):
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup,
        "disable_notification": notif
    }
    response = requests.post(
        f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendMessage", json=(data)
    )
    return response.json()

def update_message(message, chat_id, message_id, reply_markup=''):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    response = requests.post(
        f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/editMessageText", data=data
    )

def queryChatId(chat_id):
    return {"chat_id": chat_id}