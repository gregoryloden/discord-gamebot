import random

from game_common import ActiveGame, AvailableGame, COMMAND_PREFIX

HIDDEN_CARD = "🟪"
ELDER_SIGN_CARD = "🟨"
CTHULHU_CARD = "🟩"
BLANK_CARD = "🟦"
GOOD_ROLE = "🟦"
BAD_ROLE = "🟥"
CARD_TEXT_SINGULAR = 0
CARD_TEXT_PLURAL = 1
CARD_TEXT_FOUND = 2
HAND_CARD_ORDER = [ELDER_SIGN_CARD, CTHULHU_CARD, BLANK_CARD]
TOTAL_ROUNDS = 4

class GameCthulhuInstance(ActiveGame):
	def __init__(self, texts, channel, players, cultist_count, extra_roles_count):
		super().__init__()
		self.texts = texts
		self.channel = channel
		self.all_players = players
		self.investigators = []
		self.cultists = []
		self.hands = {}
		self.next_player = self.all_players[int(random.random() * len(players))]
		self.elder_signs_found = 0
		self.round_progress = 0
		self.current_turn_message = None
		self.current_round = 0
		self.investigate_verb = "investigate"
		self.text_a_player = "a player"
		self.text_one_player = "one `@player`"
		self.text_yourself = "yourself"
		self.text_you_found = "You found"

		total_roles_count = len(players) + extra_roles_count
		for player in players:
			if random.random() < cultist_count / total_roles_count:
				self.cultists.append(player)
				cultist_count -= 1
			else:
				self.investigators.append(player)
			total_roles_count -= 1

	async def start_game(self):
		for investigator in self.investigators:
			await investigator.send(
				f"{self.texts.game_title}: You are {self.texts.investigator_with_indefinite_article}")
		for cultist in self.cultists:
			await cultist.send(f"{self.texts.game_title}: You are {self.texts.cultist_with_indefinite_article}")
		await self.advance_round()

	async def advance_round(self):
		self.current_round += 1
		self.round_progress = 0
		self.current_turn_message = None
		player_count = len(self.all_players)
		cards_per_hand = TOTAL_ROUNDS + 2 - self.current_round
		deck = [CTHULHU_CARD] + [ELDER_SIGN_CARD] * (player_count - self.elder_signs_found)
		deck += [BLANK_CARD] * (player_count * cards_per_hand - len(deck))
		for player in self.all_players:
			hand = self.extract_random_hand(cards_per_hand, deck)
			self.hands[player] = hand
			hand_message_contents = []
			for card_value in HAND_CARD_ORDER:
				cards = sum(card is card_value for card in hand)
				plurality_case = CARD_TEXT_SINGULAR if cards == 1 else CARD_TEXT_PLURAL
				if cards > 0:
					hand_message_contents.append(
						f"**{cards}**x {self.texts.card_texts[card_value][plurality_case]}")
			hand.insert(0, len(hand))
			await player.send(
				f"Round {self.current_round}/{TOTAL_ROUNDS}: You have " +
					self.list_phrase(hand_message_contents))
		await self.post_game_state(None)

	async def post_game_state(self, last_found_card):
		player_count = len(self.all_players)
		round_over = self.round_progress == player_count
		elder_signs_plurality_case = CARD_TEXT_SINGULAR if self.elder_signs_found == 1 else CARD_TEXT_PLURAL
		state = [
			"Round {}/{}{}: {}/{} {} flipped, **{}**x {} found total, **{}** left".format(
				self.current_round,
				TOTAL_ROUNDS,
				" concluded" if round_over else "",
				self.round_progress,
				player_count,
				self.texts.card_plural,
				self.elder_signs_found,
				self.texts.card_texts[ELDER_SIGN_CARD][elder_signs_plurality_case],
				player_count - self.elder_signs_found)
		]
		if last_found_card:
			state.insert(0, f"{self.text_you_found} {self.texts.card_texts[last_found_card][CARD_TEXT_FOUND]}\n")
		if self.next_player and not round_over:
			formatted_commands = self.list_phrase(
				["`" + command + " @player`" for command in self.texts.investigate_commands], use_and=False)
			state.append(
				f"{self.next_player.mention}, you {self.investigate_verb} next." +
				f" To {self.investigate_verb} {self.text_a_player}, use {formatted_commands}")
		for player in self.all_players:
			hand = self.hands[player]
			hidden_cards = hand[0]
			hand_contents = [HIDDEN_CARD] * hidden_cards + ["  "] + hand[hidden_cards + 1:] + [": ", player.mention]
			state.append(" ".join(hand_contents))
		if self.current_turn_message:
			await self.current_turn_message.delete()
		self.current_turn_message = await self.channel.send("\n".join(state))

	async def post_end_game_state(self, revealed_card, investigators_won):
		self.next_player = None
		await self.post_game_state(revealed_card)
		state = [
			f"Game over. {self.texts.investigator_plural if investigators_won else self.texts.cultist_plural} win!",
			self.texts.investigator_plural + ": " +
				", ".join(investigator.mention for investigator in self.investigators),
			self.texts.cultist_plural + ": " + ", ".join(cultist.mention for cultist in self.cultists)
		]
		await self.channel.send("\n".join(state))

	async def handle_public_message(self, base_command, message):
		#wrong command, the game is still going
		if base_command not in self.texts.investigate_commands:
			return True

		if message.author.id != self.next_player.id:
			if next((player for player in self.all_players if player.id == message.author.id), None):
				await self.channel.send(message.author.mention + " it is not your turn yet")
			else:
				await self.channel.send(message.author.mention + ", you are not playing this game")
			return True
		if len(message.mentions) != 1:
			await self.channel.send(
				f"{message.author.mention}, you must {self.investigate_verb} {self.text_one_player}")
			return True
		to_player_id = message.mentions[0].id
		if to_player_id == message.author.id:
			await self.channel.send(
				f"{message.author.mention}, you cannot {self.investigate_verb} {self.text_yourself}")
			return True
		to_player = next((player for player in self.all_players if player.id == to_player_id), None)
		if not to_player:
			await self.channel.send(
				message.author.mention + ", that person is not currently playing in this channel")
			return True

		#we found a valid player to investigate, assuming the game isn't over yet
		self.next_player = to_player
		self.round_progress += 1
		hand = self.hands[to_player]
		revealed_card = hand[hand[0]]
		hand[0] -= 1
		if revealed_card is ELDER_SIGN_CARD:
			self.elder_signs_found += 1
		await message.add_reaction(revealed_card)

		#cultists win
		if revealed_card is CTHULHU_CARD:
			await self.post_end_game_state(revealed_card, False)
			return False
		#investigators win
		elif self.elder_signs_found == len(self.all_players):
			await self.post_end_game_state(revealed_card, True)
			return False
		#nothing special, the round hasn't ended
		elif self.round_progress < len(self.all_players):
			await self.post_game_state(revealed_card)
			return True
		#round is over and we have future rounds, advance to the next round
		elif self.current_round < TOTAL_ROUNDS:
			await self.post_game_state(revealed_card)
			await self.advance_round()
			return True
		#round is over and it was the last round, cultists win
		else:
			await self.post_end_game_state(revealed_card, False)
			return False

