# from langchain_nomic import NomicEmbeddings

# embeddings = NomicEmbeddings(
#     model="nomic-embed-text-v1.5",
#     inference_mode="local",
#     # dimensionality=256,
#     # Nomic's `nomic-embed-text-v1.5` model was [trained with Matryoshka learning](https://blog.nomic.ai/posts/nomic-embed-matryoshka)
#     # to enable variable-length embeddings with a single model.
#     # This means that you can specify the dimensionality of the embeddings at inference time.
#     # The model supports dimensionality from 64 to 768.
#     # inference_mode="remote",
#     # One of `remote`, `local` (Embed4All), or `dynamic` (automatic). Defaults to `remote`.
#     # api_key=... , # if using remote inference,
#     # device="cpu",
#     # The device to use for local embeddings. Choices include
#     # `cpu`, `gpu`, `nvidia`, `amd`, or a specific device name. See
#     # the docstring for `GPT4All.__init__` for more info. Typically
#     # defaults to CPU. Do not use on macOS.
# )

# # Create a vector store with a sample text
# from langchain_core.vectorstores import InMemoryVectorStore

# text = "LangChain is the framework for building context-aware reasoning applications"

# vectorstore = InMemoryVectorStore.from_texts(
#     [text],
#     embedding=embeddings,
# )

# # Use the vectorstore as a retriever
# retriever = vectorstore.as_retriever()

# # Retrieve the most similar text
# retrieved_documents = retriever.invoke("What is LangChain?")

# # show the retrieved document's content
# retrieved_documents[0].page_content

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("nomic-ai/modernbert-embed-base", truncate_dim=256)

query_embeddings = model.encode([
    "search_query: What is TSNE?",
    "search_query: Who is Laurens van der Maaten?",
])
doc_embeddings = model.encode([
    "search_document: TSNE is a dimensionality reduction algorithm created by Laurens van Der Maaten",
])
print(query_embeddings.shape, doc_embeddings.shape)
# (2, 256) (1, 256)

similarities = model.similarity(query_embeddings, doc_embeddings)
print(similarities)
# tensor([[0.7759],
#         [0.3419]])
