import asyncio
import copy

import discord
import nextcord
import importlib
import io
import os
import re
import string
import subprocess
import sys
import textwrap
import time
import traceback

from contextlib import redirect_stdout
from nextcord.ext import commands
from random import choice, randint
from typing import Optional, Dict

from cogs.utils.formats import TabularData, plural
from cogs.utils import chat_exporter

# to expose to the eval command
import datetime
from collections import Counter

class PerformanceMocker:
    """A mock object that can also be used in await expressions."""

    def __init__(self):
        self.loop = asyncio.get_event_loop()

    def permissions_for(self, obj):
        # Lie and say we don't have permissions to embed
        # This makes it so pagination sessions just abruptly end on __init__
        # Most checks based on permission have a bypass for the owner anyway
        # So this lie will not affect the actual command invocation.
        perms = nextcord.Permissions.all()
        perms.administrator = False
        perms.embed_links = False
        perms.add_reactions = False
        return perms

    def __getattr__(self, attr):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __repr__(self):
        return "<PerformanceMocker>"

    def __await__(self):
        future = self.loop.create_future()
        future.set_result(self)
        return future.__await__()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return self

    def __len__(self):
        return 0

    def __bool__(self):
        return False


class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"Could not find a channel by ID {argument!r}.")
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(f"Could not find a channel by ID {argument!r}.")
                return channel


