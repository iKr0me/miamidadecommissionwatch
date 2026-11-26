"""Hybrid retrieval over the preview's read-only snapshot of agenda items."""
from pathlib import Path
import re
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class AgendaIndex:
    def __init__(self, db):
        cache = Path.home() / ".cache/mdcw"
        self.tokenizer = Tokenizer.from_file(str(cache / "tokenizer.json"))
        self.tokenizer.enable_padding()
        self.tokenizer.enable_truncation(max_length=192)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 3
        self.model = ort.InferenceSession(str(cache / "model.onnx"), options,
                                          providers=["CPUExecutionProvider"])
        self.rows = db.execute("select rowid,date,number,page,wording from items").fetchall()
        passages = [" ".join(row[-1].lower().split())[:1800] for row in self.rows]
        self.vectors = np.vstack([self.encode(passages[i:i+12]) for i in range(0,len(passages),12)])

    def encode(self, texts):
        batch = self.tokenizer.encode_batch(texts)
        inputs = {name: np.array([getattr(s, attr) for s in batch], dtype=np.int64)
                  for name, attr in [('input_ids','ids'),('attention_mask','attention_mask'),
                                     ('token_type_ids','type_ids')]}
        hidden = self.model.run(None, inputs)[0]
        mask = inputs['attention_mask'][:, :, None]
        pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1)
        return pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-10)

    def search(self, db, query):
        concept = query
        if re.search(r"\b(houses?|homes?)\b|places? to live", query, re.I):
            concept += " residential housing"
            if re.search(r"cheap|afford|cost", query, re.I):
                concept += " affordable housing rental"
        tokens = re.findall(r'[a-z0-9]+', concept.lower())
        if not tokens:
            return []
        exact = dict(db.execute("select rowid,rank from word_forms where word_forms match ? order by rank limit 30",
                                (" OR ".join(t for t in tokens if t not in {"a","to","the","near","of"}) or '""',)))
        scores = self.vectors @ self.encode([concept])[0]
        strongest = max([-v for v in exact.values()] or [1])
        ranked = []
        for row, similarity in zip(self.rows, scores):
            ident, date, number, page, wording = row
            if similarity < .32 and ident not in exact:
                continue
            score = similarity + .4 * -exact.get(ident,0) / strongest
            if number.lower() == query.strip().lower():
                score += 2
            ranked.append((score,date,number,page," ".join(wording.split())[:400]))
        return [row[1:] for row in sorted(ranked,reverse=True)[:10]]
