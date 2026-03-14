import os
import discord
from discord.ext import commands
from discord import app_commands

# --- CONFIG ---
TOKEN = "MTQ4MjIyNDQ4ODI5MTYzMTI2NA.GD5hiN.L2crKWqEGTnu3pgYQ_kFDMVEq0vgJ3qHPKANEQ"  # replace with your real token or use an env var

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True  # only needed for prefix commands

bot = commands.Bot(command_prefix="!", intents=intents)

# In‑memory storage: user_id -> integer
user_values = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync error: {e}")


# --- Slash command: submit a number ---
@bot.tree.command(name="submit", description="Submit an integer to be recorded.")
@app_commands.describe(value="The integer you want to submit")
async def submit(interaction: discord.Interaction, value: int):
    user_id = interaction.user.id
    user_values[user_id] = value
    await interaction.response.send_message(
        f"Recorded {value} for {interaction.user.mention}.", ephemeral=True
    )


# --- Slash command: check your number ---
@bot.tree.command(name="myvalue", description="Check the integer you submitted.")
async def myvalue(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in user_values:
        await interaction.response.send_message(
            "You haven't submitted a value yet. Use `/submit <number>`.", ephemeral=True
        )
        return

    value = user_values[user_id]
    await interaction.response.send_message(
        f"Your recorded value is **{value}**.", ephemeral=True
    )


# --- Slash command: check someone else's number (optional) ---
@bot.tree.command(name="check", description="Check another user's submitted integer.")
@app_commands.describe(user="The user whose value you want to see")
async def check(interaction: discord.Interaction, user: discord.User):
    user_id = user.id
    if user_id not in user_values:
        await interaction.response.send_message(
            f"{user.mention} hasn't submitted a value yet."
        )
        return

    value = user_values[user_id]
    await interaction.response.send_message(
        f"{user.mention}'s recorded value is **{value}**."
    )


bot.run(TOKEN)