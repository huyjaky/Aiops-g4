# DESIGN: AIOps Incident serving API

## 1. Pipeline Architecture in Endpoint

The serving endpoint (`POST /incident`) implements a sequential 3-layer pipeline to process batch alerts:
- **Layer 1 (Correlation):** Alerts are grouped chronologically using a sliding time window (`gap_sec=120s`) to split distinct alert storms. Within each time window, alerts are clustered topologically based on a service dependency graph with a max distance constraint (`max_hop=2`). We choose `gap_sec=120s` because SRE alerts in typical microservices propagate within 2 minutes of the root outage, and `max_hop=2` avoids clustering unrelated network segments.
- **Layer 2 (Graph RCA):** For the primary (largest) cluster, we apply a combined heuristic: PageRank on the subgraph flow, in-degree vs out-degree differential (topology source check), earliest-alert timestamps (temporal propagation), and severity.
- **Layer 3 (LLM Enrichment):** The top candidates and service graph context are fed to the LLM (OpenAI `gpt-4o-mini`) via RAG retrieval of top-k similar historical incidents to determine the final root cause service, failure class, and remediation actions.

---

## 2. Latency Budget Breakdown (Target: p99 < 5s)

| Phase | Duration (ms) | % Budget | Explanation |
|---|---|---|---|
| Request Parsing & Validation | 5 - 15 | ~0.3% | Pydantic validation of Alert schema |
| L1 Correlation (Python Loop) | 20 - 50 | ~1.0% | Sliding window & NetworkX traversal |
| L2 Graph RCA | 10 - 30 | ~0.6% | PageRank and subgraph sorting |
| L3 LLM Inference (Outbound API) | 800 - 3000 | ~98.0% | External API network round-trip & inference |
| Response Serialization | 5 - 10 | ~0.1% | JSON serialization of response schema |
| **Total** | **840 - 3105** | **100%** | **Within p99 < 5s budget** |

---

## 3. Production Concerns (Fault Tolerance)

Our main concern is **External LLM Service Availability (LLM Down/Timeout)**. 
- **Remediation Strategy:** If the OpenAI API key is missing, or if the API call fails or times out, the server catches the exception and falls back to **Graph+Retrieval Mode**. It extracts the top candidates from the graph, queries history database using `top_k_similar` heuristic, overrides the result if a highly similar historical incident ($\ge 0.8$) is found, and returns a high-quality fallback report without LLM. This prevents API outages from breaking critical SRE alerts.

---

## 4. Trade-offs: FastAPI vs Flask vs BentoML

- **FastAPI (Chosen):** Chosen for its native asynchronous syntax, which allows non-blocking concurrency during I/O-bound LLM API calls. Additionally, auto-generated OpenAPI docs and Pydantic data validation guarantee that malformed alerts return `422 Unprocessable Entity` rather than crash with `500 Internal Server Error`.
- **Flask:** Synchronous by design. Handling concurrency for long-running LLM API calls requires complex custom threadpools or greenlets, and it lacks native input schema validation.
- **BentoML:** Highly optimized for ML model hosting (model store, micro-batching). However, it adds significant overhead, learning curve, and containerization complexity for our metadata-centric (rather than tensor-centric) pipeline.
