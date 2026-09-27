import httpx

def test_demo_auth_and_dashboard():
    with httpx.Client(base_url='http://localhost:8001', timeout=10) as c:
        r=c.post('/api/auth/demo'); assert r.status_code==200; assert r.json()['user']['full_name']=='Aarav'
        r=c.get('/api/dashboard'); assert r.status_code==200; assert 'Aarav' in r.text
