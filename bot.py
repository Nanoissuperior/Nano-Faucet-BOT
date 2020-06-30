from config import *

import json
import random
import math
import re

import discord
from discord.ext import commands

import asyncio
import aiohttp
import aioredis
from tinydb import where
from aiotinydb import AIOTinyDB

loop = asyncio.get_event_loop()

pool = aioredis.create_pool(
        'redis://localhost',
        minsize=1, maxsize=2,
        loop = loop
)

db = AIOTinyDB(DB_NAME)

activity = discord.Activity(type=discord.ActivityType.watching, name=ACTIVITY_NAME)
bot = commands.Bot(command_prefix='*')
bot.remove_command("help")

# Wrapper for aiohttp POST
async def post(js_data):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(NODE_RPC_URL, json=js_data) as response:
                return await response.json()
        except Exception as e:
            print(f"Error trying to POST {js_data}: {e}")
            return None

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=activity)
    global pool
    pool = await pool
    print('I am online!')

@bot.command()
async def help(ctx):
    await ctx.send("""Available commands:
        *blocks - shows current block count.
        *faucet ``nano_address``  - will send some Nano to the address you specify.
        """
    )

@bot.command()
async def blocks(ctx):
    """Print the block count from the node"""
    result = await post({"action" : "block_count"})
    if result and "count" in result:
        await ctx.send(f"""```
        Blocks: {result['count']}
        Uncemented: {int(result['count']) - int(result['cemented'])}```""")

def can_use_faucet(ctx):
    if ALLOWED_ROLE:
        return ALLOWED_ROLE in [role.name for role in ctx.message.author.roles]
    else:
        return str(ctx.message.channel) == ALLOWED_CHANNEL

@bot.command(pass_context=True)
@commands.check(can_use_faucet)
async def faucet(ctx, nano_address):
    user = str(ctx.message.author.id)

    ttl = int(await pool.execute('ttl', f"faucet:{user}"))
    if ttl != -2: #special return code for key does not exist or expired
        await ctx.send(f"You must wait {math.ceil(ttl/(3600))} hours before you can claim again")
        return

    p = re.compile('nano_[13]{1}[13456789abcdefghijkmnopqrstuwxyz]{59}$')
    if not p.match(nano_address):
        await ctx.send(f"Not a valid nano address, must start with nano_")
        return

    result = await post({"action":"send","wallet":NODE_WALLET_ID,"source": NODE_ACCOUNT,"destination":nano_address,"amount":FAUCET_AMOUNT})
    if result and "block" in result:
        block=result["block"]
        await ctx.send(f"```Transaction Complete\nblock: {block}```")
        # set in DB with an expiry so that they can't claim again for a while
        await pool.execute('setex',f"faucet:{user}", CLAIM_PERIOD, nano_address)
        print(f"{user} just claimed some Nano")
        async with db:
            search = db.search(where('user') == user)
            if not search:
                print(f"{user} has not claimed from the faucet before, adding to user db")
                db.insert({'user': user, 'nano_address': nano_address,'claims': 1})
            else:
                db.update({'claims': search[0].get("claims")+1, 'nano_address': nano_address}, where('user') == user)
    elif SUPPORT_ID:
        await ctx.send(f"Something has gone wrong while sending you Nano, let me get some help. <@{SUPPORT_ID}>")
    else:
        print(f"Error requesting a send: {result}")

@faucet.error
async def missing_arg_error(ctx, error):
    user = str(ctx.message.author.id)
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Usage: ``*faucet nano_1youraccount*****``")

async def shutdown():
    global pool
    pool.close()
    await pool.wait_closed()

try:
    loop.run_until_complete(bot.start(TOKEN))
except KeyboardInterrupt:
    loop.run_until_complete(bot.logout())
    loop.run_until_complete(shutdown())
finally:
    loop.close()
