import logging
from typing import Any, Dict, List

from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import CommaSeparatedListOutputParser, PydanticOutputParser
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Constants for text processing limits
_MAX_TEXT_LENGTH_FOR_TOPICS = 2000
_MAX_SNIPPET_LENGTH_FOR_RERANKING = 500
_MAX_DOCUMENT_LENGTH_FOR_CONTEXT = 3000


# Define a Pydantic model for structured output
class QueryAnalysis(BaseModel):
    """Structured representation of a query's analysis."""

    query: str
    topics: List[str]
    complexity: str
    intent: str


def analyze_query_with_llm(llm: BaseLanguageModel, query: str) -> Dict[str, Any]:
    """
    Analyze a user's query using an LLM to extract topics, complexity, and intent.
    """
    parser = PydanticOutputParser(pydantic_object=QueryAnalysis)

    prompt = PromptTemplate(
        template="""
Analyze the user's query and provide a structured analysis in JSON format.
The query is: "{query}"

Your analysis should identify the following:
1.  **topics**: A list of the main subjects or topics the query is about.
    Choose from the following list or add a new one if necessary:
    - technical
    - experience
    - skills
    - about
    - creative
    - project
    - general
2.  **complexity**: The estimated complexity of the query.
    Choose one: simple, moderate, complex.
3.  **intent**: The user's likely intent.
    Choose one: question, retrieval, explanation, general.

{format_instructions}
""",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        response = chain.invoke({"query": query})
        # Robust response conversion
        if hasattr(response, "dict"):
            result: Dict[str, Any] = response.dict()
            return result
        elif isinstance(response, dict):
            return response
        elif hasattr(response, "__dict__"):
            result_vars: Dict[str, Any] = vars(response)
            return result_vars
        else:
            logger.warning(f"Unexpected response type: {type(response)}; using default fallback.")
            return {
                "query": query,
                "topics": ["general"],
                "complexity": "simple",
                "intent": "general",
            }
    except Exception as e:
        logger.error(f"Error analyzing query with LLM: {e}")
        # Fallback to a simple default
        return {
            "query": query,
            "topics": ["general"],
            "complexity": "simple",
            "intent": "general",
        }


def extract_topics_with_llm(llm: BaseLanguageModel, text: str) -> List[str]:
    """
    Extract relevant topics from a text chunk using an LLM.
    """
    output_parser = CommaSeparatedListOutputParser()

    prompt = PromptTemplate(
        template="""
You are an expert at analyzing text and extracting key topics.
Analyze the following text chunk and extract a comma-separated list of 1-5 main topics that describe its content.
The topics should be concise and relevant.
Choose from the following list if applicable, but you can also generate new topics if needed:
- technical
- experience
- skills
- about
- creative
- project
- personal
- code
- documentation

Text chunk:
"{text}"

Your comma-separated list of topics:
""",
        input_variables=["text"],
    )

    chain = prompt | llm | output_parser

    try:
        # Limit text size to avoid excessive token usage
        truncated_text = text[:_MAX_TEXT_LENGTH_FOR_TOPICS]

        response = chain.invoke({"text": truncated_text})
        # Sanitize and clean up topics
        return [topic.strip().lower() for topic in response if topic.strip()]
    except Exception as e:
        logger.error(f"Error extracting topics with LLM: {e}")
        # Fallback to a default topic
        return ["general"]


def rerank_documents_with_llm(llm: BaseLanguageModel, query: str, documents: List[Document]) -> List[Document]:
    """
    Re-rank a list of documents based on their relevance to a query using an LLM.
    """
    if not documents:
        return []

    output_parser = CommaSeparatedListOutputParser()

    document_snippets = "\n".join(
        [
            f"Document {i}: {doc.page_content[:_MAX_SNIPPET_LENGTH_FOR_RERANKING]}"
            f"{'...' if len(doc.page_content) > _MAX_SNIPPET_LENGTH_FOR_RERANKING else ''}"
            for i, doc in enumerate(documents)
        ]
    )

    prompt = PromptTemplate(
        template="""
You are an expert relevance ranker. I will provide you with a user query and a list of document
snippets, each with an index.
Your task is to return a comma-separated list of the indices, ordered from most relevant to least relevant.
Only return the indices that are relevant to the query.

User Query: "{query}"

Documents:
{document_snippets}

Re-ordered list of relevant indices (most relevant first):
""",
        input_variables=["query", "document_snippets"],
    )

    chain = prompt | llm | output_parser

    try:
        response = chain.invoke({"query": query, "document_snippets": document_snippets})

        # Validate response format
        if not isinstance(response, list) or not response:
            logger.error(f"LLM response is not a non-empty list: {response}. Falling back to original order.")
            return documents

        # Ensure all items are strings (or convertible to int)
        if not all(isinstance(i, (str, int)) for i in response):
            logger.error(f"LLM response list contains invalid items: {response}. Falling back to original order.")
            return documents

        reordered_indices = []
        seen_indices = set()
        for i in response:
            try:
                idx = int(i.strip())
                if idx < 0 or idx >= len(documents):
                    logger.warning(f"LLM returned out-of-range index '{idx}', skipping it.")
                    continue
                if idx in seen_indices:
                    logger.warning(f"LLM returned duplicate index '{idx}', skipping duplicate.")
                    continue
                reordered_indices.append(idx)
                seen_indices.add(idx)
            except (ValueError, TypeError):
                logger.warning(f"LLM returned a non-integer index '{i}', skipping it.")

        if not reordered_indices:
            logger.error("No valid indices returned by LLM. Falling back to original order.")
            return documents

        # Create a new list of documents in the re-ordered sequence
        reordered_docs = [documents[i] for i in reordered_indices]

        return reordered_docs
    except Exception as e:
        logger.error(f"Error re-ranking documents with LLM: {e}")
        # Fallback to original order if re-ranking fails
        return documents


def generate_document_context(llm: BaseLanguageModel, content: str, file_name: str, file_type: str) -> str:
    """
    Generate a concise document context/summary that will be prepended to chunks.

    This creates contextual information about the document that helps with retrieval.
    """
    prompt = PromptTemplate(
        template="""
You are analyzing a document to create a brief contextual summary.
Create a 1-2 sentence summary that describes what this document is about and its main purpose.
This summary will be used to provide context for search chunks.

Document filename: {file_name}
Document type: {file_type}
Document content (first part):
{content}

Write a concise context summary (1-2 sentences):
""",
        input_variables=["content", "file_name", "file_type"],
    )

    chain = prompt | llm

    try:
        # Limit content size to avoid excessive token usage
        truncated_content = content[:_MAX_DOCUMENT_LENGTH_FOR_CONTEXT]

        response = chain.invoke({"content": truncated_content, "file_name": file_name, "file_type": file_type})

        # Extract text from response
        if hasattr(response, "content"):
            context = str(response.content).strip()
        elif isinstance(response, str):
            context = response.strip()
        else:
            context = str(response).strip()

        # Validate and clean the context
        if context and len(context) > 10:  # Ensure we got a meaningful response
            return context
        else:
            # Fallback to basic context if LLM response is poor
            return f"This is content from {file_name}, a {file_type} document."

    except Exception as e:
        logger.error(f"Error generating document context with LLM: {e}")
        # Fallback to basic context
        return f"This is content from {file_name}, a {file_type} document."
