from typing import NamedTuple
import json

class CfgBase(NamedTuple):
	inferkit_api_key: str = ''
	discord_bot_token: str = ''
	command_prefix: str = '!'
	auto_mention: bool = False

class Cfg(CfgBase):
	def __new__(cls, cfg_file: str = None, **kwargs):
		try:
			with open(cfg_file, 'r') as fp:
				d = json.load(fp)
			d.update(**kwargs)
		except Exception as e:
			d = dict(**kwargs)
		self = super().__new__(cls, **d)
		self.file = cfg_file
		return self
