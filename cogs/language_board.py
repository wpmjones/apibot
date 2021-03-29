from typing import Optional, Union
from pathlib import Path

import discord
from discord.ext import commands
from discord import RawReactionActionEvent, Emoji, Role, Embed, Message, Member, Guild


PANEL_DIRECTIONS = "Choose your language to receive your language role"
IMAGE_PATH = Path("language_board_image.png")


class LanguageBoard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gap = "<:gap:823216162568405012>"

    async def _get_role_obj(self, ctx: Union[commands.Context, int], role_id: int) -> Optional[Role]:
        """Get role object, otherwise log and return None"""
        if isinstance(ctx, int):
            guild = self.bot.get_guild(ctx)
            role = guild.get_role(role_id)
            return role
        else:
            try:
                return ctx.guild.get_role(role_id)
            except Exception:
                self.bot.logger.exception(f"Could not retrieve role {role_id}")
                print("Could not get role ", role_id)
                return None

    async def _get_emoji_obj(self, ctx: commands.Context, emoji_id: int) -> Optional[Emoji]:
        """Get emoji object, otherwise log and return None. Docs recommend iteration instead
        of fetching"""
        for emoji in ctx.guild.emojis:
            if emoji.id == emoji_id:
                return emoji
        self.bot.logger.exception(f"Could not retrieve role {emoji_id}")
        return None

    def _get_int_from_string(self, string: str) -> Optional[int]:
        """Cast string object into a integer object"""
        if string.isdigit():
            return int(string)
        else:
            self.bot.logger.error(f"User input {string} could not be casted to integer")
            return None

    @staticmethod
    def _get_emoji_from_string(string: str) -> Optional[int]:
        """Extract the emoji ID from the string"""
        emoji_id = string.split(":")[-1].rstrip(">")
        if emoji_id.isdigit():
            return int(emoji_id)
        return None

    @staticmethod
    def _get_emoji_repr(emoji: Emoji) -> str:
        """Cast emoji object to a discord acceptable print format"""
        return f"<:{emoji.name}:{emoji.id}>"

    async def _get_role_stats(self, guild: Guild) -> dict:
        """Counts how many users are in each role and returns a dictionary

        Parameters
        ----------
        ctx: commands.Context
            Context is used to access server roles

        Returns
        -------
        dict
            Dictionary containing the stats
                {
                    no_roles: int,
                    "roles": list,
                    "spacing": int,
                    "$sample_role": {
                            "count": int,
                            "emoji_repr: $emoji"
                            }
                }
        """
        # Local constants
        bot_maker_role = "Bot Maker"
        no_roles = "No Roles"
        sql = "SELECT role_id, role_name, emoji_repr FROM bot_language_board"
        records = await self.bot.pool.fetch(sql)
        include = [record['role_name'] for record in records]
        include.append(bot_maker_role)

        # Object that is returned
        role_stats = {
            no_roles: 0,
            "roles": [],
            "records": records,
            "spacing": 0,
        }
        for member in guild.members:
            member: discord.Member

            # If user only has @everyone role, consider them as having no roles
            if len(member.roles) == 1:
                role_stats[no_roles] += 1
                continue

            # Iterate over all roles a member has in the guild and increment the counter
            for role in member.roles:
                # Ignore excluded roles
                if role.name not in include:
                    continue

                if role_stats.get(role.name) is None:
                    # Calculate the spacing for printing
                    if len(role.name) > role_stats['spacing']:
                        role_stats['spacing'] = len(role.name)

                    emoji_repr = "🖖"
                    for record in records:
                        if record['role_id'] == role.id:
                            emoji_repr = record['emoji_repr']

                    role_stats[role.name] = {
                        "count": 1,
                        "emoji": emoji_repr
                    }
                    role_stats['roles'].append(role.name)
                else:
                    role_stats[role.name]['count'] += 1

        # Pop Bot Maker role from list
        # if bot_maker_role in role_stats['roles']:
        #     role_stats['roles'].pop(role_stats['roles'].index(bot_maker_role))

        # Sort and prep for iteration
        role_stats['roles'].sort(key=lambda x: role_stats[x]['count'], reverse=True)
        role_stats['spacing'] += 2

        return role_stats

    def _get_roles_panel(self, role_stats: dict, with_emojis=True) -> Union[str, Embed]:
        """Create the panel that is used to display the roles stats

        Parameter
        ---------
        role_stats: dict
            Return dictionary from cls._get_role_stats

        Returns
        -------
        str
            String ready to be printed
        """
        # local constants
        bot_maker_role = "Bot Maker"
        no_roles = "No Roles"
        spacing = role_stats['spacing']

        panel = ""

        # Build the rest of the panel
        if with_emojis:
            if role_stats.get(bot_maker_role):
                panel += f"{self.gap} `{bot_maker_role + ':':<{spacing}} {role_stats.get(bot_maker_role)['count']}`\n"
            panel += f"{self.gap} `{no_roles + ':':<{spacing}} {role_stats.get(no_roles)}`\n\n"
            for role in role_stats['roles']:
                if role == "Bot Maker":
                    continue
                count = role_stats.get(role)['count']
                role_name = f"{role}:"
                emoji = role_stats.get(role)['emoji']
                panel += f"{emoji} `{role_name:<{spacing}} {count}`\n"
                panel += f"{emoji} `{role_name:<{spacing}} {count}`\n"
            return Embed(
                description=panel,
                color=0x000080
            )

        else:
            if role_stats.get(bot_maker_role):
                panel += f"{bot_maker_role + ':':<{spacing}} {role_stats.get(bot_maker_role)['count']}\n"
            panel += f"{no_roles + ':':<{spacing}} {role_stats.get(no_roles)}\n"
            panel += f"{'-' * (spacing + 4)}\n"
            spacing = role_stats['spacing']
            for role in role_stats['roles']:
                if role == "Bot Maker":
                    continue
                count = role_stats.get(role)['count']
                role_name = f"{role}:"
                panel += f"{role_name:<{spacing}} {count}\n"
            panel = f"```{panel}```"
            return panel

    async def _get_message(self, message_id: int, channel_id: int, guild_id: int) -> Optional[Message]:
        """Get a message object"""
        guild, channel, message = None, None, None
        try:
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            message: Message
            message = await channel.fetch_message(message_id)
        except Exception:
            msg = (
                f"Could not find the message object\n"
                f"Guild ID: {guild_id}\n"
                f"Guild obj: {guild}\n"
                f"Channel ID: {channel_id}\n"
                f"Channel obj: {channel}\n"
                f"Message ID: {message_id}\n"
                f"Message obj: {message}\n\n"
            )

            self.bot.logger.error(f"User input {msg} could not be casted to integer", exc_info=True)
            return None
        return message

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):

        # Ignore the bot
        if payload.member.bot:
            return

        # Ignore if the reaction has nothing to do with the static board
        if payload.message_id != self.bot.stats_board_id:
            return

        # Reset the panel reaction
        message = await self._get_message(payload.message_id, payload.channel_id, payload.guild_id)
        if message is None:
            return
        await message.remove_reaction(payload.emoji, payload.member)

        # confirm that the reaction is a registered reaction
        async with self.bot.pool.acquire() as conn:
            reaction = await conn.fetch("SELECT role_id, role_name FROM bot_language_board WHERE emoji_id = $1",
                                        payload.emoji.id)
            if len(reaction) == 1:
                reaction = reaction[0]
            else:
                self.bot.logger.error(f"Returned multiple database records with emoji id of {payload.emoji.id}")
        if not reaction:
            return

        member: Member = payload.member
        member_roles = member.roles
        remove_role = False

        # Check if this operation is a add or remove
        for role in member_roles:
            if role.id == reaction['role_id']:
                remove_role = True

        # Remove role if user already  has the role
        if remove_role:
            new_roles = []
            for role in member_roles:
                if role.id != reaction['role_id']:
                    new_roles.append(role)
            try:
                await member.edit(roles=new_roles)
            except discord.Forbidden:
                self.bot.logger.error(f"Could not add {reaction['role_name']} to {member.display_name}", exc_info=True)

        # Otherwise add the role
        else:
            role = await self._get_role_obj(payload.guild_id, reaction['role_id'])
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                self.bot.logger.error(f"Could not add {reaction['role_name']} to {member.display_name}", exc_info=True)

    @commands.command(
        name="language_board",
        description= (
                    "Create a reaction based panel that gives users roles when they click " 
                    "on the emoji. The message ID is saved in memory, so if you reboot the "
                    "bot, you will have to re-create the panels."
                    )
    )
    async def language_board(self, ctx):
        # Fetch all the emojis from the database
        async with self.bot.pool.acquire() as conn:
            emojis = await conn.fetch("SELECT emoji_repr FROM bot_language_board")

        # Save the board image to memory
        with IMAGE_PATH.open("rb") as f_handle:
            board_image = discord.File(f_handle)

        board = await ctx.send(file=board_image)

        # Add the emojis to the panel
        for emoji in emojis:
            await board.add_reaction(emoji['emoji_repr'])

        # Save panel id to memory
        self.bot.stats_board_id = board.id
        self.bot.logger.info(f"Created board with ID: {board.id}")
        await self.bot.pool.execute("UPDATE bot_smelly_mike SET board_id = $1", self.bot.stats_board_id)

    @commands.group(
        aliases=["config"],
        name="configure",
        invoke_without_command=True,
        brief="",
        description="Add or remove role that get used in the Language Board.",
        usage="",
        help=""
    )
    async def configure(self, ctx, *, arg_string=None):
        await ctx.send("Run help on me to get the configuration sub commands")

    @configure.command(
        name="add_role",
        brief="",
        help="Add a role and emoji to the LanguageBoard table",
        usage="(role_id) (emoji)"
    )
    async def config_add_role(self, ctx, *, arg_string=None):
        try:
            role_id, emoji_id = arg_string.split(' ')[:2]
        except ValueError as error:
            self.bot.logger.exception("Expected two arguments.")
            return await ctx.send(f"Expected two arguments: `role_id` and `emoji_id` got {arg_string} instead.")

        role_id = self._get_int_from_string(role_id)
        emoji_id = self._get_emoji_from_string(emoji_id)
        if role_id is None or emoji_id is None:
            return await ctx.send(f"Expected arguments should be integers only.")

        role_obj = await self._get_role_obj(ctx, role_id)
        emoji_obj = await self._get_emoji_obj(ctx, emoji_id)
        if role_obj is None or emoji_obj is None:
            return await ctx.send(f"Expected arguments could not be used to retrieve either the emoji or role object.")

        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT role_id FROM bot_language_board WHERE role_id = $1", role_obj.id)
            if row:
                return await ctx.send(f"Role is already registered. Please list roles and/or "
                                      f"remove if you want to change.")
            sql = "INSERT INTO bot_language_board (role_id, role_name, emoji_id, emoji_repr) VALUES ($1, $2, $3, $4)"
            await conn.execute(sql, role_obj.id, role_obj.name, emoji_obj.id, self._get_emoji_repr(emoji_obj))
            await ctx.send("Role added")

    @configure.command(
        name="remove_role",
        brief="",
        help=("Remove a registered role. This is the only way to \"Edit\" a registration record. User \"list_roles\" "
              "to get a listing."),
        usage="(role_name)"
    )
    async def configure_remove_role(self, ctx, *, role_name=None):
        async with self.bot.pool.acquire() as conn:
            record = await conn.fetchrow("SELECT role_id FROM bot_language_board WHERE role_name = $1", role_name)
            if record:
                await conn.execute("DELETE FROM bot_language_board WHERE role_id = $1", record['role_id'])
                return await ctx.send("Role removed")
        if not record:
            await ctx.send(f"Could not find role name {role_name}. Please use `list_roles` to get a listing.")

    @configure.command(
        name="list_roles",
        brief="",
        help="List the roles registered and the emojis that they correspond to.",
        usage=""
    )
    async def configure_list_roles(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT role_name, emoji_repr FROM bot_language_board;")
        panel = f"{'Role':<30} {'Emoji'}\n"
        for row in rows:
            panel += f"`{row['role_name']:<15}` {row['emoji_repr']}\n"
        await ctx.send(panel)

    @commands.command(
        aliases=["roles"],
        description="Show role stats",
        brief=""
    )
    async def role_stats(self, ctx):
        """Responds with a formatted code block containing the number of members with each role excluding those in
        the exclude list"""
        role_stats = await self._get_role_stats(ctx.guild)
        panel = self._get_roles_panel(role_stats, with_emojis=False)

        await ctx.send(panel)


def setup(bot):
    bot.add_cog(LanguageBoard(bot))
