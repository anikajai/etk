from typing import List
from etk.extractor import Extractor, InputType
from etk.etk_extraction import Extraction
from etk.tokenizer import Tokenizer
from spacy.tokens import Token
from pygtrie import CharTrie
from itertools import *
from functools import reduce


class GlossaryExtractor(Extractor):
    def __init__(self,
                 glossary: List[str],
                 extractor_name: str,
                 tokenizer: Tokenizer,
                 ngrams: int=2,
                 case_sensitive=False) -> None:
        Extractor.__init__(self,
                           input_type=InputType.TOKENS,
                           category="glossary",
                           name=extractor_name)
        self.ngrams = ngrams
        self.case_sensitive = case_sensitive
        self.default_tokenizer = tokenizer
        self.joiner = " "
        self.glossary = self.populate_trie(glossary)
        self._category = "glossary"

    def extract(self, tokens: List[Token]) -> List[dict]:
        """Extracts information from a string(TEXT) with the GlossaryExtractor instance"""
        results = list()

        if len(tokens) > 0:
            if self.case_sensitive:
                tokens = [x.orth_ for x in tokens]
            else:
                tokens = [x.lower_ for x in tokens]

        try:
            ngrams_iter = self.generate_ngrams_with_context(tokens)
            results.extend(map(lambda term: self.wrap_value_with_context(term[0], term[1], term[2]),
                               filter(lambda term: isinstance(term[0], str),
                                      map(lambda term: (self.glossary.get(term[0]), term[1], term[2]),
                                          map(lambda term: (self.combine_ngrams(term[0], self.joiner), term[1],term[2]), ngrams_iter)))))
        except Exception as e:
            print("error operator")
            print(e)
            return []
        return results

    def generate_ngrams_with_context(self, tokens: List[Token]) -> chain:
        """Generates the 1-gram to n-grams tuples of the list of tokens"""
        chained_ngrams_iter = self.generate_ngrams_with_context_helper(iter(tokens), 1)
        for n in range(2, self.ngrams + 1):
            ngrams_iter = tee(tokens, n)
            for j in range(1, n):
                for k in range(j):
                    next(ngrams_iter[j], None)
            ngrams_iter_with_context = self.generate_ngrams_with_context_helper(zip(*ngrams_iter), n)
            chained_ngrams_iter = chain(chained_ngrams_iter, ngrams_iter_with_context)
        return chained_ngrams_iter

    def populate_trie(self, values: List[str]) -> CharTrie:
        """Takes a list and inserts its elements into a new trie and returns it"""
        return reduce(self.__populate_trie_reducer, iter(values), CharTrie())

    def __populate_trie_reducer(self, trie_accumulator=CharTrie(), value="") -> CharTrie:
        """Adds value to trie accumulator"""
        if self.case_sensitive:
            key = self.joiner.join([x.orth_ for x in self.default_tokenizer.tokenize(value)])
        else:
            key = self.joiner.join([x.lower_ for x in self.default_tokenizer.tokenize(value)])
        trie_accumulator[key] = value
        return trie_accumulator

    @staticmethod
    def wrap_value_with_context(value: str, start: int, end: int) -> Extraction:
        """Wraps the final result"""
        return Extraction({'value': value,
                'context': {'start': start,
                            'end': end
                            },
                'confidence': 1.0
                })

    @staticmethod
    def generate_ngrams_with_context_helper(ngrams_iter: iter, ngrams_len: int) -> map:
        """Updates the end index"""
        return map(lambda term: (term[1], term[0], term[0] + ngrams_len), enumerate(ngrams_iter))

    @staticmethod
    def combine_ngrams(ngrams, joiner) -> str:
        """Construct keys for checking in trie"""
        if isinstance(ngrams, str):
            return ngrams
        else:
            combined = joiner.join(ngrams)
            return combined