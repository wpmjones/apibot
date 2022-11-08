import asyncio
import coc
import nextcord
import io
import nest_asyncio
import random
import sys
import traceback

from cogs.utils import context
from cogs.utils.db import Psql
from config import settings
from datetime import datetime
from nextcord import ChannelType, Interaction, Thread, ui
from nextcord.ext import commands
from loguru import logger

# Shared development tips
# PEP8 whenever possible
# Use double quotes except when designating dict keys - my_dict['key_name']
# Use f strings whenever possible
# imports should be alphabetized
# from imports should be alphabetized and below the imports (see above)

# Environment - used for testing in various environments
# LIVE - required for live use on server
# test - used for testing
# feel free to add your own as needed

enviro = settings['enviro']

ADMIN_ROLE_ID = settings['roles']['admin']
DEVELOPER_ROLE_ID = settings['roles']['developer']
WELCOME_CHANNEL_ID = settings['channels']['welcome']
# WELCOME_CHANNEL_ID = 1011500429969993808

initial_extensions = [
                        "cogs.general",
                        "cogs.admin",
                      ]

intents = nextcord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
intents.messages = True
intents.message_content = True

if enviro == "LIVE":
    token = settings['discord']['token']
    prefix = "//"
    log_level = "INFO"
    coc_names = "galaxy"
    # append to initial_extensions if additional cogs are desired
    initial_extensions.append("cogs.members")
    initial_extensions.append("cogs.messages")
    initial_extensions.append("cogs.downtime")
    initial_extensions.append("cogs.response")
    initial_extensions.append("cogs.language_board")
elif enviro == "test":
    token = settings['discord']['test_token']
    prefix = ">"
    log_level = "DEBUG"
    coc_names = "dev"
else:
    token = settings['discord']['test_token']
    prefix = ">"
    log_level = "DEBUG"
    coc_names = "delete_me"

DESCRIPTION = ("Welcome to the Clash API Developers bot. This is a custom bot created by and for the users of the "
               "Clash API Developers Discord server. If you have questions, please reach out to "
               "@Admins on this server.")

# WELCOME_MESSAGE = ("**Welcome to the Clash API Developers server!**\nWe're glad to have you! "
#                    "We're here to help you do the things you want to do with the Clash API. While we can "
#                    "provide some language specific guidance, we are not a 'learn to code' server. There are "
#                    "plenty of resources out there for that.  But if you know the basics of coding and "
#                    "want to learn more about incorporating the Clash of Clans API into a project, you've "
#                    "come to the right place.\n\nPlease click the Introduce button below to tell us a little "
#                    "bit about yourself and gain access to the rest of the server.")

WELCOME_MESSAGE = ("**Welcome to the Clash API Developers server!**\nWe're glad to have you! "
                   "We're here to help you do the things you want to do with the Clash API. While we can "
                   "provide some language specific guidance, we are not a 'learn to code' server. There are "
                   "plenty of resources out there for that.  But if you know the basics of coding and "
                   "want to learn more about incorporating the Clash of Clans API into a project, you've "
                   "come to the right place.\n\nPlease tell us your preferred programming lanugage and share "
                   "a little bit about what you are doing with the API and we will give you additional roles to "
                   "gain access to the rest of the server.")

coc_client = coc.login(settings['supercell']['user'],
                       settings['supercell']['pass'],
                       client=coc.EventsClient,
                       key_names=coc_names,
                       key_count=2,
                       correct_tags=True)


async def close_welcome_thread(thread_channel: Thread):
    """Closes a welcome thread. Is called from either the close button or the close command."""
    if thread_channel.locked or thread_channel.archived:
        return
    await thread_channel.edit(locked=True, archived=True)


