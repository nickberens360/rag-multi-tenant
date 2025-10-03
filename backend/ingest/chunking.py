from __future__ import annotations

import re
from typing import List

from langchain.docstore.document import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


class SectionAwareSplitter:
    """Split documents by sections (headers) first, then by characters.

    Provides a `.split_documents()` method compatible with LangChain splitters.
    """

    def __init__(self, ext: str):
        self.ext = (ext or "").lower().lstrip(".")
        # Base recursive splitter tuned per type
        if self.ext == "pdf":
            self.base = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
        elif self.ext in ("md", "markdown"):
            self.base = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        elif self.ext in ("html", "htm"):
            self.base = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        else:
            self.base = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    def _split_markdown_sections(self, text: str) -> List[Document]:
        headers = [("#", "h1"), ("##", "h2"), ("###", "h3")]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
        try:
            return splitter.split_text(text)
        except Exception:
            # Fallback: no header-based split
            return [Document(page_content=text)]

    def _split_html_sections(self, text: str) -> List[Document]:
        # Lightweight sectioning by h1-h3 tags
        # Split at start of <h[1-3]> or markdown-like headings inside HTML body
        pattern = re.compile(r"(<h[1-3][^>]*>.*?</h[1-3]>)", re.IGNORECASE | re.DOTALL)
        parts = pattern.split(text)
        if not parts or len(parts) == 1:
            return [Document(page_content=text)]
        docs: List[Document] = []
        buffer = ""
        for part in parts:
            if pattern.match(part):
                if buffer.strip():
                    docs.append(Document(page_content=buffer))
                buffer = part
            else:
                buffer += part
        if buffer.strip():
            docs.append(Document(page_content=buffer))
        return docs if docs else [Document(page_content=text)]

    def split_documents(self, documents: List[Document]) -> List[Document]:
        out: List[Document] = []
        for doc in documents or []:
            content = doc.page_content or ""
            # First split into sections by headers where applicable
            if self.ext in ("md", "markdown"):
                sections = self._split_markdown_sections(content)
            elif self.ext in ("html", "htm"):
                sections = self._split_html_sections(content)
            else:
                sections = [Document(page_content=content)]

            # Then recurse within each section with the base splitter
            section_docs = [Document(page_content=s.page_content, metadata={**doc.metadata}) for s in sections]
            out.extend(self.base.split_documents(section_docs))
        return out


def splitter_for_ext(ext: str) -> SectionAwareSplitter | RecursiveCharacterTextSplitter:
    ext = (ext or "").lower().lstrip(".")
    if ext in ("md", "markdown", "html", "htm", "pdf"):
        return SectionAwareSplitter(ext)
    return SectionAwareSplitter(ext)
