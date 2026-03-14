# iouDiscordBot

The bot will keep track and notify users of how much they owe each other.

So say you have 4 people, and they all go out to eat and one person just pays for everyone, the person logs the price using the discord bot, price = $40, people = 4, and then the bot records that every person in that group owns the payer $10

Every person within that group now owes that person $10

The bot will keep track on who owes what to each person and produce a summary at the end of a week as a message.

## To‑Do: Owing Calculator

- **Set up per‑server data structures**
  - `expenses[guild_id] = [expense, ...]` with: `payer_id`, `participants`, `amount`, `description`, `timestamp`
  - `settings[guild_id] = { "window_days": 7 }` as default

- **Implement rolling 7‑day window logic**
  - Helper to get `window_days` from `settings` (default 7)
  - Helper to filter `expenses[guild_id]` to only those with `timestamp >= now - window_days`

- **Add `/expense` command**
  - Arguments: `amount`, `description`, `participants` (one or more users)
  - Validate: `amount > 0`, and at least payer + one other participant
  - Ensure participants list is correct (decide whether payer is auto‑included)
  - Calculate individual share = total / number of participants
  - Append expense entry to `expenses[guild_id]` with current UTC timestamp
  - Reply with confirmation including per‑person share

- **Implement balance calculation from expenses**
  - Function to get windowed expenses for a guild
  - For each expense, update a `net[user_id]` balance dict:
    - Positive = user is owed money
    - Negative = user owes money
  - Use chosen logic (payer vs participants) to adjust net balances

- **Implement settlement calculation**
  - Convert `net` dict into separate debtor and creditor lists
  - Use a greedy algorithm to match debtors to creditors
  - Produce a list of `(debtor_id, creditor_id, amount)` tuples representing “X pays Y $amount”

- **Add `/summary` command**
  - Compute net balances for the guild over the current window
  - Compute settlements from net balances
  - If no expenses or all nets ≈ 0, indicate that everything is settled
  - Otherwise, display who should pay whom (and optionally each user’s net position)

- **Add `/mystatus` command**
  - Compute net balances for the guild
  - Look up the invoking user’s net value
  - Send an ephemeral response indicating whether they are settled, owed money, or owe money (with amounts)

- **Add `/setwindow` command (server setting)**
  - Admin‑only (check `manage_guild` or similar permission)
  - Accept `days` integer and validate it within a reasonable range
  - Update `settings[guild_id]["window_days"]`
  - Confirm the new window length in the response

- **Optional polish and robustness**
  - Round money values to 2 decimal places
  - Use embeds for `/summary` output
  - Add clear error messages (e.g. missing participants, no expenses in window)
  - Add persistence (e.g. JSON or database) instead of in‑memory only