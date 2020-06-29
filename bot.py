
import discord
from discord.ext import commands
import requests
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import random
import math
import re
import asyncio
import aioredis
from tinydb import TinyDB, Query
db = TinyDB('users.json')

#NodeURL (Currently using pippin must be changed to what you want)
nodeurl = "http://127.0.0.1:11338"

#Wallet Created on node.
nodewallet = "WALLET HERE"

#Address created from wallet.
nodeaccount = "ADDRESS HERE"

#Amount faucet should pay out in raw
faucetamount= 100000000000000000000000000

#Set discord role allowed to use
discordrole = "SET ROLE ALLOWED TO USE FAUCET"

#bottoken
TOKEN = 'YOUR TOKEN WILL GO HERE'

#discordID for support (Should be set to YOUR discord ID)
discordID = 0000000000000

#Discord Status
status = discord.Game("Nano Network")

loop = asyncio.get_event_loop()

pool = aioredis.create_pool(
        'redis://localhost',
        minsize=5, maxsize=10,
        loop = loop
)




bot = commands.Bot(command_prefix='*')
bot.remove_command("help")

@bot.event
async def on_ready():
    print('I am online!')
    await bot.change_presence(status=discord.Status.online,activity=status)
    global pool
    pool = await pool 

@bot.command()
async def help(ctx):
    await ctx.send("*blocks - Shows current block count. \n*faucet ``nano_address``  - will send some Nano to the address you specify.")


@bot.command()
async def blocks(ctx):
    """Gives blocks"""
    count = requests.post(nodeurl, json = {"action" : "block_count"})
    count=count.json()["count"]
    await ctx.send("```Current Blocks: "+count+"```")

#FAUCET
#24 Hours seconds
CLAIM_PERIOD = 86400


@bot.command()
@commands.has_role(discordrole)
async def faucet(ctx, nano_address):
    user = str(ctx.message.author.id)
    global pool

    ttl = int(await pool.execute('ttl', ctx.message.author.id))
    if ttl != -2: #special return code for key does not exist or expired
        await ctx.send('You must wait {} hours before you can claim again'.format(math.ceil(ttl/(3600))))
        return

    p = re.compile('^(nano|xrb)_[13]{1}[13456789abcdefghijkmnopqrstuwxyz]{59}$')
    if not p.match(nano_address):
        await ctx.send('Not a valid nano address')
        return

    sendnano = requests.post(nodeurl, json = {"action":"send","wallet":nodewallet,"source": nodeaccount,"destination":nano_address,"amount":faucetamount})
    block=sendnano.json()["block"]
    if "block" in sendnano.json():
        await ctx.send("```Transaction Complete\nblock: " +block+"```")
        # set in DB with an expiry so that they can't claim again for a while
        await pool.execute('setex',ctx.message.author.id, CLAIM_PERIOD, nano_address)
        print(user + " Just claimed some Nano.")
        if len(db.search(Query().user == user))==0:
            print(user + " Has not claimed from the faucet before, adding to user db")
            db.insert({'user': user, 'nano_address': nano_address,'Claims': 1})
    
        else:
            amountofclaims = db.search(Query().user == user)[0].get("Claims")
            db.update({'Claims': amountofclaims+1 }, Query().user == user)
    else:
        await ctx.send("Something has gone wrong while sending you Nano, let me get some help. <@"+discordID+">") 

@faucet.error
async def missing_arg_error(ctx, error):
    user = str(ctx.message.author.id)
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("looks like you didnt give me a nano address, try sending again using the following format ``*faucet nano_1superior*****``")

bot.run(TOKEN)

async def shutdown():
    pool.close()
    await pool.wait_closed()
loop.run_until_complete(shutdown())
