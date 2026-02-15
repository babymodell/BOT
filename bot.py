# bot.py (fixed for Railway + Discord)
import os
import re
import asyncio
import discord
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")
ROAST_MODE = (os.getenv("ROAST_MODE") or "mild").lower()

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY fehlt.")
if not ALLOWED_CHANNEL_ID or not ALLOWED_CHANNEL_ID.isdigit():
    raise RuntimeError("ALLOWED_CHANNEL_ID fehlt oder ist nicht numerisch.")

ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)

ai = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True  # requires Message Content Intent enabled in Discord dev portal
bot = discord.Client(intents=intents)

def sanitize(text: str) -> str:
    # ping-sicher
    text = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    return text.strip()

def style_rules(mode: str) -> str:
    if mode == "spicy":
        return (
            "Frech, sarkastisch, witzig. 1–2 Sätze. "
            "Keine Slurs, keine Drohungen, keine Angriffe auf geschützte Merkmale, "
            "kein sexual content, kein self-harm."
        )
    return (
        "Neckisch-frech, humorvoll, PG-13. 1–2 Sätze. "
        "Keine harten Beleidigungen, keine Slurs, keine Drohungen, "
        "keine Angriffe auf geschützte Merkmale, kein sexual content, kein self-harm."
    )

def remove_bot_mentions(text: str) -> str:
    if bot.user:
        text = re.sub(rf"<@!?{bot.user.id}>\s*", "", text).strip()
    return text

def extract_output_text(resp) -> str:
    parts = []
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    parts.append(c.text)
    return "".join(parts)

async def generate_reply(user_name: str, content: str) -> str:
    model = "gpt-5.2-mini"
    system = (
        "Du bist ein Discord-Bot, der auf jede Nachricht frech antwortet.\n"
        + style_rules(ROAST_MODE)
        + "\nAntworte NUR mit dem Text. Optional 0–1 Emoji."
    )
    user = (
        f"User: {user_name}\n"
        f"Message: {content}\n"
        "Gib eine passende freche Antwort."
    )

    # IMPORTANT: OpenAI SDK call is synchronous; run it in a thread so the bot stays responsive
    def call_openai() -> str:
        resp = ai.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.95,
            max_output_tokens=70,
        )
        out = sanitize(extract_output_text(resp))
        return out or "Okay… und jetzt?"

    return await asyncio.to_thread(call_openai)

@bot.event
async def on_ready():
    print(f"😈 KI-Frechbot läuft als {bot.user} | Channel: {ALLOWED_CHANNEL_ID}")

@bot.event
async def on_message(message: discord.Message):
    # ignore bots (prevents bot-loops)
    if message.author.bot:
        return

    # debug log so you can verify messages arrive + channel id matches
    print(f"[MSG] channel={message.channel.id} author={message.author} content={message.content!r}")

    # only respond in the allowed channel
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    content = (message.content or "").strip()

    # handle attachment-only / sticker-only messages
    if not content and message.attachments:
        content = "Hat ein Attachment geschickt."
    if not content and message.stickers:
        content = "Hat einen Sticker geschickt."
    if not content:
        content = "…"

    content = remove_bot_mentions(content)

    try:
        reply = await generate_reply(message.author.display_name, content)
        await message.reply(reply, mention_author=False)
    except Exception as e:
        print("OpenAI error:", repr(e))
        await message.reply(
            "Mein Sarkasmus-Server ist kurz umgekippt. Schreib’s nochmal.",
            mention_author=False,
        )

bot.run(DISCORD_TOKEN)
