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
        self.clan_tag = "#CVCJR89"
        self.response_check.start()

    def cog_unload(self):
        self.response_check.cancel()

    async def fetch_as_dataframe(self, sql):
        fetch = await self.bot.pool.fetch(sql)
        columns = [key for key in fetch[0].keys()]
        return pd.DataFrame(fetch, columns=columns)

    async def get_response_times(self):
        self.bot.coc.http._cache_remove(f"/clans/{self.clan_tag.replace('#', '%23')}")
        start = time.perf_counter()
        await self.bot.coc.get_clan(self.clan_tag)
        cocpy_elapsed_time = time.perf_counter() - start
        url = "https://api.clashofclans.com/v1/clans/%23" + self.clan_tag
        api_token = settings['supercell']['home_token']
        headers = {'Accept': 'application/json', 'Authorization': 'Bearer ' + api_token}
        start = time.perf_counter()
        requests.get(url, headers=headers)
        api_elapsed_time = time.perf_counter() - start
        print(cocpy_elapsed_time)
        print(api_elapsed_time)
        return cocpy_elapsed_time, api_elapsed_time

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

        # Get current response times
        lib, api = await self.get_response_times()
        # Get historical data from database
        sql = ("SELECT check_time, cocpy_response, api_response FROM bot_responses "
               "WHERE check_time > NOW() - interval  '24 hours'"
               "ORDER BY check_time DESC")
        # fetch = await self.bot.pool.fetch(sql)
        df = await self.fetch_as_dataframe(sql)
        col1 = df['cocpy_response']
        col2 = df['api_response']
        max1 = col1.max()
        max2 = col2.max()
        y_axis_max = 1
        if max1 > 1 and max1 > max2:
            y_axis_max = math.ceil(max1)
        if max2 > 1 and max2 > max1:
            y_axis_max = math.ceil(max2)
        fig, ax = plt.subplots(figsize=(18, 9))
        ax.set_ylim([0, y_axis_max])
        ax.plot(df['check_time'], df['cocpy_response'])
        ax.plot(df['check_time'], df['api_response'])
        ax.set(xlabel="Last 24 hours", ylabel="Response Time (in secs)")
        ax.legend(["coc.py", "API"])
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
        if lib > 1 or api > 1:
            status_color = (215, 180, 0)
            status_text = "Minor Slowdown"
        if lib > 2 or api > 2:
            status_color = (100, 15, 15)
            status_text = "There is a problem!"
        draw.rectangle([50, 50, 1870, 150], fill=status_color)
        align("center", status_text, large_font, (240, 240, 240), (960, 95))
        align("left", f"coc.py response: {round_half_up(lib, decimals=5)}", small_font, (15, 15, 15), (60, 170))
        align("right", f"API response: {round_half_up(api, decimals=5)}", small_font, (15, 15, 15), (1860, 170))
        img.save("status.png")
        await ctx.send(file=discord.File('status.png'))

    @tasks.loop(minutes=15.0)
    async def response_check(self):
        """Task for monitoring coc.py and coc API response times"""
        lib, api = await self.get_response_times()
        sql = ("INSERT INTO bot_responses (check_time, cocpy_response, api_response) "
               "VALUES ($1, $2, $3)")
        await self.bot.pool.execute(sql, datetime.utcnow(), lib, api)


def setup(bot):
    bot.add_cog(Response(bot))
