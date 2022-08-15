import asyncio
import nextcord

from config import settings
from datetime import datetime, timezone, timedelta
from nextcord.ext import commands, tasks
from typing import List

WELCOME_MESSAGE = ("Welcome to the Clash API Developers server, {}! We're glad to have you!\n"
                   "First, please let us know what your preferred programming language is. "
                   "Next, if you've already started working with the API, please tell us a little about your "
                   "project. If you haven't started a project yet, let us know what you're interested in making.\n"
                   "(Once you introduce yourself, you will be granted roles to access other parts of the server.)")

PRUNE_WARNING = ("You have been a member of the Clash API Developers Discord server for "
                 "at least five days, but you have not yet introduced yourself.  Please "
                 "got to <#885193658985500722> and let us know what your preferred "
                 "programming language is. Next, if you've already started working with "
                 "the API, please tell us a little about your project. If you haven't "
                 "started a project yet, let us know what you're interested in making. "
                 "Once you introduce yourself, you will be granted roles to access "
                 "other parts of the server.")


class Confirm(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.green)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("Confirming", ephemeral=True)
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.grey)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("Cancelling", ephemeral=True)
        self.value = False
        self.stop()


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
        await self.member.edit(nick=f"{self.member.display_name} | {self.role.name}")


class RoleView(nextcord.ui.View):
    def __init__(self, guild: nextcord.Guild, member: nextcord.Member, role_ids: List[int]):
        super().__init__(timeout=None)
        for role_id in role_ids:
            role = guild.get_role(role_id)
            if not role:
                print(f"Role not found: {role_id}")
                continue
            self.add_item(RoleButton(role, member))


class MembersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prune_loop.start()

    def cog_unload(self):
        self.prune_loop.cancel()

    @tasks.loop(hours=24)
    async def prune_loop(self):
        """Prune inactive members (7 days) without roles"""
        self.bot.logger.info("Initiating prune loop")
        counter = 0
        guild = self.bot.get_guild(settings['guild']['junkies'])
        devs = guild.get_role(settings['roles']['developer'])
        guests = guild.get_role(settings['roles']['vip_guest'])
        bots = guild.get_role(settings['roles']['bots'])
        hr = guild.get_role(settings['roles']['hog_rider'])
        inactive = set(guild.members).difference(devs.members)
        inactive = inactive.difference(guests.members)
        inactive = inactive.difference(bots.members)
        inactive = inactive.difference(hr.members)
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        try:
            # Prune anyone without a role and on server for more than 7 days.
            for member in inactive:
                if now - timedelta(days=7) > member.joined_at:
                    await member.kick(reason="Pruned by Hog Rider (members.py)")
                    counter += 1
                    continue
                if now - timedelta(days=5) > member.joined_at:
                    try:
                        await member.send(content=PRUNE_WARNING)
                    except nextcord.errors.Forbidden:
                        self.bot.logger.info(f"Prune warning failed. {member.display_name} does not allow DMs.")
            if counter > 0:
                self.bot.logger.info(f"Pruned {counter} members.")
        except:
            self.bot.logger.exception("Failure in prune_loop")

    @prune_loop.before_loop
    async def before_prune_loop(self):
        await self.bot.wait_until_ready()

    @commands.command(name="ptest", hidden=True)
    async def ptest(self, ctx):
        from time import perf_counter
        guild = self.bot.get_guild(settings['guild']['junkies'])
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        start = perf_counter()
        for member in guild.members:
            if len(member.roles) == 1:
                self.bot.logger.info(f"{member.display_name} has only one role. {member.roles[0].name} "
                                     f"({now - member.joined_at})")
        stop = perf_counter()
        self.bot.logger.info(f"Elapsed: {stop - start}")

    @commands.command(name="welcome", hidden=True)
    async def welcome(self, ctx, member: nextcord.Member = None):
        if not member:
            return await ctx.send("Member does not exist.")
        channel = self.bot.get_channel(settings['channels']['welcome'])
        await channel.send(WELCOME_MESSAGE.format(member.mention))
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just joined the server."
        await mod_log.send(f"{msg} (This message generated by the `//welcome` command initiated by "
                           f"{ctx.author.display_name}.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Discord listener which is called when a user joins the Discord server."""
        if member.guild.id != 566451504332931073:
            # only act if they are joining API server
            return
        if not member.bot:
            channel = self.bot.get_channel(settings['channels']['welcome'])
            await channel.send(WELCOME_MESSAGE.format(member.mention))
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
            # only act if roles have changed
            return
        developer_role = new_member.guild.get_role(settings['roles']['developer'])
        if developer_role not in old_member.roles and developer_role in new_member.roles:
            # only act if the Developer role is new
            if new_member.bot:
                channel = self.bot.get_channel(settings['channels']['admin'])
                await channel.send(f"Who is the bonehead that assigned the Developer role to a bot? "
                                   f"{new_member.name} is a bot.")
            # At this point, it should be a member on our server that has just received the developers role
            # We're going to sleep for 10 seconds to give the admin time to add a language role as well
            await asyncio.sleep(10)
            self.bot.logger.info(f"New member with Developers role: {new_member.display_name}")
            sql = "SELECT role_id, role_name, emoji_repr FROM bot_language_board"
            fetch = await self.bot.pool.fetch(sql)
            language_roles = [[row['role_id'], row['role_name'], row['emoji_repr']] for row in fetch]
            member_languages = ""
            member_role_emoji = []
            for language_role in language_roles:
                for role in new_member.roles:
                    if language_role[0] == role.id:
                        member_languages += f"{language_role[1]}\n"
                        member_role_emoji.append(language_role[2])
            channel = new_member.guild.get_channel(settings['channels']['general'])
            embed = nextcord.Embed(color=nextcord.Color.blue(),
                                   description=f"Please welcome {new_member.display_name} to the Clash API Developers "
                                               f"server.")
            if new_member.avatar:
                embed.set_thumbnail(url=new_member.avatar.url)
            if member_languages:
                embed.add_field(name="Languages:", value=member_languages)
            msg = await channel.send(embed=embed)
            if member_role_emoji:
                for emoji in member_role_emoji:
                    await msg.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Discord listener which is called when a user leaves the Discord server."""
        if member.guild.id != 566451504332931073:
            # only act if they are joining API server
            return
        # Build random list of messages
        # msg_options = [" just left the server.  Buh Bye!",
        #                " just left our Discord. I wonder if we will miss them.",
        #                " just left. What's up with that?",
        #                " went bye-bye. Who will fill the void?",
        #                " has left us. A short moment of silence.",
        #                " has departed. Hope they learned everything they need!",
        #                ]
        # channel = self.bot.get_channel(settings['channels']['general'])
        # msg = member.display_name + random.choice(msg_options)
        # await channel.send(msg)
        mod_log = self.bot.get_channel(settings['channels']['mod-log'])
        msg = f"{member.display_name}#{member.discriminator} just left the server."
        await mod_log.send(msg)

    @nextcord.message_command(name="Developer", guild_ids=[settings['guild']['junkies']])
    async def ctx_menu_developer(self, interaction: nextcord.Interaction, message: nextcord.Message):
        member = message.author
        dev_role = interaction.guild.get_role(settings['roles']['developer'])
        if dev_role in member.roles:
            return await interaction.send(f"{member.display_name} already has the Developer role. "
                                          f"This command can only be used for members without the "
                                          f"Developer role.",
                                          ephemeral=True)
        if interaction.channel_id != settings['channels']['welcome']:
            return await interaction.send(f"I'd feel a whole lot better if you ran this command in "
                                          f"<#{settings['channels']['welcome']}>.",
                                          ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        guest_role = interaction.guild.get_role(settings['roles']['vip_guest'])
        if guest_role in member.roles:
            view = Confirm()
            await interaction.send(f"{member.display_name} currently has the Guest role. Would you "
                                   f"like to remove the Guest role and add the Developer role?",
                                   view=view)
            await view.wait()
            if view.value is None:
                return await interaction.send("Action timed out.")
            elif view.value:
                await member.remove_roles(guest_role, reason="Changing to Developer role")
            else:
                return await interaction.send("Action cancelled.")
        self.bot.logger.debug("Pre-checks complete. Starting dev add process.")
        # At this point, we should have a valid member without the dev role
        # Let's see if we want to add any language roles first
        self.bot.logger.info(f"Starting Dev Role add process for {member.display_name} (Initiated by "
                             f"{interaction.user.display_name})")
        sql = "SELECT role_id FROM bot_language_board ORDER BY role_name"
        fetch = await self.bot.pool.fetch(sql)
        role_ids = [x['role_id'] for x in fetch]
        view = RoleView(interaction.guild, member, role_ids)
        content = "Please select the member's primary language role:"
        await interaction.send(content, delete_after=60.0, view=view)
        # Add developer role
        await member.add_roles(dev_role, reason=f"Role added by {interaction.user.display_name}")
        # Send DM to new member
        welcome_msg = ("Welcome to the Clash API Developers server.  We hope you find this to be a great place to "
                       "share and learn more about the Clash of Clans API.  You can check out <#641454924172886027> "
                       "if you need some basic help.  There are some tutorials there as well as some of the more "
                       "common libraries that are used with various programming languages. If you use more than one "
                       "programming language, be sure to check out <#885216742903803925> to assign yourself the role "
                       "for each language.\nLastly, say hello in <#566451504903618561> and make some new friends!!")
        await member.send(welcome_msg)
        # Copy a message to General??
        view = Confirm()
        await interaction.send("Do you want to copy this message to #general?",
                               delete_after=60.0,
                               view=view)
        await view.wait()
        if view.value is None:
            self.bot.logger.debug("Prompt to copy message timed out. No biggie.")
        elif view.value:
            # copy message
            content = f"{message.author.display_name} says:\n>>> {message.content}"
            general = self.bot.get_channel(settings['channels']['general'])
            await general.send(content)


def setup(bot):
    bot.add_cog(MembersCog(bot))
