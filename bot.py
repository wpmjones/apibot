import asyncio
import coc
import nextcord
import io
import nest_asyncio
import sys
import traceback

from cogs.utils import context
from cogs.utils.db import Psql
from config import settings
from datetime import datetime
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

description = ("Welcome to the Clash API Developers bot. This is a custom bot created by and for the users of the "
               "Clash API Developers Discord server. If you have questions, please reach out to "
               "@Admins on this server.")

coc_client = coc.login(settings['supercell']['user'],
                       settings['supercell']['pass'],
                       client=coc.EventsClient,
                       key_names=coc_names,
                       key_count=2,
                       correct_tags=True)


class ApiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix,
                         description=description,
                         case_insensitive=True,
                         intents=intents,
                         )
        self.coc = coc_client
        self.color = nextcord.Color.greyple()
        self.logger = logger
        self.stats_board_id = None
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

    async def after_ready(self):
        await self.wait_until_ready()
        logger.add(self.send_log, level=log_level)
        await self._initialize_db()


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
