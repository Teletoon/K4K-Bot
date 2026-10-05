import os
import asyncio
import random
import re
from datetime import timedelta

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional


TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def parse_duration(duration: str, max_seconds: Optional[int] = None):
    """
    Accepts:
    60s = 60 seconds
    10m = 10 minutes
    2h  = 2 hours
    3d  = 3 days
    1w  = 1 week
    """

    match = re.fullmatch(r"(\d+)([smhdw])", duration.lower().strip())

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 60 * 60,
        "d": 60 * 60 * 24,
        "w": 60 * 60 * 24 * 7
    }

    seconds = amount * multipliers[unit]

    if max_seconds is not None and seconds > max_seconds:
        return None

    return seconds


async def temporary_unban(
    guild: discord.Guild,
    user_id: int,
    seconds: int
):
    await asyncio.sleep(seconds)

    try:
        user = await bot.fetch_user(user_id)
        await guild.unban(
            user,
            reason="Temporary ban expired."
        )
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass


# --------------------------------------------------
# READY
# --------------------------------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# --------------------------------------------------
# /say
# --------------------------------------------------

say_group = app_commands.Group(
    name="say",
    description="Send a message"
)


# --------------------------------------------------
# /say text
# --------------------------------------------------

@say_group.command(
    name="text",
    description="Send a text message."
)
@app_commands.describe(
    text="Message to send",
    color="Optional — choose a colour or leave empty for normal text"
)
@app_commands.choices(
    color=[
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="Yellow", value="yellow"),
        app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Black", value="black"),
        app_commands.Choice(name="White", value="white"),
        app_commands.Choice(name="Cyan", value="cyan"),
        app_commands.Choice(name="Orange", value="orange"),
        app_commands.Choice(name="Pink", value="pink"),
    ]
)
async def say_text(
    interaction: discord.Interaction,
    text: str,
    color: Optional[app_commands.Choice[str]] = None
):
    allowed_mentions = discord.AllowedMentions(
        users=True,
        roles=False,
        everyone=False
    )

    if color:
        colors = {
            "blue": discord.Color.blue(),
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "yellow": discord.Color.yellow(),
            "purple": discord.Color.purple(),
            "black": discord.Color(0x010101),
            "white": discord.Color(0xF0F0F0),
            "cyan": discord.Color(0x00FFFF),
            "orange": discord.Color(0xFF7700),
            "pink": discord.Color(0xFF6297),
        }

        embed = discord.Embed(
            description=text,
            color=colors[color.value]
        )

        await interaction.channel.send(
            embed=embed,
            allowed_mentions=allowed_mentions
        )

    else:
        await interaction.channel.send(
            text,
            allowed_mentions=allowed_mentions
        )

    await interaction.response.send_message(
        "Message sent.",
        ephemeral=True
    )  


# --------------------------------------------------
# /say image
# --------------------------------------------------

@say_group.command(
    name="image",
    description="Send an image."
)
async def say_image(
    interaction: discord.Interaction,
    image: discord.Attachment,
    text: Optional[str] = None
):
    await interaction.channel.send(
        content=text,
        file=await image.to_file()
    )

    await interaction.response.send_message(
        "Image sent.",
        ephemeral=True
    )


bot.tree.add_command(say_group)


# --------------------------------------------------
# /edit-message
# --------------------------------------------------

class EditMessageModal(discord.ui.Modal):
    def __init__(self, message: discord.Message):
        super().__init__(
            title="Edit Message"
        )

        self.message = message

        # Coloured embed message
        if message.embeds and message.embeds[0].description:
            current_text = message.embeds[0].description

        # Normal text message
        else:
            current_text = message.content

        self.text_input = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            default=current_text,
            required=True,
            max_length=2000
        )

        self.add_item(self.text_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        allowed_mentions = discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )

        new_text = self.text_input.value

        # If the bot message uses an embed,
        # edit the embed instead of adding normal text above it.
        if self.message.embeds:
            old_embed = self.message.embeds[0]

            new_embed = discord.Embed(
                description=new_text,
                color=old_embed.color
            )

            await self.message.edit(
                content=None,
                embed=new_embed,
                allowed_mentions=allowed_mentions
            )

        # Normal message
        else:
            await self.message.edit(
                content=new_text,
                allowed_mentions=allowed_mentions
            )

        await interaction.response.send_message(
            "Message edited.",
            ephemeral=True
        )


@bot.tree.command(
    name="edit-message",
    description="Edit a message sent by the bot."
)
async def edit_message(
    interaction: discord.Interaction,
    message_id: str
):
    try:
        message = await interaction.channel.fetch_message(
            int(message_id)
        )

        if message.author.id != bot.user.id:
            await interaction.response.send_message(
                "I can only edit K4K Bot's messages.",
                ephemeral=True
            )
            return

        modal = EditMessageModal(message)

        await interaction.response.send_modal(modal)

    except discord.NotFound:
        await interaction.response.send_message(
            "Message not found.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to edit this message.",
            ephemeral=True
        )

    except ValueError:
        await interaction.response.send_message(
            "Invalid message ID.",
            ephemeral=True
        )


