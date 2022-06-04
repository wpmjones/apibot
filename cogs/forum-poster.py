import aiohttp
import nextcord
import re

from bs4 import BeautifulSoup
from config import settings
from nextcord.ext import commands, tasks
from nextcord.utils import find

API_SUBFORUM_URL = "https://forum.supercell.com/forumdisplay.php/123-Clash-of-Clans-API"
FORUM_BASE_URL = "https://forum.supercell.com/"
FORUM_POSTS_CHANNEL_ID = settings['channels']['forum-poster']


class ForumPoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_post_id = None
        self.session = aiohttp.ClientSession()
        self.forum_post_loop.start()

    def cog_unload(self):
        self.forum_post_loop.cancel()

    @nextcord.utils.cached_property
    def channel(self):
        return self.bot.get_channel(FORUM_POSTS_CHANNEL_ID)

    @commands.command(name="repost", hidden=True)
    async def repost_thread(self, ctx):
        """When this cog starts, it marks the most recent thread as last_post_id. Sometimes, we will want it
        to post the most recent thread (e.g. there were errors preventing it from posting)."""
        self.last_post_id = "something else"
        await ctx.message.add_reaction('\u2705')

    @tasks.loop(minutes=5.0)
    async def forum_post_loop(self):
        try:
            await self.bot.wait_until_ready()
            self.bot.logger.debug("running forum-post loop")

            async with self.session.get(API_SUBFORUM_URL) as resp:
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            recent_posts = soup.find(id="threads")
            if not recent_posts:
                self.bot.logger.warning("couldn't find any posts for the subreddit")
                return

            post = recent_posts.find("li", class_="threadbit")
            post_id = post["id"]
            if self.last_post_id is None:
                self.last_post_id = post_id
                self.bot.logger.debug(f"running forum-post for the first time, setting last_post_id to {post_id}")
                return
            elif self.last_post_id == post_id:
                self.bot.logger.debug("forum-post didn't find a new post, returning.")
                return

            # we have ourselves either a new post or a new comment
            number_of_comments = find(lambda x: x.isdigit(), post.li.text)
            title = post.find("h3", class_="threadtitle")
            author = post.find("div", class_="author").span.a
            stats = post.find("ul", class_="threadstats td alt")

            async with self.session.get(FORUM_BASE_URL + title.a['href']) as resp:
                print(resp.charset)
                html = await resp.text()  # removed (encoding="utf-8")

            post_soup = BeautifulSoup(html, "html.parser")

            if number_of_comments == "0":
                prefix = f"**Author: **[{author.text}]({FORUM_BASE_URL + author['href']})\n\n"
                content = post_soup.find("div", class_="content").get_text(strip=True)
                # limit size of content if over 2048 (with prefix)
                if len(prefix) + len(content) > 2048:
                    content = content[:2045 - len(prefix)] + "..."

                embed = nextcord.Embed(
                    colour=nextcord.Colour.green(),
                    title=title.get_text(strip=True),
                    url=FORUM_BASE_URL + title.a['href'],
                    description=prefix + content,
                )

            else:
                comment = post_soup.find_all("div", class_="postdetails")[-1]
                comment_meta, _, author, *_ = comment.parent.find_all("a")
                prefix = f"**Author: **[{author.text}]({FORUM_BASE_URL + author['href']})\n" \
                         f"**Original Post Title: {title.get_text(strip=True)}\n\n"
                # limit size of content if over 2048 (with prefix)
                content = comment.blockquote.get_text(strip=True)
                if len(prefix) + len(content) > 2048:
                    content = content[:2045 - len(prefix)] + "..."
                embed = nextcord.Embed(
                    colour=0xA9EAC5,
                    title=f"New Comment",
                    url=FORUM_BASE_URL + comment_meta['href'],
                    description=prefix + content
                )

            embed.set_footer(
                text=", ".join(re.sub(r'\s+', '', t) for t in stats.stripped_strings if "Rating" not in t)
            )
            self.bot.logger.info(f"sending a new post/comment to discord, with info {embed.to_dict()}")
            await self.channel.send(embed=embed)

            self.bot.logger.debug(f"setting last_post_id to {post_id}")
            self.last_post_id = post_id
        except:
            self.bot.logger.exception("forum-post loop encountered an exception")


def setup(bot):
    bot.add_cog(ForumPoster(bot))
