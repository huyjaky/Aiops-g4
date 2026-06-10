import time
import logging
import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from pipeline import process_batch, GRAPH, HISTORY

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('aiops')

# Structured JSON log formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'ts': self.formatTime(record),
            'level': record.levelname,
            'msg': record.getMessage(),
            'logger': record.name,
        }
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        return json.dumps(log_obj)

# Create stream handler with JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.propagate = False  # Avoid duplicate logging since we added our handler

app = FastAPI(
    title='AIOps Incident Pipeline',
    version='1.0.0',
    description='Group lab W2 — correlate alerts → RCA → suggest action',
)

# Mount Prometheus metrics on /metrics
app.mount('/metrics', make_asgi_app())

# Prometheus Metrics definition
REQUEST_COUNT = Counter('aiops_incident_requests_total', 'Total incident requests', ['status'])
REQUEST_LATENCY = Histogram('aiops_incident_latency_seconds', 'Incident pipeline latency')
LLM_FAILURES = Counter('aiops_llm_failures_total', 'LLM call failures', ['reason'])
CLUSTER_COUNT = Histogram('aiops_clusters_per_request', 'Clusters produced per request')

# Pydantic schemas
class Alert(BaseModel):
    id: str
    ts: str
    service: str
    metric: str
    severity: str
    value: float
    threshold: float
    labels: Optional[dict] = Field(default_factory=dict)

class IncidentRequest(BaseModel):
    alerts: list[Alert]

class Cluster(BaseModel):
    cluster_id: str
    alert_count: int
    services: list[str]
    time_range: list[str]

class RootCause(BaseModel):
    service: str
    confidence: float
    reasoning: str

class SimilarIncident(BaseModel):
    id: str
    similarity: float
    summary: str

class IncidentResponse(BaseModel):
    clusters: list[Cluster]
    root_cause: RootCause
    recommended_actions: list[str]
    similar_incidents: list[SimilarIncident]

# Timing/Latency Middleware
@app.middleware('http')
async def add_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers['X-Response-Time-Ms'] = f'{duration_ms:.1f}'
    logger.info(
        f"{request.method} {request.url.path} {response.status_code} {duration_ms:.1f}ms",
        extra={'extra': {
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'duration_ms': duration_ms
        }}
    )
    return response

@app.get('/healthz')
def healthz() -> dict:
    return {'status': 'ok'}

@app.get('/readyz')
def readyz() -> dict:
    """Check downstream dependencies. Trả 503 nếu chưa ready."""
    checks = {}
    
    # Check graph loaded
    checks['graph'] = GRAPH.number_of_nodes() > 0
    
    # Check history loaded
    checks['history'] = len(HISTORY) > 0
    
    # Check LLM API (optional, skipped if AIOPS_USE_LLM=false)
    use_llm = os.environ.get("AIOPS_USE_LLM", "true").lower() == "true"
    api_key = os.environ.get("OPENAI_API_KEY")
    if use_llm and api_key:
        try:
            from openai import OpenAI
            base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
            # Set a low timeout so readiness check doesn't block
            OpenAI(api_key=api_key, base_url=base_url, timeout=2.0).models.list()
            checks['llm'] = True
        except Exception as e:
            logger.warning(f"LLM API readiness check failed: {e}")
            checks['llm'] = False
    else:
        checks['llm'] = True  # LLM check is bypassed when LLM usage is disabled or no key is present
        
    if not all(checks.values()) and not checks['graph']:
        raise HTTPException(status_code=503, detail=checks)
        
    return {'status': 'ready', 'checks': checks}

APP_VERSION = '1.0.0'
@app.get('/version')
def version() -> dict:
    use_llm = os.environ.get("AIOPS_USE_LLM", "true").lower() == "true"
    has_key = bool(os.environ.get('OPENAI_API_KEY'))
    return {
        'app': APP_VERSION,
        'pipeline_config': {
            'correlate_gap_sec': 120,
            'correlate_max_hop': 2,
            'rca_method': 'graph+llm' if (use_llm and has_key) else 'graph+retrieval',
            'llm_model': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            'aiops_use_llm': use_llm,
        },
    }

@app.post('/incident', response_model=IncidentResponse)
def post_incident(req: IncidentRequest) -> IncidentResponse:
    """
    Process batch of alerts → return incident report.
    Chain: correlate (L1) → rca (L2) → enrich w/ LLM (L3) → assemble response.
    """
    logger.info(f"Received {len(req.alerts)} alerts")
    if not req.alerts:
        REQUEST_COUNT.labels(status='bad_request').inc()
        raise HTTPException(status_code=400, detail='Empty alert list')
        
    alerts_dict = [a.model_dump() for a in req.alerts]
    
    with REQUEST_LATENCY.time():
        try:
            result = process_batch(alerts_dict)
            REQUEST_COUNT.labels(status='success').inc()
            CLUSTER_COUNT.observe(len(result['clusters']))
            return IncidentResponse(**result)
        except Exception as e:
            REQUEST_COUNT.labels(status='error').inc()
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            if "OpenAI" in str(e) or "LLM" in str(e) or "openai" in str(e):
                LLM_FAILURES.labels(reason=type(e).__name__).inc()
            raise HTTPException(status_code=500, detail=f'Pipeline error: {e}')
