from pathlib import Path
from typing import Literal

import markdown2

from docutranslate.decorator.markdown_mask import MaskDict
from docutranslate.utils.agent_utils import Agent
from docutranslate.utils.convert import pdf2markdown_embed_images
from docutranslate.utils.markdown_splitter import split_markdown_text
from docutranslate.utils.markdown_utils import uris2placeholder, placeholder2_uris


class FileTranslater:
    def __init__(self, file_path: Path | str | None = None, chunksize: int = 4096, base_url="", key=None,
                 model_id="", temperature=0.7, max_concurrent=6):
        if isinstance(file_path, str):
            file_path = Path(file_path)
        self.file_path: Path = file_path
        self.file_path: Path = file_path
        self._mask_dict = MaskDict()
        self.markdown: str = ""
        self.chunksize = chunksize
        self.max_concurrent = max_concurrent
        self.base_url: str = base_url
        self.key: str = key if key is not None else "xx"
        self.model_id: str = model_id
        self.temperature = temperature

    def _mask_uris_in_markdown(self):
        self.markdown = uris2placeholder(self.markdown, self._mask_dict)
        return self

    def _unmask_uris_in_markdown(self):
        self.markdown = placeholder2_uris(self.markdown, self._mask_dict)
        return self

    def _split_markdown_into_chunks(self) -> list[str]:
        chunks: list[str] = split_markdown_text(self.markdown, self.chunksize)
        print(f"markdown分为{len(chunks)}块")
        return chunks

    def create_refine_agent(self, baseurl=None, key=None, model_id=None, temperature=None):
        baseurl = self.base_url if baseurl is None else baseurl
        key = self.key if key is None else key
        model_id = self.model_id if model_id is None else model_id
        temperature = self.temperature if temperature is None else temperature
        agent = Agent(baseurl=baseurl,
                      key=key,
                      model_id=model_id,
                      temperature=temperature,
                      max_concurrent=self.max_concurrent)
        agent.system_prompt = r"""# 角色
你是一个修正markdown文本的专家。
# 工作
找到markdown片段的不合理之处，对于缺失的句子，应该查看缺失的语句是否可能被错误的放在了其他位置，并通过重组段落、去掉异常字词修复不合理之处。
尽量忠实于原文。形如<ph-abc123>的占位符不要改变。latex不要改变。
# 输出
修正后的markdown纯文本
# 示例
## 调整顺序
输入：
applications and scenarios becoming more and more extensive.
Blockchain's origination was Bitcoin, the most successful of the digital currencies (cryptocurrencies). Since 1983, when digital currency was first proposed, the Internet has continued to burgeon, with its 
输出：
Blockchain's origination was Bitcoin, the most successful of the digital currencies (cryptocurrencies). Since 1983, when digital currency was first proposed, the Internet has continued to burgeon, with its applications and scenarios becoming more and more extensive.
## 去掉异常字词
输入：
你@好,你叫什么\名#字
输出:
你好，你叫什么名字\no_think"""
        return agent

    def create_translate_agent(self, baseurl=None, key=None, model_id=None, temperature=None, to_lang="中文"):
        baseurl = self.base_url if baseurl is None else baseurl
        key = self.key if key is None else key
        model_id = self.model_id if model_id is None else model_id
        temperature = self.temperature if temperature is None else temperature
        agent = Agent(baseurl=baseurl,
                      key=key,
                      model_id=model_id,
                      temperature=temperature,
                      max_concurrent=self.max_concurrent)
        agent.system_prompt = r"""# 角色
你是一个翻译markdown文本的专家。
# 工作
将输入的markdown文本翻译成{0}。
尽量忠实于原文。
形如<ph-abc123>的占位符不要改变。
latex不要改变。
# 输出
翻译后的markdown纯文本
# 示例
## 英文翻译为中文：
输入：
hello<ph-aaaaaa>, what's your name?
输出：
你好<ph-aaaaaa>，你叫什么名字？\no_think""".format(to_lang)
        return agent

    def read_pdf_as_markdown(self, pdf: Path |str|None = None, formula=False, code=False, save=False):
        print("正在将pdf转换为markdown")
        if pdf is None:
            pdf = self.file_path
        if isinstance(pdf,str):
            pdf=Path(pdf)
        self.markdown = pdf2markdown_embed_images(pdf, formula, code)
        print("pdf已转换")
        if save:
            self.save_as_markdown(filename=f"{pdf.stem}.md")
        return self

    def read_markdown(self, markdown_path: Path | str):
        if isinstance(markdown_path, str):
            markdown_path = Path(markdown_path)
        self.file_path = markdown_path
        with open(markdown_path, "r") as f:
            self.markdown = f.read()
        return self

    def refine_markdown(self, refine_agent: Agent | None = None) -> str:
        if refine_agent is None:
            refine_agent = self.create_refine_agent(self.base_url, self.key, self.model_id, self.temperature)
        chuncks = self._split_markdown_into_chunks()
        result: list[str] = refine_agent.send_prompts(chuncks, timeout=10000)
        self.markdown = "".join(result)
        print("markdown已修正")
        return self.markdown

    def translate_markdown(self, translate_agent: Agent | None = None):
        print("正在翻译markdown")
        if translate_agent is None:
            translate_agent = self.create_translate_agent()
        chuncks = self._split_markdown_into_chunks()
        result: list[str] = translate_agent.send_prompts(chuncks, timeout=10000)
        self.markdown = "".join(result)
        print("翻译完成")
        return self.markdown

    def save_as_markdown(self, filename: str | Path = "output.md", output_dir: str | Path = "./output"):
        if isinstance(filename, str):
            filename = Path(filename)
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        full_name = output_dir / filename
        with open(full_name, "w") as file:
            file.write(self.markdown)
        print(f"文件已写入{full_name}")
        return self

    def save_as_html(self, filename: str | Path = "output.html", output_dir: str | Path = "./output"):
        if isinstance(filename, str):
            filename = Path(filename)
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        full_name = output_dir / filename
        markdowner = markdown2.Markdown(extras=['tables', 'fenced-code-blocks', 'mermaid'])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{filename}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css">
        <style>
        html {{
            padding:2vh 10vw;
            font-size: 15px;
        }}
    </style>
