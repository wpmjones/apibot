from typing import Optional

import discord
from discord import RawReactionActionEvent, Emoji, Role

from config import settings
from discord.ext import commands

LANGUAGE_TABLE = """
CREATE TABLE IF NOT EXISTS language_board_table (
    role_id BIGINT PRIMARY KEY,
    role_name TEXT,
    emoji_id BIGINT,
    emoji_repr TEXT
);
"""

class LanguageBoard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats_board_id = 0
        self.emoji_board_id = 0
        self.bot.loop.run_until_complete(self._initialize_db())
        # self._initialize_db()

    async def _initialize_db(self):
        """Could be done better. Placing this code here to not mess with the rest
        of the code base"""
        self.bot.logger.debug("Initializing LanguageBoard table")
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute(LANGUAGE_TABLE)
        except Exception:
            self.bot.logger.exception("Could not initialize LanguageBoard")

    async def _get_role_obj(self, ctx: commands.Context, role_id: int) -> Optional[Role]:
        """Get role object, otherwise log and return None"""
        try:
            return ctx.guild.get_role(role_id)
        except Exception:
            self.bot.logger.exception(f"Could not retrieve role {role_id}")
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
        emoji_id = string.split(':')[-1].rstrip('>')
        if emoji_id.isdigit():
            return int(emoji_id)
        return None

    @staticmethod
    def _get_emoji_repr(emoji: Emoji) -> str:
        return f'<:{emoji.name}:{emoji.id}>'

    async def _get_role_stats(self, ctx: commands.Context) -> dict:
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
        """
        # Local constants
        bot_maker_role = "Bot Maker"
        no_roles = "No Roles"
        async with self.bot.pool.acquire() as conn:
            records = await conn.fetch('SELECT * FROM language_board_table;')
            include = [record["role_name"] for record in records]

        # Object that is returned
        role_stats = {
            no_roles: 0,
            "roles": [],
            "records": records,
            "spacing": 0,
        }
        for member in ctx.guild.members:
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
                    if len(role.name) > role_stats["spacing"]:
                        role_stats["spacing"] = len(role.name)

                    emoji_repr = '🖖'
                    for record in records:
                        if record["role_id"] == role.id:
                            emoji_repr = record["emoji_repr"]

                    role_stats[role.name] = {
                        "count": 1,
                        "emoji": emoji_repr
                    }
                    role_stats["roles"].append(role.name)
                else:
                    role_stats[role.name]["count"] += 1

        # Pop Bot Maker role from list
        if bot_maker_role in role_stats["roles"]:
            role_stats["roles"].pop(role_stats["roles"].index(bot_maker_role))

        # Sort and prep for iteration
        role_stats["roles"].sort(key=lambda x: role_stats[x]['count'], reverse=True)
        role_stats["spacing"] += 2

        return role_stats

    @staticmethod
    def _get_roles_panel(role_stats: dict, with_emojis=True) -> str:
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
        bot_maker_role = "Bot Maker"
        no_roles = "No Roles"
        spacing = role_stats["spacing"]

        panel = ""

        # Add header to the panel "Bot Maker" and "No Roles"
        if role_stats.get(bot_maker_role):
            panel += f"{bot_maker_role + ':':<{spacing}} {role_stats.get(bot_maker_role)['count']}\n"
        panel += f"{no_roles + ':':<{spacing}} {role_stats.get(no_roles)}\n"
        # panel += f"{'-' * (spacing + 4)}\n"
        # panel = f'```{panel}```\n'

        # Build the rest of the panel
        if with_emojis:
            panel = f'```{panel}```\n'
            for role in role_stats["roles"]:
                count = role_stats.get(role)['count']
                emoji = role_stats.get(role)['emoji']
                panel += f'{emoji}⠀{count} \n'
        else:
            panel += f"{'-' * (spacing + 4)}\n"
            spacing = role_stats['spacing']
            for role in role_stats["roles"]:
                count = role_stats.get(role)['count']
                role_name = f'{role}:'
                panel += f"{role_name:<{spacing}} {count}"
            panel = f'```{panel}```'

        return panel

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        # Ignore the bot
        if payload.member.bot:
            return

    @commands.command(
        name='language_board',
        description='Create a reaction based panel that gives users roles when they click '
                    'on the emoji. The message ID is saved in memory, so if you reboot the '
                    'bot, you will have to re-create the panels.'
    )
    async def language_board(self, ctx):
        role_stats = await self._get_role_stats(ctx)
        panel = self._get_roles_panel(role_stats, with_emojis=False)


    @commands.group(
        aliases=['config'],
        name="configure",
        invoke_without_command=True,
        brief='',
        description='Add or remove role that get used in the Language Board.',
        usage='',
        help=''
    )
    async def configure(self, ctx, *, arg_string=None):
        await ctx.send("Run help on me to get the configuration sub commands")

    @configure.command(
        name='add_role',
        brief='',
        help='Add a role and emoji to the LanguageBoard table',
        usage='(role_id) (emoji)'
    )
    async def config_add_role(self, ctx, *, arg_string=None):
        try:
            role_id, emoji_id = arg_string.split(' ')[:2]
        except ValueError as error:
            self.bot.logger.exception("Expected two arguments.")
            await ctx.send(f'Expected two arguments: `role_id` and `emoji_id` got {arg_string} instead.')
            return

        role_id = self._get_int_from_string(role_id)
        emoji_id = self._get_emoji_from_string(emoji_id)
        if role_id is None or emoji_id is None:
            await ctx.send(f'Expected arguments should be integers only.')
            return

        role_obj = await self._get_role_obj(ctx, role_id)
        emoji_obj = await self._get_emoji_obj(ctx, emoji_id)
        if role_obj is None or emoji_obj is None:
            await ctx.send(f'Expected arguments could not be used to retrieve either the emoji or role object.')
            return

        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM language_board_table WHERE role_id = $1', role_obj.id)

            if row:
                await ctx.send(f'Role is already registered. Please list roles and/or remove if you want to change.')
                return
            sql = 'INSERT INTO language_board_table (role_id, role_name, emoji_id, emoji_repr) VALUES ($1, $2, $3, $4)'
            await conn.execute(sql, role_obj.id, role_obj.name, emoji_obj.id, self._get_emoji_repr(emoji_obj))
            await ctx.send('Role added')

    @configure.command(
        name='remove_role',
        brief='',
        help='Remove a registered role. This is the only way to "Edit" a registration record. User "list_roles" '
             'to get a listing.',
        usage='(role_name)'
    )
    async def configure_remove_role(self, ctx, *, role_name=None):
        async with self.bot.pool.acquire() as conn:
            record = await conn.fetchrow('SELECT * FROM language_board_table WHERE role_name = $1', role_name)

            if record:
                await conn.execute('DELETE FROM language_board_table WHERE role_id = $1', record["role_id"])
                await ctx.send("Role removed")
                return

        if not record:
            await ctx.send(f"Could not find role name {role_name}. Please use `list_roles` to get a listing.")


    @configure.command(
        name='list_roles',
        brief='',
        help='List the roles registered and the emojis that they correspond to.',
        usage=''
    )
    async def configure_list_roles(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM language_board_table;')

        panel = f"{'Role':<30} {'Emoji'}\n"
        for row in rows:
            panel += f"`{row['role_name']:<15}` {row['emoji_repr']}\n"

        await ctx.send(panel)

    @commands.command(
        aliases=["roles"],
        description='Show role stats',
        brief=''
    )
    async def role_stats(self, ctx):
        """Responds with a formatted code block containing the number of members with each role excluding those in
        the exclude list"""
        role_stats = await self._get_role_stats(ctx)
        panel = self._get_roles_panel(role_stats, with_emojis=False)

        await ctx.send(panel)


def setup(bot):
    bot.add_cog(LanguageBoard(bot))
