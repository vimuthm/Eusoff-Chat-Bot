import json
import os

import requests
from django.http import JsonResponse
from django.views import View

from .models import chatb_collection, chatb_reports, chatb_history
from .tasks import match
# , train, chatwAI


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
           "/advice : To get help or ask questions from a senior\n" + \
           "/end : To end a chat\n" + \
           "/report : To report a user (only while matched)\n" + \
           "/support : To relay an issue to the dev team\n"

startText = "Hi there and\n\n" + \
            "           Welcome to the conversEHtions bot!!!\n\n" + \
            "You can use this bot to match and anonymously chat " + \
            "with other Eusoffians; to make new connections and " + \
            "have fun. At the end, you can rate the conversation.\n\n" + \
            helpText

msg404 = "Aw, Snap! I'm broken and my devs are too tired to fix me :("

supportText = "Please contact @VimuthM or @Jaredlim to report issues or for support"

allowedFormats = set(["sticker", "document", "audio", "photo",
                      "video", "voice", "video_note"])

adviceChatIDs = [92391842] #Avina 92391842, Vimuth, Jared: 1165718697, 402947214

# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/

class ChatBotView(View):
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)

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
                text = t_message["text"]
                print(text + ' ' + str(t_id))
            except Exception as e:
                if not set(t_message).intersection(allowedFormats):
                    msg = "Unable to parse the text"
                    self.send_message(msg, t_id)
                    return JsonResponse({"ok": "POST request processed"})

            caption = t_message["caption"] \
                if "caption" in t_message else ""
            replyId = t_message["reply_to_message"]["message_id"] \
                if "reply_to_message" in t_message else None

            # Send introductory message regardless of registered status
            if text == "/start":
                self.send_message(startText, t_id)
            # Handle users not registered yet
            elif not chat:
                if text != "/register":
                    msg = "You don't seem to be registered yet! Use /register"
                    self.send_message(msg, t_id)
                else:
                    msg = "Please enter your name and room. Ex: John A101"
                    reply_markup = {"force_reply": True,
                                    "input_field_placeholder": "John A101"}
                    self.send_message(msg, t_id, reply_markup=reply_markup)
                    fromUser = t_message["from"]
                    tele = fromUser["username"] \
                        if "username" in fromUser else ""
                    first = fromUser["first_name"] \
                        if "first_name" in fromUser else ""
                    last = fromUser["last_name"] \
                        if "last_name" in fromUser else ""
                    chat = {
                        "chat_id": t_id,
                        "state": "register",
                        "tele": "@" + tele,
                        "first_name": first,
                        "last_name": last
                    }
                    chatb_collection.insert_one(chat)
            # Handle /end when queued and matched
            elif text == "/end":
                self.handleEnd(chatb_collection, chat, t_id)
            # Handle free user input (anon chat) and /report when matched
            elif chat['state'] == "matched":
                if text == "/report":
                    reported = chatb_collection.find_one(
                        {"chat_id": chat["match_id"]})
                    report = {
                        "submitter": t_id,
                        "submitter_tele": chat["tele"],
                        "reported": chat["match_id"],
                        "reported_tele": reported["tele"],
                        "state": "report"
                    }
                    chatb_reports.insert_one(report)
                    chatb_collection.update_one(
                        {"chat_id": chat["match_id"]},
                        {"$set": {"state": "untethered"},
                         "$unset": {"match_id": ""}}
                    )
                    chatb_collection.update_one(
                        queryChatId,
                        {"$set": {"state": "report"}}
                    )
                    msg1 = "The chat has been stopped. Please enter your reason for reporting"
                    reply_markup = {"force_reply": True}
                    self.send_message(msg1, t_id, reply_markup=reply_markup)
                    msg2 = "Your chat has been ended."
                    self.send_message(msg2, chat["match_id"])
                else:
                    if text is not None:
                        self.send_message(text, chat['match_id'])
                    elif "sticker" in t_message:
                        self.send_sticker(
                            t_message["sticker"]["file_id"], chat['match_id'])
                    elif "video_note" in t_message:
                        self.send_videoNote(
                            t_message["video_note"]["file_id"], chat['match_id'])
                    elif "document" in t_message:
                        self.send_document(
                            t_message["document"]["file_id"], chat['match_id'], caption)
                    elif "photo" in t_message:
                        self.send_photo(
                            t_message["photo"][0]["file_id"], chat['match_id'], caption)
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
            # Handle register inputs
            elif chat['state'] == "register":
                msg = self.handleRegister(chatb_collection, t_id, text)
                self.send_message(msg, t_id)
            # elif chat['state'] == "ai":
            #     msg = chatwAI(text)
            # Handle reported reason
            elif chat['state'] == "report":
                report = chatb_reports.find_one(
                    {
                        "submitter": t_id,
                        "reported": chat["match_id"]
                    }
                )
                chatb_reports.update_one(
                    {
                        "submitter": t_id,
                        "reported": chat["match_id"]
                    },
                    {"$set": {"reason": text}}
                )
                chatb_collection.update_one(
                    queryChatId,
                    {"$set": {"state": "untethered"},
                        "$unset": {"match_id": ""}}
                )
                msg = "Reported user. You can /match to search again."
                self.send_message(msg, t_id)

                alertMsg = report["submitter_tele"] + "reported" + report["reported_tele"] + "for: " + text
                for chatId in adviceChatIDs:
                    self.send_message(alertMsg, chatId)
            elif text == "/dontrunthisoryouwillbefired":
                msg = "Ahh tried to pull a sneaky one huh... \n...knew yall cant be trusted 😩✋"
                self.send_message(msg, t_id)
            # Start the matching background process
            # elif text == "/dontrunthisoryouwillbefiredadmin":
            #     print("Going to add to queue")
            #     match(repeat=1)
            #     print("Added to queue")
            #     msg = "I really really hope youre either Vimuth or Jared 🤞"
            #     self.send_message(msg, t_id)
            # elif text == "/dontrunthisoryouwillbefiredtrain":
            #     print("Going to add to queue")
            #     train()
            #     print("Added to queue")
            #     msg = "I really really hope youre either Vimuth or Jared 🤞"
            #     self.send_message(msg, t_id)
           
            # elif text == "/adminleaderboard":
            #     self.handleLeaderboard(chatb_collection, t_id)
            elif text == "/adminreports":
                self.handleReports(chatb_reports, t_id)
            # Handle /register when already registered
            elif text == "/register":
                msg = "You have already been registered, %s." % chat['name']
                self.send_message(msg, t_id)
            elif text == "/advice":
                # Send intro message
                # Loop available seniors
                # Get first untethered and match
                msg = "Searching for a senior to assist you! The normal procedure applies: /end to end the conversation " + \
                      "and /report to make a report. This chat too will be anonymous."
                self.send_message(msg, t_id)
                found = False
                for chatId in adviceChatIDs:
                    current_person = chatb_collection.find_one({"chat_id": chatId})
                    if current_person["state"] == "untethered":
                        found = True
                        person1 = t_id
                        person2 = chatId

                        if person1 == person2:
                            continue
                        
                        chatb_collection.update_one(
                            queryChatId,
                            {"$set": {"match_id": person2}}
                        )
                        chatb_collection.update_one(
                            {"chat_id": person2},
                            {"$set": {"match_id": person1}}
                        )
                        chatb_collection.update_one(
                            queryChatId,
                            {"$set": {"state": "matched"}}
                        )
                        chatb_collection.update_one(
                            {"chat_id": person2},
                            {"$set": {"state": "matched"}}
                        )

                        successMessage = "You have been matched with a senior! In case they aren't online, \
                            just leave your query (don't /end) and they will get back to you!"
                        seniorMessage = "Someone's looking for advice :)))"
                        self.send_message(successMessage, person1)
                        self.send_message(seniorMessage, person2)

                        break
                if not found:
                    msg = "All seniors are currently busy :( Please check again later!"
                    self.send_message(msg, t_id)
            elif text == "/support":
                self.send_message(supportText, t_id)
            # Send help text
            elif text == "/help":
                self.send_message(helpText, t_id)
            # Handle /match by changing state to queued
            elif text == "/match":
                match(t_id)
                
            # elif text == "/ai":
            #     chatb_collection.update_one(
            #         queryChatId, {"$set": {"state": "ai"}})
            #     self.send_message("Hi, I'm Herbert!!", t_id)
            # Free user input except when queued/matched
            else:
                msg = "Unknown command"
                self.send_message(msg, t_id)
        else:
            print("Failed: Neither callback nor message")

        return JsonResponse({"ok": "POST request processed"})

    @ staticmethod
    def send_message(message, chat_id, reply_markup={}, notif=True):
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

    @ staticmethod
    def send_sticker(sticker, chat_id):
        data = {
            "chat_id": chat_id,
            "sticker": sticker
        }

        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendSticker", json=(data)
        )
        return response.json()

    @ staticmethod
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

    @ staticmethod
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

    @ staticmethod
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

    @ staticmethod
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

    @ staticmethod
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

    @ staticmethod
    def send_videoNote(video_note, chat_id, caption=""):
        data = {
            "chat_id": chat_id,
            "video_note": video_note,
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendVideoNote", json=(data)
        )
        return response.json()

    @ staticmethod
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

        newRating = (p2_data["rating"] * p2_data["count"] +
                     int(t_callbackData)) / (p2_data["count"] + 1)

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

    # def handleLeaderboard(self, chatb_collection, t_id):
    #     cursor = chatb_collection.find().sort(
    #         [("rating", -1)]).limit(10)
    #     msg = "Leaderboard: \n"
    #     count = 1
    #     for doc in cursor:
    #         msg += "%d. Tele: %s \n Matches: %d \n Rating: %f \n" % (
    #             count, doc["tele"], doc["count"], doc["rating"])
    #         count += 1
    #     self.send_message(msg.replace("_", "\_"), t_id)

    def handleReports(self, chatb_reports, t_id):
        reports = chatb_reports.find()
        msg = "Reports: \n"
        count = 1
        for doc in reports:
            msg += "%d. User: %s \n Reported: %s \n Reason: %s \n" % (
                count, doc["submitter_tele"], doc["reported_tele"], doc["reason"])
            count += 1
        self.send_message(msg.replace("_", "\_"), t_id)
