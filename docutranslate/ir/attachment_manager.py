# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from typing import Literal

from docutranslate.ir.document import Document

AttachMentIdentifier = Literal["glossary", "mineru", "mineru_deploy", "docling", "md_cached"]


class AttachMent:
    def __init__(self, identifier: AttachMentIdentifier, document: Document):
        self.identifier = identifier
        self.document = document

    def __repr__(self):
        return self.document.name

class AttachMentManager:
    def __init__(self):
        self.attachment_dict: dict[AttachMentIdentifier, Document] = {}

    def add_document(self, identifier: AttachMentIdentifier, document: Document):
        self.attachment_dict[identifier] = document

    def add_attachment(self, attachment: AttachMent):
        self.attachment_dict[attachment.identifier] = attachment.document
