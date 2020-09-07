from discord import Client as Discord
from inferkit import InferKit
import log
import re

class TwerkBoi:
	_cmd_regex = re.compile(r'!(say)(\s+(.*))?$')

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
		self._member_mention = {}
		self._mention_regex = None

		@self._discord.event
		async def on_ready():
			# Get member list sorted in reverse order by lower-case
			# display name. This particular sorting choice ensures
			# that a regex matching any member name will find the
			# longest possible match in case of common prefixes.
			def display_name_lc(m):
				return m.display_name.lower()
			members = list(self._discord.get_all_members())
			members.sort(key=display_name_lc, reverse=True)

			arr = []
			for member in members:
				name = member.display_name
				arr.append(re.escape(name))
				# TODO: handle name collisions
				self._member_mention['@' + name.lower()] = member.mention
			self._mention_regex = re.compile('@(' + '|'.join(arr) + ')', flags=re.I)

			user = self._discord.user
			self._name_regex = re.compile(r'(' + re.escape(user.display_name) + r')\]\s*', flags=re.I)
			log.info('Logged in as ' + log.green(str(user), 1))

		@self._discord.event
		async def on_message(msg):
			m = TwerkBoi._cmd_regex.match(msg.content)
			if m != None:
				cmd = getattr(self, '_cmd_' + m.group(1))
				arg = m.group(3)
			else:
				cmd = None
				arg = None

			msg_log = self.chan_msg_log(msg.channel.id)
			if len(msg_log) == 0:
				await self.chan_get_history(msg_log, msg.channel)
			else:
				self.chan_append_msg(msg_log, msg, (cmd != None), TwerkBoi.list_tail(msg_log))

			user = self._discord.user

			if msg.author == user:
				return

			if cmd != None:
				await cmd(msg, arg)
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
			log.debug(log.white('<prompt>', 1) +
			          log.yellow(prompt) +
			          log.white('</prompt>', 1))
			reply = self._inferkit.generate(prompt)

			if reply == None:
				reply = 'Unable to generate a reply'
			else:
				sanitized = []
				for line in reply.splitlines():
					if (len(line) > 0) and not line.isspace():
						sanitized.append(line.strip())
				log.debug(log.white('<generated>', 1) +
				          log.blue('\n'.join(sanitized), 1) +
				          log.white('</generated>', 1))
				arr = []
				for line in sanitized:
					if line[0] == '[':
						line = line[1:]
						m = self._name_regex.match(line)
						if m == None:
							break
						span = m.span()[1]
						if span >= len(line):
							continue
						line = line[span:]
					arr.append(line)
				if len(arr) < 1:
					return
				tmp = '\n'.join(arr)
				pos = 0
				reply = ''
				for m in self._mention_regex.finditer(tmp):
					span = m.span()
					mention = m.group(0)
					reply += tmp[pos:span[0]] + \
					         self._member_mention[mention.lower()]
					pos = span[1]
				reply += tmp[pos:len(tmp)]

			await msg.channel.send(reply)

	def chan_msg_log(self, id: int):
		return self._channels.setdefault(id, [])

	async def chan_get_history(self, msg_log: [], channel):
		hist = await channel.history(limit=100).flatten()
		prev_msg = TwerkBoi.list_tail(msg_log)
		for i in range(len(hist)-1, -1, -1):
			msg = hist[i]
			is_cmd = (None != TwerkBoi._cmd_regex.match(msg.content))
			prev_msg = self.chan_append_msg(msg_log, msg, is_cmd, prev_msg)

	def chan_append_msg(self, msg_log: [], msg, is_cmd, prev_msg = None):
		author = msg.author
		clean_content = msg.clean_content
		same_author = (TwerkBoi.msg_author_id(prev_msg) == author.id)

		if same_author:
			fmt_msg = clean_content
		else:
			fmt_msg = ('[' if prev_msg == None else '\n[') \
			          + author.display_name + ']\n' + clean_content

		if is_cmd:
			# Command message: don't log, print w/ different color
			log_entry = prev_msg
			fmt_msg = log.black(fmt_msg, 1)
		elif same_author:
			log_entry = prev_msg
			log_entry['content'].append(msg.content)
			log_entry['clean_content'].append(clean_content)
			log_entry['text'] += '\n' + fmt_msg
		else:
			log_entry = {
				'author': {
					'id': author.id,
					'display_name': author.display_name,
					'name': author.name + '#' + author.discriminator
				},
				'content': [msg.content],
				'clean_content': [clean_content],
				'text': fmt_msg
			}
			msg_log.append(log_entry)

		log.debug(fmt_msg)
		return log_entry

	def msg_log_dump(self, msg_log: []):
		text = ''
		for log_entry in msg_log:
			if 'text' in log_entry:
				text += log_entry['text'] + '\n'
		return text

	def gen_prompt(self, msg_log: [], display_name):
		text = self.msg_log_dump(msg_log) + '\n[' + display_name + ']\n'
		return text[-1000:]

	def run(self):
		self._discord.run(self._discord_bot_token)

	async def _cmd_say(self, msg, text):
		await msg.channel.trigger_typing()
		pos = 0
		reply = ''
		for m in self._mention_regex.finditer(text):
			span = m.span()
			mention = m.group(0)
			reply += text[pos:span[0]] + \
			         self._member_mention[mention.lower()]
			pos = span[1]
		reply += text[pos:len(text)]
		await msg.channel.send(reply)
