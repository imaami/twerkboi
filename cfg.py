import simplejson as json

class Cfg:
	def __init__(self, cfg_file: str):
		with open(cfg_file, 'r') as fp:
			self._data = json.load(fp)

	def data(self):
		return self._data
