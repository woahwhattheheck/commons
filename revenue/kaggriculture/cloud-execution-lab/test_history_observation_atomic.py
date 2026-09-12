# SPDX-License-Identifier: Apache-2.0
"""Cancellation-safety contracts for selected-action history reconciliation."""
import copy
import unittest
from unittest.mock import patch

from terminal_history_join import TerminalHistoryJoin
from test_ordered_selected_sell import OrderedSelectedSellTests,action


class _InjectedCancellation(BaseException):
    pass


class HistoryObservationAtomicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OrderedSelectedSellTests.setUpClass()
        cls.harness=OrderedSelectedSellTests()

    def transition(self,step=100):
        history=TerminalHistoryJoin(terminal_enabled=False)
        obs,cfg,state,env=self.harness.fixture(step,{'CARROT':3})
        before=copy.deepcopy(state[0].observation)
        final=action(hands=[['PASS']],market=[['SELL','CARROT',1]])
        history.remember(before,cfg,final,copy.deepcopy(before))
        self.harness.advance(state,env,final,step)
        after=copy.deepcopy(state[0].observation)
        after['step']=step+1
        return history,after

    def test_interrupted_reconciliation_publishes_no_partial_state(self):
        history,after=self.transition()
        original_bridge=history.bridge
        original_pending=copy.deepcopy(history.pending)
        original_last=history.bridge.last_consumed_step
        original_identified=history.bridge.history.identified
        original_result=copy.deepcopy(history.bridge.ledger.last_result)
        bridge_type=type(history.bridge)

        def interrupt(working,observation,*,fill_result=None):
            # Deliberately poison every mutable family on the private working
            # bridge before simulating a hard asynchronous deadline.
            working.last_consumed_step=777
            working.history.identified=999
            working.ledger.last_result={'status':'poisoned'}
            raise _InjectedCancellation()

        with patch.object(bridge_type,'observe',interrupt):
            with self.assertRaises(_InjectedCancellation):
                history.observe(after)

        self.assertIs(history.bridge,original_bridge)
        self.assertEqual(history.pending,original_pending)
        self.assertEqual(history.bridge.last_consumed_step,original_last)
        self.assertEqual(history.bridge.history.identified,original_identified)
        self.assertEqual(history.bridge.ledger.last_result,original_result)

        # A retry of the exact next public observation must still consume the
        # original returned action exactly once.
        history.observe(after)
        self.assertIsNone(history.pending)
        self.assertIsNot(history.bridge,original_bridge)
        self.assertEqual(history.bridge.last_consumed_step,100)
        self.assertEqual(history.diagnostics['observed_fills']['status'],'recorded')
        self.assertEqual(history.fill_result,history.bridge.ledger.last_result)

    def test_same_step_and_empty_observation_keep_existing_contract(self):
        history,after=self.transition(step=200)
        history.diagnostics={'stale':True}
        history.fill_result={'stale':True}
        same=copy.deepcopy(after);same['step']=200
        pending=copy.deepcopy(history.pending)
        history.observe(same)
        self.assertEqual(history.pending,pending)
        self.assertEqual(history.diagnostics,{})
        self.assertIsNone(history.fill_result)

        history.pending=None
        history.diagnostics={'stale':True}
        history.fill_result={'stale':True}
        history.observe(after)
        self.assertEqual(history.diagnostics,{})
        self.assertIsNone(history.fill_result)


if __name__=='__main__':
    unittest.main()
