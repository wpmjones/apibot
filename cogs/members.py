import random

from config import settings
from discord.ext import commands


class MembersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="welcome", hidden=True)
    async def welcome(self, ctx, discord_id):
        guild = self.bot.get_guild(settings['guild']['junkies'])
        print(guild)
        member = guild.get_member(discord_id)
        print(member.name)
        if not member:
            return await ctx.send("Member does not exist.")
        channel = self.bot.get_channel(settings['channels']['general'])
        msg = (f"Welcome to the COC API Junkies server, {member.mention}! We're glad to have you! "
               f"Please tell us what API project(s) you are working on and what your preferred programming "
               f"language is.")
        await channel.send(msg)
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just joined the server."
        await mod_log.send(msg)
        await ctx.send(f"Welcome message sent to {member.name}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Discord listener which is called when a user joins the Discord server."""
        channel = self.bot.get_channel(settings['channels']['general'])
        msg = (f"Welcome to the COC API Junkies server, {member.mention}! We're glad to have you! "
               f"Please tell us what API project(s) you are working on and what your preferred programming "
               f"language is.")
        await channel.send(msg)
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just joined the server."
        await mod_log.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Discord listener which is called when a user leaves the Discord server."""
        # Build random list of messages
        msg_options = [" just left the server.  Buh Bye!",
                       " just left our Discord. I wonder if we will miss them.",
                       " just left. What's up with that?"]
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = member.display_name + random.choice(msg_options)
        await mod_log.send(msg)


def setup(bot):
    bot.add_cog(MembersCog(bot))
