# SPDX-License-Identifier: Apache-2.0
"""Bounded route improvements over an existing selected production controller.

Uses own observed state and authored commitments. Market valuation is a current
quote screen, not a forecast. No investment, hiring or input orders are added.
"""
from copy import deepcopy
from itertools import permutations

MOVES={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)}
WORK={'WATER','CARE','FEED','HARVEST','COLLECT_FERTILIZER'}
CHECKPOINTS=(226,360,433)

def unit(row,i):
    return row.get('farmer',['PASS']) if i==0 else (row.get('hands',[])[i-1] if i<=len(row.get('hands',[])) else ['PASS'])

def set_unit(row,i,action):
    if i==0:row['farmer']=action
    else:
        hands=row.setdefault('hands',[])
        while len(hands)<i:hands.append(['PASS'])
        hands[i-1]=action

def move(pos,action,board):
    d=MOVES.get(action[0] if action else '')
    if d:
        q=(pos[0]+d[0],pos[1]+d[1])
        if 0<=q[0]<board and 0<=q[1]<board:return q
    return pos

def path(a,b):
    return [[('EAST' if b[0]>a[0] else 'WEST')]]*abs(b[0]-a[0])+[[('SOUTH' if b[1]>a[1] else 'NORTH')]]*abs(b[1]-a[1])

def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])