# --------------------------------------------------
# /timeout
# --------------------------------------------------

@bot.tree.command(
    name="timeout",
    description="Timeout a user for up to 1 week."
)
@app_commands.describe(
    user="User to timeout",
    duration="Duration (max 1 week): s=seconds, m=minutes, h=hours, d=days, w=weeks",
    reason="Reason for the timeout (optional)"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    user: discord.Member,
    duration: str,
    reason: Optional[str] = None
):
    seconds = parse_duration(
        duration,
        max_seconds=7 * 24 * 60 * 60
    )

    if seconds is None:
        await interaction.response.send_message(
            "Invalid duration. Use something like `60s`, `10m`, `2h`, "
            "`3d`, or `1w`. Maximum: 1 week.",
            ephemeral=True
        )
        return

    try:
        await user.timeout(
            timedelta(seconds=seconds),
            reason=reason
        )

        # Private confirmation
        await interaction.response.send_message(
            "Timeout applied.",
            ephemeral=True
        )

        # Public message from K4K Bot
        await interaction.channel.send(
            f"⏱️ {user.mention} is timed out for **{duration}**.\n"
            f"Reason: {reason or 'No reason provided.'}",
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot timeout this user. Check my role and permissions.",
            ephemeral=True
        )


# --------------------------------------------------
# /remove-timeout
# --------------------------------------------------

@bot.tree.command(
    name="remove-timeout",
    description="Remove a user's timeout."
)
@app_commands.checks.has_permissions(moderate_members=True)
async def remove_timeout(
    interaction: discord.Interaction,
    user: discord.Member
):
    try:
        # Actually remove the timeout
        await user.timeout(
            None,
            reason=f"Timeout removed by {interaction.user}"
        )

        # Private confirmation
        await interaction.response.send_message(
            "Timeout removed.",
            ephemeral=True
        )

        # Public message from K4K Bot
        await interaction.channel.send(
            f"🔊 **{user}** is removed from timeout."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot remove this user's timeout.",
            ephemeral=True
        )


# --------------------------------------------------
# /ban
# --------------------------------------------------

@bot.tree.command(
    name="ban",
    description="Ban a user inside or outside the server."
)
@app_commands.describe(
    user="Username or User ID",
    reason="Reason for the ban",
    delete_messages="Delete message history"
)
@app_commands.choices(
    delete_messages=[
        app_commands.Choice(
            name="Don't delete messages",
            value=0
        ),
        app_commands.Choice(
            name="1 day",
            value=86400
        ),
        app_commands.Choice(
            name="3 days",
            value=259200
        ),
        app_commands.Choice(
            name="7 days",
            value=604800
        )
    ]
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    user: str,
    reason: str,
    delete_messages: Optional[app_commands.Choice[int]] = None
):
    await interaction.response.defer(ephemeral=True)

    delete_seconds = (
        delete_messages.value
        if delete_messages
        else 0
    )

    guild = interaction.guild

    try:
        target = None
        entered_user = user.strip()

        # User mention
        if entered_user.startswith("<@") and entered_user.endswith(">"):
            entered_user = (
                entered_user
                .replace("<@", "")
                .replace("!", "")
                .replace(">", "")
            )

        # User ID
        if entered_user.isdigit():
            user_id = int(entered_user)

            # First check if they're currently in the server
            target = guild.get_member(user_id)

            # If not, fetch their Discord account
            if target is None:
                target = await bot.fetch_user(user_id)

        # Username
        else:
            search = entered_user.lower()

            for member in guild.members:
                if (
                    member.name.lower() == search
                    or member.display_name.lower() == search
                    or str(member).lower() == search
                ):
                    target = member
                    break

            if target is None:
                await interaction.followup.send(
                    "❌ I couldn't find that username in this server. "
                    "If the user is outside the server, use their User ID.",
                    ephemeral=True
                )
                return

        user_name = str(target)

        await guild.ban(
            target,
            reason=reason,
            delete_message_seconds=delete_seconds
        )

        await interaction.followup.send(
            "User banned.",
            ephemeral=True
        )

        await interaction.channel.send(
            f"🚫 **{user_name}** is banned.\n"
            f"Reason: **{reason}**"
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ I couldn't find a Discord account with that User ID.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I cannot ban this user. Check my Ban Members "
            "permission and role position.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord rejected the ban: `{error}`",
            ephemeral=True
        )


# --------------------------------------------------
# /unban
# --------------------------------------------------

