from discord import Client as Discord
from inferkit import InferKit
import re

class TwerkBoi:
	#_id_regex = re.compile(r'<@!?(\d+)>')
	_bol_regex = re.compile(r'<([^>]+)>\s*')

	@staticmethod
	def list_tail(arr: []):
		return arr[-1] if (len(arr) > 0) else None

	@staticmethod
	def msg_author_id(msg: {}):
		if (type(msg) == dict) and ('author' in msg) and \
		   (type(msg['author']) == dict) and ('id' in msg['author']):
			return msg['author']['id']
		return None

	def __init__(self, inferkit_api_key: str, discord_bot_token: str):
		self._inferkit = InferKit(inferkit_api_key)
		self._discord = Discord()
		self._discord_bot_token = discord_bot_token
		self._channels = {}

		@self._discord.event
		async def on_ready():
			print('Logged in as {0.user}'.format(self._discord))

		@self._discord.event
		async def on_message(msg):
			msg_log = self.chan_msg_log(msg.channel.id)
			self.chan_append_msg(msg_log, msg)

			#guild = msg.guild
			#if guild:
			#	for m in TwerkBoi._id_regex.finditer(msg.content):
			#		member = guild.get_member(int(m.group(1)))
			#		if member:
			#			print(m.group(0) + ' -> ' + str(member))

			user = self._discord.user

			if msg.author == user:
				return

			user_id = user.id
			mentioned = False

			for member in msg.mentions:
				if member.id == user_id:
					mentioned = True

			if not mentioned:
				return

			await msg.channel.trigger_typing()

			prompt = self.gen_prompt(msg_log, user.display_name)
			reply = self._inferkit.generate(prompt)

			if reply == None:
				return

			arr = []
			for line in reply.splitlines():
				line = line.strip()
				if len(line) > 0:
					m = TwerkBoi._bol_regex.match(line)
					if m != None:
						if m.group(1) != user.display_name:
							break
						span = m.span()[1]
						if span >= len(line):
							continue
						line = line[span:]
					arr.append(line)

			reply='\n'.join(arr)
			await msg.channel.send(reply)

	def chan_msg_log(self, id: int):
		return self._channels.setdefault(id, [])

	def chan_append_msg(self, msg_log: [], msg):
		author = msg.author
		content = msg.content
		clean_content = msg.clean_content
		log_entry = TwerkBoi.list_tail(msg_log)

		fmt_msg = '<' + author.display_name + '> ' + clean_content

		if TwerkBoi.msg_author_id(log_entry) == author.id:
			log_entry['content'].append(content)
			log_entry['clean_content'].append(clean_content)
			log_entry['text'] += '\n' + fmt_msg
		else:
			msg_log.append({
				'author': {
					'id': author.id,
					'display_name': author.display_name,
					'name': author.name + '#' + author.discriminator
				},
				'content': [content],
				'clean_content': [clean_content],
				'text': fmt_msg
			})

		print(fmt_msg)

	def msg_log_dump(self, msg_log: []):
		text = ''
		for log_entry in msg_log:
			if 'text' in log_entry:
				text += log_entry['text'] + '\n'
		return text

	def gen_prompt(self, msg_log: [], display_name):
		text = self.msg_log_dump(msg_log) + '<' + display_name + '>'
		return text[-1000:]

	def run(self):
		self._discord.run(self._discord_bot_token)
