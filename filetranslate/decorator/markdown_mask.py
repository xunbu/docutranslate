from functools import wraps
from typing import Concatenate, ParamSpec, Callable
import re

from filetranslate.utils.markdown_utils import MaskDict

P=ParamSpec("P")
def mask_uris_temp(func:Callable[Concatenate[str, P], str]) -> Callable[Concatenate[str, P], str]:
    

    @wraps(func)
    def wrapper(markdown: str, *args: P.args, **kwargs: P.kwargs) -> str:
        mask_dict=MaskDict()
        def uri2placeholder(match:re.Match):
            id=mask_dict.create_id()
            mask_dict.set(id,match.group())
            return f"<ph-{id}>"
        def placeholder2uri(match:re.Match):
            id=match.group(1)
            uri=mask_dict.get(id)
            if uri is None:
                return match.group()
            return uri
        uri_pattern=r'!?\[.*?\]\(.*?\)'
        markdown=re.sub(uri_pattern,uri2placeholder,markdown)
        result=func(markdown, *args, **kwargs)
        ph_pattern=r"<ph-([a-zA-Z0-9]+)>"
        result=re.sub(ph_pattern,placeholder2uri,result)
        return result
    return wrapper
if __name__ == '__main__':
    pass