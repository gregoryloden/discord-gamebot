import random

from game_common import GameInstanceBase, GameBase, COMMAND_PREFIX

COIN_COMMAND = COMMAND_PREFIX + "coin"
HEADS = "heads"
TAILS = "tails"
HEADS_COMMAND = COMMAND_PREFIX + HEADS
TAILS_COMMAND = COMMAND_PREFIX + TAILS

class GameCoinInstance(GameInstanceBase):
	async def handle_public_message(self, message):
		#wrong command, game is still going
		if message.content != HEADS_COMMAND and message.content != TAILS_COMMAND:
			return True

		was_heads = random.random() < 0.5
		correct_guess = was_heads == (message.content == HEADS_COMMAND)
		await message.channel.send(
			"Result: " + (HEADS if was_heads else TAILS) + ". You " + ("win!" if correct_guess else "lose."))
		return False

class GameCoin(GameBase):
	async def start_new_game(self, message):
		if message.content != COIN_COMMAND:
			return None

		await message.channel.send("`" + HEADS_COMMAND + "` or `" + TAILS_COMMAND + "`?")
		return GameCoinInstance()
