from sentence_transformers import SentenceTransformer
from amem.memory_system import AgenticMemorySystem
from amem.retrievers import SimpleEmbeddingRetriever

model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
retriever = SimpleEmbeddingRetriever(model=model)

memory_system = AgenticMemorySystem(
    retriever=retriever,
    llm_backend="openai",
    llm_model="gpt-4o"
)