import asyncio
import logging

import discord

from config import Config
from database import Database
from discord_client import DiscordClient
from parser_client import ParserClient

logging.basicConfig(level=logging.INFO)


async def main():
    database = Database("database.sqlite3")

    discord_client = DiscordClient(database, intents=discord.Intents.default())
    parser_client = ParserClient(database, discord_client)
    discord_client.parser_client = parser_client

    await asyncio.gather(
        parser_client.start(Config.SELFBOT_TOKEN),
        discord_client.start(Config.BOT_TOKEN),
    )

    database.close()


if __name__ == "__main__":
    asyncio.run(main())
