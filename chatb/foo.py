from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

def aiChat(input):
    chatbot = ChatBot(
        'Herbert',
        # logic_adapters=[
        #     'chatterbot.logic.UnitConversion',
        #     'chatterbot.logic.MathematicalEvaluation',
        #     'chatterbot.logic.TimeLogicAdapter'
        # ]
    )

    trainer = ChatterBotCorpusTrainer(chatbot)

    trainer.train("chatterbot.corpus.english")
    trainer.train("chatterbot.corpus.english.greetings")
    trainer.train("chatterbot.corpus.english.conversations")

    return chatbot.get_response(input)

print(aiChat("what are your thoughts on loki"))
# from chatbot import Chat, register_call
# import wikipedia

# @register_call("whoIs")
# def who_is(session, query):
#     try:
#         return wikipedia.summary(query)
#     except Exception:
#         for new_query in wikipedia.search(query):
#             try:
#                 return wikipedia.summary(new_query)
#             except Exception:
#                 pass
#     return "I don't know about "+query

# first_question="Hi, how are you?"
# Chat("examples/Example.template").converse(first_question)