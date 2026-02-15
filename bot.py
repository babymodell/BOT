import os
import re
import asyncio
import discord
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID"))
ROAST_MODE = (os.getenv("ROAST_MODE") or "mild").lower()

client = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)


def sanitize(text: str):
    return text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere").strip()


def remove_mentions(text: str):
    if bot.user:
        text = re.sub(rf"<@!?{bot.user.id}>", "", text)
    return text.strip()


async def generate_reply(username: str, content: str):

    system = (
        "Du bist ein frecher Discord Bot. "
        "Antworte kurz, frech und lustig auf Deutsch."
    )

    def call_openai():

        resp = client.responses.create(
            model="gpt-4o-mini",
            input=f"{system}\n\nUser {username} sagt: {content}\nFreche Antwort:"
        )

        return sanitize(resp.output_text)

    try:
        return await asyncio.to_thread(call_openai)

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "Meine KI hat dich gesehen und beschlossen zu schweigen."


@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")


@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    content = message.content.strip()

    if not content:
        content = "..."

    content = remove_mentions(content)

    reply = await generate_reply(
        message.author.display_name,
        content
    )

    await message.reply(reply, mention_author=False)


bot.run(DISCORD_TOKEN)