class GameCthulhu(AvailableGame):
	def __init__(self):
		self.start_game_command = COMMAND_PREFIX + "cthulhu"
		self.game_title = "__Don't Mess with Cthulhu__"
		self.investigator_title = GOOD_ROLE + " **Investigator**"
		self.investigator_with_indefinite_article = "an " + self.investigator_title
		self.investigator_plural = GOOD_ROLE + " **Investigators**"
		self.cultist_title = BAD_ROLE + " **Cultist**"
		self.cultist_with_indefinite_article = "a " + self.cultist_title
		self.cultist_plural = BAD_ROLE + " **Cultists**"
		self.cultist_plural_casual = "cultists"
		self.card_texts = self.to_card_text([
			(ELDER_SIGN_CARD, ["{} **Elder Sign**", "{} **Elder Signs**", "an {} **Elder Sign**"]),
			(CTHULHU_CARD, ["{} **Cthulhu**", "{} **Cthulhu**", "{} **Cthulhu**"]),
			(BLANK_CARD, ["{} **blank stone**", "{} **blank stones**", "a {} **blank stone**"])
		])
		self.game_summary = (
			"You are a group of investigators investigating a cult's attempt to summon Cthulhu." +
			f" Players have sets of ritual stones; {self.investigator_plural} try to find" +
			f" {self.card_texts[ELDER_SIGN_CARD][CARD_TEXT_PLURAL]} to stop the ritual, while" +
			f" {self.cultist_plural} try to find {self.card_texts[CTHULHU_CARD][CARD_TEXT_SINGULAR]}.")
		self.card_title = "stone"
		self.card_plural = "stones"
		self.hand_description = "what you have this round"
		self.investigate_commands = [COMMAND_PREFIX + "to", COMMAND_PREFIX + "pass", COMMAND_PREFIX + "investigate"]
		self.reskin_instance = None

	@staticmethod
	def to_card_text(card_text_formats):
		return dict(
			(card, [text_format.format(card) for text_format in text_formats])
				for card, text_formats in card_text_formats)

	def base_command(self):
		return self.start_game_command

	async def share_rules(self, channel):
		formatted_commands = ActiveGame.list_phrase(
			["`" + command + " @player`" for command in self.investigate_commands], use_and=False)
		await channel.send(
			f"To start a game, send a message `{self.start_game_command} @player @player ...` with at least 3" +
			" players.\n\n" +
			self.game_summary +
			"\n\nAt the start of the game, this bot will send you a direct message with your role" +
			f" ({self.investigator_title} or {self.cultist_title})." +
			f"\nThen it builds a deck with a total of {TOTAL_ROUNDS + 1} {self.card_plural} per player," +
			f" containing one {self.card_texts[ELDER_SIGN_CARD][CARD_TEXT_SINGULAR]} per player," +
			f" one {self.card_texts[CTHULHU_CARD][CARD_TEXT_SINGULAR]}," +
			f" and the rest are {self.card_texts[BLANK_CARD][CARD_TEXT_PLURAL]}." +
			f"\n\nThe game is played over {TOTAL_ROUNDS} rounds." +
			" Each round, the bot will deal you a hand by sending you a direct message telling you" +
			f" {self.hand_description}." +
			f" No other player knows the contents of your hand." +
			f" You may share your role and the contents of your hand, and you may lie about what you have/are." +
			"\nA round contains a number of turns equal to the number of players." +
			f" Each turn, one player is active; this player picks another player by sending a message," +
			f" {formatted_commands} (these are synonyms and do 100% the same thing)." +
			f" Players may discuss who should be selected." +
			f"\nThe selected player flips one of their {self.card_plural} at random and becomes the next active" +
			" player." +
			f"\nWhen every turn in the round has been taken, flipped {self.card_plural} are discarded and the" +
			" rest are shuffled and redealt." +
			" The last selected player is the first active player next round." +
			"\n\nThe game ends when either:" +
			f"\n- every {self.card_texts[ELDER_SIGN_CARD][CARD_TEXT_SINGULAR]} has been found" +
			f" ({self.investigator_plural} win)," +
			f"\n- {self.card_texts[CTHULHU_CARD][CARD_TEXT_SINGULAR]} has been found" +
			f" ({self.cultist_plural} win), or" +
			f"\n- round {TOTAL_ROUNDS} ends and at least one" +
			f" {self.card_texts[ELDER_SIGN_CARD][CARD_TEXT_SINGULAR]} has not been found" +
			f" ({self.cultist_plural}"" win)")

	async def start_new_game(self, base_command, message):
		if base_command != self.start_game_command:
			return None

		contents = message.content.split(" ")
		players_count = len(message.mentions)
		if players_count < 3:
			await message.channel.send(self.game_title + " needs at least 3 @players to start")
			return True
		for player in message.mentions:
			if player.bot:
				await message.channel.send(player.mention + " is a bot and cannot play")
				return True

		#automatically determine cultist count
		#default: 3/4/5/6 get 2, 7,8,9 get 3, etc.
		cultist_count = max((players_count + 2) // 3, 2)

		#a 3 player game can have 0-2 cultists
		if players_count == 3:
			extra_roles_count = 2
			cultist_count_text = "0-2"
		#player counts divisible by 3 have exactly 1/3 of players as cultists
		elif players_count % 3 == 0:
			extra_roles_count = 0
			cultist_count_text = str(cultist_count)
		#other player counts have either floor() or ceil() of 1/3 of players as cultists
		else:
			extra_roles_count = 1
			cultist_count_text = str(max(cultist_count - 1, 0)) + " or " + str(cultist_count)

		await message.channel.send(
			f"Beginning a(n) {players_count}-player game of {self.game_title} with {cultist_count_text}" +
			f" {self.cultist_plural_casual}.")

		instance = GameCthulhuInstance(self, message.channel, message.mentions, cultist_count, extra_roles_count)
		if self.reskin_instance:
			self.reskin_instance(instance)
		await instance.start_game()
		return instance

	def kitten_reskin(self):
		self.start_game_command = COMMAND_PREFIX + "kitten"
		self.game_title = "__Don't Poke the Kitten__"
		self.investigator_title = GOOD_ROLE + " **Trainer**"
		self.investigator_with_indefinite_article = "a " + self.investigator_title
		self.investigator_plural = GOOD_ROLE + " **Trainers**"
		self.cultist_title = BAD_ROLE + " **Meanie**"
		self.cultist_with_indefinite_article = "a " + self.cultist_title
		self.cultist_plural = BAD_ROLE + " **Meanies**"
		self.cultist_plural_casual = "meanies"
		self.card_texts = self.to_card_text([
			(ELDER_SIGN_CARD, ["{} **purr**", "{} **purrs**", "{} **purrs**"]),
			(CTHULHU_CARD, ["{} **hiss**", "{} **hisses**", "{} **hisses**"]),
			(BLANK_CARD, ["{} **meow**", "{} **meows**", "{} **meows**"])
		])
		self.game_summary = (
			"You are a group of kitten trainers petting and poking kittens." +
			f" Players each have a kitten; {self.investigator_plural} try to get kittens to" +
			f" {self.card_texts[ELDER_SIGN_CARD][CARD_TEXT_SINGULAR]}, while {self.cultist_plural} will try to" +
			f" get one to {self.card_texts[CTHULHU_CARD][CARD_TEXT_SINGULAR]}.")
		self.card_title = "action"
		self.card_plural = "actions"
		self.hand_description = "how your kitten will act this round"
		self.investigate_commands = [COMMAND_PREFIX + "to", COMMAND_PREFIX + "pet", COMMAND_PREFIX + "poke"]
		def reskin_to_kitten(instance):
			instance.investigate_verb = "pet/poke"
			instance.text_a_player = "a kitten"
			instance.text_one_player = "the kitten of one `@player`"
			instance.text_yourself = "your kitten"
			instance.text_you_found = "Your kitten"
		self.reskin_instance = reskin_to_kitten
		return self
