# 🗣️ SpeakSeek

**Semantic search over meetings, talks, and tech events — powered by AI.**

SpeakSeek is an audio intelligence system that transforms recorded conversations into a searchable knowledge base. Upload full-length audio from events or meetings, and semantically search through everything that was said — by topic, speaker, or phrase.

---

## 🔧 Tech Stack

| Component | Tool |
|-----------|------|
| Transcription | [Friendli AI Whisper](https://friendli.ai/) (hosted ASR) |
| Embedding | Friendli AI Embeddings |
| Vector Database | [Weaviate](https://weaviate.io/) |
| Chunking & Orchestration | Python |
| Deployment | Local or Cloud (Fly.io, GCP, or Docker)

---

## 🧠 How It Works

1. **Audio Upload**  
   Upload `.mp3` or `.wav` audio files from meetings or talks.

2. **Transcription via Friendli Whisper**  
   Friendli’s Whisper API transcribes the audio to high-quality text.

3. **Chunking**  
   The transcript is segmented into coherent, semantic chunks (e.g. per sentence or paragraph).

4. **Vector Embedding**  
   Each chunk is embedded using Friendli's embedding API.

5. **Indexing in Weaviate**  
   Chunks + metadata (timestamp, speaker, session) are stored in Weaviate with vector search enabled.

6. **Semantic Search API**  
   A simple search interface lets you run natural language queries against the vector DB.

---

## 🔍 Example Use Cases

- Search: “What did the CTO say about LLMs?”
- Retrieve all comments about “product roadmap” in a 3-hour townhall
- Find moments where "security" was discussed across multiple events

---

## 🚀 Quickstart

### Requirements

- Python 3.10+
- Weaviate instance (local or cloud)
- Friendli API credentials

### Setup

```bash
git clone https://github.com/your-org/speakseek.git
cd speakseek
pip install -r requirements.txt
