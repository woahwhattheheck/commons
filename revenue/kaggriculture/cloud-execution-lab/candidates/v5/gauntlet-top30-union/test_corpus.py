from copy import deepcopy
import unittest
from corpus import action_tape, retain_and_extend

class CorpusTests(unittest.TestCase):
    def test_initial_state_is_not_an_action_and_seat_is_exact(self):
        replay={'statuses':['DONE','DONE'],'steps':[[{'action':None},{'action':None}]]}
        replay['steps'] += [[{'action':{'farmer':['PASS'],'hands':[],'market':[['SELL','EGG',i]]}},
                             {'action':{'farmer':['NORTH'],'hands':[],'market':[['SELL','WHEAT',i]]}}]
                            for i in range(719)]
        tape=action_tape(replay,1)
        self.assertEqual(len(tape),719)
        self.assertEqual(tape[0]['farmer'],['NORTH'])
        self.assertEqual(tape[-1]['market'][0][-1],718)
        tape[0]['farmer'][0]='PASS'
        self.assertEqual(replay['steps'][1][1]['action']['farmer'],['NORTH'])

    def test_all_old_entries_and_mirror_survive_with_opaque_fields(self):
        old={'config':{'seeds':[1,2]},'opponents':[{'id':str(i),'secret_runtime_field':{'x':i}} for i in range(30)]}
        old['opponents'].append({'id':'mirror','kind':'mirror'})
        saved=deepcopy(old)
        result=retain_and_extend(old,[{'id':'new','kind':'recorded_trace'}])
        self.assertEqual(old,saved)
        self.assertEqual(result['opponents'][:31],saved['opponents'])
        self.assertEqual(result['additive_intake']['legacy_entries'],31)
        self.assertEqual(result['config'],saved['config'])

    def test_colliding_addition_cannot_replace_old_opponent(self):
        with self.assertRaises(ValueError):
            retain_and_extend({'opponents':[{'id':'old'}]},[{'id':'old'}])

if __name__=='__main__':unittest.main()
