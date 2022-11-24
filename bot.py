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
from nextcord import ChannelType, Interaction, Thread, ui
from nextcord.ext import commands
from loguru import logger
from typing import List

from fancy_logging import setup_logging

# setup_logging("nextcord.state")
# setup_logging("nextcord.gateway")
# setup_logging("nextcord.http")
setup_logging("nextcord.application_command")

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
    WELCOME_CHANNEL_ID = settings['channels']['welcome']
    GENERAL_CHANNEL_ID = settings['channels']['general']
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
    WELCOME_CHANNEL_ID = 1011500429969993808
    GENERAL_CHANNEL_ID = settings['channels']['testing']
else:
    token = settings['discord']['test_token']
    prefix = ">"
    log_level = "DEBUG"
    coc_names = "delete_me"
    WELCOME_CHANNEL_ID = 1011500429969993808
    GENERAL_CHANNEL_ID = settings['channels']['testing']

DESCRIPTION = ("Welcome to the Clash API Developers bot. This is a custom bot created by and for the users of the "
               "Clash API Developers Discord server. If you have questions, please reach out to "
               "@Admins on this server.")

WELCOME_MESSAGE = ("**Welcome to the Clash API Developers server!**\nWe're glad to have you! "
                   "We're here to help you do the things you want to do with the Clash API. While we can "
                   "provide some language specific guidance, we are not a 'learn to code' server. There are "
                   "plenty of resources out there for that.  But if you know the basics of coding and "
                   "want to learn more about incorporating the Clash of Clans API into a project, you've "
                   "come to the right place.\n\nPlease click the Introduce button below to tell us a little "
                   "bit about yourself and gain access to the rest of the server.")

# WELCOME_MESSAGE = ("**Welcome to the Clash API Developers server!**\nWe're glad to have you! "
#                    "We're here to help you do the things you want to do with the Clash API. While we can "
#                    "provide some language specific guidance, we are not a 'learn to code' server. There are "
#                    "plenty of resources out there for that.  But if you know the basics of coding and "
#                    "want to learn more about incorporating the Clash of Clans API into a project, you've "
#                    "come to the right place.\n\n**Please tell us your preferred programming language and share "
#                    "a little bit about what you are doing with the API and we will give you additional roles to "
#                    "gain access to the rest of the server.**")

coc_client = coc.login(settings['supercell']['user'],
                       settings['supercell']['pass'],
                       client=coc.EventsClient,
                       key_names=coc_names,
                       key_count=2,
                       correct_tags=True)


class RoleButton(nextcord.ui.Button):
    def __init__(self, role: nextcord.Role, member: nextcord.Member):
        super().__init__(
            label=role.name,
            style=nextcord.ButtonStyle.blurple,
            custom_id=f"RoleView:{role.id}",
        )
        self.role = role
        self.member = member

    async def callback(self, interaction: nextcord.Interaction):
        await self.member.add_roles(self.role, reason=f"{interaction.user.display_name} using a button.")
        if "|" not in self.member.display_name:
            await self.member.edit(nick=f"{self.member.display_name} | {self.role.name}")


class RoleDropdown(nextcord.ui.Select):
    def __init__(self, member: nextcord.Member, options):
        super().__init__(
            placeholder="Select roles for this user...",
            min_values=1,
            max_values=6,
            options=options
        )
        self.member = member

    async def callback(self, interaction: Interaction):
        for value in self.values:
            role = interaction.guild.get_role(int(value))
            await self.member.add_roles(role)
            try:
                await self.member.edit(nick=f"{self.member.display_name} | {role.name}")
            except nextcord.HTTPException:
                # this might happen if the nickname gets too long
                pass


class RoleView(nextcord.ui.View):
    def __init__(self, member: nextcord.Member, roles):
        super().__init__(timeout=20.0)
        options = []
        for role in roles:
            options.append(nextcord.SelectOption(label=role[0], value=role[1]))
        self.add_item(RoleDropdown(member, options))


class ConfirmButton(ui.Button["ConfirmView"]):
    def __init__(self, label: str, style: nextcord.ButtonStyle, *, custom_id: str):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: Interaction):
        self.view.value = True if self.custom_id == f"confirm_button" else False
        self.view.stop()


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=20.0)
        self.value = None
        self.add_item(ConfirmButton("Yes", nextcord.ButtonStyle.green, custom_id="confirm_button"))
        self.add_item(ConfirmButton("No", nextcord.ButtonStyle.red, custom_id="decline_button"))


