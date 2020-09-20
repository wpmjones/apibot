import discord

from config import settings
from discord.ext import commands


JUNKIES_GUILD_ID = 566451504332931073
BOT_DEMO_CATEGORY_ID = 567551986229182474
BOTS_ROLE_ID = 567559094152724491
USERS_ROLE_ID = 566455547394785331


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @commands.command(name="setup", hidden=True)
    @commands.has_role(settings['roles']['admin'])
    async def setup_bot(self, ctx, bot: discord.Member = None, owner: discord.Member = None):
        """Admin use only: For adding bot demo channels
        Creates channel (based on bot name)
        Alphabatizes channel within the Bot-Demos category
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
        channel_name = f"{bot.name}-demo"
        topic = f"Maintained by {owner.display_name}"
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.guild.get_role(BOTS_ROLE_ID): discord.PermissionOverwrite(read_messages=False),
            ctx.guild.get_role(USERS_ROLE_ID): discord.PermissionOverwrite(read_messages=True),
            bot: discord.PermissionOverwrite(read_messages=True,
                                             send_messages=True,
                                             read_message_history=True,
                                             manage_messages=True,
                                             embed_links=True,
                                             attach_files=True,
                                             external_emojis=True,
                                             add_reactions=True),
        }
        position = category.channels[0].position + sorted(
            category.channels + [channel_name], key=lambda c: str(c)
        ).index(channel_name)

        channel = await ctx.guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=category,
            position=position,
            topic=topic,
            reason=f"Created by the setup command of Hog Rider ({ctx.author})",
        )
        # ping owner
        await channel.send(f"{owner.mention} This channel has been set up for your use in demonstrating the features "
                           f"of **{bot.name}**. Limited troubleshooting with others is acceptable, but please do not "
                           f"allow this channel to become a testing platform.  Thanks!")

        # add the "Bots" role
        await bot.add_roles(
            ctx.guild.get_role(BOTS_ROLE_ID),
            reason=f"Added by setup command of Hog Rider ({ctx.author})",
        )

        # sort the Bot-Demo channels alphabetically
        for index, channel in enumerate(
            sorted(category.channels, key=lambda c: str(c)), start=category.channels[0].position
        ):
            if channel.position != index:
                await channel.edit(position=index)


def setup(bot):
    bot.add_cog(General(bot))
