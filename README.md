# DocumentDigesterChatbot

> **IMPORTANT — embedding model:** With the bundled vector database, only use
> [Unsloth EmbeddingGemma 2 GGUF](https://huggingface.co/unsloth/embeddinggemma-2-GGUF)
> for query embeddings. The index was built with `embeddinggemma-2-BF16.gguf`;
> use that same file for the closest match. Using a different embedding model
> can produce incompatible vectors and poor or incorrect retrieval results,
> even if the vector dimensions match. This restriction applies to embeddings,
> not the chat inference model.
>
> **IMPORTANT — database:** Extract [chroma_bundle.zip](artifacts/chroma_bundle.zip)
> into `data/` before starting the app. Without the extracted database, no
> documentation can be fetched. The app does not create or populate it for you.

The application answers questions about Git, Docker, LangChain, and LangGraph.
Streamlit sends questions to FastAPI, which embeds them, retrieves document
chunks from Chroma, and sends the question and context to the chat model.
Embedding and inference providers are selected independently in `.env`.

## 1. Prepare the Python environment and database

Run commands from the repository root. Use Python 3.12 or newer. If dependencies
are already installed in `.venv`, activate it and skip the creation/install steps:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```


Extract the entire archive, including its vector index files, into the data directory.

```bash
mkdir -p data
unzip -n artifacts/chroma_bundle.zip -d data
```

The resulting layout must include:

```text
data/
├── build_metadata.json
└── chroma/
    ├── chroma.sqlite3
    └── <index directory>/
        └── ...
```


For a new setup, copy the template:

```bash
mv .env.example .env
```

Keep these values for the bundled index:

```dotenv
CHROMA_PATH=./data/chroma
COLLECTION_NAME=developer_docs
EMBEDDING_DIMENSION=768
NORMALIZE_EMBEDDINGS=true
QUERY_PROMPT_NAME=QuestionAnswering
RETRIEVAL_TOP_K=4
```

`CHROMA_PATH` is relative to the project root, or can be an absolute path to an
existing database. The other index details are recorded in
[data/build_metadata.json](data/build_metadata.json).

## 2. Start the embedding provider

Use one of the following options. Either can be combined with either inference
provider in the next section. Replace placeholder paths with local files.

### llama.cpp
Set the env vars as follows:

```dotenv
EMBEDDING_BACKEND=llama_cpp
EMBEDDING_API_URL=http://127.0.0.1:8081/v1/embeddings
EMBEDDING_API_MODEL=embeddinggemma-2
EMBEDDING_HTTP_TIMEOUT=180
```

In a dedicated terminal, start the same BF16 GGUF used for indexing:

```bash
llama-server \
  --model "/absolute/path/to/embeddinggemma-2-BF16.gguf" \
  --alias embeddinggemma-2 \
  --host 127.0.0.1 \
  --port 8081 \
  --embedding \
  --pooling mean \
  --ctx-size 2048 \
  --batch-size 2048 \
  --ubatch-size 2048 \
  --parallel 1
```


### Ollama embeddings

Set:

```dotenv
EMBEDDING_BACKEND=ollama
EMBEDDING_API_URL=http://127.0.0.1:11434/api/embed
EMBEDDING_API_MODEL=embeddinggemma-2
EMBEDDING_HTTP_TIMEOUT=180
```

Start `ollama serve` in a dedicated terminal if Ollama is not already running
as a service. Import the same local GGUF by creating a `Modelfile.embedding`:

```text
FROM /absolute/path/to/embeddinggemma-2-BF16.gguf
```

Register it with your installed Ollama version supporting EmbeddingGemma 2:

```bash
ollama create embeddinggemma-2 -f Modelfile.embedding
```


You do not need a second Ollama server when using Ollama for both embeddings and
inference.

The application also supports `sentence_transformers` for embedding generation,
but it cannot load GGUF files. That backend requires a complete local Hugging
Face/SentenceTransformers model directory in `MODEL_ID`. Use the GGUF setup above
for the supplied database; alternative embedding models require rebuilding the
index with compatible settings.

## 3. Choose the chat inference provider

### Option A: llama.cpp inference

Set:

```dotenv
INFERENCE_BACKEND=llama_cpp
INFERENCE_MODEL=gemma-e2b
INFERENCE_BASE_URL=http://127.0.0.1:8082/v1
INFERENCE_TEMPERATURE=0.2
```

In another terminal, start your local instruction-tuned Gemma E2B GGUF:

```bash
llama-server \
  --model "/absolute/path/to/gemma-e2b-it.gguf" \
  --alias gemma-e2b \
  --host 127.0.0.1 \
  --port 8082 \
  --ctx-size 8192 \
  --parallel 1 \
  --jinja
```

The model name must match `--alias`. The base URL ends at `/v1`, not
`/chat/completions`.

### Option B: Ollama inference

Set:

```dotenv
INFERENCE_BACKEND=ollama
INFERENCE_MODEL=gemma4:e2b
INFERENCE_BASE_URL=http://127.0.0.1:11434
INFERENCE_TEMPERATURE=0.2
```

Start `ollama serve` if it is not already running. If `gemma4:e2b` is already
installed, confirm it with `ollama list` and use it directly.

To import an already downloaded instruction-tuned GGUF instead, create a
`Modelfile.chat`:

```text
FROM /absolute/path/to/gemma-e2b-it.gguf
PARAMETER num_ctx 8192
```

Register the local model:

```bash
ollama create gemma4:e2b -f Modelfile.chat
```

If using an existing model, configure its context allocation to accommodate the
retrieved chunks and answer; the imported example above allocates 8192 tokens.
The chat model loads when the application sends a request; an interactive
`ollama run` session is not required.

## 4. Start FastAPI and Streamlit

Keep the selected model servers running. In a new terminal at the project root:

```bash
source .venv/bin/activate
python -m uvicorn app.app:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal at the project root:

```bash
source .venv/bin/activate
python -m streamlit run app/streamlit.py
```

Open [the Streamlit app](http://localhost:8501). FastAPI's interactive API page is
at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

| Component | Address |
| --- | --- |
| llama.cpp embeddings, if selected | `127.0.0.1:8081` |
| llama.cpp inference, if selected | `127.0.0.1:8082` |
| Ollama, if selected for either model | `127.0.0.1:11434` |
| FastAPI | `127.0.0.1:8000` |
| Streamlit | `localhost:8501` |

## Troubleshooting

- **HTTP 503:** Inspect the FastAPI terminal for the underlying embedding,
  database, or inference error. Verify the selected servers are running and
  their model names and ports match `.env`.
- **Missing collection/database:** Check extraction produced
  `data/chroma/chroma.sqlite3` and the vector index directory, and that
  `COLLECTION_NAME=developer_docs`.
- **Poor retrieval:** Use the required embedding GGUF and the index-compatible
  dimensions, normalization, pooling, and query prefix. Nearest chunks are not
  automatically proof that a claim is correct.
- **UI timeout:** Streamlit waits 120 seconds for the backend. Slow generation
  can exceed this; reduce `RETRIEVAL_TOP_K` or adjust model server resources.
- **Models fail to load:** Check that your provider supports the model
  architecture and that both models plus their context buffers fit available
  RAM/VRAM. Adjust server context/offloading settings for your hardware.

Provider references: [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
[Ollama GGUF import](https://docs.ollama.com/import), and
[Ollama embedding endpoint](https://docs.ollama.com/api/embed).
