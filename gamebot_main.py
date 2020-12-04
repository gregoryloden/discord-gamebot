import discord

from secrets import DISCORD_TOKEN
from game_common import COMMAND_PREFIX
from game_coin import GameCoin
from game_cthulu import GameCthulu

ENDGAME_COMMAND = COMMAND_PREFIX + "endgame"

class GameClient(discord.Client):
	def __init__(self, games):
		super().__init__()
		self.available_games = games
		self.active_games = {}

	async def on_ready(self):
		print("\n================================\n" + str(self.user) + " connected to servers:")
		for guild in self.guilds:
			print("    - " + guild.name + " " + str(guild.id))
			for channel in guild.channels:
				if isinstance(channel, discord.TextChannel):
					print("        #" + channel.name + " " + str(channel.id))
		print("----------------")

	async def on_message(self, message):
		if message.author == self.user:
			return
		if isinstance(message.channel, discord.DMChannel):
			await self.handle_private_message(message)
		else:
			await self.handle_public_message(message)

	async def handle_public_message(self, message):
		if not message.content.startswith(COMMAND_PREFIX):
			return

		active_game = self.active_games.get(message.channel.id)
		if active_game:
			if message.content == ENDGAME_COMMAND or not await active_game.handle_public_message(message):
				await message.channel.send("Game concluded.")
				del self.active_games[message.channel.id]
			return

		for available_game in self.available_games:
			game_instance = await available_game.start_new_game(message)
			if game_instance:
				self.active_games[message.channel.id] = game_instance
				break

	async def handle_private_message(self, message):
		pass

client = GameClient(games = [
	GameCoin()
])
client.run(DISCORD_TOKEN)
