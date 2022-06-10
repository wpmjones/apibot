import nextcord
import re

from cogs.utils import checks
from config import settings
from datetime import datetime, timedelta
from nextcord import Interaction, ui
from nextcord.ext import commands

enviro = settings['enviro']

JUNKIES_GUILD_ID = settings['guild']['junkies']
if enviro == "LIVE":
    GUILD_IDS = [JUNKIES_GUILD_ID, settings['guild']['bot_logs']]
else:
    GUILD_IDS = [settings['guild']['bot_logs']]
BOT_DEMO_CATEGORY_ID = settings['category']['bot_demo']
RULES_CHANNEL_ID = settings['channels']['rules']
PROJECTS_CHANNEL_ID = settings['channels']['projects']
HOG_RIDER_ROLE_ID = settings['roles']['hog_rider']
BOTS_ROLE_ID = settings['roles']['bots']
DEVELOPER_ROLE_ID = settings['roles']['developer']
ADMIN_ROLE_ID = settings['roles']['admin']
GUEST_ROLE_ID = settings['roles']['vip_guest']

SECTION_MATCH = re.compile(r'(?P<title>.+?)<a name="(?P<number>\d+|\d+.\d+)"></a>(?P<body>(.|\n)+?(?=(#{2,3}|\Z)))')
UNDERLINE_MATCH = re.compile(r"<ins>|</ins>")
URL_EXTRACTOR = re.compile(r"\[(?P<title>.*?)\]\((?P<url>[^)]+)\)")


