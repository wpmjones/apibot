import discord
import pandas as pd
import math
import matplotlib.pyplot as plt
import requests
import time

from datetime import datetime
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from config import settings


class Response(commands.Cog):
    """Cog to check coc.py response time and report if things are slow"""
    def __init__(self, bot):
        self.bot = bot
        self.clan_tag = "CVCJR89"
        self.player_tag = "PJU928JR"
        self.war_tag = "UGJPVJR"   # Not an actual war tag, just a clan we will use to search for wars
        self.response_check.start()

    def cog_unload(self):
        self.response_check.cancel()

    async def fetch_as_dataframe(self, sql):
        fetch = await self.bot.pool.fetch(sql)
        columns = [key for key in fetch[0].keys()]
        return pd.DataFrame(fetch, columns=columns)

    async def get_response_times(self):
        # self.bot.coc.http._cache_remove(f"/clans/{self.clan_tag.replace('#', '%23')}")
        # start = time.perf_counter()
        # await self.bot.coc.get_clan(self.clan_tag)
        # cocpy_elapsed_time = time.perf_counter() - start
        api_url = "https://api.clashofclans.com/v1/"
        clan_url = api_url + "clans/%23" + self.clan_tag
        player_url = api_url + "players/%23" + self.player_tag
        war_url = api_url + "clans/%23" + self.war_tag + "/currentwar"
        api_token = settings['supercell']['home_token']
        headers = {'Accept': 'application/json', 'Authorization': 'Bearer ' + api_token}
        # clan endpoint
        start = time.perf_counter()
        requests.get(clan_url, headers=headers)
        clan_elapsed_time = (time.perf_counter() - start) * 100
        # player endpoint
        start = time.perf_counter()
        requests.get(player_url, headers=headers)
        player_elapsed_time = (time.perf_counter() - start) * 100
        # current war endpoint
        start = time.perf_counter()
        requests.get(war_url, headers=headers)
        war_elapsed_time = (time.perf_counter() - start) * 100
        return clan_elapsed_time, player_elapsed_time, war_elapsed_time

    @commands.command(name="response")
    async def response_info(self, ctx):
        """Report information on api response times"""

        def align(alignment, text, font, color, position):
            if not isinstance(text, str):
                text = str(text)
            text_width, text_height = draw.textsize(text, font)
            if alignment == "center":
                x = position[0] - (text_width / 2)
            elif alignment == "right":
                x = position[0] - text_width
            else:
                x = position[0]
            y = position[1] - (text_height / 2)
            draw.text((x, y), text, fill=color, font=font)

        def round_half_up(n, decimals=0):
            multiplier = 10 ** decimals
            return math.floor(n * multiplier + 0.5) / multiplier

        async with ctx.typing():
            # Get current response times
            clan, player, war = await self.get_response_times()
            # Get historical data from database
            sql = ("SELECT check_time, clan_response, player_response, war_response FROM bot_responses "
                   "WHERE check_time > NOW() - interval  '24 hours'"
                   "ORDER BY check_time DESC")
            # fetch = await self.bot.pool.fetch(sql)
            df = await self.fetch_as_dataframe(sql)
            col1 = df['clan_response']
            col2 = df['player_response']
            col3 = df['war_response']
            max_value_list = [col1.max(), col2.max(), col3.max()]
            max_value = max(max_value_list)
            if max_value > 100:
                y_axis_max = math.ceil(max_value)
            else:
                y_axis_max = 100
            fig, ax = plt.subplots(figsize=(18, 9))
            ax.set_ylim([0, y_axis_max])
            ax.plot(df['check_time'], df['clan_response'])
            ax.plot(df['check_time'], df['player_response'])
            ax.plot(df['check_time'], df['war_response'])
            ax.set(xlabel="Last 24 hours", ylabel="Response Time (ms)")
            ax.legend(["Clan Endpoint", "Player Endpoint", "War Endpoint"])
            ax.grid()
            ax.set_xticklabels([])
            fig.savefig("plot.png")
            # prep data for display
            large_font = ImageFont.truetype("fonts/Aileron-Bold.otf", 54)
            small_font = ImageFont.truetype("fonts/Aileron-Regular.otf", 24)
            img = Image.new("RGB", (1920, 1080), "white")
            draw = ImageDraw.Draw(img)
            plot_img = Image.open("plot.png")
            img.paste(plot_img, (60, 175))
            status_color = (15, 100, 15)   # Green
            status_text = "All is well"
            if clan > 100 or player > 100 or war > 100:
                status_color = (215, 180, 0)
                status_text = "Minor Slowdown"
            if clan > 200 or player > 200 or war > 200:
                status_color = (100, 15, 15)
                status_text = "There is a problem!"
            draw.rectangle([50, 50, 1870, 150], fill=status_color)
            align("center", status_text, large_font, (240, 240, 240), (960, 95))
            align("left", f"Clan Endpoint: {round_half_up(clan, decimals=2)}ms", small_font, (15, 15, 15), (60, 175))
            align("center", f"Player Endpoint: {round_half_up(player, decimals=2)}ms", small_font, (15, 15, 15), (960, 175))
            align("right", f"War Endpoint: {round_half_up(war, decimals=2)}ms", small_font, (15, 15, 15), (1860, 175))
            img.save("status.png")
            await ctx.send(file=discord.File('status.png'))

    @tasks.loop(minutes=15.0)
    async def response_check(self):
        """Task for monitoring coc.py and coc API response times"""
        clan, player, war = await self.get_response_times()
        sql = ("INSERT INTO bot_responses (check_time, clan_response, player_response, war_response) "
               "VALUES ($1, $2, $3, $4)")
        await self.bot.pool.execute(sql, datetime.utcnow(), clan, player, war)


def setup(bot):
    bot.add_cog(Response(bot))
