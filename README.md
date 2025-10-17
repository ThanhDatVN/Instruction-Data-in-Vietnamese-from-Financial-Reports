# ViFin-Gen: Instruction Data from Vietnamese Financial Reports

*(Generating instruction-style training data from scanned Vietnamese financial reports)*

---

## Project summary

This repository contains the code, pipeline configuration and artifacts used to build an **instruction-style dataset** from **scanned Vietnamese financial reports (BCTC)** collected from the SSC public portal. The dataset supports three downstream tasks: **Question Answering (QA)**, **Sentiment Analysis (SA)** and **Named Entity Recognition (NER)**. The pipeline covers: crawling (Selenium), OCR (ABBYY FineReader), text extraction (pdfplumber), chunking + question generation + answer generation (Gemini-2.5-flash), automatic filtering (Mistral embeddings & rules), and supervised fine-tuning experiments on small/medium LLMs.

---

## Key facts / highlights

* Source: public SSC portal `https://congbothongtin.ssc.gov.vn` (PDF scans, 2020–2025).
* Raw PDFs collected: **>10,000**.
* Instruction examples generated (raw): **109,582**.
* Instruction examples after filtering (SFT-ready): **46,303**.
* Tasks: **QA, SA, NER** (each item labeled with task & difficulty: `Easy|Medium|Hard`).
* Primary models used for evaluation & fine-tuning: Gemma3 (Gemma3-FT), LLaMA 3.2, Qwen 3B.
* Evaluation: ROUGE (1/2/L) + human/LLM-as-a-judge metrics (Correctness, Relevance, Completeness). Example ROUGE highlights: Gemma3-FT (ROUGE-1: 0.712; ROUGE-L: 0.632).

---

> **Important:** Large files (raw PDF, OCR outputs, model checkpoints) should **not** be pushed to the Git repository. Use `.gitignore` and **Git LFS** if you must store large binaries.

---

## Minimal JSON schema for instruction data (SFT-ready)

Each example follows a unified schema:

```json
{
  "instruction": "What is the company's revenue in Q2 2024?",
  "input": {
    "chunk_id": "BCTC_2024_VNM_0001_chunk_0003",
    "company": "Công ty A",
    "ticker": "AAA",
    "report_type": "Quarterly report",
    "report_date": "2024-08-15",
    "content": "..."
  },
  "output": "Revenue in Q2 2024 is 1,234,567,000 VND (as reported).",
  "difficulty": "Medium_QA"
}
```

The final dataset is stored as JSON Lines (`.jsonl`) or a single JSON array depending on downstream tooling.

---

## How to reproduce (high-level, step-by-step)

> **Prerequisites**: Python 3.8+, Chrome + ChromeDriver, ABBYY FineReader (HotFolder), access to LLM APIs (Gemini-2.5-flash or alternative), sufficient disk space.

1. **Clone this repo**

   ```bash
   git clone https://github.com/ThanhDatVN/Instruction-Data-in-Vietnamese-from-Financial-Reports.git
   cd Instruction-Data-in-Vietnamese-from-Financial-Reports
   ```

