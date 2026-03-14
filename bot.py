import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "data.json"

if TOKEN is None:
    raise ValueError("No DISCORD_TOKEN found in .env file")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# =========================
# DATA FUNCTIONS
# =========================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"debts": {}}

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        if "debts" not in data:
            data["debts"] = {}

        return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"debts": {}}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


data = load_data()


# =========================
# DEBT HELPERS
# =========================
def get_debt(debtor_id: str, creditor_id: str) -> float:
    return data["debts"].get(debtor_id, {}).get(creditor_id, 0.0)


def set_debt(debtor_id: str, creditor_id: str, amount: float):
    if amount <= 0:
        # remove empty debt
        if debtor_id in data["debts"] and creditor_id in data["debts"][debtor_id]:
            del data["debts"][debtor_id][creditor_id]

            if len(data["debts"][debtor_id]) == 0:
                del data["debts"][debtor_id]
    else:
        if debtor_id not in data["debts"]:
            data["debts"][debtor_id] = {}

        data["debts"][debtor_id][creditor_id] = round(amount, 2)


def add_debt(debtor_id: str, creditor_id: str, amount: float):
    """
    Adds debt in a smart way:
    - if debtor already owes creditor, increase it
    - if creditor owes debtor, offset it first
    """
    if debtor_id == creditor_id or amount <= 0:
        return

    current_forward = get_debt(debtor_id, creditor_id)
    current_reverse = get_debt(creditor_id, debtor_id)

    if current_reverse > 0:
        # offset opposite debts first
        if current_reverse > amount:
            set_debt(creditor_id, debtor_id, current_reverse - amount)
        elif current_reverse < amount:
            set_debt(creditor_id, debtor_id, 0)
            set_debt(debtor_id, creditor_id, amount - current_reverse)
        else:
            set_debt(creditor_id, debtor_id, 0)
    else:
        set_debt(debtor_id, creditor_id, current_forward + amount)

    save_data(data)


def reduce_debt(debtor_id: str, creditor_id: str, amount: float):
    """
    Used when debtor pays creditor back.
    """
    if amount <= 0:
        return False, "Amount must be greater than 0."

    current = get_debt(debtor_id, creditor_id)

    if current <= 0:
        return False, "You do not currently owe that user anything."

    new_amount = current - amount

    if new_amount < 0:
        return False, f"You only owe ${current:.2f}, so you can't pay back ${amount:.2f}."

    set_debt(debtor_id, creditor_id, new_amount)
    save_data(data)
    return True, f"Payment recorded. Remaining debt: ${new_amount:.2f}"


def get_people_who_owe_user(user_id: str):
    """
    Returns list of (debtor_id, amount) where debtor owes user_id
    """
    results = []
    for debtor_id, creditors in data["debts"].items():
        if user_id in creditors:
            results.append((debtor_id, creditors[user_id]))
    return results


def get_people_user_owes(user_id: str):
    """
    Returns list of (creditor_id, amount) where user_id owes creditor
    """
    results = []
    if user_id in data["debts"]:
        for creditor_id, amount in data["debts"][user_id].items():
            results.append((creditor_id, amount))
    return results


def get_net_between(user1_id: str, user2_id: str):
    """
    Returns:
    > 0 if user1 owes user2
    < 0 if user2 owes user1
    = 0 if settled
    """
    forward = get_debt(user1_id, user2_id)
    reverse = get_debt(user2_id, user1_id)
    return round(forward - reverse, 2)


# =========================
# BOT SETUP
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync error: {e}")


# =========================
# COMMANDS
# =========================
@bot.tree.command(name="add_expense", description="Record that you paid for a group expense.")
@app_commands.describe(
    amount="Total amount you paid",
    user1="Person involved",
    user2="Optional person involved",
    user3="Optional person involved",
    user4="Optional person involved",
    user5="Optional person involved"
)
async def add_expense(
    interaction: discord.Interaction,
    amount: float,
    user1: discord.User,
    user2: discord.User = None,
    user3: discord.User = None,
    user4: discord.User = None,
    user5: discord.User = None
):
    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        return

    payer = interaction.user
    payer_id = str(payer.id)

    involved_users = [user1, user2, user3, user4, user5]
    involved_users = [u for u in involved_users if u is not None]

    # remove duplicates and remove payer if tagged
    unique_users = []
    seen_ids = set()

    for user in involved_users:
        if user.id == payer.id:
            continue
        if user.id not in seen_ids:
            seen_ids.add(user.id)
            unique_users.append(user)

    if len(unique_users) == 0:
        await interaction.response.send_message(
            "You need to tag at least one other user.",
            ephemeral=True
        )
        return

    total_people = len(unique_users) + 1  # include the payer
    split_amount = round(amount / total_people, 2)

    for user in unique_users:
        add_debt(str(user.id), payer_id, split_amount)

    mentions = ", ".join(user.mention for user in unique_users)

    await interaction.response.send_message(
        f"Expense recorded.\n"
        f"Total bill: **${amount:.2f}**\n"
        f"Split between **{total_people}** people, so each share is **${split_amount:.2f}**.\n"
        f"{mentions} now owe you **${split_amount:.2f}** each."
    )

