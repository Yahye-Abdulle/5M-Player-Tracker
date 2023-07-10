import asyncio
from http import client
import http.client
import json
import logging
import os
import platform
import random
import sys

import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from datetime import datetime
from urllib.request import Request, urlopen

import json

import exceptions

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        config = json.load(file)

"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


Default Intents:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True # `message_content` is required to get the content of the messages
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

Privileged Intents (Needs to be enabled on developer portal of Discord), please use them only if you need them:
intents.members = True
intents.message_content = True
intents.presences = True
"""

intents = discord.Intents.default()

"""
Uncomment this if you want to use prefix (normal) commands.
It is recommended to use slash commands and therefore not use prefix commands.

If you want to use prefix commands, make sure to also enable the intent below in the Discord developer portal.
"""
intents.messages = True

bot = Bot(command_prefix=commands.when_mentioned_or(
    config["prefix"]), intents=intents, help_command=None)

# Setup both of the loggers
class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(
    filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{")
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)
bot.logger = logger


async def init_db():
    async with aiosqlite.connect(f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db") as db:
        with open(f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql") as file:
            await db.executescript(file.read())
        await db.commit()


"""
Create a bot variable to access the config file in cogs so that you don't need to import it every time.

The config is available using the following code:
- bot.config # In this file
- self.bot.config # In cogs
"""
bot.config = config
guild_id = 0

@bot.event
async def on_ready() -> None:
    """
    The code in this event is executed when the bot is ready.
    """
    bot.logger.info(f"Logged in as {bot.user.name}")
    bot.logger.info(f"discord.py API version: {discord.__version__}")
    bot.logger.info(f"Python version: {platform.python_version()}")
    bot.logger.info(
        f"Running on: {platform.system()} {platform.release()} ({os.name})")
    bot.logger.info("-------------------")
    if config["sync_commands_globally"]:
        bot.logger.info("Syncing commands globally...")
        await bot.tree.sync()

@bot.event
async def on_guild_join(guild):
    path = "serverSetting/" + str(guild.id)
    try:
        global guild_id
        guild_id = guild.id
        os.makedirs(path)
        print("Making dir:" + path)
        json_dict = {
            "guild_id": guild.id,
            "guild_data": {
                    "normal_data": {
                    "message_id": 0,
                    "old_message_id": 0,
                    "serverInviteId": "",
                    "channelId": 0
                },
                "embed_data": {
                    "embedTitle": ":pencil: Server Statistics",
                    "embedServerName": "",
                    "embedGangName": ""      
                }
            }
        }
        json_object = json.dumps(json_dict, indent=4)
        with open(f"./serverSetting/{str(guild.id)}/settings.json", "w") as f:
            f.write(json_object)
    # if the dir exist
    except FileExistsError:
        print("Dir exist " + path)

# @tasks.loop(minutes=1.0)
# async def status_task() -> None:
#     """
#     Setup the game status task of the bot.
#     """
#     statuses = ["", "with Krypton!", "with humans!"]
#     await bot.change_presence(activity=discord.Game(random.choice(statuses)))


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    The code in this event is executed every time someone sends a message, with or without the prefix

    :param message: The message that was sent.
    """
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_command_completion(context: Context) -> None:
    """
    The code in this event is executed every time a normal command has been *successfully* executed.

    :param context: The context of the command that has been executed.
    """
    full_command_name = context.command.qualified_name
    split = full_command_name.split(" ")
    executed_command = str(split[0])
    if context.guild is not None:
        bot.logger.info(
            f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})")
    else:
        bot.logger.info(
            f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs")


@bot.event
async def on_command_error(context: Context, error) -> None:
    """
    The code in this event is executed every time a normal valid command catches an error.

    :param context: The context of the normal command that failed executing.
    :param error: The error that has been faced.
    """
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        hours, minutes = divmod(minutes, 60)
        hours = hours % 24
        embed = discord.Embed(
            description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
            color=0xE02B2B
        )
        await context.send(embed=embed)
    elif isinstance(error, exceptions.UserBlacklisted):
        """
        The code here will only execute if the error is an instance of 'UserBlacklisted', which can occur when using
        the @checks.not_blacklisted() check in your command, or you can raise the error by yourself.
        """
        embed = discord.Embed(
            description="You are blacklisted from using the bot!",
            color=0xE02B2B
        )
        await context.send(embed=embed)
        bot.logger.warning(
            f"{context.author} (ID: {context.author.id}) tried to execute a command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is blacklisted from using the bot.")
    elif isinstance(error, exceptions.UserNotOwner):
        """
        Same as above, just for the @checks.is_owner() check.
        """
        embed = discord.Embed(
            description="You are not the owner of the bot!",
            color=0xE02B2B
        )
        await context.send(embed=embed)
        bot.logger.warning(
            f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot.")
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            description="You are missing the permission(s) `" + ", ".join(
                error.missing_permissions) + "` to execute this command!",
            color=0xE02B2B
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            description="I am missing the permission(s) `" + ", ".join(
                error.missing_permissions) + "` to fully perform this command!",
            color=0xE02B2B
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="Error!",
            # We need to capitalize because the command arguments have no capital letter in the code.
            description=str(error).capitalize(),
            color=0xE02B2B
        )
        await context.send(embed=embed)
    else:
        raise error


async def load_cogs() -> None:
    """
    The code in this function is executed whenever the bot will start.
    """
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"cogs.{extension}")
                bot.logger.info(f"Loaded extension '{extension}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                bot.logger.error(
                    f"Failed to load extension {extension}\n{exception}")            

# embedTitle = ":pencil: Server Statistics"
# embedServerName = ""
# embedGangName = ""
# embedServerCount = ""
embedGangCount = []
gangDiscordId = []
serverDiscordId = []
# message_id = 0
# old_message_id = 0
# serverIviteId = ""
# channelId = 0


def getJsonData():
    with open(f"./serverSetting/{str(guild_id)}/settings.json", "r") as f:
        return json.loads(f.read())        

def getData():
    def get_page_content(url, head):
        """
        Function to get the page content
        """
        req = Request(url, headers=head)
        return urlopen(req)
    
    url = 'https://servers-frontend.fivem.net/api/servers/single/'+getJsonData()['guild_data']['normal_data']['serverInviteId']
    head = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    }

    data = get_page_content(url, head).read()
    newData = data.decode("utf-8").replace("'", '"')
    jsonData = json.loads(newData)
    realData = json.loads(json.dumps(jsonData))

    return realData

def getPlayerCount():
    data_json = getData()['Data']
    return f"{data_json['clients']}/{data_json['sv_maxclients']}"

def getGangCount():
    global serverDiscordId
    global embedGangCount

    data_json = getData()['Data']['players']
    
    for i in range(len(data_json)):
        for j in range(len(data_json[i]['identifiers'])):
            if 'discord' in (data_json[i]['identifiers'][j]):
                serverDiscordId.append(int(data_json[i]['identifiers'][j].split(':')[1]))

    for i in range(len(gangDiscordId)):
        if gangDiscordId[i] in serverDiscordId and gangDiscordId[i] not in embedGangCount:
            embedGangCount.append(gangDiscordId[i])

    return embedGangCount

@bot.command()
async def help(ctx):
    global guild_id
    guild_id = ctx.guild.id
    embed=discord.Embed(title=":book: Help Documentation", description="Execute the following commands in order to set up the bot!",color=0xffffff)

    embed.add_field(name="!setinvite [server invite code] e.g. zb8lmd", value="", inline=False)
    embed.add_field(name="!setchannel [tag channel] e.g. #general", value="", inline=False)
    embed.add_field(name="!setup [server name] [gang name]", value="", inline=False)
    embed.add_field(name="!role [tag universal role of members] e.g. @role", value="", inline=False)
    embed.add_field(name="!run", value="", inline=False)
    embed.add_field(name="", value="server & gang name and role must be set up to execute run", inline=False)
    embed.add_field(name="", value="dont include square brackets in the setup and role", inline=False)

    embed.set_footer(text=f"Created by yne#2654.")

    await ctx.send(embed=embed)

@bot.command()
async def reset(ctx):
    json_dict = {
            "guild_id": ctx.guild.id,
            "guild_data": {
                    "normal_data": {
                    "message_id": 0,
                    "old_message_id": 0,
                    "serverInviteId": "",
                    "channelId": 0
                },
                "embed_data": {
                    "embedTitle": ":pencil: Server Statistics",
                    "embedServerName": "",
                    "embedGangName": ""      
                }
            }
        }
    json_object = json.dumps(json_dict, indent=4)
    with open(f"./serverSetting/{str(ctx.guild.id)}/settings.json", "r+") as f:
        f.truncate()
        f.write(json_object)

@bot.command()
async def setinvite(ctx, serverId):
    global guild_id
    guild_id = ctx.guild.id
    with open(f"./serverSetting/{str(ctx.guild.id)}/settings.json", "r+") as jsonFile:
        data = json.load(jsonFile)

        data['guild_data']['normal_data']['serverInviteId'] = serverId

        jsonFile.seek(0)  # rewind
        json.dump(data, jsonFile, indent=4)
        jsonFile.truncate()

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    global guild_id
    guild_id = ctx.guild.id
    with open(f"./serverSetting/{str(ctx.guild.id)}/settings.json", "r+") as jsonFile:
        data = json.load(jsonFile)

        data['guild_data']['normal_data']['channelId'] = channel.id

        jsonFile.seek(0)  # rewind
        json.dump(data, jsonFile, indent=4)
        jsonFile.truncate()

@bot.command()
async def setup(ctx, *args):
    global guild_id
    guild_id = ctx.guild.id
    embedServerName = (args[0])
    embedGangName = (args[1])
    with open(f"./serverSetting/{str(ctx.guild.id)}/settings.json", "r+") as jsonFile:
        data = json.load(jsonFile)

        data['guild_data']['embed_data']['embedServerName'] = embedServerName
        data['guild_data']['embed_data']['embedGangName'] = embedGangName

        jsonFile.seek(0)  # rewind
        json.dump(data, jsonFile, indent=4)
        jsonFile.truncate()

    #await ctx.send(ctx.message.guild.name)

@bot.command()
async def role(ctx, role: discord.Role):
    global guild_id
    guild_id = ctx.guild.id
    global gangDiscordId
    if role in ctx.message.author.roles:
        gangDiscordId.append(ctx.message.id)
    for user in ctx.guild.members:
        if role in user.roles:
            gangDiscordId.append(user.id)

@bot.command()
async def run(ctx):
    global guild_id
    guild_id = ctx.guild.id
    getJsonDataArr = getJsonData()
    if getJsonDataArr['guild_data']['embed_data']['embedServerName'] == "" or getJsonDataArr['guild_data']['embed_data']['embedGangName'] == "" or getJsonDataArr['guild_data']['normal_data']['channelId'] == 0 or getJsonDataArr['guild_data']['normal_data']['serverInviteId'] == 0: await ctx.send('Please setup the required details!')
    else:
        embedServerCount = getPlayerCount()
        embedGangCount = getGangCount()
        now = datetime.now()
        embed=discord.Embed(title=f"{getJsonDataArr['guild_data']['embed_data']['embedTitle']}", color=0xffffff)

        embed.add_field(name=f"{getJsonDataArr['guild_data']['embed_data']['embedServerName']} Player Count: {embedServerCount}", value="", inline=False)
        embed.add_field(name=f"In City {getJsonDataArr['guild_data']['embed_data']['embedGangName']} Count: {len(embedGangCount)}", value="", inline=False)

        embed.set_footer(text=f"Created by yne#2654. Last refresh at {now}")

        if (getJsonDataArr['guild_data']['normal_data']['old_message_id'] != 0 and ctx.channel.id == getJsonDataArr['guild_data']['normal_data']['channelId']) :
            run_count_background.stop()
            msg = await ctx.fetch_message(getJsonDataArr['guild_data']['normal_data']['old_message_id'])
            await msg.delete()            

        message = await ctx.send(embed=embed)
        with open(f"./serverSetting/{str(ctx.guild.id)}/settings.json", "r+") as jsonFile:
            data = json.load(jsonFile)

            data['guild_data']['normal_data']['message_id'] = message.id
            data['guild_data']['normal_data']['old_message_id'] = message.id

            jsonFile.seek(0)  # rewind
            json.dump(data, jsonFile, indent=4)
            jsonFile.truncate()

        if not run_count_background.is_running():
            run_count_background.start()

@tasks.loop(seconds=60.0)
async def run_count_background():
    getJsonDataArr = getJsonData()
    embedServerCount = getPlayerCount()
    embedGangCount = getGangCount()
    now = datetime.now()
    newEmbed=discord.Embed(title=f"{getJsonDataArr['guild_data']['embed_data']['embedTitle']}", color=0xffffff)

    newEmbed.add_field(name=f"{getJsonDataArr['guild_data']['embed_data']['embedServerName']} Player Count: {embedServerCount}", value="", inline=False)
    newEmbed.add_field(name=f"In City {getJsonDataArr['guild_data']['embed_data']['embedGangName']} Count: {len(embedGangCount)}", value="", inline=False)
    # for i in range(len(embedGangCount)):
    #     newEmbed.add_field(name="", value=f"@{await bot.fetch_user(embedGangCount[i])}", inline=False)

    newEmbed.set_footer(text=f"Created by yne#2654. Last refresh at {now}")
    
    message = await bot.get_channel(getJsonDataArr['guild_data']['normal_data']['channelId']).fetch_message(getJsonDataArr['guild_data']['normal_data']['message_id'])
    await message.edit(embed = newEmbed)

asyncio.run(init_db())
#asyncio.run(load_cogs())
#asyncio.run(init_json())
bot.run(config["token"])
