COMMAND_PREFIX = "!"

class GameInstanceBase:
	async def handle_public_message(self, message):
		return False

class GameBase:
	async def start_new_game(self, message):
		return None
