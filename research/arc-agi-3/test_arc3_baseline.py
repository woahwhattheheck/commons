from pathlib import Path
import json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from arc3_baseline import NoveltyExplorer,grid_signature,normalize_actions,normalize_grid
class T(unittest.TestCase):
 def test_latest(self): self.assertEqual(normalize_grid([[[0,0],[0,0]],[[1,0],[0,0]]]),((1,0),(0,0)))
 def test_invalid(self):
  for f in ([[[0]*2 for _ in range(65)]], [[[16]]], [[[0],[0,1]]]):
   with self.assertRaises(ValueError): normalize_grid(f[0])
 def test_actions(self): self.assertEqual(normalize_actions([7,2,2,9,0,'3']),(2,3,7))
 def test_reset(self):
  p=NoveltyExplorer()
  self.assertEqual(p.choose([[0]],[1],state='NOT_PLAYED').action_id,0); self.assertEqual(p.choose([[0]],[1],state='GAME_OVER').action_id,0)
 def test_available_only(self): self.assertEqual(NoveltyExplorer().choose([[0]],[4],state='NOT_FINISHED').action_id,4)
 def test_deterministic_explore(self):
  p=NoveltyExplorer(); f=[[0,0],[0,0]]; self.assertEqual([p.choose(f,[1,2,3],state='NOT_FINISHED').action_id for _ in range(3)],[1,2,3])
 def test_action6_salient(self):
  g=[[0]*5 for _ in range(5)]; g[4][1]=9; d=NoveltyExplorer().choose(g,[6],state='NOT_FINISHED'); self.assertEqual((d.action_id,d.x,d.y),(6,1,4))
 def test_change_reward(self):
  p=NoveltyExplorer(); a=[[0,0],[0,0]]; b=[[1,0],[0,0]]; d=p.choose(a,[1],state='NOT_FINISHED'); sig=grid_signature(normalize_grid(a)); p.choose(b,[1],state='NOT_FINISHED'); st=p.stats[(sig,d.key)]; self.assertEqual(st.changed_cells,1); self.assertGreater(st.mean_reward,0)
 def test_level_bonus(self):
  p=NoveltyExplorer(); f=[[0]]; d=p.choose(f,[1],state='NOT_FINISHED',levels_completed=0); sig=grid_signature(normalize_grid(f)); p.choose(f,[1],state='NOT_FINISHED',levels_completed=1); self.assertGreater(p.stats[(sig,d.key)].mean_reward,7)
 def test_repeatable(self):
  seq=[([[0,0],[0,0]],[1,2,6]),([[1,0],[0,0]],[1,2,6]),([[1,0],[0,2]],[1,2,6]),([[1,0],[0,2]],[1,2,6])]
  def run():
   p=NoveltyExplorer(); return [(d.action_id,d.x,d.y) for f,a in seq for d in [p.choose(f,a,state='NOT_FINISHED')]]
  self.assertEqual(run(),run())
 def test_json_diag(self):
  p=NoveltyExplorer(); p.choose([[0]],[1],state='NOT_FINISHED'); p.choose([[1]],[1],state='NOT_FINISHED'); self.assertIn('unique_states',json.dumps(p.diagnostics()))
if __name__=='__main__': unittest.main(verbosity=2)
