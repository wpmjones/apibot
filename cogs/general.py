import os
import traceback

import coc.utils
import nextcord
import re
import youtube_dl

from cogs.utils import checks
from config import settings
from nextcord import Interaction, ui
from nextcord.ext import commands, application_checks

enviro = settings['enviro']

JUNKIES_GUILD_ID = settings['guild']['junkies']
if enviro == "LIVE":
    GUILD_IDS = [JUNKIES_GUILD_ID, settings['guild']['bot_logs']]
    WELCOME_CHANNEL_ID = settings['channels']['welcome']
else:
    GUILD_IDS = [settings['guild']['bot_logs']]
    WELCOME_CHANNEL_ID = 1011500429969993808
BOT_DEMO_CATEGORY_ID = settings['category']['bot_demo']
RULES_CHANNEL_ID = settings['channels']['rules']
PROJECTS_CHANNEL_ID = settings['channels']['projects']
FAQS_CHANNEL_ID = 1036742156230070282
RESOURCES_CATEGORY_ID = 823259072002392134
HOG_RIDER_ROLE_ID = settings['roles']['hog_rider']
BOTS_ROLE_ID = settings['roles']['bots']
DEVELOPER_ROLE_ID = settings['roles']['developer']
ADMIN_ROLE_ID = settings['roles']['admin']
GUEST_ROLE_ID = settings['roles']['vip_guest']

SECTION_MATCH = re.compile(r'(?P<title>.+?)<a name="(?P<number>\d+|\d+.\d+)"></a>(?P<body>(.|\n)+?(?=(#{2,3}|\Z)))')
UNDERLINE_MATCH = re.compile(r"<ins>|</ins>")
URL_EXTRACTOR = re.compile(r"\[(?P<title>.*?)\]\((?P<url>[^)]+)\)")



