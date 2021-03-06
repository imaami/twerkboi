from discord.ext import commands
from inferkit import InferKit
from cfg import Cfg
from gear import Gear
import log
import re

class TwerkBoi:
	@staticmethod
	def list_tail(arr: []):
		return arr[-1] if (len(arr) > 0) else None

	@staticmethod
	def msg_author_id(msg: {}):
		if (type(msg) == dict) and ('author' in msg) and \
		   (type(msg['author']) == dict) and ('id' in msg['author']):
			return msg['author']['id']
		return None

	def get_command_prefix(self):
		return self._cfg.command_prefix

	def _is_cmd(self, msg):
		return (None != self._cmd_regex.match(msg.content))

	def __init__(self, cfg_file: str = None, **kwargs):

		self._cfg = Cfg(cfg_file, **kwargs)
		self._discord = commands.Bot(self._cfg.command_prefix)
		self._inferkit = InferKit(self._cfg.inferkit_api_key)
		self._channels = {}
		self._member_mention = {}
		self._mention_regex = None

		self._discord.add_cog(Gear(self))
		cog = self._discord.get_cog('Gear')
		self._cmd_regex = cog.compile_regex()

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
			await self._discord.process_commands(msg)
			is_cmd = self._is_cmd(msg)

			msg_log = self.chan_msg_log(msg.channel.id)
			if len(msg_log) == 0:
				await self.chan_get_history(msg_log, msg.channel)
			else:
				self.chan_append_msg(msg_log, msg, is_cmd, TwerkBoi.list_tail(msg_log))

			user = self._discord.user

			if msg.author == user:
				return

			if is_cmd:
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

				if self._cfg.auto_mention:
					need_receiver_mention = True
					receiver_mention = msg.author.mention
				else:
					if len(arr) < 1:
						return
					need_receiver_mention = False
					receiver_mention = None

				tmp = '\n'.join(arr)
				pos = 0
				reply = ''
				mentions_seen = {
					'@' + user.display_name.lower(): True
				}
				for m in self._mention_regex.finditer(tmp):
					span = m.span()
					reply += tmp[pos:span[0]]
					pos = span[1]
					cleaned_mention = m.group(0).lower()
					if cleaned_mention in mentions_seen:
						continue
					mentions_seen[cleaned_mention] = True
					mention = self._member_mention[cleaned_mention]
					reply += mention
					if need_receiver_mention and (mention == receiver_mention):
						need_receiver_mention = False
				reply += tmp[pos:len(tmp)]

				if need_receiver_mention:
					if len(reply) > 0:
						reply = receiver_mention + ' ' + reply
					else:
						reply = receiver_mention

			await msg.channel.send(reply)

	def chan_msg_log(self, id: int):
		return self._channels.setdefault(id, [])

	async def chan_get_history(self, msg_log: [], channel):
		hist = await channel.history(limit=100).flatten()
		prev_msg = TwerkBoi.list_tail(msg_log)
		for i in range(len(hist)-1, -1, -1):
			msg = hist[i]
			prev_msg = self.chan_append_msg(msg_log, msg, self._is_cmd(msg), prev_msg)

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
		self._discord.run(self._cfg.discord_bot_token)
