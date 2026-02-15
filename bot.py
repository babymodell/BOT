# bot.py — FINAL FIXED VERSION (Railway + Discord + OpenAI)

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
intents.message_content = True  # must be enabled in Discord Developer Portal
bot = discord.Client(intents=intents)


# ------------- helpers -------------

def sanitize(text: str) -> str:
    if not text:
        return ""
    text = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    return text.strip()

def style_rules(mode: str) -> str:
    # Keep it "frech" but avoid hateful/violent stuff.
    if mode == "spicy":
        return (
            "Frech, sarkastisch, witzig. 1–2 kurze Sätze. "
            "Keine Slurs, keine Drohungen, keine Angriffe auf geschützte Merkmale."
        )
    return (
        "Neckisch-frech, humorvoll, PG-13. 1–2 kurze Sätze. "
        "Keine Slurs, keine Drohungen, keine Angriffe auf geschützte Merkmale."
    )

def remove_bot_mentions(text: str) -> str:
    if bot.user:
        text = re.sub(rf"<@!?{bot.user.id}>\s*", "", text).strip()
    return text


# ------------- OpenAI (FINAL FIX: chat.completions) -------------

async def generate_reply(user_name: str, content: str) -> str:
    system = (
        "Du bist ein Discord-Bot, der auf jede Nachricht frech antwortet (Deutsch).\n"
        + style_rules(ROAST_MODE)
        + "\nAntworte NUR mit dem Text. Optional 0–1 Emoji."
    )

    def call_openai() -> str:
        resp = ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"{user_name}: {content}"},
            ],
            temperature=0.9,
            max_tokens=70,
        )
        out = resp.choices[0].message.content or ""
        out = sanitize(out)
        return out or "Okay… und jetzt?"

    try:
        return await asyncio.to_thread(call_openai)
    except Exception as e:
        print("OPENAI ERROR:", repr(e))
        return "Selbst meine KI hat gerade keinen Bock auf das."


# ------------- Discord events -------------

@bot.event
async def on_ready():
    print(f"😈 KI-Frechbot läuft als {bot.user} | Channel: {ALLOWED_CHANNEL_ID} | Mode: {ROAST_MODE}")

@bot.event
async def on_message(message: discord.Message):
    # ignore bots to avoid loops
    if message.author.bot:
        return

    # debug log (helps in Railway logs)
    print(f"[MSG] channel={message.channel.id} author={message.author} content={message.content!r}")

    # only respond in this one channel
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    content = (message.content or "").strip()

    # attachment / sticker only
    if not content and message.attachments:
        content = "Hat ein Attachment geschickt."
    if not content and message.stickers:
        content = "Hat einen Sticker geschickt."
    if not content:
        content = "…"

    content = remove_bot_mentions(content)

    reply = await generate_reply(message.author.display_name, content)
    await message.reply(reply, mention_author=False)


bot.run(DISCORD_TOKEN)
