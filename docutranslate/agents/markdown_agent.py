# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from dataclasses import dataclass

from .agent import Agent, AgentConfig
from ..glossary.glossary import Glossary


def get_original_markdown(prompt: str):
    match = re.search(r'<input>\n(.*)\n</input>', prompt, re.DOTALL)
    if match:
        return match.group(1)
    else:
        raise ValueError("无法从prompt中提取初始文本")


def generate_prompt(markdown_text: str, to_lang: str):
    return f"""
Treat the text input as markdown text and translate it into {to_lang},output translation ONLY. 
- NO explanations. NO notes. 
- For special tags or other non-translatable elements (like codes, brand names, specific jargon), keep them in their original form.
- All formulas, regardless of length, must be represented as valid, parsable LaTeX. They must be correctly enclosed by `$`, `\\(\\)`, or `$$`. If a formula is not formatted correctly, you must fix it.
- Remove or correct any obviously abnormal characters, but without altering the original meaning.
- When citing references, strictly preserve the original text; do not translate them. Examples of reference formats are as follows:
  [1] Author A, Author B. "Original Title". Journal, 2023.
  [2] 作者C. 《中文标题》. 期刊, 2022.
- Output the translated markdown text as plain text (not in a markdown code block, with no extraneous text).

The markdown text input:
<input>
 {markdown_text}
</input>
"""


@dataclass
class MDTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class MDTranslateAgent(Agent):
    def __init__(self, config: MDTranslateAgentConfig):
        super().__init__(config)
        self.to_lang = config.to_lang
        self.system_prompt = f"""
# Role
You are a professional machine translation engine.
"""
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\nEND\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            system_prompt += glossary.append_system_prompt(prompt)
        return system_prompt, prompt

    def send_chunks(self, prompts: list[str]):
        prompts = [generate_prompt(prompt, self.to_lang) for prompt in prompts]
        return super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                    error_result_handler=lambda prompt, logger: get_original_markdown(prompt))

    async def send_chunks_async(self, prompts: list[str]):
        prompts = [generate_prompt(prompt, self.to_lang) for prompt in prompts]
        return await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                error_result_handler=lambda prompt, logger: get_original_markdown(
                                                    prompt))

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
