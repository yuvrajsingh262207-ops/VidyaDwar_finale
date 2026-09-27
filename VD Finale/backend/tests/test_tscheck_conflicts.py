import httpx

def test_conflict_analysis():
    with httpx.Client(base_url='http://localhost:8001', timeout=10) as c:
        assert c.post('/api/auth/demo').status_code==200
        r=c.post('/api/conflicts/analyze', json={'scholarship_ids':['national-stem','maharashtra-support']}); assert r.status_code==200; data=r.json(); assert len(data['stages'])==5; assert 'evidence' in data['stages'][0]
