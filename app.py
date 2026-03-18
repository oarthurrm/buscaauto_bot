from dotenv import load_dotenv
import os

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import WebBaseLoader

import telebot

# ---------------------------------
# CONFIG
# ---------------------------------

load_dotenv()

API_TOKEN = os.getenv('API_KEY')

os.environ["USER_AGENT"] = os.getenv("USER_AGENT", "BuscaAuto/1.0")
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY não foi encontrada. Configure no .env!")

# ---------------------------------
# Groq
# ---------------------------------
chat = ChatGroq(api_key=api_key, model='llama-3.3-70b-versatile')
bot = telebot.TeleBot(API_TOKEN)

# ---------------------------------
# A.I
# ---------------------------------
def consultar_carro(marca, modelo, ano):
    loader = WebBaseLoader('https://www.carrosnaweb.com.br/avancada.asp')
    documents_list = loader.load()
    
    document = ''
    for element in documents_list:
        document += element.page_content
    
    input_user = f"Me informe com detalhes e de forma organizada a ficha técnica, vantagens e desvantagens do veículo: {marca} {modelo} {ano}."     
    
    SYSTEM_PROMPT = (
        "Você se chama Luigi e é especialista em automóveis. "
        "Use as informações de contexto abaixo para enriquecer sua resposta. "
        "Apresente ficha técnica, vantagens e desvantagens de forma organizada: "
        "títulos em MAIÚSCULAS, sem asteriscos, com linha em branco antes e depois de cada título. "
        "Se não souber algo, recomende consultar um mecânico.\n\n"
        "CONTEXTO:\n[{context}]"
    )

    # Criando um prompt template válido
    template = ChatPromptTemplate.from_messages([
        ('system', SYSTEM_PROMPT),
        ('user', '{input}')
    ])

    # Criando a cadeia de execução
    chain = template | chat

    # Enviando a pergunta para a IA
    response = chain.invoke({'context': document, 'input': input_user}).content  

    return response if response else "Desculpe! Não consegui obter informações sobre esse veículo."

user_data = {}

@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    user_data[message.chat.id] = {}
    username = message.from_user.first_name
    print(f"{username} iniciou a conversa...")
    bot.reply_to(message, f"Olá, {username}! Eu sou o Luigi.\nQual a MARCA do carro que você deseja buscar?")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'brand' not in user_data[message.chat.id])
def get_brand(message):
    user_data[message.chat.id]['brand'] = message.text.lower()
    bot.reply_to(message, f"Marca {message.text.upper()} selecionada com sucesso!\n\nQual o MODELO e VERSÃO do veículo?")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'brand' in user_data[message.chat.id] and 'model' not in user_data[message.chat.id])
def get_model(message):
    user_data[message.chat.id]['model'] = message.text.lower()
    bot.reply_to(message, f"Modelo {message.text.upper()} registrado!\n\nAgora informe o ANO do veículo.")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'model' in user_data[message.chat.id] and 'year' not in user_data[message.chat.id])
def get_year(message):
    user_data[message.chat.id]['year'] = message.text.lower()
    brand = user_data[message.chat.id]['brand'].upper()
    model = user_data[message.chat.id]['model'].upper()
    year = user_data[message.chat.id]['year']
    print(f"Carro escolhido: {brand} {model} - {year}")
    bot.reply_to(message, f"Veículo registrado: {brand} {model} {year}!\n\nBuscando informações...")

    # Consultar informações do veículo na IA
    info = consultar_carro(brand, model, year)
    bot.reply_to(message, f"Aqui estão as informações do veículo:\n\n{info}")
    print("Resposta enviada com sucesso!")

try:
    print('Bot rodando...')
    bot.polling()
except Exception as e:
    print(f"Não foi possível iniciar o Bot! {e}")