class Admin(commands.Cog):
    """Admin-only commands that make the bot dynamic."""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    def get_syntax_error(self, e):
        if e.text is None:
            return f"```py\n{e.__class__.__name__}: {e}\n```"
        return f"```py\n{e.text}{'^':>{e.offset}}\n{e.__class__.__name__}: {e}```"

    @commands.command(name="archive", hidden=True)
    @commands.has_role("Admin")
    async def archive_channel(self, ctx, limit: int = None):
        """Create html file with a transcript of the channel (Admin only)"""
        transcript = await chat_exporter.export(ctx.channel, limit=limit, bot=self.bot)
        if transcript is None:
            return await ctx.send("Nothing to export")
        transcript_file = nextcord.File(io.BytesIO(transcript.encode()),
                                        filename=f"transcript-{ctx.channel.name}.html"
                                        )
        await ctx.send(file=transcript_file)

    @commands.command(name="add_user", hidden=True)
    @commands.is_owner()
    async def add_user(self, ctx, usr):
        """Add user for coc discord links api (owner only)"""
        PUNCTUATION = "!@#$%^&*"
        pwd = choice(string.ascii_letters) + choice(PUNCTUATION) + choice(string.digits)
        characters = string.ascii_letters + PUNCTUATION + string.digits
        pwd += "".join(choice(characters) for x in range(randint(8, 12)))
        sql = "INSERT INTO coc_discord_users (username, passwd) VALUES ($1, $2)"
        await self.bot.pool.execute(sql, usr, pwd)
        await ctx.send(f"User: {usr} has been created with the following password:")
        await ctx.send(pwd)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, module):
        """Loads a module. (owner only)"""
        try:
            self.bot.load_extension(module)
            self.bot.logger.debug(f"{module} loaded successfully")
        except commands.ExtensionError as e:
            await ctx.send(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.send("\N{OK HAND SIGN}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, module):
        """Unloads a module. (owner only)"""
        try:
            self.bot.unload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.send("\N{OK HAND SIGN}")

    @commands.command(name="resync", hidden=True)
    @commands.is_owner()
    async def application_command_resync(self, ctx):
        """Resync all application commands (saves having to restart the bot) (owner only)"""
        cached_guild_data: Dict[Optional[int], list[ApplicationCommand]] = {}
        self.bot.add_all_cog_commands()
        for app_cmd in self.bot.get_all_application_commands():
            if not app_cmd.command_ids:
                if app_cmd.is_global:
                    if None not in cached_guild_data:
                        cached_guild_data[None] = await self.bot.http.get_global_commands(self.bot.application_id)
                elif app_cmd.is_guild:
                    for guild_id in app_cmd.guild_ids_to_rollout:
                        if guild_id not in cached_guild_data:
                            cached_guild_data[guild_id] = await self.bot.http.get_guild_commands(
                                self.bot.application_id, guild_id
                            )
        for guild_id in cached_guild_data:
            if guild_id is None:
                await self.bot.sync_application_commands(data=cached_guild_data[None])
            else:
                guild = self.bot.get_guild(guild_id)

                await self.bot.sync_application_commands(data=cached_guild_data[guild_id], guild_id=guild.id)
        await ctx.send("Application Commands resynced.")

    @commands.group(name="reload", hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def _reload(self, ctx, *, module):
        """Reloads a module. (owner only)"""
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.send("\N{OK HAND SIGN}")

    _GIT_PULL_REGEX = re.compile(r"\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+")

    def find_modules_from_git(self, output):
        files = self._GIT_PULL_REGEX.findall(output)
        ret = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != ".py":
                continue

            if root.startswith("cogs/"):
                # A submodule is a directory inside the main cog directory for
                # my purposes
                ret.append((root.count("/") - 1, root.replace("/", ".")))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    def reload_or_load_extension(self, module):
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            self.bot.load_extension(module)

    @_reload.command(name="all", hidden=True)
    @commands.is_owner()
    async def _reload_all(self, ctx):
        """Reloads all modules, while pulling from git. (owner only)"""

        async with ctx.typing():
            stdout, stderr = await self.run_process("git pull")

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "already up-to-date" are in stdout

        if stdout.startswith("Already "):
            return await ctx.send(stdout)

        modules = self.find_modules_from_git(stdout)
        mods_text = "\n".join(f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1))
        prompt_text = f"This will update the following modules, are you sure?\n{mods_text}"
        confirm = await ctx.prompt(prompt_text, reacquire=False)
        if not confirm:
            return await ctx.send("Aborting.")

        statuses = []
        for is_submodule, module in modules:
            if is_submodule:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((ctx.tick(None), module))
                else:
                    try:
                        importlib.reload(actual_module)
                    except Exception as e:
                        statuses.append((ctx.tick(False), module))
                    else:
                        statuses.append((ctx.tick(True), module))
            else:
                try:
                    self.reload_or_load_extension(module)
                except commands.ExtensionError:
                    statuses.append((ctx.tick(False), module))
                else:
                    statuses.append((ctx.tick(True), module))

        await ctx.send("\n".join(f"{status}: `{module}`" for status, module in statuses))

    @commands.command(name="pull", hidden="true")
    @commands.is_owner()
    async def git_pull(self, ctx):
        async with ctx.typing():
            stdout, stderr = await self.run_process("git pull")
        if stderr:
            return await ctx.send(stderr)
        if stdout.startswith("Already "):
            return await ctx.send(stdout)
        else:
            modules = self.find_modules_from_git(stdout)
            mods_text = '\n'.join(f'{index}. `{module}`' for index, (_, module) in enumerate(modules, start=1))
            await ctx.send(f"The following files were pulled from GitHub:\n{mods_text}")

    @commands.command(hidden=True, name="eval")
    @commands.has_role("Admin")
    async def _eval(self, ctx, *, body: str):
        """Evaluates (executes) supplied Python code (Admin only)"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f"async def func():\n{textwrap.indent(body, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sudo(self, ctx, channel: Optional[GlobalChannel], who: nextcord.User, *, command: str):
        """Run a command as another user optionally in another channel. (owner only)"""
        msg = copy.copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = channel.guild.get_member(who.id) or who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db
        await self.bot.invoke(new_ctx)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def do(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times. (owner only)"""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db

        for i in range(times):
            await new_ctx.reinvoke()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def perf(self, ctx, *, command):
        """Checks the timing of a command, attempting to suppress HTTP and DB calls. (owner only)"""

        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = PerformanceMocker()

        # Intercepts the Messageable interface a bit
        new_ctx._state = PerformanceMocker()
        new_ctx.channel = PerformanceMocker()

        if new_ctx.command is None:
            return await ctx.send("No command found")

        start = time.perf_counter()
        try:
            await new_ctx.command.invoke(new_ctx)
        except commands.CommandError:
            end = time.perf_counter()
            success = False
            try:
                await ctx.send(f"```py\n{traceback.format_exc()}\n```")
            except nextcord.HTTPException:
                pass
        else:
            end = time.perf_counter()
            success = True

        await ctx.send(f"Status: {ctx.tick(success)} Time: {(end - start) * 1000:.2f}ms")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def psql(self, ctx, *, query: str):
        """Run some PostgreSQL. (owner only)"""

        query = self.cleanup_code(query)

        is_multistatement = query.count(';') > 1
        if is_multistatement:
            # fetch does not support multiple statements
            strategy = ctx.db.execute
        else:
            strategy = ctx.db.fetch

        try:
            start = time.perf_counter()
            results = await strategy(query)
            dt = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.send(f'`{dt:.2f}ms: {results}`')

        headers = list(results[0].keys())
        table = TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f'```{query}\n\n{render}\n```\n*Returned {plural(rows):row} in {dt:.2f}ms*'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=nextcord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)


def setup(bot):
    bot.add_cog(Admin(bot))
