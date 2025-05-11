from io import BytesIO
from pathlib import Path
from typing import Literal

import markdown2
from docling.datamodel.document import DocumentStream

from docutranslate.Agents import Agent, AgentArgs
from docutranslate.Agents import MDRefineAgent, MDTranslateAgent
from docutranslate.utils.convert import file2markdown_embed_images
from docutranslate.utils.markdown_splitter import split_markdown_text
from docutranslate.utils.markdown_utils import uris2placeholder, placeholder2_uris, MaskDict


# import mdformat


class FileTranslater:
    def __init__(self, file_path: Path | str | None = None, chunksize: int = 3500, base_url="", key=None,
                 model_id="", temperature=0.7, max_concurrent=10, docling_artifact: Path | str | None = None,
                 timeout=2000, tips=True):
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
        self.docling_artifact = docling_artifact
        self.timeout = timeout
        if tips:
            print("""
=======
[docutranslate](https://github.com/xunbu/docutranslate)
>以下操作会自动从[huggingface](https://huggingface.co)下载模型，windows需要使用**管理员模式**打开IDE运行脚本，并按需换源
- 第一次使用该库读取、翻译非markdown文本
- 第一次使用该库的公式识别或代码识别功能
=======
""")

    def _markdown_format(self):
        # 该方法还需要改进
        # self.markdown=mdformat.text(self.markdown)
        pass

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

    def default_agent_params(self) -> AgentArgs:
        result: AgentArgs = {
            "baseurl": self.base_url,
            "key": self.key,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout
        }
        return result

    def read_bytes(self, name: str, file: bytes, formula=False, code=False, save=False,
             save_format: Literal["markdown", "html"] = "markdown", refine=False,
             refine_agent: Agent | None = None):
        ds = DocumentStream(name=name, stream=BytesIO(file))
        file_path = Path(name)
        # 如果是markdown，直接读取
        if file_path.suffix == ".md":
            self.markdown = file.decode()
        else:
            print(f"正在将{file_path.resolve().name}转换为markdown")
            self.markdown = file2markdown_embed_images(ds, formula, code, artifacts_path=self.docling_artifact)
            print("已转换为markdown")
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        if save:
            if save_format == "html":
                self.save_as_html(filename=f"{file_path.stem}.html")
            else:
                self.save_as_markdown(filename=f"{file_path.stem}.md")
        return self

    def read_file(self, file_path: Path | str | None = None, formula=False, code=False, save=False,
                  save_format: Literal["markdown", "html"] = "markdown", refine=False,
                  refine_agent: Agent | None = None):
        if file_path is None:
            if self.file_path is None:
                raise Exception("未设置文件路径")
            file_path = self.file_path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        print(f"读取文件：{file_path.name}")
        # 如果是markdown，直接读取
        if file_path.suffix == ".md":
            with open(file_path, "r") as f:
                self.markdown = f.read()
        else:
            print(f"正在将{file_path.resolve().name}转换为markdown")
            self.markdown = file2markdown_embed_images(file_path, formula, code, artifacts_path=self.docling_artifact)
            print("已转换为markdown")
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        if save:
            if save_format == "html":
                self.save_as_html(filename=f"{file_path.stem}.html")
            else:
                self.save_as_markdown(filename=f"{file_path.stem}.md")
        return self

    def refine_markdown_by_agent(self, refine_agent: Agent | None = None) -> str:
        print("正在修正markdown")
        self._mask_uris_in_markdown()
        chuncks = self._split_markdown_into_chunks()
        if refine_agent is None:
            refine_agent = MDRefineAgent(**self.default_agent_params())
        result: list[str] = refine_agent.send_prompts(chuncks)
        self.markdown = "\n".join(result)
        self._unmask_uris_in_markdown()
        print("markdown已修正")
        return self.markdown

    def translate_markdown_by_agent(self, translate_agent: Agent | None = None, to_lang="中文"):
        print("正在翻译markdown")
        self._mask_uris_in_markdown()
        chuncks = self._split_markdown_into_chunks()
        if translate_agent is None:
            translate_agent = MDTranslateAgent(to_lang=to_lang, **self.default_agent_params())
        result: list[str] = translate_agent.send_prompts(chuncks)
        self.markdown = "\n".join(result)
        self._unmask_uris_in_markdown()
        print("翻译完成")
        return self.markdown

    def save_as_markdown(self, filename: str | Path | None = None, output_dir: str | Path = "./output"):
        if isinstance(filename, str):
            filename = Path(filename)
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        if filename is None:
            if self.file_path is not None:
                filename = self.file_path.name
            else:
                filename = "output.md"
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        full_name = output_dir / filename
        # 输出前格式化markdown
        self._markdown_format()
        with open(full_name, "w") as file:
            file.write(self.markdown)
        print(f"文件已写入{full_name.resolve()}")
        return self

    def export_to_markdown(self):
        # 输出前格式化markdown
        self._markdown_format()
        return self.markdown

    def save_as_html(self, filename: str | Path | None = None, output_dir: str | Path = "./output"):
        if isinstance(filename, str):
            filename = Path(filename)
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        if filename is None:
            if self.file_path is not None:
                filename = self.file_path.name
            else:
                filename = "output.html"
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        full_name = output_dir / filename
        html = self.export_to_html(str(filename.resolve().stem))
        with open(full_name, "w") as file:
            file.write(html)
        print(f"文件已写入{full_name.resolve()}")
        return self

    def export_to_html(self, title="title") -> str:
        markdowner = markdown2.Markdown(extras=['tables', 'fenced-code-blocks', 'mermaid', "code-friendly"])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css">
        <style>
        html {{
            padding:2vh 10vw;
            font-size: 15px;
        }}
    </style>
    <script type="text/x-mathjax-config">
      MathJax.Hub.Config({{
        tex2jax: {{
          inlineMath: [ ['$','$'], ["\\\\(","\\\\)"] ],
          processEscapes: true
        }}
      }});
    </script>
        
    <script type="text/javascript"
            src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
    </script>
