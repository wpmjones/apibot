import copy
import discord
import re

from config import settings
from discord.ext import commands

JUNKIES_GUILD_ID = settings['guild']['junkies']
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
TITLE_EXTRACTOR = re.compile(r"\[(.*?)\]")
# URL_EXTRATOR = re.compile(r"\(([^)]+)\)")
URL_EXTRACTOR = re.compile(r"/\(([^)]+)\)/")


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="invite")
    async def invite(self, ctx):
        """Responds with the invite link to this server"""
        await ctx.send("https://discord.gg/clashapi")

    @commands.command(name="regex")
    async def regex(self, ctx):
        """Responds with the RegEx for player/clan tags"""
        await ctx.send("^#[PYLQGRJCUV0289]+$")

    @commands.command(name="rate_limit")
    async def rate_limit(self, ctx):
        """Responds with the rate limit information for the Clash API"""
        await ctx.send("We have found that the approximate rate limit is 30-40 requests per second. Staying "
                       "below this should be safe.")

    @commands.command(name="vps")
    async def vps(self, ctx):
        """Responds with a link to a Discord message on inexpensive VPS options"""
        await ctx.send("https://discordapp.com/channels/566451504332931073/566451504903618561/662484243808780309")

    @commands.command(name="links")
    async def links(self, ctx):
        """Responds with a link to a Discord message on the Discord Link API (by ReverendMike)"""
        await ctx.send("https://discordapp.com/channels/566451504332931073/681617252814159904/755489156146397311")

    @commands.command(name="rules")
    async def rules(self, ctx):
        """Respond with a link to the rules markdown file."""
        await ctx.send("<https://github.com/wpmjones/apibot/blob/master/Rules/code_of_conduct.md>")

    @commands.command(name="setup", aliases=["set_up", ], hidden=True)
    @commands.has_role("Admin")
    async def setup_bot(self, ctx, bot: discord.Member = None, owner: discord.Member = None):
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
            bot: discord.PermissionOverwrite(read_messages=True,
                                             send_messages=True,
                                             read_message_history=True,
                                             manage_messages=True,
                                             embed_links=True,
                                             attach_files=True,
                                             external_emojis=True,
                                             add_reactions=True),
            admin_role: discord.PermissionOverwrite(read_messages=True,
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
            hog_rider_role: discord.PermissionOverwrite(read_messages=True,
                                                        send_messages=True,
                                                        read_message_history=True,
                                                        manage_messages=True,
                                                        embed_links=True,
                                                        attach_files=True,
                                                        external_emojis=True,
                                                        add_reactions=True),
            developer_role: discord.PermissionOverwrite(read_messages=True,
                                                        send_messages=True,
                                                        read_message_history=True,
                                                        manage_messages=False,
                                                        embed_links=True,
                                                        attach_files=True,
                                                        external_emojis=True,
                                                        add_reactions=True),
            guest_role: discord.PermissionOverwrite(read_messages=True,
                                                    send_messages=True,
                                                    read_message_history=True,
                                                    manage_messages=False,
                                                    embed_links=True,
                                                    attach_files=True,
                                                    external_emojis=False,
                                                    add_reactions=True),
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
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
                       f"`/bot add {bot.id}`")

    @commands.command(name="clear", hidden=True)
    @commands.is_owner()
    async def clear(self, ctx, msg_count: int = None):
        """Clears the specified number of messages in the current channel (defaults to all messages)."""
        if msg_count:
            await ctx.channel.purge(limit=msg_count + 1)
        else:
            async for message in ctx.channel.history():
                await message.delete()

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
                colour = discord.Colour.blue()

            embeds.append(discord.Embed(title=title, description=description.strip(), colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        rows = []
        buttons = []

        # FIXME: Update when d.py goes to v2
        for i, (message, title) in enumerate(zip(messages, titles)):
            if i == 3:
                rows.append({
                    "type": 1,  # action row
                    "components": copy.copy(buttons),
                })
                buttons.clear()

            buttons.append({
                "type": 2,  # button type
                "label": title.replace("#", "").strip(),
                "style": 5,  # URL
                "url": message.jump_url,
            })

        if buttons:
            rows.append({
                "type": 1,  # action row
                "components": buttons,
            })

        await self.send_buttons(channel.id, rows, "\u200b")
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
            self.bot.logger.info(raw_title)
            if URL_EXTRACTOR.match(raw_title):
                title = TITLE_EXTRACTOR.match(raw_title).group(0)
                url = URL_EXTRACTOR.match(raw_title).group(0)
                self.bot.logger.info(f"TRUE\nTitle: {title}\nURL: {url}")
            else:
                title = raw_title.replace("#", "").strip()
                url = ""
                self.bot.logger.info(f"FALSE\nTitle: {title}\nURL: {url}")

            if "." in match.group("number"):
                colour = 0xBDDDF4  # lighter blue for sub-headings/groups
            else:
                colour = discord.Colour.blue()

            embeds.append(discord.Embed(title=title, url=url, description=description.strip(), colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        rows = []
        buttons = []

        # FIXME: Update when d.py goes to v2
        for i, (message, title) in enumerate(zip(messages, titles)):
            if i == 3:
                rows.append({
                    "type": 1,  # action row
                    "components": copy.copy(buttons),
                })
                buttons.clear()

            buttons.append({
                "type": 2,  # button type
                "label": title.replace("#", "").strip(),
                "style": 5,  # URL
                "url": message.jump_url,
            })

        if buttons:
            rows.append({
                "type": 1,  # action row
                "components": buttons,
            })

        await self.send_buttons(channel.id, rows, "\u200b")
        await ctx.send(f"Project list has been recreated. View here <#{PROJECTS_CHANNEL_ID}>")

    async def send_buttons(self, channel_id, action_rows, content):
        # d.py v1.x doesn't support components, so just construct the payloads manually for now.
        route = discord.http.Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id)
        payload = {
            "components": action_rows,
            "content": content
        }
        await self.bot.http.request(route, json=payload)


def setup(bot):
    bot.add_cog(General(bot))
