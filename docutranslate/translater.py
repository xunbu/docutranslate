import asyncio
import html
from pathlib import Path
from typing import Literal
import markdown2
import jinja2
from docutranslate.agents import Agent, AgentArgs
from docutranslate.agents import MDRefineAgent, MDTranslateAgent
from docutranslate.cacher import document_cacher_global
from docutranslate.converter import Document, ConverterMineru
from docutranslate.utils.markdown_splitter import split_markdown_text, join_markdown_texts
from docutranslate.utils.markdown_utils import uris2placeholder, placeholder2_uris, MaskDict, clean_markdown_math_block
from docutranslate.logger import translater_logger
from docutranslate.global_values import available_packages
from docutranslate.utils.resource_utils import resource_path

DOCLING_FLAG = True if available_packages.get("docling") else False
if DOCLING_FLAG:
    from docutranslate.converter import ConverterDocling


class FileTranslater:
    def __init__(self, file_path: Path | str | None = None, chunksize: int = 3000,
                 base_url="", key=None, model_id="", temperature=0.7,
                 max_concurrent=30, timeout=2000,
                 convert_engin: Literal["docling", "mineru"] = "mineru",
                 docling_artifact: Path | str | None = None,
                 mineru_token: str = None, cache=True):
        self.convert_engin = convert_engin
        self.mineru_token = mineru_token.strip() if mineru_token is not None else None
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
        if docling_artifact is None:
            artifact_path = Path("./docling_artifact")
            print(f"artifact_path:{artifact_path.resolve()}，existed：{artifact_path.is_dir()}")
            if artifact_path.is_dir():
                translater_logger.info("检测到docling_artifact文件夹")
                self.docling_artifact = artifact_path
        self.timeout = timeout
        self.file_suffix: str | None = None  # 现在处理的文件后缀如".md"、".txt"
        self.cache = cache
        self.cacher = document_cacher_global

    def _markdown_format(self):
        # 该方法还需要改进
        # self.markdown=mdformat.text(self.markdown)
        self.markdown = self.markdown.replace(r'\（', r'\(')
        self.markdown = self.markdown.replace(r'\）', r'\)')
        self.markdown = clean_markdown_math_block(self.markdown)
        pass

    def _mask_uris_in_markdown(self):
        self.markdown = uris2placeholder(self.markdown, self._mask_dict)
        return self

    def _unmask_uris_in_markdown(self):
        self.markdown = placeholder2_uris(self.markdown, self._mask_dict)
        return self

    def _split_markdown_into_chunks(self) -> list[str]:
        chunks: list[str] = split_markdown_text(self.markdown, self.chunksize)
        translater_logger.info(f"markdown分为{len(chunks)}块")
        return chunks

    def _default_agent_params(self) -> AgentArgs:
        result: AgentArgs = {
            "baseurl": self.base_url,
            "key": self.key,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout
        }
        return result

    def default_refine_agent(self, custom_prompt=None) -> MDRefineAgent:
        return MDRefineAgent(custom_prompt=custom_prompt, **self._default_agent_params())

    def default_translate_agent(self, custom_prompt=None, to_lang="中文") -> MDTranslateAgent:
        return MDTranslateAgent(custom_prompt=custom_prompt, to_lang=to_lang, **self._default_agent_params())

    def _convert2markdown(self, document: Document, formula: bool, code: bool, artifact: Path = None) -> str:
        cached_result = self.cacher.get_cached_result(document, formula, code, convert_engin=self.convert_engin)
        if cached_result:
            translater_logger.info("正在获取缓存结果")
            return cached_result
        if document.suffix in [".md", ".txt"]:
            return document.filebytes.decode("utf-8")
        translater_logger.info("正在转化为markdown")
        if self.convert_engin == "docling":
            if artifact is None:
                artifact = self.docling_artifact
            mdconverter = ConverterDocling(formula=formula, code=code, artifact=artifact)
            result = mdconverter.convert(document)
        else:
            if self.mineru_token is None:
                raise Exception("mineru_token未配置")
            if code:
                translater_logger.info("mineru暂不支持code识别")
            mdconverter = ConverterMineru(token=self.mineru_token, formula=formula)
            result = mdconverter.convert(document)
        return self.cacher.cache_result(result, document, formula, code, convert_engin=self.convert_engin)

    async def _convert2markdown_async(self, document: Document, formula: bool, code: bool,
                                      artifact: Path = None) -> str:
        cached_result = self.cacher.get_cached_result(document, formula, code, convert_engin=self.convert_engin)
        if cached_result:
            translater_logger.info("解析结果已缓存，获取缓存结果")
            return cached_result
        if document.suffix in [".md", ".txt"]:
            return document.filebytes.decode("utf-8")
        translater_logger.info("正在转化为markdown")
        if self.convert_engin == "docling":
            if artifact is None:
                artifact = self.docling_artifact
            mdconverter = ConverterDocling(formula=formula, code=code, artifact=artifact)
            result = await mdconverter.convert_async(document)
        else:
            if self.mineru_token is None:
                raise Exception("mineru_token未配置")
            if code:
                translater_logger.info("mineru暂不支持code识别")
            mdconverter = ConverterMineru(token=self.mineru_token, formula=formula)
            result = await mdconverter.convert_async(document)
        return self.cacher.cache_result(result, document, formula, code, convert_engin=self.convert_engin)

    def read_document(self, document: Document, formula: bool, code: bool, save: bool,
                      save_format: Literal["markdown", "html"], refine: bool,
                      refine_agent: Agent | None):
        self.file_suffix = document.suffix
        self.markdown = self._convert2markdown(document, formula=formula, code=code, artifact=self.docling_artifact)
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        if save:
            if save_format == "html":
                self.save_as_html(filename=f"{document.stem}.html")
            else:
                self.save_as_markdown(filename=f"{document.stem}.md")
        return self

    async def read_document_async(self, document: Document, formula: bool, code: bool, save: bool,
                                  save_format: Literal["markdown", "html"], refine: bool,
                                  refine_agent: Agent | None):
        self.file_suffix = document.suffix
        self.markdown = await self._convert2markdown_async(document, formula=formula, code=code,
                                                           artifact=self.docling_artifact)
        if refine:
            await self.refine_markdown_by_agent_async(refine_agent)
        if save:
            if save_format == "html":
                self.save_as_html(filename=f"{document.stem}.html")
            else:
                self.save_as_markdown(filename=f"{document.stem}.md")
        return self

    def read_bytes(self, name: str, file: bytes, formula=True, code=True, save=False,
                   save_format: Literal["markdown", "html"] = "markdown", refine=False,
                   refine_agent: Agent | None = None):
        document = Document(filename=name, filebytes=file)
        self.read_document(document, formula=formula, code=code, save=save, save_format=save_format,
                           refine=refine, refine_agent=refine_agent)
        return self

    async def read_bytes_async(self, name: str, file: bytes, formula=True, code=True, save=False,
                               save_format: Literal["markdown", "html"] = "markdown", refine=False,
                               refine_agent: Agent | None = None):
        document = Document(filename=name, filebytes=file)
        await self.read_document_async(document, formula=formula, code=code, save=save, save_format=save_format,
                                       refine=refine, refine_agent=refine_agent)
        return self

    def read_file(self, file_path: Path | str | None = None, formula=True, code=True, save=False,
                  save_format: Literal["markdown", "html"] = "markdown", refine=False,
                  refine_agent: Agent | None = None):
        if file_path is None:
            if self.file_path is None:
                translater_logger.debug("未设置文件路径")
                raise Exception("未设置文件路径")
            file_path = self.file_path
        document = Document(path=file_path)
        translater_logger.info(f"读取文件：{document.filename}")
        self.read_document(document, formula=formula, code=code, save=save, save_format=save_format, refine=refine,
                           refine_agent=refine_agent)
        return self

    async def read_file_async(self, file_path: Path | str | None = None, formula=True, code=True, save=False,
                              save_format: Literal["markdown", "html"] = "markdown", refine=False,
                              refine_agent: Agent | None = None):
        if file_path is None:
            if self.file_path is None:
                translater_logger.debug("未设置文件路径")
                raise Exception("未设置文件路径")
            file_path = self.file_path
        document = Document(file_path)
        translater_logger.info(f"读取文件：{document.filename}")
        # 如果是markdown，直接读取
        await self.read_document_async(document, formula=formula, code=code, save=save, save_format=save_format,
                                       refine=refine, refine_agent=refine_agent)
        return self

    def refine_markdown_by_agent(self, refine_agent: Agent | None = None, custom_prompt=None) -> str:
        translater_logger.info("正在修正markdown")
        self._mask_uris_in_markdown()
        chuncks = self._split_markdown_into_chunks()
        if refine_agent is None:
            refine_agent = self.default_refine_agent(custom_prompt)
        result: list[str] = refine_agent.send_prompts(chuncks)
        if self.file_suffix == ".txt":
            self.markdown = "\n".join(result)
        else:
            self.markdown = join_markdown_texts(result)
        self._unmask_uris_in_markdown()
        translater_logger.info("markdown已修正")
        return self.markdown

    def translate_markdown_by_agent(self, translate_agent: Agent | None = None, to_lang="中文", custom_prompt=None):
        translater_logger.info("正在翻译markdown")
        self._mask_uris_in_markdown()
        chuncks = self._split_markdown_into_chunks()
        if translate_agent is None:
            translate_agent = self.default_translate_agent(custom_prompt=custom_prompt, to_lang=to_lang)
        result: list[str] = translate_agent.send_prompts(chuncks)
        if self.file_suffix == ".txt":
            self.markdown = "\n".join(result)
        else:
            self.markdown = join_markdown_texts(result)
        self._unmask_uris_in_markdown()
        translater_logger.info("翻译完成")
        return self.markdown

    async def refine_markdown_by_agent_async(self, refine_agent: Agent | None = None, custom_prompt=None) -> str:
        translater_logger.info("正在修正markdown")
        self._mask_uris_in_markdown()
        chuncks = self._split_markdown_into_chunks()
        if refine_agent is None:
            refine_agent = self.default_refine_agent(custom_prompt=custom_prompt)
        result: list[str] = await refine_agent.send_prompts_async(chuncks)
        if self.file_suffix == ".txt":
            self.markdown = "\n".join(result)
        else:
            self.markdown = join_markdown_texts(result)
        self._unmask_uris_in_markdown()
        translater_logger.info("markdown已修正")
        return self.markdown

    async def translate_markdown_by_agent_async(self, translate_agent: Agent | None = None, to_lang="中文",
                                                custom_prompt=None):
        translater_logger.info("正在翻译markdown")
        self._mask_uris_in_markdown()
        chuncks = self._split_markdown_into_chunks()
        if translate_agent is None:
            translate_agent = self.default_translate_agent(to_lang=to_lang, custom_prompt=custom_prompt)
        result: list[str] = await translate_agent.send_prompts_async(chuncks)
        if self.file_suffix == ".txt":
            self.markdown = "\n".join(result)
        else:
            self.markdown = join_markdown_texts(result)
        self._unmask_uris_in_markdown()
        translater_logger.info("翻译完成")
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
        translater_logger.info(f"文件已写入{full_name.resolve()}")
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
        html_content = self.export_to_html(title=str(full_name.resolve().stem))
        with open(full_name, "w") as file:
            file.write(html_content)
        translater_logger.info(f"文件已写入{full_name.resolve()}")
        return self

    def export_to_html(self, title="title", cdn=True) -> str:
        markdowner = markdown2.Markdown(extras=['tables', 'fenced-code-blocks', 'mermaid', "code-friendly"])
        # language=html
        pico = f"<style>{resource_path("static/pico.css").read_text(encoding='utf-8')}</style>"
        html_template = resource_path("template/markdown.html").read_text(encoding='utf-8')
        katex_css = f"<style>{resource_path("static/katex.css").read_text(encoding='utf-8')}</style>" if not cdn else r"""<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.css" integrity="sha512-fHwaWebuwA7NSF5Qg/af4UeDx9XqUpYpOGgubo3yWu+b2IQR4UeQwbb42Ti7gVAjNtVoI/I9TEoYeu9omwcC6g==" crossorigin="anonymous" referrerpolicy="no-referrer" />"""
        katex_js = f"<script>{resource_path("static/katex.js").read_text(encoding='utf-8')}</script>" if not cdn else r"""<script defer src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.js" integrity="sha512-LQNxIMR5rXv7o+b1l8+N1EZMfhG7iFZ9HhnbJkTp4zjNr5Wvst75AqUeFDxeRUa7l5vEDyUiAip//r+EFLLCyA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>"""
        auto_render = f'<script>{resource_path("static/autoRender.js").read_text(encoding='utf-8')}</script>' if not cdn else r"""<script defer src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js" integrity="sha512-iWiuBS5nt6r60fCz26Nd0Zqe0nbk1ZTIQbl3Kv7kYsX+yKMUFHzjaH2+AnM6vp2Xs+gNmaBAVWJjSmuPw76Efg==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>"""
        # language=javascript
        renderMathInElement = r"""
                              <script>
                                  document.addEventListener("DOMContentLoaded", function () {
                                  renderMathInElement(document.body, {
                                      delimiters: [
                                          {left: '$$', right: '$$', display: true},
                                          {left: '\\[', right: '\\]', display: true},
                                          {left: '$', right: '$', display: false},
                                          {left: '\\(', right: '\\)', display: false}
                                      ],
                                      throwOnError: false
                                  })
                              });
                              </script>""" if cdn else r"""
                                                       <script>
                                                           document.addEventListener("DOMContentLoaded", function () {
                                                           renderMathInElement(document.body, {
                                                               delimiters: [
                                                                   {left: '$$', right: '$$', display: true},
                                                                   {left: '\\[', right: '\\]', display: true},
                                                                   {left: '$', right: '$', display: false},
                                                                   {left: '\\(', right: '\\)', display: false}
                                                               ],
                                                               fonts: false,
                                                               throwOnError: false
                                                           })
                                                       });
                                                       </script>"""
        mermaid = f'<script>{resource_path("static/mermaid.js").read_text(encoding='utf-8')}</script>'

        if self.file_suffix == ".txt":
            content = html.escape(self.export_to_markdown()).replace("\n", "<br>")
        else:
            content = markdowner.convert(self.export_to_markdown().replace("\\", "\\\\"))
        # TODO:实现MathJax本地化
        render = jinja2.Template(html_template).render(
            title=title,
            pico=pico,
            katexCss=katex_css,
            katexJs=katex_js,
            autoRender=auto_render,
            markdown=content,
            renderMathInElement=renderMathInElement,
            mermaid=mermaid,
        )
        return render

    def translate_file(self, file_path: Path | str | None = None, to_lang="中文", output_dir="./output",
                       formula=True,
                       code=True, output_format: Literal["markdown", "html"] = "markdown", refine=False,
                       custom_prompt_translate=None, refine_agent: Agent | None = None,
                       translate_agent: Agent | None = None,
                       save=True):
        if file_path is None:
            assert self.file_path is not None, "未输入文件路径"
            file_path = self.file_path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        self.read_file(file_path, formula=formula, code=code)
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        self.translate_markdown_by_agent(translate_agent, to_lang=to_lang, custom_prompt=custom_prompt_translate)
        if save:
            if output_format == "markdown":
                filename = f"{file_path.stem}_{to_lang}.md"
                self.save_as_markdown(filename=filename, output_dir=output_dir)
            elif output_format == "html":
                filename = f"{file_path.stem}_{to_lang}.html"
                self.save_as_html(filename=filename, output_dir=output_dir)
        return self

    async def translate_file_async(self, file_path: Path | str | None = None, to_lang="中文", output_dir="./output",
                                   formula=True,
                                   code=True, output_format: Literal["markdown", "html"] = "markdown",
                                   custom_prompt_translate=None, refine=False,
                                   refine_agent: Agent | None = None, translate_agent: Agent | None = None, save=True):
        if file_path is None:
            assert self.file_path is not None, "未输入文件路径"
            file_path = self.file_path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        await asyncio.to_thread(
            self.read_file,
            file_path,
            formula=formula,
            code=code
        )
        if refine:
            await self.refine_markdown_by_agent_async(refine_agent)
        await self.translate_markdown_by_agent_async(translate_agent, to_lang=to_lang,
                                                     custom_prompt=custom_prompt_translate)
        if save:
            if output_format == "markdown":
                filename = f"{file_path.stem}_{to_lang}.md"
                self.save_as_markdown(filename=filename, output_dir=output_dir)
            elif output_format == "html":
                filename = f"{file_path.stem}_{to_lang}.html"
                self.save_as_html(filename=filename, output_dir=output_dir)
        return self

    def translate_bytes(self, name: str, file: bytes, to_lang="中文", output_dir="./output",
                        formula=True,
                        code=True, output_format: Literal["markdown", "html"] = "markdown",
                        custom_prompt_translate=None,
                        refine=False,
                        refine_agent: Agent | None = None, translate_agent: Agent | None = None, save=True):
        self.read_bytes(name=name, file=file, formula=formula, code=code)
        if refine:
            self.refine_markdown_by_agent(refine_agent)
        self.translate_markdown_by_agent(translate_agent, to_lang=to_lang, custom_prompt=custom_prompt_translate)
        if save:
            if output_format == "markdown":
                filename = f"{name}_{to_lang}.md"
                self.save_as_markdown(filename=filename, output_dir=output_dir)
            elif output_format == "html":
                filename = f"{name}_{to_lang}.html"
                self.save_as_html(filename=filename, output_dir=output_dir)
        return self

    async def translate_bytes_async(self, name: str, file: bytes, to_lang="中文", output_dir="./output",
                                    formula=True,
                                    code=True, output_format: Literal["markdown", "html"] = "markdown",
                                    custom_prompt_translate=None, refine=False,
                                    refine_agent: Agent | None = None, translate_agent: Agent | None = None, save=True):
        await self.read_bytes_async(name=name, file=file, formula=formula, code=code)

        if refine:
            await self.refine_markdown_by_agent_async(refine_agent)
        await self.translate_markdown_by_agent_async(translate_agent, to_lang=to_lang,
                                                     custom_prompt=custom_prompt_translate)
        if save:
            if output_format == "markdown":
                filename = f"{name}_{to_lang}.md"
                self.save_as_markdown(filename=filename, output_dir=output_dir)
            elif output_format == "html":
                filename = f"{name}_{to_lang}.html"
                self.save_as_html(filename=filename, output_dir=output_dir)
        return self