class SpatialTempo:
    def __init__(self,mechanics,pathing=True,tempo=True,seed_reserve=None):
        self.m=mechanics;self.pathing=pathing;self.tempo=tempo
        self.events=[];self.edits=[];self.active={};self.reserved=set();self.day=None
        self.plans={};self._committed=None;self._pending=None;self._selected=None
        self.supported=True
        self.seed_reserve=seed_reserve

    def configure(self, configuration):
        cfg=configuration or {}
        self.supported=(int(cfg.get('turnsPerDay',24))==24
                        and int(cfg.get('episodeSteps',720))==720
                        and int(cfg.get('shedCapacity',100))==100)

    def finish(self, observation, returned_action):
        """Commit only after TitanAgent returns, including its selected fallback.

        Retain this object across controller reconstruction and install it on the
        replacement controller. A cancelled producer never commits a proposal.
        Market-only fallback changes do not invalidate completed unit actions.
        """
        count=1+len(observation['farms'][observation['player']]['hands'])
        now=int(observation['step'])
        if self._pending is not None and self._selected is not None:
            prior=self._pending['previous'] or {}
            accepted={i for i in range(count)
                      if unit(returned_action,i)==unit(self._selected,i)}
            old=prior.get('plans',{});proposed=self._pending['plans']
            plans={}
            for i in old.keys() | proposed.keys():
                plan=proposed.get(i) if i in accepted else old.get(i)
                if plan is not None and plan['end']>now and i<count:
                    plans[i]=plan
            # Commit each actor's exact stream. Whole rows would accidentally
            # retain an unrelated actor's proposal after its action was replaced.
            patches={}
            for i,plan in plans.items():
                for offset,action in enumerate(plan['replacement']):
                    t=plan['step']+offset
                    if t>=now:
                        patches.setdefault((plan['route'],t),{})[i]=list(action)
            events=list(prior.get('events',[]))
            for event in self._pending['events']:
                if event['worker'] in accepted and event not in events:
                    events.append(event)
            reserved=set(prior.get('reserved',()))
            for i,plan in proposed.items():
                if i in accepted and plan.get('extra'):
                    reserved.add(tuple(plan['extra']['tile']))
            self._committed={'patches':patches,'plans':plans,'events':events,
                'reserved':reserved,'active':{i:p['end'] for i,p in plans.items()},
                'day':now//24,'step':now}
        self._pending=None;self._selected=None
        self.events=[] if self._committed is None else self._committed['events']

    def _begin(self, controller, pristine, obs):
        now=int(obs['step']);state=self._committed
        if state and (not self.supported or now<=state['step'] or now//24!=state['day']):
            state=None
        self.plans={} if not state else {i:p for i,p in state['plans'].items()
                                        if p['end']>now and p['route']==controller.cur}
        self.events=[] if not state else list(state['events'])
        farm=obs['farms'][obs['player']]
        positions=[tuple(farm['farmer']),*[tuple(p) for p in farm['hands']]]
        # Returning DIG records intent; the next observation establishes its
        # actual effect. A later consumer can change another actor's actions.
        # Before inserting the retry, require the same actor, empty site, and
        # enough observed stock for every remaining seed obligation again.
        for i,plan in list(self.plans.items()):
            if plan.get('kind')!='weed_continuation' or now!=plan['step']+1:continue
            reason=None;x,y=plan['origin']
            if i>=len(positions) or positions[i]!=tuple(plan['origin']):
                reason='retry_actor_or_position_changed'
            elif farm['tiles'][y][x] is not None:
                reason='retry_site_not_empty'
            elif plan['obligation'][0]=='PLANT':
                crop=plan['obligation'][1]
                reserve=(self.seed_reserve(crop,now-1,controller.cur)
                         +self.future_seed_requests(now-1).get(crop,0))
                if obs['private']['seeds'].get(crop,0)<reserve:
                    reason='retry_seed_reserve_changed'
            if reason:
                del self.plans[i]
                self.events.append({'step':now,'worker':i,'invalidated':reason})
        if state:
            state=dict(state,plans=dict(self.plans),events=list(self.events))
        self._base_state=state
        # Build replacement tables before publishing. Original rows are read-only;
        # every changed row is copied below. Branch-prefix checks see pristine past.
        routes={key:list(rows) for key,rows in pristine.items()}
        if state:
            for (route,t),actions in state['patches'].items():
                if t>=now and route==controller.cur:
                    row=deepcopy(routes[route][t])
                    for i,action in actions.items():
                        if i in self.plans:set_unit(row,i,list(action))
                    routes[route][t]=row
        controller.R=routes
        self.edits=[];self._pending=None;self._selected=None
        self.active={i:p['end'] for i,p in self.plans.items()}
        self.day=now//24
        self.reserved=set() if not state or state['day']!=self.day else set(state['reserved'])
        self._repair_positions(obs,controller)

    def _repair_positions(self, obs, controller):
        """Rejoin a committed route after a missed move using actual own position.

        Preserve remaining task order when the shortened route fits. Otherwise
        abandon that optional segment and return to its exact endpoint. This
        recovery is never used as a forecast of unobserved farm changes.
        """
        now=int(obs['step']);farm=obs['farms'][obs['player']]
        positions=[tuple(farm['farmer'])]+[tuple(p) for p in farm['hands']]
        for i,plan in list(self.plans.items()):
            if i>=len(positions) or plan['route']!=controller.cur:continue
            offset=now-plan['step'];expected=tuple(plan['origin'])
            for a in plan['replacement'][:offset]:expected=move(expected,a,10)
            if positions[i]==expected:continue
            cursor=expected;tasks=[]
            for a in plan['replacement'][offset:]:
                if a[0] not in MOVES and a[0]!='PASS':tasks.append((cursor,a))
                cursor=move(cursor,a,10)
            trial=[];cursor=positions[i]
            for location,action in tasks:
                trial+=path(cursor,location)+[action];cursor=location
            trial+=path(cursor,tuple(plan['goal']))
            left=plan['end']-now;abandoned=len(trial)>left
            if abandoned:trial=path(positions[i],tuple(plan['goal']))
            if len(trial)>left:
                # No feasible rejoin exists; retain the already committed stream.
                continue
            trial+= [['PASS']]*(left-len(trial))
            route=controller.R[plan['route']]
            for k,action in enumerate(trial):
                row=deepcopy(route[now+k]);set_unit(row,i,list(action));route[now+k]=row
                self.edits.append((plan['route'],now+k,None))
            updated=dict(plan,step=now,origin=positions[i],replacement=trial)
            self.plans[i]=updated
            self.events.append({'step':now,'worker':i,'recovery':True,'abandoned':abandoned})

    def install(self,controller):
        """Bind to the same producer; caller must call finish after each return."""
        pristine=controller.R
        original=controller.act
        def act(obs):
            self._begin(controller,pristine,obs)
            selected=original(obs)
            result=self.transform(obs,selected,controller)
            self._pending={'previous':self._base_state,
                'events':list(self.events),'plans':dict(self.plans)}
            self._selected=deepcopy(result)
            return result
        controller.act=act

    def future_seed_requests(self,after_step):
        """Extra requests augment the existing compatible-route seed bound."""
        demand={}
        for plan in self.plans.values():
            if plan.get('obligation',[''])[0]!='PLANT':continue
            for offset,a in enumerate(plan['replacement']):
                if plan['step']+offset>after_step and a[0]=='PLANT':
                    demand[a[1]]=demand.get(a[1],0)+1
        return demand

    def _apply_units(self,farm,private,row,now):
        actions=[row.get('farmer',['PASS']),*row.get('hands',[])]
        demand={}
        for a in actions:
            if a and a[0]=='PLANT' and len(a)>1:
                demand[a[1]]=demand.get(a[1],0)+1
        blocked={crop for crop,n in demand.items() if n>private['seeds'].get(crop,0)}
        for i,a in enumerate(actions):
            if a and a[0]=='PLANT' and a[1] in blocked:a=['PASS']
            self.m._apply_unit_action(farm,private,i,a,10,now//24,24,100)
        self.m._decay_plants(farm,now)

    def _weed_witness(self,obs,selected,route,worker,obligation,stop,reserve):
        """Certify a bounded insertion using observed, pre-market resources.

        Only movement and resource-free service may be delayed. No future
        purchase is credited. Other workers cannot touch a delayed service site,
        and exact joint unit mechanics must rejoin with only the new tile and
        its one seed differing. Markets retain their original times and slots.
        """
        now=int(obs['step']);farm=deepcopy(obs['farms'][obs['player']])
        private=deepcopy(obs['private']);origin=tuple(self.m._farmer_position(farm,worker))
        self._apply_units(farm,private,selected,now)
        x,y=origin
        if farm['tiles'][y][x] is not None:return None
        if obligation[0]=='PLANT' and private['seeds'].get(obligation[1],0)<=reserve:
            return None
        original=[list(unit(route[t],worker)) for t in range(now+1,stop+1)]
        replacement=[list(obligation),*original[:-1]]
        service={origin};cursor=origin
        for a in original:
            if a[0] in ('WATER','CARE'):service.add(cursor)
            tile=farm['tiles'][cursor[1]][cursor[0]]
            if isinstance(tile,dict) and tile.get('kind')=='WEED' and a[0] not in MOVES:
                return None
            cursor=move(cursor,a,10)
        goal=cursor
        positions=[tuple(farm['farmer']),*[tuple(p) for p in farm['hands']]]
        for t in range(now+1,stop+1):
            for i,pos in enumerate(positions):
                if i==worker:continue
                a=unit(route[t],i)
                if a[0] not in (*MOVES,'PASS') and pos in service:return None
                positions[i]=move(pos,a,10)
        results=[]
        for schedule in (original,replacement):
            f=deepcopy(farm);p=deepcopy(private)
            for offset,a in enumerate(schedule):
                t=now+1+offset;row=deepcopy(route[t]);set_unit(row,worker,a)
                self._apply_units(f,p,row,t)
                if offset==0 and schedule is replacement:
                    tile=f['tiles'][y][x]
                    kind='PLANT' if obligation[0]=='PLANT' else obligation[0][6:]
                    if not isinstance(tile,dict) or tile.get('kind')!=kind:return None
                    if kind=='PLANT' and tile.get('crop')!=obligation[1]:return None
            results.append((f,p))
        baseline,bp=results[0];candidate,cp=results[1]
        tile=candidate['tiles'][y][x]
        if baseline['tiles'][y][x] is not None or tile is None:return None
        if obligation[0]=='PLANT' and not tile.get('watered_today'):return None
        candidate['tiles'][y][x]=None
        if obligation[0]=='PLANT':
            crop=obligation[1]
            if cp['seeds'].get(crop,0)!=bp['seeds'].get(crop,0)-1:return None
            cp['seeds'][crop]=bp['seeds'][crop]
        if candidate!=baseline or cp!=bp:return None
        return original,replacement,goal

    def _continue_weed(self,obs,selected,controller,end):
        now=int(obs['step']);route=controller.R[controller.cur]
        farm=obs['farms'][obs['player']]
        positions=[tuple(farm['farmer']),*[tuple(p) for p in farm['hands']]]
        # Finish before the turn which performs reset, not merely before the
        # next day's first call. Branch boundaries are already in end.
        end=min(end,(now//24+1)*24-1)
        for i,origin in enumerate(positions):
            if i in self.active:continue
            obligation=unit(route[now],i)
            if not obligation or obligation[0] not in ('PLANT','BUILD_COOP','BUILD_PASTURE'):continue
            if obligation[0]=='PLANT' and (len(obligation)<2 or obligation[1] not in self.m.CROPS):continue
            tile=farm['tiles'][origin[1]][origin[0]]
            if unit(selected,i)!=['DIG'] or not isinstance(tile,dict) or tile.get('kind')!='WEED':continue
            stop=None
            for t in range(now+1,end):
                a=unit(route[t],i)
                if a==['PASS']:
                    stop=t;break
                if not a or a[0] not in (*MOVES,'WATER','CARE'):break
            if stop is None:continue
            reserve=0
            if obligation[0]=='PLANT':
                # A surviving crop can still starve a much later commitment
                # (ASH step622). Preserve the full incumbent suffix across all
                # prefix-compatible branches, without credit for future buys.
                if self.seed_reserve is None:continue
                crop=obligation[1]
                reserve=(self.seed_reserve(crop,now,controller.cur)
                         +self.future_seed_requests(now).get(crop,0))
            witness=self._weed_witness(obs,selected,route,i,obligation,stop,reserve)
            if witness is None:continue
            original,replacement,goal=witness
            for offset,a in enumerate(replacement):
                t=now+1+offset;row=deepcopy(route[t]);set_unit(row,i,list(a));route[t]=row
                self.edits.append((controller.cur,t,None))
            event={'kind':'weed_continuation','step':now,'worker':i,'end':stop+1,
                'route':controller.cur,'origin':origin,'goal':goal,'saved_travel':0,'extra':None,
                'obligation':list(obligation),'absorbed_step':stop,
                'original':[list(unit(selected,i)),*original],
                'replacement':[['DIG'],*replacement]}
            self.plans[i]=event;self.active[i]=stop+1;self.events.append(event)
            return True
        return False

    def _suffix(self,obs,route,now,end):
        farm=obs['farms'][obs['player']];positions=[tuple(farm['farmer'])]+[tuple(p) for p in farm['hands']]
        touches={};harvests={};board=len(farm['tiles'])
        for t in range(now,end):
            for i,p in enumerate(positions):
                a=unit(route[t],i);op=a[0] if a else 'PASS'
                if op in MOVES:positions[i]=move(p,a,board)
                elif op not in ('PASS','DROP','PICKUP'):
                    touches.setdefault(p,set()).add(i)
                    if op=='HARVEST':harvests.setdefault(p,t)
        return touches,harvests

    def _same_work_state(self,obs,worker,original,replacement):
        # Compare exact own-unit mechanics; no invented future state.
        result=[];n=len(obs['farms'][obs['player']]['tiles'])
        for sequence in (original,replacement):
            farm=deepcopy(obs['farms'][obs['player']]);private=deepcopy(obs['private'])
            for a in sequence:
                x,y=self.m._farmer_position(farm,worker);tile=farm['tiles'][y][x]
                # The producer may replace a no-op on an observed weed with DIG.
                # Do not certify a raw stream which omits that live repair.
                if isinstance(tile,dict) and tile.get('kind')=='WEED' and a[0] not in MOVES:return False
                self.m._apply_unit_action(farm,private,worker,a,n,int(obs['day']),24,100)
            result.append((farm,private))
        return result[0]==result[1]

    def transform(self,obs,selected,controller):
        now=int(obs['step']);board=len(obs['farms'][obs['player']]['tiles'])
        if board!=10 or not self.supported:return selected
        end=min((now//24+1)*24,719,*[x for x in CHECKPOINTS if x>now]) if any(x>now for x in CHECKPOINTS) else min((now//24+1)*24,719)
        if end-now<3:return selected
        route=controller.R[controller.cur];farm=obs['farms'][obs['player']];private=obs['private']
        # HIRE happens after unit moves. Existing positions choose the spawn
        # corner, so every worker must rejoin before the next hiring turn.
        if any(a and a[0]=='HIRE' for a in selected.get('market',[])):return selected
        for step in range(now,end):
            if any(a and a[0]=='HIRE' for a in route[step].get('market',[])):
                end=step;break
        if self._continue_weed(obs,selected,controller,end):return selected
        if not self.pathing and not self.tempo:return selected
        if end-now<3:return selected
        positions=[tuple(farm['farmer'])]+[tuple(p) for p in farm['hands']]
        touches,harvests=self._suffix(obs,route,now,end);out=deepcopy(selected);planned=0
        for i,origin in enumerate(positions):
            if i in self.active or planned>=2:continue
            actual=unit(selected,i);baseline=unit(route[now],i)
            if actual!=baseline:continue
            sequence=[];tasks=[];p=origin;t=now
            while t<end:
                a=unit(route[t],i);op=a[0] if a else 'PASS'
                if op not in MOVES and op!='PASS' and op not in WORK:break
                if op in WORK:
                    if touches.get(p,set())-{i}:break
                    tasks.append((p,list(a)))
                sequence.append(list(a));p=move(p,a,board);t+=1
            length=len(sequence);goal=p
            if length<3:continue
            # Only alter a complete segment ending at the exact original place.
            groups=[]
            for pos,a in tasks:
                if groups and groups[-1][0]==pos:groups[-1][1].append(a)
                else:groups.append((pos,[a]))
            best=list(sequence);saved=0
            if self.pathing and 1<=len(groups)<=6 and len({p for p,_ in groups})==len(groups):
                choices=[]
                for order in permutations(range(len(groups))):
                    q=origin;trial=[]
                    for index in order:
                        pos,acts=groups[index];trial+=path(q,pos)+acts;q=pos
                    trial+=path(q,goal)
                    if len(trial)<=length:choices.append(trial)
                if choices:
                    trial=min(choices,key=lambda a:sum(x[0] in MOVES for x in a));trial+= [['PASS']]*(length-len(trial))
                    saved=sum(a[0] in MOVES for a in sequence)-sum(a[0] in MOVES for a in trial)
                    if saved>0 and self._same_work_state(obs,i,sequence,trial):best=trial
                    else:saved=0
            extra=None
            if self.tempo:
                # The slack suffix follows all existing work; service ordering is preserved.
                last=max([j for j,a in enumerate(best) if a[0] not in MOVES and a[0]!='PASS'],default=-1)
                start=origin
                for a in best[:last+1]:start=move(start,a,board)
                available=length-last-1
                candidates=[]
                for y,row in enumerate(farm['tiles']):
                    for x,tile in enumerate(row):
                        pos=(x,y)
                        if not isinstance(tile,dict) or pos in touches or pos in self.reserved:continue
                        quantity=int(tile.get('yield_units',0))
                        if quantity<=0:continue
                        if 'animal' in tile:item=self.m.ANIMALS[tile['animal']]['product']
                        elif tile.get('crop') in self.m.CROPS and self.m.CROPS[tile['crop']]['ongoing']:
                            item=tile['crop']
                            if int(obs['day'])-tile['planted_day']<self.m.CROPS[item]['first_yield_day']:continue
                        else:continue
                        # Retain input stocks; current marginal liquidation must clear the floor.
                        if item in ('WHEAT','FERTILIZER'):continue
                        market=obs['market'];inv=market['inventory'][item]
                        marginal=self.m.market_price(item,inv+quantity-1,market.get('params'))
                        if marginal<=1:continue
                        for shed in ((4,4),(5,4),(4,5),(5,5)):
                            trial=path(start,pos)+[['HARVEST']]+path(pos,shed)+[['DROP']]+path(shed,goal)
                            if len(trial)>available:continue
                            deposit=now+last+1+distance(start,pos)+1+distance(pos,shed)
                            # Conservative visible-stock reservation through arrival; no sale credit.
                            pending=0
                            for cell,when in harvests.items():
                                if when<=deposit:
                                    tile2=farm['tiles'][cell[1]][cell[0]]
                                    if isinstance(tile2,dict):pending+=max(0,int(tile2.get('yield_units',0)))
                            reserved=sum(p['extra']['quantity'] for p in self.plans.values()
                                         if p.get('extra') and p['extra']['deposit_step']>=now)
                            stock=sum(private['shed'].values())+sum(sum(v.values()) for v in private['inventories'])+pending+reserved+quantity
                            if stock>100:continue
                            value=sum(self.m.market_price(item,inv+q,market.get('params')) for q in range(quantity))
                            candidates.append((value,-len(trial),-distance(pos,shed),pos,item,quantity,trial,deposit))
                if candidates:
                    extra=max(candidates,key=lambda z:z[:3]);trial=best[:last+1]+extra[6]
                    best=trial+[['PASS']]*(length-len(trial));self.reserved.add(extra[3])
            if saved<=0 and extra is None:continue
            for offset,a in enumerate(best):
                step=now+offset;old=route[step];new=deepcopy(old);set_unit(new,i,list(a));route[step]=new;self.edits.append((controller.cur,step,old))
            set_unit(out,i,list(best[0]));self.active[i]=t;planned+=1
            event={'step':now,'worker':i,'end':t,'route':controller.cur,'origin':origin,'goal':goal,'saved_travel':saved,'extra':None if extra is None else {'tile':extra[3],'item':extra[4],'quantity':extra[5],'deposit_step':extra[7]},'original':sequence,'replacement':best}
            self.plans[i]=event;self.events.append(event)
        return out
