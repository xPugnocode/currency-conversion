import asyncio
import datetime
import json
import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from modules.minervini import getMinervini


import aiohttp

app = Flask('')


@app.route('/')
def home():
	return "Bot is online"


def run():
	app.run(host='0.0.0.0', port=8080)


def keep_alive():
	t = Thread(target=run)
	t.start()

intents = discord.Intents.all()
client = commands.Bot(command_prefix='$', intents=intents)
client.remove_command('help')
discord.utils.setup_logging()

async def getExchangeOnce():
	async with aiohttp.ClientSession() as cs:
		async with cs.get(f"https://v6.exchangerate-api.com/v6/{os.environ['CURRENCY_KEY']}/latest/USD") as r:
			r = json.dumps(await r.json())
			with open("data/currency.json", "w") as outfile:
				outfile.write(r)


async def dailyTask():
	while True:
		now = datetime.datetime.utcnow()
		runTime = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 1))
		print(((runTime - now) % datetime.timedelta(days=1)).total_seconds())
		await asyncio.sleep(
			((runTime - now) % datetime.timedelta(days=1)).total_seconds())
		await getExchangeOnce()

async def hourlyTask():
	while True:
		now = datetime.datetime.utcnow()
		runTime = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
		print(((runTime - now) % datetime.timedelta(hours=1)).total_seconds())
		await asyncio.sleep(((runTime - now) % datetime.timedelta(hours=1)).total_seconds())
		getMinervini()


@client.event
async def on_ready():
	print('We have logged in as {0.user}'.format(client))
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='the global market'))


@client.tree.command(name="ping", description="get the latency")
async def ping(interaction):
	ping = '{:.2f}'.format(round(client.latency*1000, 2))
	await interaction.response.send_message(f"Ping: {ping}ms")

@client.tree.command(name="magic", description="magic stock picker")
async def magic(interaction):
	with open("data/stocks.json") as f:
		data = json.load(f)
		stocks = " ".join([data[i][0] for i in range(3)])
		await interaction.response.send_message(f"Your magic stocks are: {stocks}")

@client.command()
async def sync(ctx):
	print("sync command")
	if ctx.author.id == 567924760370085899:
		await client.tree.sync()
		await ctx.send('Command tree synced.')


@client.command()
async def updateExchange(ctx):
	if ctx.author.id == 567924760370085899:
		print("manually fetching currency api")
		await getExchangeOnce()
		await ctx.send("Fetched APIs")

@client.command()
async def updateStocks(ctx):
	if ctx.author.id == 567924760370085899:
		print("manually fetching minervini data")
		getMinervini()
		await ctx.send("Updated Stocks")

@client.command()
async def convert(ctx, value, baseCode, finalCode):
	try:
		baseCode = baseCode.upper()
		finalCode = finalCode.upper()
		with open("data/currency.json", "r") as rates:
			rates = json.load(rates)
			if (rates["result"] != "success"):
				await ctx.send("the bot broken lmfao")
				return
			try:
				value = float(value)
			except:
				await ctx.send("that isnt a valid number lmfao")
				return
			rates = rates["conversion_rates"]
			if baseCode in rates and finalCode in rates:
				finalVal = value * (1.0 / rates[baseCode])
				finalVal *= rates[finalCode]
				await ctx.send('{:.2f}'.format(round(value, 2)) + " " + baseCode + " -> " + '{:.2f}'.format(round(finalVal, 2)) + " " + finalCode)
			else:
				await ctx.send("i dont recognize that currency code lmfao")
	except Exception as e:
		await ctx.send(e)


async def main():
	dt = asyncio.create_task(dailyTask())
	ht = asyncio.create_task(hourlyTask())
	asyncio.ensure_future(dt)
	async with client:
		try:
			keep_alive()
			await client.start(os.getenv("BOT_TOKEN"))
		except discord.HTTPException as e:
			if e.status == 429:
				print("The Discord servers denied the connection for making too many requests")
				print("Get help from https://stackoverflow.com/questions/66724687/in-discord-py-how-to-solve-the-error-for-toomanyrequests")
			else:
				raise e


asyncio.run(main())
