"""Deterministic dependency-free ARC-AGI-3 exploration baseline."""
from __future__ import annotations
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import hashlib, json, math
from typing import Any, Iterable

MAX_SIDE=64; RESET=0; VALID=frozenset(range(1,8)); RESET_STATES=frozenset({'NOT_PLAYED','GAME_OVER'})
Grid=tuple[tuple[int,...],...]

@dataclass(frozen=True)
class Decision:
    action_id:int; x:int|None=None; y:int|None=None; reason:str=''
    @property
    def key(self)->str:
        return f'6:{self.x}:{self.y}' if self.action_id==6 else str(self.action_id)
    def as_action_data(self)->dict[str,int]:
        if self.action_id!=6: return {}
        if self.x is None or self.y is None: raise ValueError('ACTION6 requires x,y')
        return {'x':self.x,'y':self.y}

@dataclass
class TransitionStat:
    visits:int=0; reward_sum:float=0.0; changed_cells:int=0; novel_successors:int=0; level_advances:int=0
    @property
    def mean_reward(self)->float: return self.reward_sum/self.visits if self.visits else 0.0

def state_name(state:Any)->str:
    name=getattr(state,'name',None)
    if isinstance(name,str): return name.upper()
    text=str(state or 'NOT_FINISHED').upper()
    return text.rsplit('.',1)[-1]

def normalize_grid(frame:Any)->Grid:
    if hasattr(frame,'tolist'): frame=frame.tolist()
    if not isinstance(frame,(list,tuple)) or not frame: raise ValueError('frame must be non-empty')
    first=frame[0]
    if isinstance(first,(list,tuple)) and first and isinstance(first[0],(list,tuple)):
        frame=frame[-1]
        if hasattr(frame,'tolist'): frame=frame.tolist()
    if not isinstance(frame,(list,tuple)) or not frame or len(frame)>64: raise ValueError('invalid grid height')
    rows=[]; width=None
    for row in frame:
        if hasattr(row,'tolist'): row=row.tolist()
        if not isinstance(row,(list,tuple)) or not row or len(row)>64: raise ValueError('invalid grid row')
        width=len(row) if width is None else width
        if len(row)!=width: raise ValueError('grid must be rectangular')
        out=[]
        for cell in row:
            if isinstance(cell,bool) or not isinstance(cell,int) or not 0<=cell<=15: raise ValueError('grid cells must be ints 0..15')
            out.append(cell)
        rows.append(tuple(out))
    return tuple(rows)

def normalize_actions(actions:Iterable[Any]|None)->tuple[int,...]:
    if actions is None: return tuple(sorted(VALID))
    ids=set()
    for action in actions:
        raw=getattr(action,'value',action)
        try: value=int(raw)
        except (TypeError,ValueError): continue
        if value in VALID: ids.add(value)
    if not ids: raise ValueError('no valid available actions')
    return tuple(sorted(ids))

def grid_signature(grid:Grid)->str:
    return hashlib.sha256(json.dumps(grid,separators=(',',':')).encode('ascii')).hexdigest()[:24]

def changed_cells(a:Grid,b:Grid)->tuple[tuple[int,int],...]:
    if len(a)!=len(b) or len(a[0])!=len(b[0]): return tuple()
    return tuple((x,y) for y,(ra,rb) in enumerate(zip(a,b)) for x,(va,vb) in enumerate(zip(ra,rb)) if va!=vb)

def component_centers(grid:Grid)->list[tuple[int,int,int]]:
    bg=Counter(c for r in grid for c in r).most_common(1)[0][0]; h=len(grid); w=len(grid[0]); seen=set(); parts=[]
    for y in range(h):
        for x in range(w):
            if grid[y][x]==bg or (x,y) in seen: continue
            color=grid[y][x]; q=deque([(x,y)]); seen.add((x,y)); pts=[]
            while q:
                cx,cy=q.popleft(); pts.append((cx,cy))
                for nx,ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
                    if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and grid[ny][nx]==color:
                        seen.add((nx,ny)); q.append((nx,ny))
            parts.append((len(pts),round(sum(px for px,_ in pts)/len(pts)),round(sum(py for _,py in pts)/len(pts))))
    return sorted(parts,key=lambda z:(z[0],z[2],z[1]))

