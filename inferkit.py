import requests
import simplejson

class InferKit:
	__URL_PREFIX = 'https://api.inferkit.com/v1/models/'
	__URL_SUFFIX = '/generate'

	def __init__(self, api_key: str, model: str = 'standard'):
		self.url = self.__URL_PREFIX + model + self.__URL_SUFFIX
		self._headers = {'Authorization': 'Bearer ' + api_key}

	def generate(self, prompt: str, length: int = 100):
		data = {
			'prompt': {
				'text': prompt,
				'isContinuation': True
			},
			'length': length
		}

		try:
			r = requests.post(self.url, headers=self._headers, json=data)
			r.raise_for_status()
		except requests.exceptions.RequestException as e:
			print('\x1b[1;31mRequestException: ' + str(e) + '\x1b[0m')
			return None

		try:
			reply = r.json()
		except simplejson.errors.JSONDecodeError as e:
			print('\x1b[1;31mJSONDecodeError: ' + str(e) + '\x1b[0m')
			return None

		if ('data' in reply) and ('text' in reply['data']):
			return reply['data']['text']

		return None
