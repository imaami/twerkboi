import logging
from transformers import pipeline, TextGenerationPipeline, set_seed, GPT2Tokenizer
import secrets
import sys
import log

logging.disable(logging.WARNING)

class GPT2:
	@staticmethod
	def _as_stripped_lines(txt: str):
		arr = []
		for line in txt.splitlines():
			if (len(line) > 0) and not line.isspace():
				arr.append(line.strip())
		return arr

	@staticmethod
	def _get_return_seq(arr, idx: int, prompt_len: int = 0):
		return arr[idx]['generated_text'][prompt_len:]

	def __init__(self, model: str, sampling_count: int = 1, seed: int = 0):
		self.busy = False
		self._tok = GPT2Tokenizer.from_pretrained(model)
		self._gen = pipeline('text-generation', model = model,
		                     tokenizer = self._tok,
		                     device = 0)
		self.seed = seed or secrets.randbits(32)
		set_seed(self.seed)
		self.sampling_count = sampling_count

	def _ntokens(self, txt: str):
		t = self._tok(txt, return_tensors = 'pt',
		              add_special_tokens = False,
		              padding = False)
		return len(t['input_ids'][0]) \
		       if ('input_ids' in t and len(t['input_ids']) > 0) \
		       else 0

	def truncate_prompt(self, txt: str, max: int):
		t = self._tok(txt, return_tensors = 'pt',
		              add_special_tokens = False,
		              padding = False)
		n = len(t['input_ids'][0]) \
		    if ('input_ids' in t and len(t['input_ids']) > 0) \
		    else 0
		#log.debug('input tokens before truncation: ' + str(n))
		return '' if n < 1 else \
		       self._tok.decode(t['input_ids'][0][-1024+max:],
		                        skip_special_tokens = True,
		                        clean_up_tokenization_spaces = True)

	def generate(self, prompt: str, max: int = 20):
		if self.busy:
			log.error('GPT-2 busy')
		self.busy = True
		prompt = self.truncate_prompt(prompt, max)
		ntokens = self._ntokens(prompt)
		#log.debug('input tokens after truncation:  ' + str(ntokens))
		try:
			tmp = self._gen(prompt, \
			                max_length = ntokens + max, \
			                clean_up_tokenization_spaces = True,
			                num_return_sequences = self.sampling_count)
			prompt_len = len(prompt)

			out = []
			for i in range(0, self.sampling_count):
				lines = GPT2._as_stripped_lines(GPT2._get_return_seq(tmp, i, prompt_len))
				out.append(lines)
				log.warn('(' + str(i) + ') ' + '\n'.join(lines))
		except Exception as e:
			log.error('GPT-2 ' + type(e).__name__ + ': ' + str(e))
			if isinstance(e, RuntimeError):
				log.error('      ^ ' + str(ntokens) + ' input tokens')
			out = []
		self.busy = False
		return out

if __name__ == "__main__":
	with open(sys.argv[1], 'r') as f:
		prompt = f.read()
		g = GPT2('gpt2-large')
		txt = g.generate(prompt)
		print(txt)
