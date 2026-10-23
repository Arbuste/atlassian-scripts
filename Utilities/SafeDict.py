class SafeDict(dict):
    def __getitem__(self, key):
        val = super().get(key, False)
        return val if val else False