from fastapi.testclient import TestClient
from unittest.mock import patch
from serve import app

client = TestClient(app)

def test_healthz():
    r = client.get('/healthz')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok'}

def test_version():
    r = client.get('/version')
    assert r.status_code == 200
    body = r.json()
    assert 'app' in body
    assert 'pipeline_config' in body

def test_incident_empty_alerts():
    r = client.post('/incident', json={'alerts': []})
    assert r.status_code == 422 or r.status_code == 400 # Empty list throws bad request or fails validation

@patch('rca.call_llm_rca')
def test_incident_happy_path(mock_call_llm):
    # Mock LLM API response to bypass OpenAI connection
    mock_call_llm.return_value = {
        'root_cause': 'payment-svc',
        'class': 'connection_pool_exhaustion',
        'confidence': 0.85,
        'actions': ['Scale up service', 'Restart database connection pool'],
        'reasoning': 'Mocked LLM diagnosis indicating payment-svc connection pool is exhausted.',
        'similar_incidents': ['INC-001']
    }
    
    payload = {
        'alerts': [
            {
                'id': 'a-1',
                'ts': '2026-06-12T09:42:01Z',
                'service': 'payment-svc',
                'metric': 'latency_p99_ms',
                'severity': 'crit',
                'value': 1840.0,
                'threshold': 800.0,
                'labels': {}
            }
        ]
    }
    r = client.post('/incident', json=payload)
    assert r.status_code == 200
    body = r.json()
    assert 'clusters' in body
    assert 'root_cause' in body
    assert body['root_cause']['service'] == 'payment-svc'
    assert len(body['recommended_actions']) > 0

@patch('rca.call_llm_rca')
def test_incident_llm_flag_disabled(mock_call_llm):
    import os
    from unittest.mock import patch as patch_env
    
    # We disable LLM usage via environment variable mock
    with patch_env.dict(os.environ, {"AIOPS_USE_LLM": "false"}):
        payload = {
            'alerts': [
                {
                    'id': 'a-1',
                    'ts': '2026-06-12T09:42:01Z',
                    'service': 'payment-svc',
                    'metric': 'latency_p99_ms',
                    'severity': 'crit',
                    'value': 1840.0,
                    'threshold': 800.0,
                    'labels': {}
                }
            ]
        }
        r = client.post('/incident', json=payload)
        assert r.status_code == 200
        body = r.json()
        assert 'clusters' in body
        assert 'root_cause' in body
        # Should complete using graph+retrieval method without calling LLM
        mock_call_llm.assert_not_called()

