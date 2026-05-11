import time


class WordsTimedCache:

    def __init__(self, time_in_seconds):
        self.time_in_seconds = time_in_seconds
        self.store = dict()
    def put(self, word):
        self.store[word] = time.time()
    def check(self, word):
        if self.store.get(word) is not None:
            return self.__check_timestamp(word)
        else:
            return False

    def to_string(self):
        return str(self.store)

    def keys(self):
        return self.store.keys()

    def keys_as_string(self):
        return str(self.keys())

    def __check_timestamp(self,word):
        timestamp = self.store.get(word)
        return (time.time() - timestamp) > self.time_in_seconds