@bot.tree.command(
    name="unban",
    description="Unban a user by their Discord user ID."
)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):
    try:
        user = await bot.fetch_user(int(user_id))

        # Actually unban the user
        await interaction.guild.unban(user)

        # Private confirmation to the moderator
        await interaction.response.send_message(
            "User unbanned.",
            ephemeral=True
        )

        # Public announcement from K4K Bot
        await interaction.channel.send(
            f"✅ **{user}** is unbanned."
        )

    except ValueError:
        await interaction.response.send_message(
            "Invalid user ID.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.response.send_message(
            "That user is not currently banned.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to unban users.",
            ephemeral=True
        )


# --------------------------------------------------
# /kick
# --------------------------------------------------

@bot.tree.command(
    name="kick",
    description="Kick a user from the server."
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None
):
    try:
        user_name = str(user)

        await user.kick(reason=reason)

        # Private confirmation to the moderator
        await interaction.response.send_message(
            "User kicked.",
            ephemeral=True
        )

        # Public announcement from K4K Bot
        await interaction.channel.send(
            f"🦿 **{user_name}** is kicked.\n"
            f"Reason: {reason or 'No reason provided.'}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot kick this user. Check the role hierarchy.",
            ephemeral=True
        )


# --------------------------------------------------
# /clear
# --------------------------------------------------

@bot.tree.command(
    name="clear",
    description="Clear messages from a specified member."
)
@app_commands.describe(
    amount="Amount of messages to delete (1-20)",
    member="Member whose messages will be deleted"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(
    interaction: discord.Interaction,
    amount: int,
    member: discord.Member
):
    if amount < 1 or amount > 20:
        await interaction.response.send_message(
            "❌ You can only delete between **1 and 20 messages**.",
            ephemeral=True
        )
        return

    # Private acknowledgement — hides "used /clear"
    await interaction.response.defer(
        ephemeral=True
    )

    messages = []

    async for message in interaction.channel.history(limit=100):
        if message.author.id == member.id:
            messages.append(message)

            if len(messages) >= amount:
                break

    for message in messages:
        await message.delete()

    # Public message sent normally by K4K Bot
    await interaction.channel.send(
        f"🧹 Deleted **{len(messages)} message(s)** from **{member}**."
    )


# --------------------------------------------------
# /avatar
# --------------------------------------------------

@bot.tree.command(
    name="avatar",
    description="Show a user's avatar."
)
async def avatar(
    interaction: discord.Interaction,
    user: Optional[discord.Member] = None
):
    user = user or interaction.user

    embed = discord.Embed(
        title=f"{user.display_name}'s Avatar",
        color=discord.Color.green()
    )

    embed.set_image(
        url=user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed)


# --------------------------------------------------
# /server-icon
# --------------------------------------------------

@bot.tree.command(
    name="server-icon",
    description="Show the server icon."
)
async def server_icon(
    interaction: discord.Interaction
):
    guild = interaction.guild

    if guild.icon is None:
        await interaction.response.send_message(
            "This server does not have an icon.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"{guild.name} Server Icon",
        color=discord.Color.green()
    )

    embed.set_image(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


# --------------------------------------------------
# /help
# --------------------------------------------------

@bot.tree.command(
    name="help",
    description="Show all K4K Bot commands."
)
async def help_command(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🤖 K4K Bot — Help",
        description=(
            "Here is the list of available K4K Bot commands.\n"
            "Some moderation commands require staff permissions."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="💬 Messages",
        value=(
            "**/say text** — Send a text message through K4K Bot.\n"
            "**/say image** — Send an image through K4K Bot.\n"
            "**/edit-message** — Edit a message previously sent by K4K Bot."
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "**/timeout** — Timeout a member up to 1 week.\n"
            "**/remove-timeout** — Remove a member's timeout.\n"
            "**/ban** — Ban a member from the server.\n"
            "**/unban** — Unban a member with their User ID.\n"
            "**/kick** — Kick a member from the server.\n"
            "**/clear** — Delete 1–20 messages from a selected member."
        ),
        inline=False
    )

    embed.add_field(
        name="👤 Server & User",
        value=(
	    "**/server-icon** — Show the server's icon.\n"
             "**/avatar** — Show a user's avatar."
        ),
        inline=False
    )

    embed.set_footer(
        text="K4K Bot"
    )

    await interaction.response.send_message(
        embed=embed
    )


# --------------------------------------------------
# ERROR HANDLER
# --------------------------------------------------

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        message = "❌ You don't have permission to use this command."

    else:
        print(f"Command error: {error}")
        message = "❌ Something went wrong while running this command."

    if interaction.response.is_done():
        await interaction.followup.send(
            message,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            message,
            ephemeral=True
        )


bot.run(TOKEN)