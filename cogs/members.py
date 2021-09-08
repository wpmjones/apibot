import discord
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
        channel = self.bot.get_channel(settings['channels']['welcome'])
        msg = (f"Welcome to the Clash API Developers server, {member.mention}! We're glad to have you!\n"
               f"First, please let us know what your preferred programming language is. "
               f"Next, if you've already started working with the API, please tell us a little about your project. "
               f"If you haven't started a project yet, let us know what you're interested in making.")
        await channel.send(msg)
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just joined the server."
        await mod_log.send(msg)
        await ctx.send(f"Welcome message sent to {member.name}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Discord listener which is called when a user joins the Discord server."""
        if member.guild.id != 566451504332931073:
            # only act if they are joining API server
            return
        if not member.bot:
            channel = self.bot.get_channel(settings['channels']['welcome'])
            msg = (f"Welcome to the Clash API Developers server, {member.mention}! We're glad to have you!\n"
                   f"First, please let us know what your preferred programming language is. "
                   f"Next, if you've already started working with the API, please tell us a little about your project. "
                   f"If you haven't started a project yet, let us know what you're interested in making.")
            await channel.send(msg)
        else:
            channel = self.bot.get_channel(settings['channels']['admin'])
            await channel.send(f"{member.mention} has just been invited to the server. "
                               f"Perhaps it is time to set up a demo channel?  Try `//setup {member.mention} @owner`")
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just joined the server."
        await mod_log.send(msg)

    @commands.Cog.listener()
    async def on_member_update(self, old_member, new_member):
        """Discord listener to announce new member with Developer role to #general"""
        if new_member.guild.id != 566451504332931073:
            # only act if this is the API server
            return
        if old_member.roles == new_member.roles:
            return
        developer_role = new_member.guild.get_role(settings['roles']['developer'])
        self.bot.logger.debug(developer_role.name)
        if developer_role not in old_member.roles and developer_role in new_member.roles:
            if new_member.bot:
                channel = self.bot.get_channel(settings['channels']['admin'])
                await channel.send(f"Who is the bonehead that assigned the Developer role to a bot? "
                                   f"{new_member.name} is a bot.")
            # At this point, it should be a member on our server that has just received the developers role
            self.bot.logger.info(f"New member with Developers role: {new_member.display_name}")
            sql = "SELECT role_id, role_name FROM bot_language_board"
            fetch = await self.bot.pool.fetch(sql)
            language_roles = [[row['role_id'], row['role_name']] for row in fetch]
            member_languages = ""
            for language_role in language_roles:
                for role in new_member.roles:
                    self.bot.logger.info(f"Comparing {language_role[0]} and {role.id}")
                    self.bot.logger.info(f"{type(language_role[0])} vs {type(role.id)}")
                    if language_role[0] == role.id:
                        member_languages += f"{language_role[1]}\n"
            channel = new_member.guild.get_channel(settings['channels']['general'])
            embed = discord.Embed(color=discord.Color.blue(),
                                  description=f"Please welcome {new_member.display_name} to the Clash API Developers "
                                              f"server.")
            embed.set_image(url=new_member.avatar_url_as(size=128))
            if member_languages != "":
                embed.add_field(name="Languages:", value=member_languages)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Discord listener which is called when a user leaves the Discord server."""
        if member.guild.id != 566451504332931073:
            # only act if they are joining API server
            return
        # Build random list of messages
        msg_options = [" just left the server.  Buh Bye!",
                       " just left our Discord. I wonder if we will miss them.",
                       " just left. What's up with that?",
                       " went bye-bye. Who will fill the void?",
                       " has left us. A short moment of silence.",
                       " has departed. Hope they learned everything they need!",
                       ]
        channel = self.bot.get_channel(settings['channels']['general'])
        msg = member.display_name + random.choice(msg_options)
        await channel.send(msg)
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just left the server."
        await mod_log.send(msg)


def setup(bot):
    bot.add_cog(MembersCog(bot))
