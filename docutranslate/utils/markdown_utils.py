import re
import threading
import uuid



class MaskDict:
    def __init__(self):
        self._dict = {}
        self._lock = threading.Lock()

    def create_id(self):
        with self._lock:
            while True:
                id = uuid.uuid1().hex[:6]
                if id not in self._dict:
                    return id

    def get(self, key):
        with self._lock:
            return self._dict.get(key)

    def set(self, key, value):
        with self._lock:
            self._dict[key] = value

    def delete(self, key):
        with self._lock:
            if key in self._dict:
                del self._dict[key]

    def __contains__(self, item):
        with self._lock:
            return item in self._dict
def uris2placeholder(markdown:str, mask_dict:MaskDict):
    def uri2placeholder(match: re.Match):
        id = mask_dict.create_id()
        mask_dict.set(id, match.group())
        return f"<ph-{id}>"

    uri_pattern = r'!?\[.*?\]\(.*?\)'
    markdown = re.sub(uri_pattern, uri2placeholder, markdown)
    return markdown

def placeholder2_uris(markdown:str, mask_dict:MaskDict):
    def placeholder2uri(match:re.Match):
        id=match.group(1)
        uri=mask_dict.get(id)
        if uri is None:
            return match.group()
        return uri

    ph_pattern = r"<ph-([a-zA-Z0-9]+)>"
    markdown = re.sub(ph_pattern, placeholder2uri, markdown)
    return markdown




if __name__ == '__main__':
    pass
