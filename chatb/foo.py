from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

def aiChat(input):
    chatbot = ChatBot(
        'Herbert',
        logic_adapters=[
            'chatterbot.logic.UnitConversion',
            'chatterbot.logic.MathematicalEvaluation',
            'chatterbot.logic.TimeLogicAdapter'
        ]
    )

    trainer = ChatterBotCorpusTrainer(chatbot)

    trainer.train("chatterbot.corpus.english")
    trainer.train("chatterbot.corpus.english.greetings")
    trainer.train("chatterbot.corpus.english.conversations")

    return chatbot.get_response(input)