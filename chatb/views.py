import json
import os

import requests
from django.http import JsonResponse
from django.views import View

from .models import chatb_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = os.getenv("TUTORIAL_BOT_TOKEN", "error_token")

# state for each user. This is to tackle free user input
# - register
# - untethered
# - queued
# - matched
# - report

helpText = """
            /register : To register
            /help : To get the list of bot commands
            /match : To match with someone
            /end : To end a chat
            /report : To report a user
            """

startText = """Hi there and Welcome to the Eusoff Chat Bot. You can use this bot
            to match and anonymously chat with other Eusoffians. At the end, you
            can rate the conversation as well.
            """ + helpText

# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/


class ChatBotView(View):
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)
        if "callback_query" in t_data:
            t_callbackQuery = t_data["callback_query"]
            t_id = t_callbackQuery["from"]["id"]
            t_callbackData = t_callbackQuery["data"]

            p1 = t_id
            p2 = chatb_collection.find(
                {"chat_id": p1})[0]["match_id"]

            self.send_message("Thanks for the rating. Press /start to have another conversation.", t_id)

            chatb_collection.update_one(
                self.queryChatId(p1), {"$unset": {"match_id": ""}})

            chatb_collection.update_one(
                self.queryChatId(p2), {"$set": {"rating": t_callbackData}})

        elif "message" in t_data:
            t_message = t_data["message"]
            t_chat = t_message["chat"]
            t_message_id = t_message["message_id"]
            t_id = t_chat["id"]
            print("message")
            print(t_message)

            try:
                text = t_message["text"].strip().lower()
            except Exception as e:
                try:
                    msg = "Unable to parse the text"
                    self.send_message(msg, t_id)
                    return JsonResponse({"ok": "POST request processed"})
                except Exception as e:
                    return JsonResponse({"ok": "POST request processed"})

            text = text.lstrip("/")
            print(text + str(t_id))

            chat = chatb_collection.find_one(self.queryChatId(t_id))
            print(chat)

            print("foo")
            print(t_data)
            print("bar")

            if not chat:
                if text != "register":
                    print("not reg")
                    msg = "You don't seem to be registered yet! Use /register"
                    self.send_message(msg, t_id)
                else:
                    print("registering")
                    msg = "Please enter your name and room. Ex: John A101"
                    reply_markup = {"force_reply": True,
                                    "input_field_placeholder": "John A101"}
                    self.send_message(msg, t_id, reply_markup=reply_markup)
                    chat = {
                        "chat_id": t_id,
                        "counter": 0,
                        "state": "register"
                    }
                    response = chatb_collection.insert_one(chat)
                    # # we want chat obj to be the same as fetched from collection
                    # chat["_id"] = response.inserted_id
            elif chat['state'] == "matched":
                if text == "end":
                    person1 = t_id
                    person2 = chatb_collection.find(
                        {"chat_id": person1})[0]["match_id"]
                    print(person2)
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "1", "callback_data": 1},
                                {"text": "2", "callback_data": 2},
                                {"text": "3", "callback_data": 3},
                                {"text": "4", "callback_data": 4},
                                {"text": "5", "callback_data": 5}
                            ]
                        ]}

                    chatb_collection.update_one(
                        self.queryChatId(person1),
                        {"$set": {"state": "untethered"}}
                    )
                    chatb_collection.update_one(
                        self.queryChatId(person2),
                        {"$set": {"state": "untethered"}}
                    )
                    print("person2 is here")

                    self.send_message(
                        "Your conversation has ended. Please rate the user you chatted with", person1, reply_markup=keyboard)
                    self.send_message(
                        "Your conversation has ended. Please rate the user you chatted with", person2, reply_markup=keyboard)

                elif text == "report":
                    self.send_message("Report not done", t_id)
                else:
                    self.send_message("Anon chat not done", t_id)
            elif text == "start":
                self.send_message(startText, t_id)
            elif text == "register":
                registeredMessage = "You have already been registered, {name}.".format(
                    name=chat['name'])
                self.send_message(registeredMessage, t_id)
            elif text == "help":
                self.send_message(helpText, t_id)

            elif text == "match":
                chatb_collection.update_one(self.queryChatId(
                    t_id), {"$set": {"state": "queued"}})
                inQueue = chatb_collection.count_documents({"state": "queued"})
                waitMessage = "Looking for another Eusoffian."
                sentMessage = self.send_message(waitMessage, t_id, '', False)
                count = 0
                while inQueue == 1:
                    waitMessageX = waitMessage + (count % 3) * "."
                    self.update_message(waitMessageX, t_id,
                                        sentMessage['result']['message_id'])
                    inQueue = chatb_collection.count_documents(
                        {"state": "queued"})
                    count += 1
                    if count > 20:
                        terminateMessage = "Sorry, there are no Eusoffians available at the moment."
                        self.update_message(
                            terminateMessage, t_id, sentMessage['result']['message_id'])
                        chatb_collection.update_one(self.queryChatId(
                            t_id), {"$set": {"state": "untethered"}})
                        break
                if inQueue > 1:
                    personsInQueue = chatb_collection.find({"state": "queued"})

                    person1 = personsInQueue[0]["chat_id"]
                    person2 = personsInQueue[1]["chat_id"]
                    chatb_collection.update_one(
                        self.queryChatId(person1),
                        {"$set": {"match_id": person2}}
                    )
                    chatb_collection.update_one(
                        self.queryChatId(person2),
                        {"$set": {"match_id": person1}}
                    )
                    chatb_collection.update_one(
                        self.queryChatId(person1),
                        {"$set": {"state": "matched"}}
                    )
                    chatb_collection.update_one(
                        self.queryChatId(person2),
                        {"$set": {"state": "matched"}}
                    )

                    successMessage = "You have been matched! Have fun!"
                    self.send_message(successMessage, person1)
                    self.send_message(successMessage, person2)
            elif text == "+":
                chat["counter"] += 1
                chatb_collection.save(chat)
                msg = f"Number of '+' messages that were parsed: {chat['counter']}"
                self.send_message(msg, t_id)
            elif text == "restart":
                blank_data = {"counter": 0}
                chat.update(blank_data)
                chatb_collection.save(chat)
                msg = "The Tutorial bot was restarted"
                self.send_message(msg, t_id)
            else:
                if chat['state'] == "register":
                    try:
                        name, room = text.split(' ')
                        print(room)
                        self.checkRoomValidity(room)
                        print("passed")
                        chatb_collection.update_one(
                            self.queryChatId(t_id),
                            {"$set": {"state": "untethered",
                                      "name": name,
                                      "room": room}}
                        )
                        msg = "Successfully registered!"
                        self.send_message(msg, t_id)
                    except Exception as e:
                        msg = "Please follow the format, John A101"
                        self.send_message(msg, t_id)
                elif chat['state'] == "queued":
                    msg = "Please wait, searching for a match!"
                    self.send_message(msg, t_id)
                elif chat['state'] == "report":
                    msg = "Reporting not done (free)"
                    self.send_message(msg, t_id)
                else:
                    msg = "Unknown command"
                    self.send_message(msg, t_id)

            return JsonResponse({"ok": "POST request processed"})

    @ staticmethod
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

    @ staticmethod
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

    @ staticmethod
    def queryChatId(chat_id):
        return {"chat_id": chat_id}

    @ staticmethod
    def checkRoomValidity(room):
        if not (room[0].lower() >= 'a' and
                room[0].lower() <= 'e' and
                int(room[1]) >= 1 and
                int(room[1]) <= 4):
            raise Exception('Invalid room!')
