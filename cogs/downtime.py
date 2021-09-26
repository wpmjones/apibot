import coc
import discord
import asyncio

from cogs.utils.send_email import SendMail
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from config import settings


def to_time(seconds):
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d > 0:
        return f"{d:.0f}d {h:.0f}h"
    elif h > 0:
        return f"{h:.0f}h {m:.0f}m"
    else:
        return f"{m:.0f}m {s:.0f}s"


class Bot:
    def __init__(self, name, bot_id, channel_id, owner, monitor, email=None):
        self.name = name
        self.bot_id = bot_id
        self.channel_id = channel_id
        self.owner = owner
        self.monitor = monitor
        self.email = email

    async def notify_down(self, bot):
        """Notify bot owner that the bot is down"""
        channel = bot.get_channel(self.channel_id)
        msg = await channel.send(f"<@{self.owner}> - It would appear that {self.name} is down.")
        bot.logger.info(f"Bot down: {self.name} - Email: {self.email}")
        # if self.email:
        #     send_email = SendMail(self.email, "Bot Owner", self.name, msg.guild.id, msg.channel.id, msg.id)
        #     send_email.send_mail_down()

    async def notify_follow_up(self, bot, downtime):
        """Notify bot owner that the bot is still down"""
        channel = bot.get_channel(self.channel_id)
        msg = await channel.send(f"<@{self.owner}> - {self.name} has been down for {downtime}")
        # if self.email:
        #     send_email = SendMail(self.email, "Bot Owner", self.name, msg.guild.id, msg.channel.id, msg.id)
        #     send_email.send_mail_followup(downtime)

    async def notify_up(self, bot, downtime):
        """Notify bot owner that the bot is back up again"""
        channel = bot.get_channel(self.channel_id)
        msg = await channel.send(f"<@{self.owner}> - {self.name} is back up.\n"
                                 f"Downtime: {downtime}")
        # if self.email:
        #     send_email = SendMail(self.email, "Bot Owner", self.name, msg.guild.id, msg.channel.id, msg.id)
        #     send_email.send_mail_up(downtime)