def coordinate_candidates(grid:Grid, previous:Grid|None=None)->tuple[tuple[int,int],...]:
    h=len(grid); w=len(grid[0]); pts=[]
    if previous is not None:
        diff=changed_cells(previous,grid)
        if diff:
            pts.append((round(sum(x for x,_ in diff)/len(diff)),round(sum(y for _,y in diff)/len(diff)))); pts.extend(diff[:8])
    pts.extend((x,y) for _,x,y in component_centers(grid)[:12])
    pts.extend([(w//2,h//2),(0,0),(w-1,0),(0,h-1),(w-1,h-1)])
    out=[]; seen=set()
    for x,y in pts:
        p=(max(0,min(63,int(x))),max(0,min(63,int(y))))
        if p not in seen: seen.add(p); out.append(p)
    return tuple(out[:24])

class NoveltyExplorer:
    ORDER={1:0,2:1,3:2,4:3,5:4,6:5,7:6}
    def __init__(self)->None:
        self.seen_states=Counter(); self.state_action_visits=Counter(); self.coord_visits=Counter(); self.stats=defaultdict(TransitionStat); self.successors=defaultdict(Counter)
        self.last_state=None; self.last_grid=None; self.last_level=0; self.last_decision=None; self.total_decisions=0
    def reset_episode_memory(self)->None:
        self.last_state=self.last_grid=self.last_decision=None; self.last_level=0
    def _observe(self,state:str,grid:Grid,level:int)->None:
        if self.last_state is None or self.last_decision is None or self.last_grid is None: return
        diff=changed_cells(self.last_grid,grid); resized=(len(self.last_grid)!=len(grid) or len(self.last_grid[0])!=len(grid[0])); advance=max(0,level-self.last_level); novel=self.seen_states[state]==0
        reward=(-0.15 if not diff and not resized else 0.5+min(1.5,len(diff)/max(1,len(grid)*len(grid[0]))*6.0))+int(novel)+8.0*advance
        key=(self.last_state,self.last_decision.key); st=self.stats[key]; st.visits+=1; st.reward_sum+=reward; st.changed_cells+=len(diff); st.novel_successors+=int(novel); st.level_advances+=advance; self.successors[key][state]+=1
    def _score(self,state:str,a:int)->tuple[float,float,float,int]:
        visits=self.state_action_visits[(state,a)]; total=1+sum(self.state_action_visits[(state,x)] for x in VALID)
        matching=[st for (s,k),st in self.stats.items() if s==state and k.split(':',1)[0]==str(a)]; n=sum(st.visits for st in matching); mean=sum(st.reward_sum for st in matching)/n if n else 0.0
        return (1.0 if visits==0 else 0.0, mean+0.45*math.sqrt(math.log(total+1)/(visits+1)), -float(visits), -self.ORDER.get(a,99))
    def choose(self,frame:Any,available_actions:Iterable[Any]|None,*,state:Any='NOT_FINISHED',levels_completed:int=0)->Decision:
        sname=state_name(state)
        if sname in RESET_STATES: self.reset_episode_memory(); return Decision(0,reason=f'{sname}: RESET only')
        if sname=='WIN': return Decision(0,reason='WIN observed')
        grid=normalize_grid(frame); actions=normalize_actions(available_actions); sig=grid_signature(grid); self._observe(sig,grid,int(levels_completed)); self.seen_states[sig]+=1
        aid=max(actions,key=lambda a:self._score(sig,a))
        if aid==6:
            cands=coordinate_candidates(grid,self.last_grid); x,y=min(cands,key=lambda p:(self.coord_visits[(sig,p[0],p[1])],cands.index(p))); self.coord_visits[(sig,x,y)]+=1; decision=Decision(6,x,y,f'novelty-UCB ACTION6 target ({x},{y})')
        else: decision=Decision(aid,reason=f'novelty-UCB ACTION{aid}')
        self.state_action_visits[(sig,aid)]+=1; self.total_decisions+=1; self.last_state=sig; self.last_grid=grid; self.last_level=int(levels_completed); self.last_decision=decision; return decision
    def diagnostics(self)->dict[str,Any]:
        return {'total_decisions':self.total_decisions,'unique_states':len(self.seen_states),'transitions':{f'{s}:{k}':{'visits':st.visits,'mean_reward':round(st.mean_reward,6),'changed_cells':st.changed_cells,'novel_successors':st.novel_successors,'level_advances':st.level_advances,'successor_count':len(self.successors[(s,k)])} for (s,k),st in sorted(self.stats.items())}}
