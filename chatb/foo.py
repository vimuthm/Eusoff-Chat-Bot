from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

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

def aiChat(input):
    return chatbot.get_response(input)

print(aiChat("what are your thoughts on loki").text)