class ConfirmButton(ui.Button["ConfirmView"]):
    def __init__(self, label: str, style: nextcord.ButtonStyle, *, custom_id: str):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: Interaction):
        self.view.value = True if self.custom_id == f"confirm_button" else False
        self.view.stop()


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=10.0)
        self.value = None
        self.add_item(ConfirmButton("Yes", nextcord.ButtonStyle.green, custom_id="confirm_button"))
        self.add_item(ConfirmButton("No", nextcord.ButtonStyle.red, custom_id="decline_button"))


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == WELCOME_CHANNEL_ID and message.type is nextcord.MessageType.thread_created:
            await message.delete(delay=5)

    @nextcord.slash_command(name="invite", guild_ids=GUILD_IDS)
    async def invite(self, interaction: nextcord.Interaction):
        """Responds with the invite link to this server"""
        await interaction.response.send_message("https://discord.gg/clashapi")

    @nextcord.slash_command(name="regex", guild_ids=GUILD_IDS)
    async def regex(self, interaction: nextcord.Interaction):
        """Responds with the RegEx for player/clan tags"""
        await interaction.response.send_message("^#[PYLQGRJCUV0289]{3,9}$")

    @nextcord.slash_command(name="rate_limit", guild_ids=GUILD_IDS)
    async def rate_limit(self, interaction: nextcord.Interaction):
        """Responds with the rate limit information for the Clash API"""
        print("preparing to respond")
        await interaction.response.send_message("We have found that the approximate rate limit is 30-40 requests per "
                                                "second. Staying below this should be safe.")
        print("done responding")

    @nextcord.slash_command(name="cache_max_age", guild_ids=GUILD_IDS)
    async def refresh_interval(self, interaction: nextcord.Interaction):
        """Responds with the max age of the information for each endpoint in the ClashAPI"""
        embed = nextcord.Embed(title="Max age of information due to caching")
        embed.add_field(name="Clans", value="2 Minutes", inline=False)
        embed.add_field(name="current war", value="2 Minutes", inline=False)
        embed.add_field(name="All other war related", value="10 Minutes", inline=False)
        embed.add_field(name="Player", value="1 Minute", inline=False)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="vps", guild_ids=GUILD_IDS)
    async def vps(self, interaction: nextcord.Interaction):
        """Responds with a link to a GitHub MD on VPS options"""
        await interaction.response.send_message(
            "<https://github.com/wpmjones/apibot/blob/master/Rules/vps_services.md>")

    @nextcord.slash_command(name="rules", guild_ids=GUILD_IDS)
    async def rules(self, interaction: nextcord.Interaction):
        """Respond with a link to the rules markdown file."""
        await interaction.response.send_message("<https://github.com/wpmjones/apibot/blob/master/"
                                                "Rules/code_of_conduct.md>")

    @nextcord.slash_command(name="links", guild_ids=GUILD_IDS)
    async def link_api(self, interaction: nextcord.Interaction):
        """Responds with a link to a Discord message on the Discord Link API (by TubaKid)"""
        await interaction.response.send_message("https://discord.com/channels/566451504332931073/681617252814159904/"
                                                "936126372873650237")

    @nextcord.slash_command(name="coc_wrappers", guild_ids=GUILD_IDS)
    async def link_coc_wrappers(self, interaction: nextcord.Interaction):
        """Respond with a link to the page created by @Doluk"""
        await interaction.response.send_message("<https://coc-libs.vercel.app/>")

    @nextcord.slash_command(name="discord_wrappers", guild_ids=GUILD_IDS)
    async def link_discord_wrappers(self, interaction: nextcord.Interaction):
        """Respond with a link to a list of known discord wrappers"""
        await interaction.response.send_message("<https://libs.advaith.io/>")

    @nextcord.slash_command(name="player_url", guild_ids=GUILD_IDS)
    async def format_player_url(self, interaction: nextcord.Interaction,
                                player_tag: str = ""):
        """Gives info on how to construct a player profile url and optionally the url for a specific player"""
        if player_tag:
            if coc.utils.is_valid_tag(player_tag):
                response = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23" \
                           f"{coc.utils.correct_tag(player_tag, prefix='')}\n\n"
            else:
                response = "I will not construct you a link with an invalid player tag\n\n"
        else:
            response = ""
        response += ("You can construct a profile link for any player by combining the following base url with the "
                     "player's tag. But make sure to replace the `#` prefix with its encoded form `%23`\n"
                     "```https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=```")
        await interaction.response.send_message(response)

    @nextcord.slash_command(name="help", description="Help command for slash commands", guild_ids=GUILD_IDS)
    async def slash_help(self, interaction: nextcord.Interaction):
        embed = nextcord.Embed(title="Overview of Slash Commands",
                               color=0xFFFFFF)
        commands: list[nextcord.BaseApplicationCommand] = self.bot.get_all_application_commands()
        global_outside_group = []
        guild_outside_group = []
        global_groups = []
        guild_groups = []
        for cmd in commands:
            # skip all non slash commands
            if cmd.type != nextcord.ApplicationCommandType(1):
                continue
            # skip admin specific slash commands
            if cmd.qualified_name in ["doobie", "help"]:
                continue
            # get guild specific payload
            payload = cmd.get_payload(interaction.guild_id if cmd.guild_ids else None)
            options = payload.get("options", {})
            if all([option['type'] > 2 for option in options]):
                # there is no subcommand or command group
                if cmd.guild_ids:
                    guild_outside_group.append(f"</{cmd.qualified_name}:"
                                               f"{cmd.command_ids[interaction.guild_id]}> "
                                               f"{cmd.description}\n")
                    continue
                else:
                    global_outside_group.append(f"</{cmd.qualified_name}:"
                                                f"{cmd.command_ids[None]}>"
                                                f" {cmd.description}\n")
                    continue
            else:
                # handle subcommand group/ subcommands
                sub_commands = sorted([f"</{cmd.qualified_name} {option['name']}:"
                                       f"{cmd.command_ids[interaction.guild_id if cmd.guild_ids else None]}> "
                                       f"{option['description']}" for option in options if option['type'] <= 2],
                                      key=lambda x: x)
                if cmd.guild_ids:
                    embed = nextcord.Embed(
                        title=f'Guild Commands of the {cmd.qualified_name} group [{len(sub_commands)}]',
                        description="\n".join(sub_commands),
                        color=0xDDDDDD
                    )
                    guild_groups.append(embed)
                else:
                    embed = nextcord.Embed(
                        title=f'Global Commands of the {cmd.qualified_name} group [{len(sub_commands)}]',
                        description="\n".join(sub_commands),
                        color=0xDDDDDD
                    )
                    global_groups.append(embed)
        ungrouped_global = nextcord.Embed(title=f'Global Commands [{len(global_outside_group)}]',
                                          description="\n".join(sorted(global_outside_group, key=lambda x: x)),
                                          color=0xFFFFFF)
        ungrouped_guild = nextcord.Embed(title=f'Guild Commands [{len(guild_outside_group)}]',
                                         description="\n".join(sorted(guild_outside_group, key=lambda x: x)),
                                         color=0xFFFFFF)
        embeds = ([ungrouped_global] + list(sorted(global_groups, key=lambda x: x.title)) + [ungrouped_guild] +
                  list(sorted(guild_groups, key=lambda x: x.title)))
        await interaction.response.send_message(embeds=embeds)

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
        //setup @bot @owner

        **Permissions:**
        Admin role required
        """
        if not bot or not owner:
            return await ctx.send("Please be sure to provide a Discord ID or mention both the bot and the owner. "
                                  "`//setup @bot @owner`")
        if not bot.bot:
            return await ctx.send(f"{bot.mention} does not appear to be a bot. Please try again with "
                                  f"`//setup @bot @owner`.")
        if owner.bot:
            return await ctx.send(f"{owner.mention} appears to be a bot, but should be the bot owner. Please try "
                                  f"again with `//setup @bot @owner`.")

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
        await ctx.message.delete()
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
        if (ctx.channel.id != settings['channels']['welcome'] or
                ctx.channel.parent.id == settings['channels']['welcome']):
            return await ctx.send(f"I'd feel a whole lot better if you ran this command in "
                                  f"<#{settings['channels']['welcome']}> or a thread.")
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
                content += f"{i + 1} - {role_names[i]}\n"
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
        try:
            await ctx.invoke(self.bot.get_command("to_gen"))
        except:
            await self.bot.logger.exception(f"Failure when calling to_gen")

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

    @nextcord.slash_command(name="doobie", guild_ids=GUILD_IDS)
    @application_checks.has_role("Admin")
    async def clear(self,
                    interaction: nextcord.Interaction,
                    msg_count: str = nextcord.SlashOption(description="Message count OR Message ID",
                                                          required=False)):
        """Clears the specified number of messages OR all messages from the specified ID. (Admin only)

        **Examples:**
        /doobie (will ask for confirmation first)
        /doobie 7 (no confirmation, will delete the 7 previous messages)
        /doobie 1044857124779466812 (no confirmation, will delete all messages up to and including that one)

        **Permissions:**
        Manage Messages
        """
        if msg_count:
            msg_count = int(msg_count)
            if msg_count < 100:
                await interaction.channel.purge(limit=msg_count)
                await interaction.send(f"{msg_count} messages deleted.",
                                       delete_after=5,
                                       ephemeral=True)
            else:
                try:
                    message = await interaction.channel.fetch_message(msg_count)
                    messages = await interaction.channel.history(after=message).flatten()
                    msg_count = len(messages) + 1
                    await interaction.channel.delete_messages(messages)
                    async for message in interaction.channel.history(limit=1):
                        await message.delete()
                    await interaction.send(f"{msg_count} messages deleted.",
                                           delete_after=5,
                                           ephemeral=True)
                except nextcord.errors.NotFound:
                    return await interaction.send("It appears that you tried to enter a message ID, but I can't find "
                                                  "that message in this channel.")
        else:
            confirm_view = ConfirmView()

            def disable_all_buttons():
                for _item in confirm_view.children:
                    _item.disabled = True

            confirm_content = (f"Are you really sure you want to remove ALL messages from "
                               f"the {interaction.channel.name} channel?")
            msg = await interaction.send(content=confirm_content, view=confirm_view)
            await confirm_view.wait()
            if confirm_view.value is False or confirm_view.value is None:
                disable_all_buttons()
                await msg.delete()
            else:
                disable_all_buttons()
                await interaction.channel.purge()

    @nextcord.slash_command(name="youtube", guild_ids=GUILD_IDS)
    @application_checks.has_role("Admin")
    async def youtube(self,
                      interaction: nextcord.Interaction,
                      youtube_id: str = nextcord.SlashOption(description="Just the ID of the video",
                                                             required=True)):
        ydl_options = {
            "default-search": "ytsearch",
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        }
        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            ydl.download(youtube_id)
        await interaction.response.send_message("Download complete.")


    @commands.command(hidden=True)
    @commands.has_role("Admin")
    async def recreate_rules(self, ctx):
        """Recreate the #rules channel. (Admin only)

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
        """Recreate the #community-projects channel. (Admin only)

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
    async def recreate_faqs(self, ctx):
        """Clone the admin faqs to public ones or update them"""
        # generate permission overwrite
        guild = ctx.guild
        reader_perms = nextcord.PermissionOverwrite(view_channel=True, read_messages=True, read_message_history=True,
                                                    create_private_threads=False, create_public_threads=False,
                                                    send_messages_in_threads=False)
        everyone_perms = nextcord.PermissionOverwrite(view_channel=False, read_messages=False)
        perm_over = {nextcord.utils.get(guild.roles, name="Developer"): reader_perms,
                     nextcord.utils.get(guild.roles, name="Guest"): reader_perms,
                     guild.default_role: everyone_perms}
        # get admin faq channel
        template: nextcord.ForumChannel = await guild.fetch_channel(FAQS_CHANNEL_ID)
        # get the resources category
        cat = nextcord.utils.get(guild.categories, id=RESOURCES_CATEGORY_ID)
        # check if faq channel exists
        faq_channel = nextcord.utils.get(cat.channels, name="FAQs")
        # create faq channel if not existing
        if not faq_channel:
            faq_channel = await cat.create_forum_channel(name="FAQs", topic=template.topic,
                                                         auto_archive_duration=10080,
                                                         overwrites=perm_over)
        # pick a template thread, try to find it in the new faq channel
        for t_thread in template.threads:
            try:
                if not os.path.exists(f"FAQs/{t_thread.name}.md"):
                    continue
                # prepare embed
                with open(f"FAQs/{t_thread.name}.md", encoding="utf-8") as fp:
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
                        color = 0xBDDDF4  # lighter blue for sub-headings/groups
                    else:
                        color = nextcord.Color.blue()

                    embeds.append(nextcord.Embed(title=title, description=description.strip(), color=color))
                    titles.append(title)

                n_thread = None
                for thread in faq_channel.threads:
                    if thread.name == t_thread.name:
                        n_thread = thread

                # thread does not exist
                if not n_thread:
                    n_thread = faq_channel.create_thread(name=t_thread.name, embeds=embeds)
                else:
                    msg = await n_thread.fetch_message(n_thread.last_message_id)
                    await msg.edit(embeds=embeds)
                await ctx.send(f'Created {n_thread.name}')
            except Exception as e:
                self.bot.logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(General(bot))
