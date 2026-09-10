# Presidio Free-Text Masking Service

Service masking untuk konten **free-text / unstructured** — target utama: dokumen Confluence yang sudah dikonversi ke markdown, sebelum masuk ke pipeline chunking/embedding RAG.

## Cara Kerja

Skema "restrukturisasi + Presidio + replace-balik" 

1. **Segmentasi** — dokumen markdown asli dipisah per elemen: `prose`, `code_block`, `table` (`src/segmentation/markdown_parser.py`). Markdown asli disimpan utuh untuk langkah replace di akhir.
2. **Restrukturisasi** — tiap segmen diubah jadi teks polos yang bisa dibaca Presidio (`src/reconstruction/`):
   - `table` → `table_to_sentence()`: baris "Header: value" per field, per row.
   - `code_block` → `code_block_to_lines()`: fence dibuang; JSON diratakan (flatten) jadi "key: value"; label/value yang terpisah baris digabung lewat `kv_joiner`.
   - `prose` → `strip_markdown()`: markup (`**`, `` ` ``, `#`, `-`, dll.) dibuang, isi teks (termasuk isi inline code) dipertahankan.
3. **Deteksi** — semua hasil restrukturisasi digabung jadi **satu** teks, dianalisis Presidio **sekali** untuk seluruh dokumen (regex + NER + custom recognizer + context word) — satu sumber kebenaran untuk semua jenis segmen, tidak ada whitelist nama kolom/key yang perlu di-maintain manual.
4. **Replace-balik** — literal value yang terdeteksi dikumpulkan (dedup, urut dari yang terpanjang dulu supaya substring seperti `"admin"` di dalam `"admin_prod"` tidak rusak duluan), lalu diganti **langsung ke markdown asli** dengan placeholder seragam `<REDACTED>` (`src/replace_engine.py`). Karena masking terjadi lewat replace ke dokumen asli (bukan menggabungkan ulang segmen yang masing-masing sudah di-mask), format tabel/list/heading/code fence di output tetap utuh.

## Fitur

- **Masking PII umum**: EMAIL_ADDRESS, PHONE_NUMBER via Presidio predefined recognizer. 
- **Masking kredensial teknis**: CREDENTIAL_KV, DB_CONNECTION_STRING, API_KEY, HOST_PORT, USERNAME via custom PatternRecognizer — span hasil deteksinya cuma mencakup value (bukan label/kutip/backtick di sekitarnya), supaya replace-balik ke markdown asli presisi.
- **Segmentasi markdown**: mencegah markup memecah pattern matching, dan memberi bentuk yang tepat per jenis elemen (tabel/code block/prose) sebelum dianalisis.
- **Placeholder seragam**: semua entity yang terdeteksi diganti `<REDACTED>` — tidak membocorkan jenis data apa yang dimask.
- **Konfigurasi hardcoded di kode** (`src/config/settings.py`) — entity list, threshold, model spaCy. 

## Struktur

```
presidio-masking-service/
├── plan.md
├── requirements.txt
├── pytest.ini
├── src/
│   ├── config/settings.py                     # Konfigurasi hardcoded: threshold, entity list, model spaCy
│   ├── segmentation/
│   │   ├── markdown_parser.py                 # Parse markdown → list[Segment]
│   │   └── segment_types.py                   # Dataclass Segment
│   ├── recognizers/
│   │   ├── credential_patterns.py             # Custom PatternRecognizer (span = value only)
│   │   └── registry.py                        # AnalyzerEngine factory (NlpEngine model kecil)
│   ├── reconstruction/
│   │   ├── table_to_sentence.py                # table → "Header: value" per baris
│   │   ├── code_block_to_lines.py              # code block → baris key-value (fence dibuang)
│   │   ├── kv_joiner.py                        # gabungkan label/value yang terpisah baris
│   │   └── strip_markdown.py                   # prose → plain text (markup dibuang)
│   ├── replace_engine.py                       # kumpulkan literal value + replace ke markdown asli
│   ├── masker.py                               # Orchestrator
│   └── api/
│       ├── main.py                             # FastAPI app
│       └── schemas.py                          # Pydantic schemas
└── tests/
    ├── test_markdown_parser.py
    ├── test_credential_recognizers.py
    ├── test_strip_markdown.py
    ├── test_kv_joiner.py
    ├── test_table_to_sentence.py
    ├── test_code_block_to_lines.py
    ├── test_replace_engine.py
    └── test_masker.py
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

> **Catatan:** `en_core_web_sm` adalah model spaCy yang dipakai NlpEngine Presidio (lihat `src/recognizers/registry.py`). dipakai untuk tokenization/lemma yang mendukung context-enhancement pada custom recognizer kredensial.

### 2. Jalankan service

```bash
uvicorn src.api.main:app --reload --port 8002
```

## API

### `POST /mask-text`

**Request:**
```json
{
  "content": "# Dokumentasi\n\npassword=mySecret\n"
}
```

**Response:**
```json
{
  "content": "# Dokumentasi\n\npassword=<REDACTED>\n"
}
```

### `GET /health`

```json
{"status": "ok", "service": "presidio-masking-service"}
```

## Konfigurasi

Tidak ada `.env` — semua nilai hardcoded di [`src/config/settings.py`](src/config/settings.py). Untuk mengubahnya, edit langsung field di class `Settings` (perubahan konfigurasi jadi ter-review & ter-versi lewat Git):

| Field | Deskripsi | Nilai saat ini |
|---|---|---|
| `presidio_language` | Bahasa Presidio | `en` |
| `presidio_score_threshold` | Minimum confidence score | `0.6` |
| `spacy_model_name` | Model spaCy untuk NlpEngine | `en_core_web_sm` |
| `presidio_entities` | Daftar entity yang di-detect | `EMAIL_ADDRESS,PHONE_NUMBER,CREDENTIAL_KV,DB_CONNECTION_STRING,API_KEY,HOST_PORT,USERNAME` |

Placeholder replace (`<REDACTED>`) hardcoded di `src/replace_engine.py` (`DEFAULT_PLACEHOLDER`), sama untuk semua entity — bukan per jenis, dan bukan strategi redact/partial seperti versi sebelumnya (lihat `plan.md` bagian "Keputusan Terbuka").

## Testing

```bash
pytest
```

Atau per modul:

```bash
pytest tests/test_markdown_parser.py -v
pytest tests/test_credential_recognizers.py -v
pytest tests/test_masker.py -v
```

## Integrasi ke Pipeline RAG

Panggil endpoint ini tepat **setelah** konversi Confluence → markdown, **sebelum** tahap chunking/embedding:

```
Confluence → markdown → [POST /mask-text] → chunking → embedding → vector DB
```

Ini memastikan credential tidak terkirim ke embedding API eksternal maupun tersimpan di payload vector DB.