</head>
<body>
{markdowner.convert(self.markdown)}
</body>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.min.js"></script>
<script type="module" defer>
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@9/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{
    securityLevel: 'loose',
    startOnLoad: true
  }});
  let observer = new MutationObserver(mutations => {{
    for(let mutation of mutations) {{
      mutation.target.style.visibility = "visible";
    }}
  }});
  document.querySelectorAll("pre.mermaid-pre div.mermaid").forEach(item => {{
    observer.observe(item, {{ 
      attributes: true, 
      attributeFilter: ['data-processed'] 
    }});
  }});
</script>
</html>
"""
        with open(full_name, "w") as file:
            file.write(html)
        print(f"文件已写入{full_name}")
        return self

    def translate_pdf_file(self, pdf_path: Path | str | None = None, to_lang="中文", output_dir="./output",
                           formula=False,
                           code=False, output_format: Literal["markdown", "html"] = "markdown", refine=True,
                           refine_agent: Agent | None = None, translate_agent: Agent | None = None):
        assert output_format in ("markdown", "html"), "output_format格式错误"
        if pdf_path is None:
            assert self.file_path is not None, "未输入文件路径"
            pdf_path = self.file_path
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
        self.read_pdf_as_markdown(pdf_path, formula=formula, code=code)
        self._mask_uris_in_markdown()
        if refine:
            if refine_agent is None:
                refine_agent = self.create_refine_agent()
            self.refine_markdown(refine_agent)
        if translate_agent is None:
            translate_agent = self.create_translate_agent(to_lang=to_lang)
        self.translate_markdown(translate_agent)
        self._unmask_uris_in_markdown()
        if output_format == "markdown":
            filename = f"{pdf_path.stem}_{to_lang}.md"
            self.save_as_markdown(filename=filename, output_dir=output_dir)
        elif output_format == "html":
            filename = f"{pdf_path.stem}_{to_lang}.html"
            self.save_as_html(filename=filename, output_dir=output_dir)
        return self

    def translate_markdown_file(self, markdown_path: Path | str | None = None, to_lang="中文", output_dir="./output",
                                output_format: Literal["markdown", "html"] = "markdown",
                                refine=False, refine_agent: Agent | None = None, translate_agent: Agent | None = None):
        assert output_format in ("markdown", "html"), "output_format格式错误"
        if markdown_path is None:
            assert self.file_path is not None, "未输入文件路径"
            markdown_path = self.file_path
        elif isinstance(markdown_path, str):
            markdown_path = Path(markdown_path)
        with open(markdown_path, "r") as f:
            self.markdown = f.read()
        self._mask_uris_in_markdown()
        if refine:
            if refine_agent is None:
                refine_agent = self.create_refine_agent()
            self.refine_markdown(refine_agent)
        if translate_agent is None:
            translate_agent = self.create_translate_agent(to_lang=to_lang)
        self.translate_markdown(translate_agent)
        self._unmask_uris_in_markdown()
        if output_format == "markdown":
            filename = f"{markdown_path.stem}_{to_lang}.md"
            self.save_as_markdown(filename=filename, output_dir=output_dir)
        elif output_format == "html":
            filename = f"{markdown_path.stem}_{to_lang}.html"
            self.save_as_html(filename=filename, output_dir=output_dir)
        return self


if __name__ == '__main__':
    pass