2. **Create Python environment & install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   .venv\Scripts\activate         # Windows
   pip install -r requirements.txt
   ```

   Example `requirements.txt` items: `selenium`, `pdfplumber`, `tqdm`, `pandas`, `transformers`, `sentencepiece`, `faiss-cpu` (or `faiss-gpu`), `torch`, `openai` or SDK for the LLM provider.

3. **Crawl PDFs (Selenium)**

   * Configure `scripts/crawl_selenium.py` with `OUTPUT_FOLDER` and `page range`.
   * Run:

     ```bash
     python scripts/crawl_selenium.py --start 1 --end 695 --output data/raw_pdfs
     ```
   * The script records `download_log.txt` to avoid duplicates and supports resume.

4. **OCR (ABBYY FineReader HotFolder)**

   * ABBYY HotFolder processes PDF batches and outputs searchable PDFs and `.txt`.
   * Follow `docs/02_ocr_abbyy_hotfolder.md` for HotFolder configuration (Vietnamese language, 300 DPI recommended).
   * Output layout: `data/ocr_output/folder_{n}_txt/`

5. **Extract text with pdfplumber**

   ```bash
   python scripts/extract_pdfplumber.py --input data/ocr_output --output data/txt
   ```

6. **Chunk & generate instructions (LLM prompting)**

   * Use `notebooks/04_chunk_and_prompting.ipynb` or `scripts/chunk_generate.py` to:

     * Break each document into chunks (400–800 tokens target, keep context fields),
     * Send chunk -> Gemini-2.5-flash prompt to generate 3–6 questions and classify difficulty/task.
   * Example prompt instructions are included in notebook/scripts.

7. **Generate answers (LLM)**

   * Use `scripts/gen_answers.py` to produce answers for each (chunk, question) pair. The model must be instructed **not to hallucinate** and to reply `"Thông tin không có trong dữ liệu"` (or `"Information not present in data"`) when data is missing.

8. **Validate & filter**

   * Run `scripts/filter_merge.py` to:

     * Validate JSON schema,
     * Check instruction+input+output token length (512–2048 tokens) using Mistral-7B embeddings/tokenization,
     * Remove duplicates,
     * Move good / repairable / error examples to separate folders.
   * Merge valid examples into `instruction_data_final/46303_instruction_data.jsonl`.

9. **Fine-tune / SFT experiments**

   * Use your chosen training recipe (LoRA recommended for resource-limited setups). Example configs (LoRA rank 16, batch size 32, 3 epochs) are in `docs/finetune_configs/`.
   * Example (LoRA + PEFT):

     ```bash
     python train_sft.py \
       --train_file data/instruction_data_final/46303_instruction_data.jsonl \
       --model_name_or_path <base-model> \
       --output_dir models/gemma3-ft \
       --lora_rank 16 --per_device_train_batch_size 32 --num_train_epochs 3
     ```

10. **Evaluate**

    * Evaluate on the held-out testset (600 samples: 200 per task) using ROUGE + LLM-as-a-judge scripts in `notebooks/05_evaluation.ipynb`.

---

## Reproducibility notes & operational details

* **Resumeable pipeline**: every step writes intermediate artifacts to disk (`folder_{n}_step1`, `folder_{n}_step2`, `*_good`, `*_error`) so the pipeline can resume after failures or rate limits.
* **API rate-limiting**: pipeline supports multiple API keys, exponential backoff, random delays, and per-key queues.
* **OCR quality control**: store ABBYY logs and a per-file confidence score. Low-confidence files can be triaged for manual review.
* **Token counting & filtering**: use Mistral tokenization/embeddings to measure (instruction + input + output) token length. Keep examples with 512–2048 tokens for SFT.
* **Logging**: all steps produce logs with timestamps and error categories for auditing.

---

## Dataset statistics (summary)

* Raw generated examples: **109,582**
* After validation & token filtering: **46,303** (SFT-ready)
* Split by task (after filter):

  * QA: 32,060
  * SA: 12,015
  * NER: 2,228

---

## Results (high-level)

* Example automatic metrics (ROUGE F1 on held-out testset):

  * Gemma3-FT — ROUGE-1: **0.712**, ROUGE-2: **0.629**, ROUGE-L: **0.632**
  * Gemma3-raw — ROUGE-1: 0.664, ROUGE-L: 0.584
  * FT-Llama3.2 — ROUGE-1: 0.668, ROUGE-L: 0.572
  * raw-Llama3.2 — ROUGE-1: 0.614, ROUGE-L: 0.518
* Human/LLM-as-a-judge scores (1–5 average) indicate modest but consistent improvements after SFT. Gemma3-FT performed best across Correctness / Relevance / Completeness.

> Note: numeric results are summarized from experiments reported in the project — see `docs/report.pdf` or the `docs/` folder for full tables/figures.

---

## Limitations & caveats

* **OCR errors** and complicated table layouts decrease data quality. Manual checks or improved table extraction are recommended.
* **Temporal bias**: dataset skewed heavily to 2024 reports (~68%). Consider stratified sampling or collecting older reports.
* **Task imbalance**: QA dominates; NER has relatively few examples. Consider targeted labeling to rebalance.
* **Large raw data**: raw PDFs and converted text are large and **must not** be pushed to GitHub. Use external storage (S3, Google Cloud Storage) or Git LFS with quotas.

---

## Recommendations for repo hygiene (practical)

1. Add a `.gitignore` that excludes `data/raw_pdfs/`, `data/ocr_output/`, `models/`, `*.ckpt`, `*.pt`, `*.bin`.
2. Use **Git LFS** for necessary large binary files (but keep usage minimal).
3. Keep final SFT-ready `.jsonl` (46k examples) as the canonical dataset inside `data/instruction_data_final/` if storage permits; otherwise share via external storage and provide download script.

Example `.gitignore` snippet:

```
# data
data/raw_pdfs/
data/ocr_output/
data/*.db
# models & checkpoints
models/
*.ckpt
*.pt
*.bin
# python
__pycache__/
.venv/
```

To enable Git LFS for a file type:

```bash
git lfs install
git lfs track "*.zip"
git add .gitattributes
```

---

## Contributors

* **Lê Thành Đạt** — Crawling (Selenium), OCR preprocessing, report writing.
* **Hoàng Bùi Tuấn Anh** — Instruction generation pipeline, error handling, data analysis.
* **Đỗ Quang Dũng** — Data curation, SFT experiments, model evaluation.
* Supervisor: **TS. Trần Hồng Việt**.

---

## How to cite

If you use this dataset or pipeline in research, cite the project report and relevant papers (example entry below):

```
Vu, T.P., Tran, T.H., Nguyen, D.N., et al., "ViFin-Gen: Efficient Vietnamese Instruction Dataset Generation Pipeline for Finance Domain", ATC 2024.
```

(Provide full bibliographic entry in `docs/`).

---

## License

This repository is provided under the **MIT License** (suggested). If you prefer a different license, replace `LICENSE` accordingly.

---

## Contact / support

For questions or to request dataset access (for large files), open an issue or contact the maintainers:

* Email: <your-contact-email> (add your preferred contact)
* GitHub: `https://github.com/ThanhDatVN/Instruction-Data-in-Vietnamese-from-Financial-Reports`

---

