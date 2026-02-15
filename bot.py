# bot.py — FIXED VERSION

import os
import re
import asyncio
import discord
from dotenv import load_dotenv
from openai import OpenAI

# load env vars (Railway automatically provides them)
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")
ROAST_MODE = (os.getenv("ROAST_MODE") or "mild").lower()

# use correct valid model
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

# validation
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY fehlt.")
if not ALLOWED_CHANNEL_ID or not ALLOWED_CHANNEL_ID.isdigit():
    raise RuntimeError("ALLOWED_CHANNEL_ID fehlt oder ist nicht numerisch.")

ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)

# init openai
ai = OpenAI(api_key=OPENAI_API_KEY)

# discord setup
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)


# ---------------- utils ----------------

def sanitize(text: str) -> str:
    text = text.replace("@everyone", "@\u200beveryone")
    text = text.replace("@here", "@\u200bhere")
    return text.strip()


def style_rules(mode: str) -> str:
    if mode == "spicy":
        return (
            "Sei frech, sarkastisch und witzig. 1–2 kurze Sätze. "
            "Keine Slurs, keine Drohungen."
        )
    return (
        "Sei frech, aber humorvoll und PG-13. 1–2 kurze Sätze."
    )


def remove_bot_mentions(text: str) -> str:
    if bot.user:
        text = re.sub(rf"<@!?{bot.user.id}>", "", text)
    return text.strip()


# ---------------- AI ----------------

async def generate_reply(user_name: str, content: str) -> str:

    system = (
        "Du bist ein frecher Discord-Bot.\n"
        + style_rules(ROAST_MODE)
        + "\nAntworte kurz."
    )

    user = f"{user_name} schrieb: {content}"

    def call_openai():

        resp = ai.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.9,
            max_output_tokens=60,
        )

        # FIX: use output_text (stable)
        reply = getattr(resp, "output_text", "")

        return sanitize(reply) or "Du bist sprachlos? Ich auch."

    try:
        return await asyncio.to_thread(call_openai)

    except Exception as e:
        print("OpenAI ERROR:", repr(e))
        return "Ich wollte dich roasten, aber mein Gehirn hat dich gesehen und aufgegeben."


# ---------------- discord events ----------------

@bot.event
async def on_ready():
    print(f"😈 Bot online als {bot.user}")
    print(f"📡 Channel: {ALLOWED_CHANNEL_ID}")
    print(f"🧠 Model: {OPENAI_MODEL}")


@bot.event
async def on_message(message: discord.Message):

    # ignore bots
    if message.author.bot:
        return

    print(f"[MSG] {message.channel.id} {message.author}: {message.content}")

    # only allowed channel
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    content = message.content.strip()

    if not content and message.attachments:
        content = "hat ein Bild geschickt"

    if not content:
        content = "..."

    content = remove_bot_mentions(content)

    reply = await generate_reply(
        message.author.display_name,
        content
    )

    await message.reply(reply, mention_author=False)


# ---------------- start bot ----------------

bot.run(DISCORD_TOKEN)