@bot.tree.command(name="payback", description="Record that you paid someone back.")
@app_commands.describe(
    user="The person you are paying back",
    amount="Amount you paid back"
)
async def payback(interaction: discord.Interaction, user: discord.User, amount: float):
    debtor_id = str(interaction.user.id)
    creditor_id = str(user.id)

    if debtor_id == creditor_id:
        await interaction.response.send_message("You cannot pay yourself.", ephemeral=True)
        return

    success, message = reduce_debt(debtor_id, creditor_id, amount)

    if success:
        await interaction.response.send_message(
            f"Recorded that you paid {user.mention} **${amount:.2f}** back.\n{message}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="owed_to_me", description="See who owes you money.")
async def owed_to_me(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    owed_list = get_people_who_owe_user(user_id)

    if not owed_list:
        await interaction.response.send_message("Nobody owes you anything right now.", ephemeral=True)
        return

    lines = []
    total = 0.0

    for debtor_id, amount in owed_list:
        debtor_user = await bot.fetch_user(int(debtor_id))
        lines.append(f"- **{debtor_user.name}** owes you **${amount:.2f}**")
        total += amount

    message = "\n".join(lines)
    message += f"\n\n**Total owed to you: ${total:.2f}**"

    await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="i_owe", description="See who you owe money to.")
async def i_owe(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    owe_list = get_people_user_owes(user_id)

    if not owe_list:
        await interaction.response.send_message("You do not owe anyone anything right now.", ephemeral=True)
        return

    lines = []
    total = 0.0

    for creditor_id, amount in owe_list:
        creditor_user = await bot.fetch_user(int(creditor_id))
        lines.append(f"- You owe **{creditor_user.name}** **${amount:.2f}**")
        total += amount

    message = "\n".join(lines)
    message += f"\n\n**Total you owe: ${total:.2f}**"

    await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="check_with", description="Check the balance between you and another user.")
@app_commands.describe(user="The user you want to check with")
async def check_with(interaction: discord.Interaction, user: discord.User):
    me_id = str(interaction.user.id)
    other_id = str(user.id)

    if me_id == other_id:
        await interaction.response.send_message("You cannot check balances with yourself.", ephemeral=True)
        return

    net = get_net_between(me_id, other_id)

    if net > 0:
        await interaction.response.send_message(
            f"You owe {user.mention} **${net:.2f}**.",
            ephemeral=True
        )
    elif net < 0:
        await interaction.response.send_message(
            f"{user.mention} owes you **${abs(net):.2f}**.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"You and {user.mention} are all settled up.",
            ephemeral=True
        )


@bot.tree.command(name="all_balances", description="Show all balances involving you.")
async def all_balances(interaction: discord.Interaction):
    user_id = str(interaction.user.id)

    owed_to_me = get_people_who_owe_user(user_id)
    i_owe_list = get_people_user_owes(user_id)

    if not owed_to_me and not i_owe_list:
        await interaction.response.send_message(
            "You have no balances recorded right now.",
            ephemeral=True
        )
        return

    lines = []

    if owed_to_me:
        lines.append("**People who owe you:**")
        total_in = 0.0
        for debtor_id, amount in owed_to_me:
            debtor_user = await bot.fetch_user(int(debtor_id))
            lines.append(f"- {debtor_user.name}: ${amount:.2f}")
            total_in += amount
        lines.append(f"Total owed to you: **${total_in:.2f}**\n")

    if i_owe_list:
        lines.append("**People you owe:**")
        total_out = 0.0
        for creditor_id, amount in i_owe_list:
            creditor_user = await bot.fetch_user(int(creditor_id))
            lines.append(f"- {creditor_user.name}: ${amount:.2f}")
            total_out += amount
        lines.append(f"Total you owe: **${total_out:.2f}**")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


bot.run(TOKEN)