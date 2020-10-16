import asyncio
import coc
import discord
import io
import sys
import traceback

from cogs.utils import context
from cogs.utils.db import Psql
from config import settings
from datetime import datetime
from discord.ext import commands
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

enviro = "LIVE"

initial_extensions = ["cogs.general",
                      "cogs.admin",
                      ]

if enviro == "LIVE":
    token = settings['discord']['token']
    prefix = "/"
    log_level = "INFO"
    coc_names = "galaxy"
    # append to initial_extensions if additional cogs are desired
    initial_extensions.append("cogs.members")
    initial_extensions.append("cogs.downtime")
    initial_extensions.append("cogs.forum-poster")
elif enviro == "test":
    token = settings['discord']['test_token']
    prefix = ">"
    log_level = "DEBUG"
    coc_names = "dev"
else:
    token = settings['discord']['test_token']
    prefix = ">"
    log_level = "DEBUG"
    coc_names = "dev"

description = ("Welcome to the COC API Junkies bot. This is a custom bot created by and for the users of the "
               "COC API Junkies Discord server. If you have questions, please reach out to @Admins on this server.")

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
                         case_insensitive=True)
        self.coc = coc_client
        self.color = discord.Color.greyple()
        self.logger = logger
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
            return await self.log_channel.send(file=discord.File(fp, filename='log_message.txt'))
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
            if not isinstance(original, discord.HTTPException):
                self.logger.error(f"In {ctx.command.qualified_name}:", file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                self.logger.error(f"{original.__class__.__name__}: {original}", file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(error)

    async def on_error(self, event_method, *args, **kwargs):
        e = discord.Embed(title="Discord Event Error", color=0xa32952)
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

    async def on_ready(self):
        activity = discord.Activity(type=discord.ActivityType.watching, name="you write code")
        await bot.change_presence(activity=activity)

    async def after_ready(self):
        await self.wait_until_ready()
        logger.add(self.send_log, level=log_level)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        pool = loop.run_until_complete(Psql.create_pool())
        bot = ApiBot()
        bot.loop = loop
        bot.pool = pool
        bot.run(token, reconnect=True)
    except:
        traceback.print_exc()
