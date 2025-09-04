import os
import discord
from discord.ext import commands
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Conexão com PostgreSQL
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Criar tabelas
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            discord_id BIGINT UNIQUE NOT NULL,
            habbo_nick TEXT,
            saldo INT DEFAULT 0
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="-", intents=intents)

# Função para verificar se autor é admin
def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# Gerar avatar do Habbo
def habbo_avatar(nick):
    return f"https://www.habbo.com.br/habbo-imaging/avatarimage?user={nick}&action=std&direction=2&head_direction=2&size=l"

# Evento de inicialização
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

# -----------------------------
# 📌 COMANDOS
# -----------------------------

# Vincular usuário ao Habbo
@bot.command()
async def vincular(ctx, nick: str, membro: discord.Member, cargo: str = None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO usuarios (discord_id, habbo_nick, saldo)
        VALUES (%s, %s, 0)
        ON CONFLICT (discord_id) DO UPDATE SET habbo_nick = EXCLUDED.habbo_nick
    """, (membro.id, nick))
    conn.commit()
    cur.close()
    conn.close()

    msg = f"✅ {membro.mention} vinculado ao Habbo **{nick}**"

    # Se foi passado um cargo
    if cargo:
        role = discord.utils.get(ctx.guild.roles, name=cargo)
        if role:
            await membro.add_roles(role)
            msg += f" e recebeu o cargo **{cargo}**"
        else:
            msg += f"\n⚠️ Cargo **{cargo}** não encontrado no servidor."

    await ctx.send(msg)

# Consultar saldo
@bot.command()
async def saldo(ctx, membro: discord.Member = None):
    autor = ctx.author

    if membro and not is_admin(ctx):
        await ctx.send("❌ Você não tem permissão para ver o saldo de outros usuários.")
        return

    alvo = membro or autor

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT habbo_nick, saldo FROM usuarios WHERE discord_id = %s", (alvo.id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        embed = discord.Embed(
            title="Verificação de Saldo",
            description=f"Saldo de {alvo.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Saldo", value=f"CAM {row['saldo']}", inline=False)

        if row["habbo_nick"]:
            embed.set_thumbnail(url=habbo_avatar(row["habbo_nick"]))

        await ctx.send(embed=embed)
    else:
        await ctx.send("⚠️ Usuário não vinculado. Use `-vincular` primeiro.")

# Ranking (admins apenas)
@bot.command(name="saldos-todos")
async def saldos_todos(ctx):
    if not is_admin(ctx):
        await ctx.send("❌ Apenas administradores podem usar este comando.")
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT habbo_nick, saldo FROM usuarios ORDER BY saldo DESC LIMIT 20")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if rows:
        embed = discord.Embed(title="🏆 Ranking de Saldos", color=discord.Color.gold())
        for i, row in enumerate(rows, 1):
            embed.add_field(
                name=f"{i}. {row['habbo_nick']}",
                value=f"CAM {row['saldo']}",
                inline=False
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send("⚠️ Nenhum usuário cadastrado.")

# -----------------------------
# 📌 COMANDOS DE ADMINISTRAÇÃO
# -----------------------------
@bot.command()
async def addsaldo(ctx, membro: discord.Member, valor: int):
    if not is_admin(ctx):
        await ctx.send("❌ Apenas administradores podem usar este comando.")
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET saldo = saldo + %s WHERE discord_id = %s", (valor, membro.id))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO usuarios (discord_id, saldo) VALUES (%s, %s)", (membro.id, valor))
    conn.commit()
    cur.close()
    conn.close()
    await ctx.send(f"✅ {valor} CAM adicionados para {membro.mention}")

@bot.command()
async def removersaldo(ctx, membro: discord.Member, valor: int):
    if not is_admin(ctx):
        await ctx.send("❌ Apenas administradores podem usar este comando.")
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET saldo = saldo - %s WHERE discord_id = %s", (valor, membro.id))
    conn.commit()
    cur.close()
    conn.close()
    await ctx.send(f"✅ {valor} CAM removidos de {membro.mention}")

@bot.command()
async def setsaldo(ctx, membro: discord.Member, valor: int):
    if not is_admin(ctx):
        await ctx.send("❌ Apenas administradores podem usar este comando.")
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO usuarios (discord_id, saldo)
        VALUES (%s, %s)
        ON CONFLICT (discord_id) DO UPDATE SET saldo = EXCLUDED.saldo
    """, (membro.id, valor))
    conn.commit()
    cur.close()
    conn.close()
    await ctx.send(f"✅ Saldo de {membro.mention} definido para CAM {valor}")

# -----------------------------

bot.run(TOKEN)
