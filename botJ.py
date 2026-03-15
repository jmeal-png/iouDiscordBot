import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from typing import Optional

# --- CONFIG ---
#TOKEN = "TOKEN"  # replace with your real token or use an env var

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# In‑memory per‑server storage
# -----------------------------
# guild_id -> list of expense dicts
# expense: {
#   "payer_id": int,
#   "participants": list[int],
#   "amount": float,
#   "description": str,
#   "timestamp": datetime
# }
expenses: dict[int, list[dict]] = {}

# guild_id -> settings dict
# default: { "window_days": 7 }
settings: dict[int, dict] = {}


def get_guild_settings(guild_id: int) -> dict:
    """Return settings for a guild, creating default if missing."""
    if guild_id not in settings:
        settings[guild_id] = {"window_days": 7}
    return settings[guild_id]


def get_guild_expenses(guild_id: int) -> list:
    """Return expense list for a guild, creating empty if missing."""
    if guild_id not in expenses:
        expenses[guild_id] = []
    return expenses[guild_id]


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync error: {e}")


# -----------------------------
# Slash commands
# -----------------------------

@bot.tree.command(name="add_expense", description="Add an expense for this server.")
@app_commands.describe(
    amount="Total amount paid",
    description="What was this expense for?",
    payer_included="Should the payer be included as a participant?"
)
async def add_expense(
    interaction: discord.Interaction,
    amount: float,
    description: str,
    participant1: discord.User,
    participant2: Optional[discord.User] = None,
    participant3: Optional[discord.User] = None,
    participant4: Optional[discord.User] = None,
    participant5: Optional[discord.User] = None,
    participant6: Optional[discord.User] = None,
    payer_included: bool = True,
):
        await interaction.response.send_message("Expense added! (not implemented yet)")

@bot.tree.command(name="list_expenses", description="List recent expenses for this server.")
async def list_expenses(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.", ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    guild_settings = get_guild_settings(guild_id)
    window_days = guild_settings["window_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    exp_list = get_guild_expenses(guild_id)
    recent = [e for e in exp_list if e["timestamp"] >= cutoff]

    if not recent:
        await interaction.response.send_message(
            f"No expenses in the last **{window_days}** day(s)."
        )
        return

    lines = []
    for e in recent[-10:]:  # last 10 only for brevity
        payer_mention = f"<@{e['payer_id']}>"
        participant_mentions = ", ".join(f"<@{pid}>" for pid in e["participants"])
        time_str = e["timestamp"].strftime("%Y-%m-%d %H:%M UTC")
        lines.append(
            f"- {time_str}: {payer_mention} paid **${e['amount']:.2f}** "
            f"for *{e['description']}* (participants: {participant_mentions})"
        )

    msg = f"Recent expenses (last {window_days} day(s)):\n" + "\n".join(lines)
    await interaction.response.send_message(msg)


@bot.tree.command(name="get_settings", description="Show owing settings for this server.")
async def get_settings_cmd(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.", ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    guild_settings = get_guild_settings(guild_id)
    await interaction.response.send_message(
        f"Current window is **{guild_settings['window_days']}** day(s)."
    )


@bot.tree.command(name="set_window", description="Set the number of days used for owing calculations.")
@app_commands.describe(days="Number of days to look back for expenses")
async def set_window(interaction: discord.Interaction, days: int):
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.", ephemeral=True
        )
        return

    if days <= 0:
        await interaction.response.send_message(
            "Window must be a positive number of days.", ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    guild_settings = get_guild_settings(guild_id)
    guild_settings["window_days"] = days

    await interaction.response.send_message(
        f"Set owing window to **{days}** day(s) for this server."
    )


bot.run(TOKEN)