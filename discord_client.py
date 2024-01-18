import asyncio
import io
import json
import math
import time
from datetime import datetime

import discord
from discord.ext.commands import Bot
from pyppeteer import launch

from config import Config
from database import Database
from finviz_api import get_stock_data, login_finviz

browser = None
try:
    with open("cookies.json", "r") as file:
        cookies = json.loads(file.read())
except:
    cookies = None

list_cooldown = {}


async def cooldown(id: int, user_time: int = 3, name: str = None):
    key = f"{id}_{name if name else ''}"

    if key in list_cooldown and time.time() - list_cooldown[key] < user_time:
        times = abs(int((time.time() - list_cooldown[key]) - user_time))
        return times
    else:
        list_cooldown[key] = time.time()
        return True


class DiscordClient(Bot):
    def __init__(self, database: Database, **kwargs):
        super().__init__(command_prefix="/", **kwargs)
        self.database = database
        self.parser_client = None
        self.setup_commands()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

        try:
            login_finviz()
            print("Logged in Finviz.")
        except Exception as ex:
            print(ex)
            print("Failed to log in Finviz.")

        guild = discord.Object(id=Config.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Synced commands for the guild.")
        global browser
        if not browser:
            browser = await launch(headless=True)
            page = await browser.newPage()
            if cookies:
                await page.setCookie(*cookies)
                await page.close()
            else:
                await browser.close()

    def setup_commands(self):
        @self.tree.command(name="add-parse-channel")
        async def add_parse_channel(
            interaction: discord.Interaction,
            post_channel_id: str,
            parse_channel_id: str,
        ):
            await interaction.response.defer(ephemeral=True)

            try:
                self.database.add_parse_channel(
                    int(post_channel_id), int(parse_channel_id)
                )
                await interaction.followup.send("✅ Канал был успешно добавлен.")
            except Exception as ex:
                print(ex)
                await interaction.followup.send("❌ Не удалось добавить канал.")

        @self.tree.command(name="remove-parse-channel")
        async def remove_parse_channel(
            interaction: discord.Interaction,
            post_channel_id: str,
            parse_channel_id: str,
        ):
            await interaction.response.defer(ephemeral=True)

            try:
                self.database.remove_parse_channel(
                    int(post_channel_id), int(parse_channel_id)
                )
                await interaction.followup.send("✅ Канал был успешно удален.")
            except Exception as ex:
                print(ex)
                await interaction.followup.send("❌ Не удалось удалить канал.")

        @self.tree.command(name="parse-list")
        async def parse_list(interaction: discord.Interaction, page: int = 1):
            if page < 1:
                return await interaction.response.send_message(
                    "❌ Неверный номер страницы.", ephemeral=True
                )

            await interaction.response.defer(ephemeral=True)

            ITEMS_PER_PAGE = 15

            parse_channels = self.database.get_all_parse_channels()
            page_parse_channels = parse_channels[
                ITEMS_PER_PAGE * (page - 1) : ITEMS_PER_PAGE * page
            ]

            if len(page_parse_channels) == 0:
                return await interaction.followup.send("❌ Эта страница пуста.")

            total_pages = math.ceil(len(parse_channels) / ITEMS_PER_PAGE)
            discord_page_parse_channels = []

            for parse_channel in parse_channels:
                discord_post_channel = self.get_channel(parse_channel[0])
                discord_parse_channel = self.parser_client.get_channel(parse_channel[1])
                discord_page_parse_channels.append(
                    (discord_post_channel, discord_parse_channel)
                )

            parse_channels_visualization = "\n".join(
                [
                    f"**#{parse_channel[1].name}** ({parse_channel[1].id}) -> **#{parse_channel[0].name}** ({parse_channel[0].id})"
                    for parse_channel in discord_page_parse_channels
                ]
            )
            response_content = f"**Текущие соединения** (Страница {page}, всего страниц - {total_pages}):\n\n{parse_channels_visualization}"

            await interaction.followup.send(response_content)

        @self.tree.command(name="parse-reset")
        async def parse_reset(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            self.database.drop_all_parse_channels()
            await interaction.followup.send("✅ Все соединения были успешно сброшены.")

        @self.tree.command(name="stock")
        async def stock(interaction: discord.Interaction, name: str):
            await interaction.response.defer(ephemeral=True)

            data = get_stock_data(name)

            if data.get("error") == "no data":
                return await interaction.followup.send("❌ Couldn't fetch the data.")

            embed = discord.Embed(
                color=discord.Color.random(), timestamp=datetime.now()
            )
            view = discord.ui.View()

            view.add_item(discord.ui.Button(label="📰 News", url=data["Last News URL"]))
            view.add_item(discord.ui.Button(label="📈 TradingView", url=data["URL"]))

            keys = [
                "Market Cap",
                "Price",
                "Avg Volume",
                "Shortable",
                "Shs Float",
                "Optionable",
                "Insider Own",
                "Inst Own",
                "Short Float / Ratio",
                "Target Price",
            ]

            for i in range(len(keys)):
                embed.add_field(name=keys[i], value=data[keys[i]], inline=True)

            embed.set_image(url=data["Chart URL"])

            await interaction.followup.send(embed=embed, view=view)

        @self.tree.command(name="future")
        async def future(interaction: discord.Interaction, symbol: str):
            await interaction.response.defer()
            check_cooldown = await cooldown(
                id=interaction.user.id, user_time=10, name="tradingview"
            )
            if check_cooldown != True:
                return await interaction.followup.send(
                    f"Просмотр будет доступен через {check_cooldown}с."
                )
            global browser
            page = await browser.newPage()
            await page.setViewport({"width": 1920, "height": 1080})
            await page.setCookie(*cookies)
            await page.goto(
                f"https://www.tradingview.com/chart/?symbol={symbol}&interval=60",
                {"timeout": 600000},
            )
            await asyncio.sleep(3)
            element = await page.waitForSelector(".chart-container-border")
            box = await element.boundingBox()
            chart_screenshot = await page.screenshot({"clip": box})
            buffer = io.BytesIO(chart_screenshot)
            buffer.seek(0)
            await interaction.followup.send(
                file=discord.File(buffer, filename="chart.png")
            )
            buffer.close()
            await page.close()