class IntroduceModal(ui.Modal):
    def __init__(self, pass_bot):
        super().__init__(title="Getting to know you",
                         timeout=None)
        self.bot = pass_bot
        self.value = None
        self.language = ui.TextInput(label="Enter your preferred programming language.",
                                     required=True,
                                     placeholder="Programming language")
        self.information = ui.TextInput(
            label="Tell us a little about your project.",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            placeholder="What are you doing or what would you like to be doing with the API?",
            max_length=544)
        self.add_item(self.language)
        self.add_item(self.information)

    async def create_welcome_thread(self, interaction: Interaction, lang, info) -> Thread:
        thread = await interaction.channel.create_thread(name=f"Welcome {interaction.user.display_name}",
                                                         type=ChannelType.public_thread)
        embed = nextcord.Embed(title=f"Introducing {interaction.user.display_name}",
                               description=f"Created by: {interaction.user} ({interaction.user.id})",
                               color=nextcord.Color.green())
        embed.add_field(name="Language(s):", value=lang, inline=False)
        embed.add_field(name="Message:", value=info, inline=False)
        embed.set_footer(text="Admins can approve or invite the member to request more information.")

        welcome_button_view = WelcomeButtonView(self.bot, interaction.user, lang, info)

        await thread.send(embed=embed, view=welcome_button_view)
        return thread

    async def callback(self, interaction: Interaction):
        lang = self.language.value
        info = self.information.value
        created_thread = await self.create_welcome_thread(interaction, lang, info)
        await created_thread.send(f"<@&{ADMIN_ROLE_ID}>", delete_after=5)
        # Add temp_guest role so they can "look around"
        # Send DM so user knows we're working on it
        guild = self.bot.get_guild(settings['guild']['junkies'])
        temp_guest_role = guild.get_role(settings['roles']['temp_guest'])
        await interaction.user.add_roles(temp_guest_role)
        welcome_msg = ("Thank you for introducing yourself. One of our admins will review your information "
                       "shortly and get things moving. If they have any other questions, they will let you know! "
                       "In the meantime, we've given you access to a few channels.")
        await interaction.user.send(welcome_msg)


class SendButton(nextcord.ui.Button):
    def __init__(self, count, content, author):
        super().__init__(label=count,
                         style=nextcord.ButtonStyle.primary)
        self.content = content
        self.author = author

    async def callback(self, interaction: Interaction):
        channel = interaction.guild.get_channel(GENERAL_CHANNEL_ID)
        await channel.send(f"{self.author} says:\n>>> {self.content}")


class SendMessage(ui.View):
    def __init__(self, messages: List[nextcord.Message]):
        super().__init__(timeout=20.0)
        for count, message in enumerate(messages):
            self.add_item(SendButton(count, message.content, message.author.display_name))