class Downtime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bots = []
        self.watchman.start()
        self.bot.coc.add_events(self.maintenance_start, self.maintenance_end)

    def cog_unload(self):
        self.bot.coc.remove_events(self.maintenance_start, self.maintenance_end)
        self.watchman.cancel()

    async def init_bots(self):
        """Initialize self.bots with info from database"""
        self.bots = []  # clear list of any previous entries
        sql = "SELECT bot_id, name, owner_id, channel_id, monitor, email FROM bot_owners ORDER BY name"
        fetch = await self.bot.pool.fetch(sql)
        for row in fetch:
            self.bots.append(Bot(row['name'], row['bot_id'], row['channel_id'], row['owner_id'],
                                 row['monitor'], row['email']))

    @commands.group(name="bot", invoke_without_command=True)
    async def my_bot(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
        response = ("To list bots, use `/bot list`\n"
                    "To add a bot, use `/bot add [bot_id]`\n"
                    "To toggle monitoring, use `/bot monitor [bot_id]`\n"
                    "To delete a bot, use `/bot remove [bot_id]` - FUTURE ADDITION")
        await ctx.send(response)

    @my_bot.command(name="test", hidden=True)
    async def my_bot_test(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send("Gimme a bot man")
        self.bot.logger.debug("Starting...")
        sql = "SELECT bot_id, name, owner_id, channel_id, monitor, email FROM bot_owners WHERE bot_id = $1"
        row = await self.bot.pool.fetchrow(sql, member.id)
        if not row:
            return
        bot = Bot(row['name'], row['bot_id'], row['channel_id'], row['owner_id'], row['monitor'], row['email'])
        self.bot.logger.debug("About to send notification")
        await bot.notify_down(self.bot)

    @my_bot.command(name="add")
    async def my_bot_add(self, ctx, user: discord.User = None):
        """Add a bot to be monitored.  Provide the Discord ID or mention the bot and you will be prompted for other
        information.

        **Examples:**
        /bot add 123457890
        /bot add @Minion Bot

        **Other Info:**
        You will be prompted to provide the Discord ID of the bot owner and the channel where notifications will be
        sent."""
        if not user:
            return await ctx.send("Please mention or provide a valid Discord ID for the bot.")
        if not user.bot:
            return await ctx.send(f"It would appear that {user.name} ({user.id}) is not a bot user.")

        def check_author(m):
            return m.author == ctx.author

        # ask user for bot owner ID
        try:
            await ctx.send("Please mention or enter Discord ID of the bot owner (this is the person I will "
                           "notify when the bot goes offline).")
            response = await ctx.bot.wait_for("message", check=check_author, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send("Seriously, I'm not going to wait that long. Start over!")
        try:
            if type(response.content) == discord.Member:
                owner = response
            else:
                guild = self.bot.get_guild(settings['guild']['junkies'])
                owner = guild.get_member(int(response.content))
        except ValueError:
            return await ctx.send(f"{response.content} is not a valid Discord ID.  Please start over and try again.")
        if not owner:
            return await ctx.send(f"{response.content} is not a valid Discord member of the Clash API Developers"
                                  f" server.  Please start over and try again.")
        if owner.bot:
            return await ctx.send(f"{owner.name} ({owner.id}) is a bot and cannot be added as a bot owner.")

        # ask user for channel id (for reporting)
        try:
            await ctx.send("Please mention or enter the Discord ID of the channel in which you would like me "
                           "to report outages.")
            response = await ctx.bot.wait_for("message", check=check_author, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send("I waited 60 seconds for you to talk to me. Now I'm ignoring you!")
        try:
            if type(response.content) == discord.TextChannel:
                channel = response
            else:
                channel = self.bot.get_channel(int(response.content))
        except ValueError:
            return await ctx.send(f"{response.content} is not a valid Discord ID.  Please start over and try again.")
        if not channel:
            return await ctx.send(f"{response.content} is not a valid Discord channel.  Please start over and try again.")
        if channel.guild.id != settings['guild']['junkies']:
            return await ctx.send(f"{channel.name} ({channel.id}) is not a valid channel on Clash API Developers.  "
                                  f"I am only able to report things on that server.  Please start over and try "
                                  f"again.")

        sql = ("INSERT INTO bot_owners (bot_id, name, owner_id, channel_id) "
               "VALUES ($1, $2, $3, $4)")
        await self.bot.pool.execute(sql, user.id, user.name, owner.id, channel.id)
        await ctx.send(f"Congratulations! You have successfully added {user.name} to the bot monitoring system. "
                       f"If there is an outage that lasts more than 60 seconds, I will ping {owner.display_name} in "
                       f"{channel.mention}.  To toggle monitoring, please use `/bot monitor {user.id}` or "
                       f"`/bot monitor @{user.display_name}#{user.discriminator}`.")

    @my_bot.command(name="list")
    async def my_bot_list(self, ctx):
        """List the bots that are being monitored.

        **Example:**
        /bot list"""
        await self.init_bots()
        embed = discord.Embed(title="Bots that are configured for monitoring")
        for bot in self.bots:
            owner = self.bot.get_user(bot.owner)
            channel = self.bot.get_channel(bot.channel_id)
            embed.add_field(name=f"{bot.name}",
                            value=f"Bot ID: {bot.bot_id}\n"
                                  f"Owner: {owner.mention}\n"
                                  f"Channel: {channel.mention}\n"
                                  f"Monitoring: {bot.monitor}",
                            inline=True)
        await ctx.send(embed=embed)

    @my_bot.command(name="monitor")
    async def my_bot_monitor(self, ctx, bot: discord.Member = None):
        """Toggle monitoring for the specified bot

        **Example:**
        /bot monitor 1234567890
        /bot monitor @Ruby
        """
        if not bot:
            return await ctx.send("Please provide a Discord ID or mention the bot in question.")
        sql = ("UPDATE bot_owners "
               "SET monitor = NOT monitor "
               "WHERE bot_id = $1 "
               "RETURNING monitor")
        monitor = await self.bot.pool.fetchval(sql, bot.id)
        if monitor:
            new_monitor = "ON"
        else:
            new_monitor = "OFF"
        await ctx.send(f"Monitoring for {bot.display_name} is now set to {new_monitor}.")

    @commands.Cog.listener()
    async def on_member_update(self, before, member):
        """Task for monitoring API bots
        Downtime is stored in the bot_downtime table of postgresql
        """
        conn = self.bot.pool
        # Only monitor updates seen in our Discord server
        if member.guild.id != settings['guild']['junkies']:
            return
        # Is this user a bot?
        if not member.bot:
            return
        # Is this update a status change?
        if before.status == member.status:
            return
        sql = "SELECT bot_id, name, owner_id, channel_id, monitor, email FROM bot_owners WHERE bot_id = $1"
        row = await conn.fetchrow(sql, member.id)
        if not row:
            return
        bot = Bot(row['name'], row['bot_id'], row['channel_id'], row['owner_id'], row['monitor'], row['email'])
        # Are we currently monitoring this bot?
        if not bot.monitor:
            return
        now = datetime.utcnow()
        offline_sql = "SELECT offline_start FROM bot_downtime WHERE online = False AND bot_id = $1"
        reported_sql = ("UPDATE bot_downtime "
                        "SET online = True, reported = True, offline_end = $1 "
                        "WHERE bot_id = $2 AND reported = False")
        insert_sql = ("INSERT INTO bot_downtime (bot_id, online, offline_start, last_notification) "
                      "VALUES ($1, False, $2, $3)")
        offline_start = await conn.fetchval(offline_sql, member.id)
        if offline_start:
            # simply tells us that the bot is marked offline in the database
            if member.status == discord.Status.online:
                # bot is back online
                downtime = to_time((now - offline_start).total_seconds())
                try:
                    await bot.notify_up(self.bot, downtime)
                    self.bot.logger.info(f"{bot.name} is back online and notification sent. "
                                         f"Downtime: {downtime}")
                except discord.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")
                await conn.execute(reported_sql, now, bot.bot_id)
        else:
            if member.status != discord.Status.online:
                # bot is offline for the first time
                # pause 60 seconds to make sure it's a real outage
                await asyncio.sleep(65)
                check = member.guild.get_member(member.id)
                if check.status == discord.Status.online:
                    # bot is back online, no need to report anything
                    return
                await conn.execute(insert_sql, bot.bot_id, now, now)
                try:
                    await bot.notify_down(self.bot)
                    self.bot.logger.info(f"{bot.name} is down and notification has been sent.")
                except discord.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")

    @tasks.loop(hours=24.0)
    async def watchman(self):
        """Task for monitoring API bots
        Downtime is stored in the bot_downtime table of postgresql
        Bot owner is notified once every 24 hours until the bot comes back online
        """
        conn = self.bot.pool
        now = datetime.utcnow()
        update_sql = "UPDATE bot_downtime SET last_notification = $1 WHERE bot_id = $2 AND online = False"
        sql = "SELECT offline_start, last_notification FROM bot_downtime WHERE bot_id = $1 AND online = False"
        await self.init_bots()
        for bot in self.bots:
            if not bot.monitor:
                continue
            fetch = await conn.fetchrow(sql, bot.bot_id)
            if not fetch:
                continue
            offline_start = fetch['offline_start']
            last_notification = fetch['last_notification']
            if offline_start and last_notification < now - timedelta(hours=23.0):
                downtime = to_time((now - offline_start).total_seconds())
                try:
                    await bot.notify_follow_up(self.bot, downtime)
                except discord.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")
                await conn.execute(update_sql, now, bot.bot_id)

    @watchman.before_loop
    async def before_watchman(self):
        await self.bot.wait_until_ready()

    @coc.ClientEvents.maintenance_start()
    async def maintenance_start(self):
        channel = self.bot.get_channel(settings['channels']['general'])
        await channel.send("The Clash API has entered maintenance mode.")

    @coc.ClientEvents.maintenance_completion()
    async def maintenance_end(self, time_started):
        channel = self.bot.get_channel(settings['channels']['general'])
        await channel.send("Maintenance has ended. Get back to work!")


def setup(bot):
    bot.add_cog(Downtime(bot))
