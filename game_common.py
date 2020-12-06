COMMAND_PREFIX = "!"

class GameInstanceBase:
	async def handle_public_message(self, base_command, message):
		return False

class GameBase:
	async def start_new_game(self, base_command, message):
		return None
