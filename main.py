import os
import psycopg2
from discord.ext import commands
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Conexão com PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Criar tabela se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT,
    pontos INTEGER DEFAULT 0
)
""")
conn.commit()

# Configuração do bot
bot = commands.Bot(command_prefix="!", intents=None)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.command()
async def add(ctx, nome: str, pontos: int):
    """Adicionar usuário e pontos"""
    cursor.execute("INSERT INTO usuarios (nome, pontos) VALUES (%s, %s)", (nome, pontos))
    conn.commit()
    await ctx.send(f"✅ {nome} adicionado com {pontos} pontos!")

@bot.command()
async def lista(ctx):
    """Listar todos os usuários"""
    cursor.execute("SELECT nome, pontos FROM usuarios ORDER BY pontos DESC")
    rows = cursor.fetchall()
    if rows:
        msg = "\n".join([f"{nome}: {pontos}" for nome, pontos in rows])
        await ctx.send("📋 Ranking:\n" + msg)
    else:
        await ctx.send("⚠️ Nenhum usuário cadastrado.")

@bot.command()
async def reset(ctx):
    """Zerar a tabela de usuários"""
    cursor.execute("DELETE FROM usuarios")
    conn.commit()
    await ctx.send("🗑️ Todos os usuários foram apagados!")

bot.run(TOKEN)