class Dropdown(ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Select programming languages:",
            max_values=len(options),
            options=options,
            custom_id="persistent_modal:lang_dropdown"
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message("Great! Now, please tell us a little bit about what you are doing "
                                                "(or hope to do) with the API.")
        # TODO How do we respond to this message and how does the approve button work?
        roles = self.values


class ApproveButton(ui.Button['WelcomeThread']):
    def __init__(self):
        super().__init__(
            label="Approve",
            style=nextcord.ButtonStyle.green,
            custom_id="persistent_view:approve"
        )

    async def callback(self, interaction: Interaction):
        # Add dev role and language roles
        guild = self.bot.get_guild(settings['guild']['junkies'])
        dev_role = guild.get_role(settings['roles']['developer'])
        temp_guest_role = guild.get_role(settings['roles']['temp_guest'])
        if temp_guest_role in interaction.user.roles:
            await interaction.user.remove_roles(temp_guest_role)
        # Add language roles first so that on_member_join detects roles when dev role is added
        for role_id in self.roles:
            lang_role = guild.get_role(int(role_id))
            await interaction.user.add_roles(lang_role)
            # Change nickname (Yes, I'm aware this will change it each time, but there is no good
            # way to determine their "primary" language, so I'm just taking the last one. In most cases,
            # they will only pick one language anyway.
            # await self.member.edit(nick=f"{self.member.display_name} | {lang_role.name}")
        await interaction.user.add_roles(dev_role)
        await close_welcome_thread(interaction.channel)


class IntroduceButton(ui.Button['WelcomeView']):
    def __init__(self):
        super().__init__(
            label="Introduce",
            style=nextcord.ButtonStyle.green,
            custom_id="persistent_button:intro"
        )

    async def create_intro_thread(self, interaction: Interaction):
        thread = await interaction.channel.create_thread(
            name=f"Welcome {interaction.user.display_name}",
            type=ChannelType.public_thread,
        )
        embed = nextcord.Embed(
            title=f"Welcome {interaction.user.display_name}!",
            description="Please select your preferred programming language",
            color=nextcord.Color.green()
        )
        await thread.send(embed=embed)
        return thread

    async def callback(self, interaction: Interaction):
        sql = "SELECT role_id, role_name, emoji_repr FROM bot_language_board ORDER BY role_name"
        fetch = await self.view.bot.pool.fetch(sql)
        roles = []
        for row in fetch:
            roles.append(nextcord.SelectOption(label=row[1], value=row[0], emoji=row[2]))
        created_thread = await self.create_intro_thread(interaction)
        dropdown = Dropdown(roles)
        await created_thread.send(view=dropdown)


class IntroduceView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(IntroduceButton())

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.get_role(DEVELOPER_ROLE_ID) is not None:
            await interaction.send("You already have the developer role.", ephemeral=True)
            return False
        else:
            return True


class ApiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix,
                         description=DESCRIPTION,
                         case_insensitive=True,
                         intents=intents,
                         )
        self.coc = coc_client
        self.color = nextcord.Color.greyple()
        self.logger = logger
        self.stats_board_id = None
        # self.persistent_views_added = False
        self.loop.create_task(self.after_ready())

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
                self.logger.debug(f"{extension} loaded successfully")
            except Exception as extension:
                self.logger.error(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()

    @property
    def log_channel(self):
        return self.get_channel(settings['channels']['logs'])

    async def send_message(self, message):
        if len(message) > 2000:
            fp = io.BytesIO(message.encode())
            return await self.log_channel.send(file=nextcord.File(fp, filename='log_message.txt'))
        else:
            return await self.log_channel.send(message)

    def send_log(self, message):
        asyncio.ensure_future(self.send_message(message))

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)
        if ctx.command is None:
            return
        await self.invoke(ctx)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send("This command cannot be used in private messages.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send("Oops. This command is disabled and cannot be used.")
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, nextcord.HTTPException):
                self.logger.error(f"In {ctx.command.qualified_name}:", file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                self.logger.error(f"{original.__class__.__name__}: {original}", file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(error)

    async def on_error(self, event_method, *args, **kwargs):
        e = nextcord.Embed(title="Discord Event Error", color=0xa32952)
        e.add_field(name="Event", value=event_method)
        e.description = f"```py\n{traceback.format_exc()}\n```"
        e.timestamp = datetime.utcnow()

        args_str = ["```py"]
        for index, arg in enumerate(args):
            args_str.append(f"[{index}]: {arg!r}")
        args_str.append("```")
        e.add_field(name="Args", value="\n".join(args_str), inline=False)
        try:
            await self.log_channel.send(embed=e)
        except:
            pass

    async def _initialize_db(self) -> None:
        """Could be done better. Placing this code here to not mess with the rest
        of the code base"""
        self.logger.debug("Initializing LanguageBoard table")
        language_table = """
            CREATE TABLE IF NOT EXISTS bot_language_board(
            role_id BIGINT PRIMARY KEY,
            role_name TEXT,
            emoji_id BIGINT,
            emoji_repr TEXT     -- Discord print format
        )"""

        mike_smells = """
            CREATE TABLE IF NOT EXISTS bot_smelly_mike (
            board_id BIGINT PRIMARY KEY DEFAULT 0
        )"""
        try:
            async with pool.acquire() as conn:
                await conn.execute(language_table)
                await conn.execute(mike_smells)
                self.stats_board_id = await conn.fetchval("SELECT board_id FROM bot_smelly_mike")
                if not self.stats_board_id:
                    await conn.execute("INSERT INTO bot_smelly_mike (board_id) VALUES (0)")
        except Exception:
            self.logger.exception("Could not initialize LanguageBoard")

    async def on_ready(self):
        activity = nextcord.Activity(type=nextcord.ActivityType.watching, name="you write code")
        await bot.change_presence(activity=activity)
        # if not self.persistent_views_added:
        #     self.add_view(IntroduceView(self))
        #     self.persistent_views_added = True

    async def after_ready(self):
        await self.wait_until_ready()
        logger.add(self.send_log, level=log_level)
        await self._initialize_db()
        welcome_channel = self.get_channel(WELCOME_CHANNEL_ID)
        await welcome_channel.purge()
        await welcome_channel.send(embed=nextcord.Embed(description=WELCOME_MESSAGE, color=nextcord.Color.green()))
        # await welcome_channel.send(view=IntroduceView(self))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        # Fix async to be able to add coros while it is running
        nest_asyncio.apply()
        pool = loop.run_until_complete(Psql.create_pool())
        bot = ApiBot()
        bot.loop = loop
        bot.pool = pool
        bot.run(token, reconnect=True)
    except:
        traceback.print_exc()
