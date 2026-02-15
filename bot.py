import os
import time
import random
from dotenv import load_dotenv

import discord
from discord import app_commands

from db import init_db, get_user, set_balance, set_last_daily

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # optional für schnelleres Command-Sync

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt als Env-Variable.")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def clamp_bet(bet: int, balance: int) -> int:
    try:
        bet = int(bet)
    except Exception:
        return 0
    if bet <= 0:
        return 0
    return min(bet, balance)

@client.event
async def on_ready():
    init_db()
    # Slash-Commands synchronisieren
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"✅ Eingeloggt als {client.user} | Commands synced to guild {GUILD_ID}")
    else:
        await tree.sync()
        print(f"✅ Eingeloggt als {client.user} | Commands synced globally (kann dauern)")

@tree.command(name="balance", description="Zeigt dein Guthaben.")
async def balance(interaction: discord.Interaction):
    bal, _ = get_user(str(interaction.user.id))
    await interaction.response.send_message(f"💰 Du hast **{bal}** Chips.")

@tree.command(name="daily", description="Tägliche Belohnung (alle 24h).")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    bal, last_daily = get_user(user_id)

    now = int(time.time())
    day = 24 * 60 * 60
    if now - last_daily < day:
        left = day - (now - last_daily)
        hours = (left + 3599) // 3600
        await interaction.response.send_message(f"⏳ Daily schon geholt. Versuch es in ca. **{hours}h** nochmal.")
        return

    reward = 300
    bal += reward
    set_balance(user_id, bal)
    set_last_daily(user_id, now)
    await interaction.response.send_message(f"🎁 Daily: **+{reward}** Chips → Neues Guthaben: **{bal}**")

@tree.command(name="coinflip", description="Kopf oder Zahl um Spielgeld.")
@app_commands.describe(einsatz="Wie viel setzen?", wahl="kopf oder zahl")
@app_commands.choices(
    wahl=[
        app_commands.Choice(name="kopf", value="kopf"),
        app_commands.Choice(name="zahl", value="zahl"),
    ]
)
async def coinflip(interaction: discord.Interaction, einsatz: int, wahl: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    bal, _ = get_user(user_id)

    bet = clamp_bet(einsatz, bal)
    if bet <= 0:
        await interaction.response.send_message("❌ Ungültiger Einsatz.")
        return

    result = random.choice(["kopf", "zahl"])
    won = (result == wahl.value)

    bal = bal + bet if won else bal - bet
    set_balance(user_id, bal)

    await interaction.response.send_message(
        f"🪙 Ergebnis: **{result}** — du hast {'gewonnen' if won else 'verloren'}! "
        f"({('+' if won else '-')}{bet}) → **{bal}** Chips"
    )

@tree.command(name="slots", description="Spielautomaten (virtuell).")
@app_commands.describe(einsatz="Wie viel setzen?")
async def slots(interaction: discord.Interaction, einsatz: int):
    user_id = str(interaction.user.id)
    bal, _ = get_user(user_id)

    bet = clamp_bet(einsatz, bal)
    if bet <= 0:
        await interaction.response.send_message("❌ Ungültiger Einsatz.")
        return

    symbols = ["🍒", "🍋", "🔔", "⭐", "💎"]
    a, b, c = (random.choice(symbols), random.choice(symbols), random.choice(symbols))

    mult = 0
    if a == b == c:
        mult = 5
    elif a == b or b == c or a == c:
        mult = 2

    delta = bet * mult - bet  # netto
    bal += delta
    set_balance(user_id, bal)

    msg = (
        f"🎰 {a} | {b} | {c}\n"
        f"{'😬 Leider nix.' if mult == 0 else f'🎉 Multiplikator: x{mult}'}\n"
        f"Änderung: **{delta:+d}**\n"
        f"Guthaben: **{bal}**"
    )
    await interaction.response.send_message(msg)

client.run(TOKEN)

