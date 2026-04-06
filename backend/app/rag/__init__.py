"""
RAG (Retrieval-Augmented Generation) Service for DevArchAI.

Provides documentation retrieval to enrich LLM prompts with relevant
DevSecOps context (CIS benchmarks, K8s security, Terraform best practices,
Docker security, CI/CD security).
"""

from app.rag.retriever import (
    DocEntry,
    RAGRetriever,
    RetrievalResult,
    get_retriever,
    retrieve_docs,
)

__all__ = [
    "DocEntry",
    "RAGRetriever",
    "RetrievalResult",
    "get_retriever",
    "retrieve_docs",
]
