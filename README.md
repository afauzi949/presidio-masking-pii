# Presidio Free-Text Masking Service

Service masking untuk konten **free-text / unstructured** — target utama: dokumen Confluence yang sudah dikonversi ke markdown, sebelum masuk ke pipeline chunking/embedding RAG.

## Fitur

- **Masking PII umum**: EMAIL_ADDRESS, PHONE_NUMBER via Presidio predefined recognizer. PERSON sengaja tidak dipakai (lihat catatan model di bawah).
- **Masking kredensial teknis**: CREDENTIAL_KV, DB_CONNECTION_STRING, API_KEY, HOST_PORT, USERNAME via custom PatternRecognizer.
- **Segmentasi markdown**: Dokumen dipisah per elemen (prose, code block, tabel) sebelum diproses — mencegah markup memecah pattern matching.
- **Handler berbeda per tipe segmen**:
  - **Prose** → Presidio Analyzer penuh (NLP + pattern).
  - **Code block** → Key-based masking untuk bahasa terstruktur (env, yaml, json), regex fallback untuk bahasa lain.
  - **Tabel** → Key-based masking berdasarkan nama kolom.
- **Strategi masking**: `redact` (full mask) dan `partial` (sebagian tampil), konsisten dengan `masking-service` transaksi.
- **Konfigurasi hardcoded di kode** (`src/config/settings.py`) — entity list, strategy, key hints. Tidak ada `.env`; ubah lewat kode supaya perubahan konfigurasi ikut ter-review dan ter-versi lewat Git.

## Struktur

```
presidio-masking-service/
├── requirements.txt
├── pytest.ini
├── src/
│   ├── config/settings.py        # Konfigurasi hardcoded: threshold, entity list, key hints, model spaCy
│   ├── segmentation/
│   │   ├── markdown_parser.py    # Parse markdown → list[Segment]
│   │   └── segment_types.py      # Dataclass Segment
│   ├── recognizers/
│   │   ├── credential_patterns.py # Custom PatternRecognizer
│   │   └── registry.py            # AnalyzerEngine factory
│   ├── handlers/
│   │   ├── prose_handler.py       # Presidio Analyzer + Anonymizer
│   │   ├── code_block_handler.py  # Key-based + regex masking
│   │   └── table_handler.py       # Structural table masking
│   ├── masker.py                  # Orchestrator
│   └── api/
│       ├── main.py                # FastAPI app
│       └── schemas.py             # Pydantic schemas
└── tests/
    ├── test_markdown_parser.py
    ├── test_credential_recognizers.py
    ├── test_prose_handler.py
    ├── test_code_block_handler.py
    ├── test_table_handler.py
    └── test_masker.py
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

> **Catatan:** `en_core_web_sm` adalah model spaCy yang dipakai NlpEngine Presidio (lihat `src/recognizers/registry.py`). Service ini tidak memakai predefined recognizer PERSON, jadi model kecil sudah cukup — hanya dipakai untuk tokenization/lemma yang mendukung context-enhancement pada custom recognizer kredensial.

### 2. Jalankan service

```bash
uvicorn src.api.main:app --reload --port 8001
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
| `mask_redact_entities` | Entity yang di-redact penuh | `CREDENTIAL_KV,DB_CONNECTION_STRING,API_KEY` |
| `mask_partial_entities` | Entity yang di-partial mask | `EMAIL_ADDRESS,PHONE_NUMBER,HOST_PORT,USERNAME` |
| `credential_key_hints` | Key hints untuk code block & tabel | `password,passwd,pwd,...` |
| `table_sensitive_columns` | Kolom tabel yang otomatis sensitif | `password,secret,token,...` |

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