class Dropdown(ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Select programming languages:",
            min_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        # Add language roles
        for value in self.values:
            await interaction.send(f"I will add {value} role to user")


class Introduce(ui.Modal):
    def __init__(self, roles):
        super().__init__(
            "Getting to know you",
            timeout=5*60  # 5 minutes
        )

        self.add_item(Dropdown(roles))
        self.information = ui.TextInput(
            label="Tell us a little about your project and what you are doing (or would like to do) with the API.",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="Information that can help us get to know you",
            required=True,
            max_length=1800
        )
        self.add_item(self.information)

    async def callback(self, interaction: Interaction):
        # Add dev roles
        await interaction.send("I will add the developer role.")
        welcome_msg = ("Welcome to the Clash API Developers server.  We hope you find this to be a great place to "
                       "share and learn more about the Clash of Clans API.  You can check out <#641454924172886027> "
                       "if you need some basic help.  There are some tutorials there as well as some of the more "
                       "common libraries that are used with various programming languages. If you use more than one "
                       "programming language, be sure to check out <#885216742903803925> to assign yourself the role "
                       "for each language.\nLastly, say hello in <#566451504903618561> and make some new friends!!")
        await interaction.user.send(welcome_msg)
        await interaction.send(f"This is what I would send to #general.\n{self.information.value}")


class IntroduceButton(ui.Button["WelcomeView"]):
    def __init__(self):
        super().__init__(
            label="Introduce",
            style=nextcord.ButtonStyle.green,
            custom_id="IntroduceButton"
        )

    async def callback(self, interaction: Interaction):
        self.view.bot.logger.info("Button callback")
        sql = "SELECT role_id, role_name, emoji_repr FROM bot_language_board ORDER BY role_name"
        fetch = await self.view.bot.pool.fetch(sql)
        self.view.bot.logger.info(len(fetch))
        roles = []
        for row in fetch:
            roles.append(nextcord.SelectOption(label=row[1], value=row[0], emoji=row[2]))
        modal = Introduce(roles)
        await interaction.response.send_modal(modal)


class WelcomeView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(IntroduceButton())

    # async def interaction_check(self, interaction: Interaction):
    #     if interaction.user.get_role(DEVELOPER_ROLE_ID) is not None:
    #         await interaction.send("You already have the developer role.", ephemeral=True)
    #         return False
    #     else:
    #         return True


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="invite")
    async def invite(self, ctx):
        """Responds with the invite link to this server"""
        await ctx.send("https://discord.gg/clashapi")

    @nextcord.slash_command(name="regex", guild_ids=GUILD_IDS)
    async def regex(self, interaction: nextcord.Interaction):
        """Responds with the RegEx for player/clan tags"""
        await interaction.response.send_message("^#[PYLQGRJCUV0289]+$")

    @nextcord.slash_command(name="rate_limit", guild_ids=GUILD_IDS)
    async def rate_limit(self, interaction: nextcord.Interaction):
        """Responds with the rate limit information for the Clash API"""
        await interaction.response.send_message("We have found that the approximate rate limit is 30-40 requests per second. Staying "
                       "below this should be safe.")

    @nextcord.slash_command(name="vps", guild_ids=GUILD_IDS)
    async def vps(self, interaction: nextcord.Interaction):
        """Responds with a link to a GitHub MD on VPS options"""
        await interaction.response.send_message("<https://github.com/wpmjones/apibot/blob/master/Rules/vps_services.md>")

    @nextcord.slash_command(name="rules", guild_ids=GUILD_IDS)
    async def rules(self, interaction: nextcord.Interaction):
        """Respond with a link to the rules markdown file."""
        await interaction.response.send_message("<https://github.com/wpmjones/apibot/blob/master/"
                                                "Rules/code_of_conduct.md>")

    @nextcord.slash_command(name="links", guild_ids=GUILD_IDS)
    async def link_api(self, interaction: nextcord.Interaction):
        """Responds with a link to a Discord message on the Discord Link API (by TubaKid)"""
        await interaction.response.send_message("https://discord.com/channels/566451504332931073/681617252814159904/936126372873650237")

    @nextcord.slash_command(name="coc_wrappers", guild_ids=GUILD_IDS)
    async def link_coc_wrappers(self, interaction: nextcord.Interaction):
        """Respond with a link to the page created by @Doluk"""
        await interaction.response.send_message("<https://coc-libs.vercel.app/>")

    @nextcord.slash_command(name="discord_wrappers", guild_ids=GUILD_IDS)
    async def link_discord_wrappers(self, interaction: nextcord.Interaction):
        """Respond with a link to a list of known discord wrappers"""
        await interaction.response.send_message("<https://libs.advaith.io/>")

    @commands.command(name="setup", aliases=["set_up", ], hidden=True)
    @commands.has_role("Admin")
    async def setup_bot(self, ctx, bot: nextcord.Member = None, owner: nextcord.Member = None):
        """Admin use only: For adding bot demo channels
        Creates channel (based on bot name)
        Alphabetizes channel within the Bot-Demos category
        Sets proper permissions
        Sets the channel topic to 'Maintained by [owner]'
        Pings owner so they see the channel and can demonstrate features
        Adds the "Bots" role to the bot.

        **Example:**
        /setup @bot @owner

        **Permissions:**
        Admin role required
        """
        if not bot or not owner:
            return await ctx.send("Please be sure to provide a Discord ID or mention both the bot and the owner. "
                                  "`/setup @bot @owner`")
        if not bot.bot:
            return await ctx.send(f"{bot.mention} does not appear to be a bot. Please try again with "
                                  f"`/setup @bot @owner`.")
        if owner.bot:
            return await ctx.send(f"{owner.mention} appears to be a bot, but should be the bot owner. Please try "
                                  f"again with `/setup @bot @owner`.")

        category = self.bot.get_channel(BOT_DEMO_CATEGORY_ID)
        guild = self.bot.get_guild(JUNKIES_GUILD_ID)
        guest_role = guild.get_role(GUEST_ROLE_ID)
        developer_role = guild.get_role(DEVELOPER_ROLE_ID)
        hog_rider_role = guild.get_role(HOG_RIDER_ROLE_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        channel_name = f"{bot.name}-demo"
        topic = f"Maintained by {owner.display_name}"

        # check for existing bot demo channel before proceeding
        for channel in category.channels:
            if channel_name == channel.name:
                return await ctx.send("It appears that there is already a demo channel for this bot.")

        # No match found, just keep swimming
        overwrites = {
            bot: nextcord.PermissionOverwrite(read_messages=True,
                                              send_messages=True,
                                              read_message_history=True,
                                              manage_messages=True,
                                              embed_links=True,
                                              attach_files=True,
                                              external_emojis=True,
                                              add_reactions=True),
            admin_role: nextcord.PermissionOverwrite(read_messages=True,
                                                     send_messages=True,
                                                     read_message_history=True,
                                                     manage_messages=True,
                                                     embed_links=True,
                                                     attach_files=True,
                                                     external_emojis=True,
                                                     add_reactions=True,
                                                     manage_channels=True,
                                                     manage_permissions=True,
                                                     manage_webhooks=True),
            hog_rider_role: nextcord.PermissionOverwrite(read_messages=True,
                                                         send_messages=True,
                                                         read_message_history=True,
                                                         manage_messages=True,
                                                         embed_links=True,
                                                         attach_files=True,
                                                         external_emojis=True,
                                                         add_reactions=True),
            developer_role: nextcord.PermissionOverwrite(read_messages=True,
                                                         send_messages=True,
                                                         read_message_history=True,
                                                         manage_messages=False,
                                                         embed_links=True,
                                                         attach_files=True,
                                                         external_emojis=True,
                                                         add_reactions=True),
            guest_role: nextcord.PermissionOverwrite(read_messages=True,
                                                     send_messages=True,
                                                     read_message_history=True,
                                                     manage_messages=False,
                                                     embed_links=True,
                                                     attach_files=True,
                                                     external_emojis=False,
                                                     add_reactions=True),
            guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
        }
        try:
            position = category.channels[0].position + sorted(
                category.channels + [channel_name], key=lambda c: str(c)
            ).index(channel_name)

            channel = await ctx.guild.create_text_channel(channel_name,
                                                          overwrites=overwrites,
                                                          category=category,
                                                          position=position,
                                                          topic=topic,
                                                          reason=f"Created by the setup command of Hog Rider ({ctx.author})",
                                                          )
        except:
            self.bot.logger.exception("Failed creating channel")

        # ping owner
        await channel.send(f"{owner.mention} This channel has been set up for your use in demonstrating the features "
                           f"of **{bot.name}**. Limited troubleshooting with others is acceptable, but please do not "
                           f"allow this channel to become a testing platform.  Thanks!")

        # add the "Bots" role
        await bot.add_roles(ctx.guild.get_role(BOTS_ROLE_ID),
                            reason=f"Added by setup command of Hog Rider ({ctx.author})",
                            )

        # sort the Bot-Demo channels alphabetically
        for index, channel in enumerate(sorted(category.channels,
                                               key=lambda c: str(c)),
                                        start=category.channels[0].position):
            if channel.position != index:
                await channel.edit(position=index)

        # Provide user feedback on success
        await ctx.message.add_reaction("\u2705")
        await ctx.send(f"If {owner.display_name} would like bot monitoring, here's your command:\n"
                       f"`//bot add {bot.id}`")

    @commands.command(name="developer", aiases=["dev", "devrole", "dev_role"], hidden=True)
    @commands.has_role("Admin")
    async def dev_role(self, ctx, member: nextcord.Member = None):
        """Add appropriate role to new users.  It will:

        Prompt you to add primary language role (optional)
        Add the Developer role
        Announce the new member in #general
        Send a welcome message to new member (via DM)
        Offer to allow you to copy a message from #welcome to #general to help introduce the new member (it will
        ask you to provide the Discord message ID of the message to copy)

        **Permissions:**
        Admin role required
        """
        if not member:
            return await ctx.send("Please provide a valid member of this server.")
        if member.guild.id != settings['guild']['junkies']:
            return await ctx.send("This command can only be performed on the Clash API Developers server.")
        dev_role = member.guild.get_role(settings['roles']['developer'])
        if dev_role in member.roles:
            return await ctx.send(f"{member.display_name} already has the Developer role. This command can only "
                                  f"be used for members without the Developer role.")
        guest_role = member.guild.get_role(settings['roles']['vip_guest'])
        if guest_role in member.roles:
            remove = await ctx.prompt(f"{member.display_name} currently has the Guest role. Would you like to remove "
                                      f"the Guest role and add the Developer role?")
            if remove:
                await member.remove_roles(guest_role, reason="Changing to Developer role")
            else:
                return await ctx.send("Action cancelled.")
        if ctx.channel.id != settings['channels']['welcome']:
            return await ctx.send(f"I'd feel a whole lot better if you ran this command in "
                                  f"<#{settings['channels']['welcome']}>.")
        self.bot.logger.info("Pre-checks complete. Starting dev add process.")
        # At this point, we should have a valid member without the dev role
        # Let's see if we want to add any language roles first
        self.bot.logger.info(f"Starting Dev Role add process for {member.display_name} (Initiated by "
                             f"{ctx.author.display_name})")
        prompt = await ctx.prompt("Would you like to add a language role first?")
        if prompt:
            sql = "SELECT role_id, role_name FROM bot_language_board ORDER BY role_name"
            fetch = await self.bot.pool.fetch(sql)
            role_names = [x['role_name'] for x in fetch]
            role_ids = [x['role_id'] for x in fetch]
            content = "Please select the member's primary language role:\n"
            for i in range(len(fetch)):
                content += f"{i+1} - {role_names[i]}\n"
            lang_int = await ctx.prompt(content, additional_options=len(fetch))
            lang_int -= 1  # decrement by one for list index
            role = member.guild.get_role(role_ids[lang_int])
            await member.add_roles(role, reason=f"Role added by {ctx.author.display_name}")
            # change nickname (32 character limit)
            await member.edit(nick=f"{member.display_name} | {role_names[lang_int]}")
            self.bot.logger.info(f"{role_names[lang_int]} added to {member.display_name}")
        else:
            self.bot.logger.info(f"No language roles added for {member.display_name}")
        # Add developer role
        await member.add_roles(dev_role, reason=f"Role added by {ctx.author.display_name}")
        # Send DM to new member
        welcome_msg = ("Welcome to the Clash API Developers server.  We hope you find this to be a great place to "
                       "share and learn more about the Clash of Clans API.  You can check out <#641454924172886027> "
                       "if you need some basic help.  There are some tutorials there as well as some of the more "
                       "common libraries that are used with various programming languages. If you use more than one "
                       "programming language, be sure to check out <#885216742903803925> to assign yourself the role "
                       "for each language.\nLastly, say hello in <#566451504903618561> and make some new friends!!")
        await member.send(welcome_msg)
        # Copy a message to General??
        await ctx.invoke(self.bot.get_command("to_gen"))

    @commands.command(name="to_gen", hidden=True)
    @checks.manage_messages()
    async def send_to_general(self, ctx):
        """Copy message from #Welcome to #General

        After entering the command, it will prompt you to provide the Discord message ID of the message in question.
        It will repost the specified message in #general.

        **Permissions:**
        Manage Messages
        """

        def check_author(m):
            return m.author == ctx.author

        prompt = await ctx.prompt("Would you like to copy a message to #general?")
        if prompt:
            await ctx.send("Please enter the Message ID of the message to copy.")
            response = await ctx.bot.wait_for("message", check=check_author, timeout=45)
            message_id = response.content
            try:
                msg = await ctx.channel.fetch_message(message_id)
                content = f"{msg.author.display_name} says:\n>>> {msg.content}"
                channel = self.bot.get_channel(settings['channels']['general'])
                await channel.send(content)
            except (nextcord.NotFound, nextcord.HTTPException) as e:
                self.bot.logger.exception(f"Failure trying to send message to #General\n{e}")
                return await ctx.send(f"Copying of the message failed.  Please confirm you copied the correct "
                                      f"message ID and try `//to_gen`.\n"
                                      f"Status: {e.status}\n"
                                      f"Error: {e.text}\n\n"
                                      f"This message will self-destruct in 120 seconds.",
                                      delete_after=120.0)

    @commands.command(name="clear", hidden=True)
    @checks.manage_messages()
    async def clear(self, ctx, msg_count: int = None):
        """Clears the specified number of messages in the current channel (defaults to all messages).

        **Examples:**
        //clear (will ask for confirmation first)
        //clear 7 (no confirmation, will delete the clear command and the 7 previous messages)

        **Permissions:**
        Manage Messages
        """
        if msg_count:
            await ctx.channel.purge(limit=msg_count + 1)
        else:
            prompt = await ctx.prompt(f"Are you sure you want to remove ALL messages from the "
                                      f"{ctx.channel.name} channel?")
            if prompt:
                await ctx.channel.purge()
            else:
                await ctx.message.delete()

    @commands.command(name="clear_old", hidden=True)
    @checks.manage_messages()
    async def clear_old(self, ctx):
        """Clears all messages older than the last 24 hours."""
        before = datetime.now() - timedelta(hours=24)
        await ctx.channel.purge(before=before)
        await ctx.message.delete()

    @commands.command(hidden=True)
    @commands.has_role("Admin")
    async def recreate_rules(self, ctx):
        """Recreate the #rules channel.

        This parses the Rules/code_of_conduct.md markdown file, and sends it as a series of embeds.
        Assumptions are made that each section is separated by <a name="x.x"></a>.

        Finally, buttons are sent with links which correspond to the various messages.
        """
        channel = self.bot.get_channel(RULES_CHANNEL_ID)
        await channel.purge()

        with open("Rules/code_of_conduct.md", encoding="utf-8") as fp:
            text = fp.read()

        sections = SECTION_MATCH.finditer(text)

        embeds = []
        titles = []
        for match in sections:
            description = match.group("body")
            # underlines, dividers, bullet points
            description = UNDERLINE_MATCH.sub("__", description).replace("---", "").replace("-", "\u2022")
            title = match.group("title").replace("#", "").strip()

            if "." in match.group("number"):
                colour = 0xBDDDF4  # lighter blue for sub-headings/groups
            else:
                colour = nextcord.Colour.blue()

            embeds.append(nextcord.Embed(title=title, description=description.strip(), colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        # create buttons
        view = ui.View()
        for i, (message, title) in enumerate(zip(messages, titles)):
            view.add_item(ui.Button(label=title.replace("#", "").strip(), url=message.jump_url))
        await channel.send(view=view)
        await ctx.send(f"Rules have been recreated. View here <#{RULES_CHANNEL_ID}>")

    @commands.command(hidden=True)
    @commands.has_role("Admin")
    async def recreate_projects(self, ctx):
        """Recreate the #community-projects channel.

        This parses the Rules/community_projects.md markdown file, and sends it as a series of embeds.
        Assumptions are made that each section is separated by <a name="x.x"></a>.

        Finally, buttons are sent with links which correspond to the various messages.
        """
        channel = self.bot.get_channel(PROJECTS_CHANNEL_ID)
        await channel.purge()

        with open("Rules/community_projects.md", encoding="utf-8") as fp:
            text = fp.read()

        sections = SECTION_MATCH.finditer(text)

        embeds = []
        titles = []
        for match in sections:
            description = match.group("body")
            # underlines, dividers
            description = UNDERLINE_MATCH.sub("__", description).replace("---", "")
            raw_title = match.group("title")
            if re.search(URL_EXTRACTOR, raw_title):
                match = re.search(URL_EXTRACTOR, raw_title)
                title = match.group("title")
                url = match.group("url")
            else:
                title = raw_title.replace("#", "").strip()
                url = ""

            colour = nextcord.Colour.blue()

            embeds.append(nextcord.Embed(title=title, url=url, description=description.strip(), colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        # create buttons
        view = ui.View()
        for i, (message, title) in enumerate(zip(messages, titles)):
            view.add_item(ui.Button(label=title.replace("#", "").strip(), url=message.jump_url))
        await channel.send(view=view)
        await ctx.send(f"Project list has been recreated. View here <#{PROJECTS_CHANNEL_ID}>")

    @commands.command(hidden=True)
    @commands.has_role("Admin")
    async def recreate_welcome(self, ctx):
        """Recreate the welcome message for new members"""
        welcome_msg = ("Welcome to the Clash API Developers server! We're glad to have you! "
                       "We're here to help you do the things you want to do with the Clash API. While we can "
                       "provide some language specific guidance, we are not a 'learn to code' server. There are "
                       "plenty of resources out there for that.  But if you know the basics of coding and "
                       "want to learn more about incorporating the Clash of Clans API into a project, you've "
                       "come to the right place.\n\nPlease click the Introduce button below to tell us a little "
                       "bit about yourself and gain access to the rest of the server.")
        await ctx.send(embed=nextcord.Embed(description=welcome_msg, color=nextcord.Color.green()))
        await ctx.send(view=WelcomeView(self.bot))


def setup(bot):
    bot.add_cog(General(bot))