</head>
<body>
{markdowner.convert(self.markdown)}
</body>
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
        return html

    def translate_file(self, file_path: Path | str | None = None, to_lang="中文", output_dir="./output",
                       formula=False,
                       code=False, output_format: Literal["markdown", "html"] = "markdown", refine=False,
                       refine_agent: Agent | None = None, translate_agent: Agent | None = None,save=True):
        if file_path is None:
            assert self.file_path is not None, "未输入文件路径"
            file_path = self.file_path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        self.read_file(file_path, formula=formula, code=code)
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        self.translate_markdown_by_agent(translate_agent, to_lang=to_lang)
        if save:
            if output_format == "markdown":
                filename = f"{file_path.stem}_{to_lang}.md"
                self.save_as_markdown(filename=filename, output_dir=output_dir)
            elif output_format == "html":
                filename = f"{file_path.stem}_{to_lang}.html"
                self.save_as_html(filename=filename, output_dir=output_dir)
        return self

    def translate_bytes(self, name:str,file: bytes, to_lang="中文", output_dir="./output",
                       formula=False,
                       code=False, output_format: Literal["markdown", "html"] = "markdown", refine=False,
                       refine_agent: Agent | None = None, translate_agent: Agent | None = None,save=True):
        self.read_bytes(name=name,file=file, formula=formula, code=code)
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        self.translate_markdown_by_agent(translate_agent, to_lang=to_lang)
        if save:
            if output_format == "markdown":
                filename = f"{name}_{to_lang}.md"
                self.save_as_markdown(filename=filename, output_dir=output_dir)
            elif output_format == "html":
                filename = f"{name}_{to_lang}.html"
                self.save_as_html(filename=filename, output_dir=output_dir)
        return self
