# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import csv
import re
from io import StringIO

from docutranslate.ir.document import Document


class Glossary:
    def __init__(self, glossary_dict: dict[str,str] = None):
        if glossary_dict:
            self.glossary_dict = glossary_dict
        else:
            self.glossary_dict={}


    def update(self, update_dict: dict[str,str]):
        for src, dst in update_dict.items():
            if src.strip().lower() not in self.glossary_dict:
                self.glossary_dict[src.strip().lower()] = dst

    def append_system_prompt(self, text: str):
        flag = False
        prompt = """
        Please refer to the glossary for the translation of terms that appear in the glossary.
        Here is the reference glossary:
        """
        for src, dst in self.glossary_dict.items():
            if src.lower() in text.lower():
                prompt += f"{src}=>{dst}\n"
                flag = True
        prompt += "Glossary ends\n"
        if flag:
            return prompt
        else:
            return ""

    @staticmethod
    def glossary_dict2csv(glossary_dict: dict[str, str], delimiter=",", stem="glossary_gen") -> Document:
        csv_rows = [[src, dst] for src, dst in glossary_dict.items()]
        content = StringIO()
        writer = csv.writer(content, delimiter=delimiter)
        writer.writerow(['src', 'dst'])
        writer.writerows(csv_rows)
        bom = '\ufeff'
        content_with_bom = bom + content.getvalue()
        return Document.from_bytes(content=content_with_bom.encode("utf-8"), suffix=".csv", stem=stem)
