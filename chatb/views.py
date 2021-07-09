import json
import os

import requests
from django.http import JsonResponse
from django.views import View

from .models import chatb_collection
from .tasks import match, train, chatwAI
# from .foo import aiChat


TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = os.getenv("TUTORIAL_BOT_TOKEN", "error_token")

# Possible states for a user. This is to tackle free user input
# - register
# - untethered
# - queued
# - matched
# - report

helpText = "/start : To understand what this bot can do\n" + \
           "/register : To register\n" + \
           "/help : To get a list of bot commands\n" + \
           "/match : To match with another Eusoffian\n" + \
           "/end : To end a chat\n" + \
           "/report : To report a user (only while matched)\n"

startText = "Hi there and\n\n" + \
            "           Welcome to the Eusoff Chat Bot!!!\n\n" + \
            "You can use this bot to match and anonymously chat" + \
            "with other Eusoffians; to make new connections and" + \
            "have fun. At the end, you can rate the conversation.\n\n" + \
            helpText

msg404 = "Aw, Snap! I'm broken and my devs are too tired to fix me :("

# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/


class ChatBotView(View):
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)
        print(t_data)

        # Handle rating feedback
        if "callback_query" in t_data:
            self.handleRating(t_data)
        # Handle all user input
        elif "message" in t_data:
            t_message = t_data["message"]
            t_chat = t_message["chat"]
            t_message_id = t_message["message_id"]
            t_id = t_chat["id"]
            queryChatId = {"chat_id": t_id}
            chat = chatb_collection.find_one(queryChatId)
            text = None

            try:
                text = t_message["text"].strip()
                print(text + ' ' + str(t_id))
            except Exception as e:
                try:
                    t_message["sticker"]["file_id"]
                except Exception as e:
                    try:
                        t_message["document"]["file_id"]
                    except Exception as e:
                        try:
                            t_message["audio"]["file_id"]
                        except Exception as e:
                            try:
                                t_message["photo"]["file_id"]
                            except Exception as e:
                                try:
                                    t_message["video"]["file_id"]
                                except Exception as e:
                                    try:
                                        t_message["voice"]["file_id"]
                                    except Exception as e:
                                        msg = "Unable to parse the text"
                                        self.send_message(msg, t_id)
                                        return JsonResponse({"ok": "POST request processed"})

            if "caption" in t_message:
                caption = t_message["caption"]
            else:
                caption = ""

            if "reply_to_message" in t_message:
                replyId = t_message["reply_to_message"]["message_id"]
                print(replyId)
                print(type(replyId))
            else:
                replyId = None
                print("dont have")

            # Send introductory message regardless of registered status
            if text == "/start":
                self.send_message(startText, t_id)
            # handle users not registered yet
            elif not chat:
                if text != "/register":
                    msg = "You don't seem to be registered yet! Use /register"
                    self.send_message(msg, t_id)
                else:
                    msg = "Please enter your name and room. Ex: John A101"
                    reply_markup = {"force_reply": True,
                                    "input_field_placeholder": "John A101"}
                    self.send_message(msg, t_id, reply_markup=reply_markup)
                    chat = {
                        "chat_id": t_id,
                        "state": "register"
                    }
                    chatb_collection.insert_one(chat)
            # Handle /end when queued and matched
            elif text == "/end":
                self.handleEnd(chatb_collection, chat, t_id)
            # Handle free user input (anon chat) and /report when matched
            elif chat['state'] == "matched":
                if text == "/report":
                    self.send_message("Report not done", t_id)
                else:
                    if text is not None:
                        self.send_message(text, chat['match_id'])
                        print(self.send_message(
                            text, chat['match_id']))
                        print("sent")
                    elif "sticker" in t_message:
                        self.send_sticker(
                            t_message["sticker"]["file_id"], chat['match_id'])
                    elif "document" in t_message:
                        self.send_document(
                            t_message["document"]["file_id"], chat['match_id'], caption)
                    elif "photo" in t_message:
                        self.send_photo(
                            t_message["photo"]["file_id"], chat['match_id'], caption)
                        print(self.send_photo(
                            t_message["photo"]["file_id"], chat['match_id'], caption))
                    elif "audio" in t_message:
                        self.send_audio(
                            t_message["audio"]["file_id"], chat['match_id'], caption)
                    elif "video" in t_message:
                        self.send_video(
                            t_message["video"]["file_id"], chat['match_id'], caption)
                    elif "voice" in t_message:
                        self.send_voice(
                            t_message["voice"]["file_id"], chat['match_id'], caption)
            # Handle free user input other than /end when queued
            elif chat['state'] == "queued":
                msg = "Please wait, searching for a match! Press /end to stop searching"
                self.send_message(msg, t_id)
            elif text == "/dontrunthisoryouwillbefired":
                self.send_message(
                    "Ahh tried to pull a sneaky one huh... \n...knew yall cant be trusted 😩✋", t_id)
            # Start the matching background process
            elif text == "/dontrunthisoryouwillbefiredadmin":
                print("Going to add to queue")
                match(repeat=1)
                print("Added to queue")
                msg = "I really really hope your either Vimuth or Jared 🤞"
                self.send_message(msg, t_id)
            elif text == "/dontrunthisoryouwillbefiredtrain":
                print("Going to add to queue")
                train()
                print("Added to queue")
                msg = "I really really hope your either Vimuth or Jared 🤞"
                self.send_message(msg, t_id)
            # Handle /register when already registered
            elif text == "/register":
                msg = "You have already been registered, %s." % chat['name']
                self.send_message(msg, t_id)
            # Send help text
            elif text == "/help":
                self.send_message(helpText, t_id)
            # Handle /match by changing state to queued
            elif text == "/match":
                chatb_collection.update_one(
                    queryChatId, {"$set": {"state": "queued"}})
            elif text == "/ai":
                chatb_collection.update_one(
                    queryChatId, {"$set": {"state": "ai"}})
                self.send_message("Hi, I'm Herbert!!", t_id)
            # Free user input except when queued/matched
            else:
                # Handle register inputs
                if chat['state'] == "register":
                    msg = self.handleRegister(chatb_collection, t_id, text)
                # Handle reported reason
                elif chat['state'] == "ai":
                    msg = chatwAI(text)
                elif chat['state'] == "report":
                    msg = "Reporting user (WIP)"
                else:
                    msg = "Unknown command"
                self.send_message(msg, t_id)
        else:
            print("Failed: Neither callback nor message")

        return JsonResponse({"ok": "POST request processed"})

    @staticmethod
    def send_message(message, chat_id, reply_markup="", notif=True):
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup,
            "disable_notification": notif,
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendMessage", json=(data)
        )
        return response.json()

    @staticmethod
    def send_sticker(sticker, chat_id):
        data = {
            "chat_id": chat_id,
            "sticker": sticker
        }

        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendSticker", json=(data)
        )
        return response.json()

    @staticmethod
    def send_photo(photo, chat_id, caption=""):
        data = {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendPhoto", json=(data)
        )
        return response.json()

    @staticmethod
    def send_audio(audio, chat_id, caption=""):
        data = {
            "chat_id": chat_id,
            "audio": audio,
            "caption": caption,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendAudio", json=(data)
        )
        return response.json()

    @staticmethod
    def send_document(document, chat_id, caption=""):
        data = {
            "chat_id": chat_id,
            "document": document,
            "caption": caption,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendDocument", json=(data)
        )
        return response.json()

    @staticmethod
    def send_voice(voice, chat_id, caption=""):
        data = {
            "chat_id": chat_id,
            "voice": voice,
            "caption": caption,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendVoice", json=(data)
        )
        return response.json()

    @staticmethod
    def send_video(video, chat_id, caption=""):
        data = {
            "chat_id": chat_id,
            "video": video,
            "caption": caption,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendVideo", json=(data)
        )
        return response.json()

    @staticmethod
    def checkRoomValidity(room):
        if not (room[0].lower() >= 'a' and
                room[0].lower() <= 'e' and
                int(room[1]) >= 1 and
                int(room[1]) <= 4):
            raise Exception('Invalid room!')

    def handleRating(self, t_data):
        t_callbackQuery = t_data["callback_query"]
        t_id = t_callbackQuery["from"]["id"]
        t_callbackData = t_callbackQuery["data"]

        person1 = t_id
        p1_data = chatb_collection.find_one({"chat_id": person1})
        person2 = p1_data["match_id"]
        p2_data = chatb_collection.find_one({"chat_id": person2})

        newRating = (p2_data["rating"] * p2_data["count"] + int(t_callbackData)) / \
                    (p2_data["count"] + 1)

        msg = "Thanks for the rating. Press /match to have another conversation."
        self.send_message(msg, person1)

        chatb_collection.update_one(
            {"chat_id": person1},
            {
                "$unset": {"match_id": ""}
            }
        )

        chatb_collection.update_one(
            {"chat_id": person2},
            {
                "$set": {"rating": newRating},
                "$inc": {"count": 1}
            }
        )

    def handleRegister(self, chatb_collection, t_id, text):
        try:
            name, room = text.split(' ')
            self.checkRoomValidity(room)
            chatb_collection.update_one(
                {"chat_id": t_id},
                {
                    "$set": {
                        "state": "untethered",
                        "name": name,
                        "room": room,
                        "count": 0,
                        "rating": 0
                    }
                }
            )
            msg = "Successfully registered!"
        except Exception as e:
            msg = "Please follow the format, John A101"
        return msg

    def handleEnd(self, chatbcollection, chat, t_id):
        if chat['state'] == "matched":
            person1 = t_id
            person2 = chatb_collection.find(
                {"chat_id": person1})[0]["match_id"]
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
                {"chat_id": person1},
                {"$set": {"state": "untethered"}}
            )
            chatb_collection.update_one(
                {"chat_id": person2},
                {"$set": {"state": "untethered"}}
            )

            msg1 = "Your conversation has ended. Please rate your conversation."
            msg2 = "Your partner has ended the conversation. Please rate your conversation."
            self.send_message(msg1, person1, reply_markup=keyboard)
            self.send_message(msg2, person2, reply_markup=keyboard)

        elif chat['state'] == "queued":
            chatb_collection.update_one(
                {"chat_id": t_id},
                {"$set": {"state": "untethered"}}
            )
            msg = "Stopped searching :("
            self.send_message(msg, t_id)
        elif chat['state'] == "ai":
            chatb_collection.update_one(
                {"chat_id": t_id},
                {"$set": {"state": "untethered"}}
            )
            msg = "Herbert says bye :("
            self.send_message(msg, t_id)
        else:
            msg = "This command is only applicable when you're matched or in queue."
            self.send_message(msg, t_id)
