import os
import re
import discord
from discord import app_commands
from discord.ext import commands

# ============ ENV VARS (Railway Variables) ============
def required_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v

TOKEN = required_env("TOKEN")

# Optional, aber empfohlen für schnelles Command-Sync:
# Wenn du es nicht setzen willst, kann der Bot trotzdem laufen,
# dann syncen wir global (kann länger dauern, bis /panel erscheint).
GUILD_ID = os.getenv("GUILD_ID")  # optional

PANEL_CHANNEL_ID = int(required_env("PANEL_CHANNEL_ID"))
TICKET_CATEGORY_ID = int(required_env("TICKET_CATEGORY_ID"))
STAFF_ROLE_ID = int(required_env("STAFF_ROLE_ID"))

# ============ DISCORD SETUP ============
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def slugify_channel_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\-_]", "-", name)
    name = re.sub(r"-{2,}", "-", name)
    name = name[:90].strip("-")
    return name or "ticket"


# ============ UI: MODAL ============
class CreateChannelModal(discord.ui.Modal, title="Channel-Erstellung"):
    channel_name = discord.ui.TextInput(
        label="Channel-Name (z.B. ticket-max)",
        placeholder="ticket-max",
        required=True,
        max_length=50
    )

    discord_user_id = discord.ui.TextInput(
        label="Discord User ID (z.B. 123...)",
        placeholder="123456789012345678",
        required=True,
        max_length=30
    )

    phone = discord.ui.TextInput(
        label="Telefonnummer",
        required=False,
        max_length=30
    )

    email = discord.ui.TextInput(
        label="E-Mail",
        required=False,
        max_length=80
    )

    name_ingame = discord.ui.TextInput(
        label="Name | Ingame Name | Ingame ID",
        placeholder="Max Mustermann | Max#123 | 9999",
        required=False,
        max_length=120
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "❌ Das geht nur in einem Server.", ephemeral=True
            )

        raw_name = str(self.channel_name.value)
        user_id_raw = str(self.discord_user_id.value).strip()

        phone = str(self.phone.value).strip() if self.phone.value else "—"
        email = str(self.email.value).strip() if self.email.value else "—"
        name_ingame = str(self.name_ingame.value).strip() if self.name_ingame.value else "—"

        safe_name = slugify_channel_name(raw_name)

        # Member fetch
        try:
            target_member = await guild.fetch_member(int(user_id_raw))
        except Exception:
            return await interaction.response.send_message(
                "❌ User ID nicht gefunden. Bitte prüfe die Discord User ID.",
                ephemeral=True
            )

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "❌ TICKET_CATEGORY_ID ist falsch oder keine Kategorie.",
                ephemeral=True
            )

        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role is None:
            return await interaction.response.send_message(
                "❌ STAFF_ROLE_ID ist falsch (Rolle nicht gefunden).",
                ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
            target_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
        }

        # Create channel
        try:
            channel = await guild.create_text_channel(
                name=safe_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user} for {target_member}"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ Mir fehlen Rechte (Manage Channels / Zugriff auf Kategorie).",
                ephemeral=True
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"❌ Fehler beim Erstellen des Channels: {e}",
                ephemeral=True
            )

        embed = discord.Embed(title="🧾 Neue Anfrage", color=discord.Color.blurple())
        embed.add_field(name="Discord User", value=f"{target_member.mention} ({target_member.id})", inline=False)
        embed.add_field(name="Telefon", value=phone, inline=True)
        embed.add_field(name="E-Mail", value=email, inline=True)
        embed.add_field(name="Name | Ingame | Ingame ID", value=name_ingame, inline=False)
        embed.set_footer(text="Bilder bitte hier im Channel als Upload oder Link posten.")
        embed.timestamp = discord.utils.utcnow()

        await channel.send(content=f"{target_member.mention} {staff_role.mention}", embed=embed)

        await interaction.response.send_message(
            f"✅ Channel erstellt: {channel.mention}",
            ephemeral=True
        )


# ============ UI: PANEL VIEW ============
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Channel erstellen", style=discord.ButtonStyle.primary, custom_id="panel_create_channel")
    async def create_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateChannelModal())


# ============ COMMANDS ============
@bot.event
async def on_ready():
    print(f"✅ Eingeloggt als {bot.user} ({bot.user.id})")


@bot.tree.command(name="panel", description="Postet das Channel-Erstell-Panel in den Panel-Channel (Admin).")
@app_commands.default_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    # Panel channel holen
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(PANEL_CHANNEL_ID)
        except Exception:
            return await interaction.response.send_message(
                "❌ PANEL_CHANNEL_ID ist falsch / Channel nicht gefunden.",
                ephemeral=True
            )

    embed = discord.Embed(title="📌 Channel erstellen", color=discord.Color.green())
    embed.description = (
        "Klicke auf den Button und fülle das Formular aus.\n"
        "Es wird automatisch ein privater Channel erstellt."
    )
    embed.set_footer(text="Bitte keine Fake-Daten. Datenschutz beachten.")

    await channel.send(embed=embed, view=PanelView())
    await interaction.response.send_message("✅ Panel wurde gepostet.", ephemeral=True)


# ============ STARTUP: persistent view + sync ============
class MyBot(commands.Bot):
    async def setup_hook(self):
        # Persistente View (Buttons funktionieren auch nach Restart)
        self.add_view(PanelView())

        # Command sync
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("✅ Commands (Guild) synced.")
        else:
            await self.tree.sync()
            print("✅ Commands (Global) synced (kann dauern bis sichtbar).")


# replace bot instance with subclassed bot
bot = MyBot(command_prefix="!", intents=intents)

# re-register command on new bot tree
@bot.tree.command(name="panel", description="Postet das Channel-Erstell-Panel in den Panel-Channel (Admin).")
@app_commands.default_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(PANEL_CHANNEL_ID)
        except Exception:
            return await interaction.response.send_message(
                "❌ PANEL_CHANNEL_ID ist falsch / Channel nicht gefunden.",
                ephemeral=True
            )

    embed = discord.Embed(title="📌 Channel erstellen", color=discord.Color.green())
    embed.description = (
        "Klicke auf den Button und fülle das Formular aus.\n"
        "Es wird automatisch ein privater Channel erstellt."
    )
    embed.set_footer(text="Bitte keine Fake-Daten. Datenschutz beachten.")

    await channel.send(embed=embed, view=PanelView())
    await interaction.response.send_message("✅ Panel wurde gepostet.", ephemeral=True)


bot.run(TOKEN)
