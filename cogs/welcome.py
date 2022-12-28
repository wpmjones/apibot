import traceback

import nextcord

from nextcord.ext import commands, tasks
from nextcord import ui, Interaction, Thread, ChannelType
from datetime import datetime, timezone, timedelta
from typing import List
from config import settings

enviro = settings['enviro']

if enviro == "LIVE":
    WELCOME_CHANNEL_ID = settings['channels']['welcome']
    GENERAL_CHANNEL_ID = settings['channels']['general']
else:
    WELCOME_CHANNEL_ID = 1011500429969993808
    GENERAL_CHANNEL_ID = settings['channels']['testing']

DEVELOPER_ROLE_ID = settings['roles']['developer']
ADMIN_ROLE_ID = settings['roles']['admin']

WELCOME_MESSAGE = ("**Welcome to the Clash API Developers server!**\nWe're glad to have you! "
                   "We're here to help you do the things you want to do with the Clash API. While we can "
                   "provide some language specific guidance, we are not a 'learn to code' server. There are "
                   "plenty of resources out there for that.  But if you know the basics of coding and "
                   "want to learn more about incorporating the Clash of Clans API into a project, you've "
                   "come to the right place.\n\nPlease click the Introduce button below to tell us a little "
                   "bit about yourself and gain access to the rest of the server.")


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
            if int(value) == 0:
                # escape other role
                continue
            role = interaction.guild.get_role(int(value))
            self.view.role_list.append(role.name)
            await self.member.add_roles(role)
            try:
                await self.member.edit(nick=f"{self.member.display_name} | {role.name}")
            except nextcord.HTTPException:
                # this might happen if the nickname gets too long
                pass
            self.view.stop()


class RoleView(nextcord.ui.View):
    def __init__(self, member: nextcord.Member, roles):
        super().__init__(timeout=20.0)
        self.role_list = []
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
            min_length=12,
            max_length=544)
        self.add_item(self.language)
        self.add_item(self.information)

    async def create_welcome_thread(self, interaction: Interaction, lang, info) -> Thread:
        thread = await interaction.channel.create_thread(name=f"Welcome {interaction.user.name}",
                                                         type=ChannelType.private_thread)
        embed = nextcord.Embed(title=f"Introducing {interaction.user.name}",
                               description=f"Created by: {interaction.user} ({interaction.user.id})",
                               color=nextcord.Color.green())
        embed.add_field(name="Language(s):", value=lang, inline=False)
        embed.add_field(name="Message:", value=info, inline=False)
        embed.set_footer(text="Admins can approve or invite the member to request more information.")

        welcome_button_view = WelcomeButtonView(self.bot, interaction.user, lang, info)

        await thread.send(embed=embed, view=welcome_button_view)
        return thread

    async def callback(self, interaction: Interaction):
        if self.bot.pending_members[interaction.user.id]:
            return
        lang = self.language.value
        info = self.information.value
        created_thread = await self.create_welcome_thread(interaction, lang, info)
        self.bot.pending_members[interaction.user.id] = True
        await created_thread.send(f"<@&{ADMIN_ROLE_ID}>", delete_after=5)
        last_month = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=30)
        if interaction.user.created_at > last_month:
            msg = (f"{interaction.user.name}#{interaction.user.discriminator}, is less than one month old. "
                   f"Please do not approve without further investigation.")
            await created_thread.send(msg)
        # Add temp_guest role so they can "look around"
        # Send DM so user knows we're working on it
        temp_guest_role = interaction.guild.get_role(settings['roles']['temp_guest'])
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
        self.view.msg = self.content
        await channel.send(f"{self.author} says:\n>>> {self.content}")
        self.view.stop()


