import httpx

def test_scholarships_and_detail():
    with httpx.Client(base_url='http://localhost:8001', timeout=10) as c:
        assert c.post('/api/auth/demo').status_code==200
        r=c.get('/api/scholarships'); assert r.status_code==200; rows=r.json(); assert any(x['scholarship']['id']=='national-stem' for x in rows)
        r=c.get('/api/scholarships/national-stem'); assert r.status_code==200; assert 'conditions' in r.json()