class WelcomeButtonView(ui.View):
    def __init__(self, pass_bot, member, lang, info):
        super().__init__(timeout=None)
        self.bot = pass_bot
        self.member = member
        self.lang = lang
        self.info = info
        self.more = False

    @ui.button(label="Approve",
               style=nextcord.ButtonStyle.green)
    async def thread_approve_button(self, button: nextcord.ui.Button, interaction: Interaction):
        dev_role = interaction.guild.get_role(settings['roles']['developer'])
        # remove temp guest role
        temp_guest_role = interaction.guild.get_role(settings['roles']['temp_guest'])
        if temp_guest_role in self.member.roles:
            await self.member.remove_roles(temp_guest_role)
        # remove perms for welcome - this covers a case where they were individually
        # added with the More Info button
        await interaction.channel.parent.set_permissions(
            self.member,
            overwrite=None
        )
        await interaction.send(f"{interaction.user.display_name} has started the approval process.")
        sql = "SELECT role_id, role_name FROM bot_language_board ORDER BY role_name"
        fetch = await self.bot.pool.fetch(sql)
        roles = [(x['role_name'], x['role_id']) for x in fetch]
        if not self.more:  # We're approving straight away. Try and decipher language from input
            role_found = False
            for role in roles:
                if self.lang.lower() == role[0].lower():
                    lang_role = interaction.guild.get_role(role[1])
                    await self.member.add_roles(lang_role)
                    role_found = True
            if not role_found:  # Couldn't figure out role, let's prompt for it
                role_view = RoleView(self.member, roles)
                content = "Please select the member's primary language role:"
                await interaction.send(content, delete_after=21.0, view=role_view, ephemeral=False)
                await role_view.wait()
            channel = interaction.guild.get_channel(GENERAL_CHANNEL_ID)
            await channel.send(f"{self.member.display_name} says:\n>>> {self.info}")
        else:
            # prompt for language role
            role_view = RoleView(self.member, roles)
            content = "Please select the member's primary language role:"
            await interaction.send(content, delete_after=21.0, view=role_view, ephemeral=False)
            await role_view.wait()
            confirm_view = ConfirmView()

            def disable_all_buttons():
                for _item in confirm_view.children:
                    _item.disabled = True

            confirm_content = "Would you like to copy a message to #general?"
            await interaction.send(content=confirm_content, ephemeral=False, view=confirm_view)
            await confirm_view.wait()
            if confirm_view.value is False or confirm_view.value is None:
                disable_all_buttons()
                content = "OK, then I won't do it." if confirm_view.value is False else "You're too slow! Cancelled."
                await interaction.send(content)
            else:
                disable_all_buttons()
                messages = []
                embed = nextcord.Embed(title="Please select the message to copy to #general.")
                description = ""
                async for message in interaction.channel.history():
                    counter = 0
                    if message.author == self.member and len(message.content) > 8:
                        description += f"\n**{counter}** - {message.content}"
                        counter += 1
                        messages.append(message)
                embed.description = description
                role_view = SendMessage(messages)
                await interaction.send(embed=embed, view=role_view, ephemeral=False)
                await role_view.wait()
        await self.member.add_roles(dev_role)
        await interaction.send("This channel will self-destruct in 1-20 seconds.")
        await interaction.channel.delete()

    @ui.button(label="More Info",
               style=nextcord.ButtonStyle.blurple)
    async def thread_info_button(self, button: nextcord.ui.Button, interaction: Interaction):
        self.more = True
        # disable button in view since we don't want to use them anymore
        button.disabled = True
        await interaction.edit(view=self)
        # Add user to thread
        await interaction.channel.add_user(self.member)
        await interaction.channel.parent.set_permissions(
            self.member,
            read_messages=True,
            send_messages_in_threads=True,
            add_reactions=True
        )
        await interaction.send(f"{self.member.mention}, can you please give us a little more information?")

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not isinstance(interaction.channel, Thread) or interaction.channel.parent_id != WELCOME_CHANNEL_ID:
            self.bot.logger.info("Button failed on thread check")
            return False
        if interaction.channel.archived or interaction.channel.locked:
            self.bot.logger.info("Button failed on archive/locked")
            return False
        if interaction.user.get_role(ADMIN_ROLE_ID):
            return True
        else:
            await interaction.send("Only admins may use these buttons.", ephemeral=True)
            return False


class IntroduceButton(ui.Button['WelcomeView']):
    def __init__(self, pass_bot):
        super().__init__(
            label="Introduce",
            style=nextcord.ButtonStyle.green
        )
        self.bot = pass_bot

    async def callback(self, interaction: Interaction):
        # sql = "SELECT role_id, role_name, emoji_repr FROM bot_language_board ORDER BY role_name"
        # fetch = await self.view.bot.pool.fetch(sql)
        # roles = []
        # for row in fetch:
        #     roles.append(nextcord.SelectOption(label=row[1], value=row[0], emoji=row[2]))
        # created_thread = await self.create_intro_thread(interaction)
        # dropdown = Dropdown(roles)
        # await created_thread.send(view=dropdown)
        intro_modal = IntroduceModal(self.view.bot)
        await interaction.response.send_modal(intro_modal)


class IntroduceView(ui.View):
    def __init__(self, pass_bot):
        super().__init__(timeout=None)
        self.bot = pass_bot
        self.add_item(IntroduceButton(self.bot))

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

    async def after_ready(self):
        await self.wait_until_ready()
        logger.add(self.send_log, level=log_level)
        # if enviro == "LIVE":
        #     await self._initialize_db()
        welcome_channel = self.get_channel(WELCOME_CHANNEL_ID)
        await welcome_channel.purge()
        await welcome_channel.send(embed=nextcord.Embed(description=WELCOME_MESSAGE, color=nextcord.Color.green()))
        await welcome_channel.send(view=IntroduceView(self))


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
