import tempfile
import unittest
from pathlib import Path

import app as taka

class TakaDaoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        taka.DATA = Path(self.tmp.name)
        taka.init_store()
        self.client = taka.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_safe_limit_within_and_exceeded(self):
        state = taka.dashboard()['safe']
        self.assertTrue(state['within'])
        self.assertEqual(state['remaining'], '600')
        settings = taka.read('settings')
        settings['daily_limit'] = '500'
        taka.write('settings', settings)
        state = taka.dashboard()['safe']
        self.assertFalse(state['within'])
        self.assertEqual(state['over'], '100')
        self.assertEqual(state['excess_percent'], '20')

    def test_successful_simulated_payment_is_idempotent(self):
        body = {'idempotency_key':'same-payment','method_id':'pm-card','recipient':'Campus shop',
                'description':'Notebook','amount':'300','currency':'BDT','category':'Education','outcome':'success'}
        first = self.client.post('/api/payments', json=body)
        second = self.client.post('/api/payments', json=body)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(taka.read('payment_events')), 1)
        matches = [x for x in taka.read('transactions') if x.get('event_id')]
        self.assertEqual(len(matches), 1)

    def test_failed_payment_does_not_create_expense(self):
        before = len(taka.read('transactions'))
        r = self.client.post('/api/payments', json={'idempotency_key':'failed-one','method_id':'pm-card',
            'recipient':'Campus shop','description':'Notebook','amount':'300','currency':'BDT','outcome':'failed'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(taka.read('transactions')), before)
        self.assertEqual(taka.read('payment_events')[0]['status'], 'failed')

if __name__ == '__main__':
    unittest.main()
