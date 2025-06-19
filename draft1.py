import io, pydub, daft, friendli, weaviate

# --- 1. chunk audio ---
audio = pydub.AudioSegment.from_file("voice.mp3")
chunks = [audio[i:i+30_000] for i in range(0, len(audio), 30_000)]

cli = friendli.Client(api_key="FRIENDLI_KEY")
rows = []
for idx, seg in enumerate(chunks):
    buf = io.BytesIO(); seg.export(buf, format="wav")
    text = cli.speech_to_text(audio=buf.getvalue())["text"]
    vec  = cli.embed(text=text)
    rows.append({"text": text, "start": idx*30, "end": (idx+1)*30, "vector": vec})

# --- 2. dataframe ---
df = daft.from_pydict(rows)           # keeps things tidy for later ETL

# --- 3. upsert & query ---
w = weaviate.connect_to_wcs("https://y0xrqtdnseqitmbe2lcota.c0.us-west3.gcp.weaviate.cloud/", auth_api_key="WEAVIATE_KEY")
col = w.collections.get_or_create(
        name="Transcript",
        properties={"text":"text", "start":"number", "end":"number"},
        vectorizer_config={"vectorizer":"none"}
)
col.data.insert_many([{"text":r["text"], "start":r["start"], "end":r["end"], "vector":r["vector"]} for r in rows])

# search
qvec = cli.embed(text="mention of revenue plans?")
hits = col.query.near_vector(qvec, limit=3)
for h in hits.objects:
    print(f"[{h.properties['start']}-{h.properties['end']} s] {h.properties['text']}")