class SendMessage(ui.View):
    def __init__(self, messages: List[nextcord.Message]):
        super().__init__(timeout=20.0)
        self.msg = ""
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
               style=nextcord.ButtonStyle.green,
               custom_id="thread_approve")
    async def thread_approve_button(self, button: nextcord.ui.Button, interaction: Interaction):
        dev_role = interaction.guild.get_role(settings['roles']['developer'])
        log_channel = interaction.guild.get_channel(settings['channels']['mod-log'])
        embed = nextcord.Embed(title=f"{self.member.name} Approved",
                               description=f"{interaction.user.name}#{interaction.user.discriminator} has approved new "
                                           f"member, {self.member.name}#{self.member.discriminator}",
                               color=0x00FFFF)
        # remove temp guest role
        temp_guest_role = interaction.guild.get_role(settings['roles']['temp_guest'])
        if temp_guest_role in self.member.roles:
            await self.member.remove_roles(temp_guest_role)
        # remove perms for welcome - this covers a case where they were individually
        # added with the More Info button
        await interaction.channel.parent.set_permissions(self.member, overwrite=None)
        await interaction.send(f"{interaction.user.display_name} has started the approval process.")
        sql = "SELECT role_id, role_name FROM bot_language_board ORDER BY role_name"
        fetch = await self.bot.pool.fetch(sql)
        roles = [(x['role_name'], x['role_id']) for x in fetch]
        if not self.more:  # We're approving straight away. Try and decipher language from input
            role_found = False
            for role in roles:
                if self.lang.lower().strip() == role[0].lower():
                    lang_role = interaction.guild.get_role(role[1])
                    await self.member.add_roles(lang_role)
                    self.bot.logger.info(f"Adding {lang_role.name} to user")
                    await self.member.edit(nick=f"{self.member.display_name} | {lang_role.name}")
                    embed.add_field(name="Role:", value=role[0], inline=False)
                    role_found = True
                    continue
            if not role_found:  # Couldn't figure out role, let's prompt for it
                role_view = RoleView(self.member, roles + [('other', 0)])
                content = "Please select the member's primary language role:"
                await interaction.send(content, delete_after=21.0, view=role_view, ephemeral=False)
                await role_view.wait()
                embed.add_field(name="Roles:", value=", ".join(role_view.role_list), inline=False)
            channel = interaction.guild.get_channel(GENERAL_CHANNEL_ID)
            await channel.send(f"{self.member.display_name} says:\n>>> {self.info}")
            embed.add_field(name="Message:", value=self.info, inline=False)
        else:
            # prompt for language role
            role_view = RoleView(self.member, roles + [('other', 0)])
            content = "Please select the member's primary language role:"
            await interaction.send(content, delete_after=21.0, view=role_view, ephemeral=False)
            await role_view.wait()
            embed.add_field(name="Roles:", value=", ".join(role_view.role_list), inline=False)
            confirm_view = ConfirmView()

            def disable_all_buttons():
                for _item in confirm_view.children:
                    _item.disabled = True

            self.bot.logger.info("Starting prompt for copying message to #general")
            confirm_content = "Would you like to copy a message to #general?"
            await interaction.send(content=confirm_content, ephemeral=False, view=confirm_view)
            await confirm_view.wait()
            if confirm_view.value is False or confirm_view.value is None:
                disable_all_buttons()
                await interaction.edit(view=self)
                content = "OK, then I won't do it." if confirm_view.value is False else "You're too slow! Cancelled."
                await interaction.send(content)
            else:
                try:
                    self.bot.logger.info("Disabling buttons")
                    disable_all_buttons()
                    await interaction.edit(view=self)
                    messages = [self.info]  # include the original message
                    msg_embed = nextcord.Embed(title="Please select the message to copy to #general.")
                    description = ""
                    counter = 0
                    async for message in interaction.channel.history(oldest_first=True):
                        if message.author == self.member and len(message.content) > 8:
                            description += f"\n**{counter}** - {message.content}"
                            counter += 1
                            messages.append(message)
                    msg_embed.description = description
                    msg_view = SendMessage(messages)
                    await interaction.send(embed=msg_embed, view=msg_view, ephemeral=False)
                    await msg_view.wait()
                    embed.add_field(name="Message:", value=msg_view.msg, inline=False)
                except Exception as e:
                    self.bot.logger.error(f"Message sending failed: {e}")
                    self.bot.logger.error(traceback.format_exc())
        await self.member.add_roles(dev_role)
        await log_channel.send(embed=embed)
        await interaction.channel.delete()

    @ui.button(label="More Info",
               style=nextcord.ButtonStyle.blurple,
               custom_id="thread_more")
    async def thread_info_button(self, button: nextcord.ui.Button, interaction: Interaction):
        self.bot.logger.info(f"{interaction.user.display_name} pressed the More Info button in "
                             f"{interaction.channel.name}")
        self.more = True
        # disable button in view since we don't want to use them anymore
        button.disabled = True
        await interaction.edit(view=self)
        try:
            # give the user perms to use threads in general
            await interaction.channel.parent.set_permissions(
                    self.member,
                    read_messages=True,
                    read_message_history=True,
                    send_messages_in_threads=True,
                    add_reactions=True,
                    attach_files=True
            )
            # Add user to his thread
            await interaction.channel.add_user(self.member)

            await interaction.send(f"{self.member.mention}, can you please give us a little more information?")
        except Exception as e:
            self.bot.logger.error(f"More Info button failed.\n{e}")
            self.bot.logger.error(traceback.format_exc())

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
            style=nextcord.ButtonStyle.green,
            custom_id="persistent_view:intro"
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
        if self.bot.pending_members[interaction.user.id]:
            await interaction.send("You've already introduced yourself. Please allow the admins time to "
                                   "review and respond.", ephemeral=True)
            return False
        for thread in interaction.guild.threads:
            if thread.name == f"Welcome {interaction.user.name}":
                await interaction.send("You've already introduced yourself. Please allow the admins time to "
                                       "review and respond.", ephemeral=True)
                return False
        return True


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.create_view())

    async def create_view(self):
        if getattr(self.bot, "welcome_view_set", False) is False:
            self.bot.welcome_view_set = True
            self.bot.add_view(IntroduceView(self.bot))

    @commands.command(name="recreate_welcome", hidden=True)
    @commands.has_role("Admin")
    async def recreate_welcome(self, ctx):
        """Command to re-add the welcome message and intro button"""
        welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        await welcome_channel.purge()
        await welcome_channel.send(embed=nextcord.Embed(description=WELCOME_MESSAGE, color=nextcord.Color.green()))
        await welcome_channel.send(view=IntroduceView(self.bot))


def setup(bot):
    bot.add_cog(WelcomeCog(bot))
