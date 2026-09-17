from __future__ import annotations
import copy, importlib.util, json, sys, unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODDIR=ROOT/'revenue/recon_portfolio'
sys.path.insert(0,str(MODDIR))
import validate
import render

class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.catalog=validate.load(MODDIR/'catalog.json')
        self.targets=validate.load(MODDIR/'targets.json')
    def test_current_data_valid(self):
        s=validate.validate(self.catalog,self.targets)
        self.assertEqual(s['products'],5); self.assertEqual(s['bundles'],5); self.assertEqual(s['targets'],75)
    def test_exact_target_floor(self):
        counts=Counter(t['bundle_id'] for t in self.targets['targets'])
        self.assertEqual(set(counts.values()),{15})
    def test_product_truth_split(self):
        p={x['id']:x for x in self.catalog['products']}
        self.assertEqual(p['telecom_invoice_reconciliation']['state'],'OPEN_NEAR_SHIP')
        self.assertIsNone(p['telecom_invoice_reconciliation']['merge_commit_sha'])
        self.assertTrue(all(x['merge_commit_sha'] for x in p.values() if x['state']=='MERGED_DELIVERABLE'))
    def test_telecom_is_mechanically_held(self):
        b={x['id']:x for x in self.catalog['bundles']}['telecom_expense']
        self.assertFalse(b['outreach_ready'])
        rows=[t for t in self.targets['targets'] if t['bundle_id']=='telecom_expense']
        self.assertTrue(all(t['contact_route']['state']=='PRODUCT_GATE_HOLD' for t in rows))
    def test_no_target_has_send_authority(self):
        self.assertTrue(all(t['research_only'] and not t['outbound_authority'] for t in self.targets['targets']))
    def test_airlst_provider_sent_dnr_preserved(self):
        row=next(t for t in self.targets['targets'] if t['organization']=='AirLST')
        self.assertEqual(row['contact_route']['state'],'DNR_PROVIDER_SENT')
        self.assertEqual(row['next_action'],'WAIT_FOR_GENUINE_INBOUND')
    def test_validator_rejects_open_product_promoted_to_outreach(self):
        c=copy.deepcopy(self.catalog)
        next(b for b in c['bundles'] if b['id']=='telecom_expense')['outreach_ready']=True
        with self.assertRaises(validate.PortfolioError): validate.validate(c,self.targets)
    def test_validator_rejects_send_authority(self):
        t=copy.deepcopy(self.targets); t['targets'][0]['outbound_authority']=True
        with self.assertRaises(validate.PortfolioError): validate.validate(self.catalog,t)
    def test_renderer_is_deterministic_and_checked_in(self):
        a=render.render(self.catalog,self.targets); b=render.render(self.catalog,self.targets)
        self.assertEqual(a,b)
        self.assertEqual((MODDIR/'PORTFOLIO.md').read_text(encoding='utf-8'),a)

if __name__=='__main__': unittest.main()
