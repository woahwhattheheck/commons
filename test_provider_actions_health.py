import unittest
from coordination import provider_actions_health as m

def row(name='owner/repo', latest=None, eligible=None, kind='NONE'):
    return {'repository':name,'provider_state':'UNKNOWN','workflow_present':True,'latest_run_at':latest,'eligible_event_at':eligible,'eligible_event_kind':kind}

def packet(rows):
    return {'schema':m.INPUT_SCHEMA,'cutoff_at':'2026-09-14T00:00:00Z','observed_at':'2026-09-18T06:33:32Z','repositories':rows}

class ProviderActionsHealthTests(unittest.TestCase):
    def test_recent_provider_run(self):
        got=m.compile_health(packet([row(latest='2026-09-18T01:00:00Z')]))['repositories'][0]
        self.assertEqual(got['state'],'HEALTHY_PROVIDER_SEEN')
    def test_later_eligible_event_is_suspicious(self):
        got=m.compile_health(packet([row(latest='2026-09-14T01:00:00Z',eligible='2026-09-15T01:00:00Z',kind='PUSH')]))['repositories'][0]
        self.assertEqual(got['state'],'SUSPICIOUS_EVENT_SUPPRESSION')
        self.assertFalse(got['disabled_inferred_from_silence'])
    def test_duplicate_rejected(self):
        with self.assertRaises(m.ProviderActionsHealthError):
            m.compile_health(packet([row(),row()]))
    def test_noncanonical_time_rejected(self):
        with self.assertRaises(m.ProviderActionsHealthError):
            m.compile_health(packet([row(latest='2026-09-18T01:00:00+00:00')]))
    def test_deterministic_order(self):
        got=m.compile_health(packet([row('z/repo'),row('a/repo')]))
        self.assertEqual([x['repository'] for x in got['repositories']],['a/repo','z/repo'])
    def test_markdown_boundary(self):
        self.assertIn('silence alone never proves',m.render_markdown(m.compile_health(packet([row()]))))

if __name__=='__main__':
    unittest.main()
