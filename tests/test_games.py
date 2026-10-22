import unittest,random,copy,json,os,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from games import hitler as h,ninja as n
IDS=list('abcdefg')
class HitlerTests(unittest.TestCase):
 def test_roles_deck_privacy(self):
  for size in range(5,11):
   ids=list(map(str,range(size)));s=h.start(ids)
   self.assertEqual(list(s['roles'].values()).count('Фашист'),(size-5)//2+1)
   self.assertEqual(s['deck'].count('Л'),6);self.assertEqual(s['deck'].count('Ф'),11)
   for p in ids:
    v=h.view(s,p);self.assertNotIn('deck',v);self.assertNotIn('roles',v);self.assertNotIn('discard',v)
    if s['roles'][p]=='Либерал' or (s['roles'][p]=='Гитлер' and size>6):self.assertEqual(v['allies'],{})
 def test_simultaneous_votes_and_duplicate(self):
  s=h.start(IDS);h.act(s,s['pres'],{'target':h.eligible(s)[0]});h.act(s,'a',{'yes':True})
  self.assertEqual(h.view(s,'b')['result'],{});self.assertNotIn('votes',h.view(s,'b'))
  with self.assertRaises(AssertionError):h.act(s,'a',{'yes':False})
 def test_chaos_does_not_use_power(self):
  s=h.start(IDS);s['laws']['Ф']=2;s['tracker']=2;s['deck']=['Ф']+s['deck'];s['last']=['a','b'];h.failed(s)
  self.assertEqual(s['phase'],'nominate');self.assertEqual(s['last'],[]);self.assertEqual(s['tracker'],0)
 def test_term_limit_at_five(self):
  s=h.start(IDS);s.update(pres='c',last=['a','b'],dead=['f','g']);self.assertIn('a',h.eligible(s));self.assertNotIn('b',h.eligible(s))
 def test_hitler_election(self):
  s=h.start(IDS);t=next(p for p in IDS if s['roles'][p]=='Гитлер');s['pres']=next(p for p in IDS if p!=t);s['laws']['Ф']=3
  h.act(s,s['pres'],{'target':t})
  for p in IDS:h.act(s,p,{'yes':True})
  self.assertEqual(s['winner'],'Фашисты')
 def test_veto_tracker_and_refusal(self):
  s=h.start(IDS);s.update(phase='chancellor',pres='a',ch='b',hand=['Л','Ф'],tracker=1);s['laws']['Ф']=5
  h.act(s,'b',{'op':'veto'});h.act(s,'a',{'yes':False})
  with self.assertRaises(AssertionError):h.act(s,'b',{'op':'veto'})
  s['veto_refused']=False;h.act(s,'b',{'op':'veto'});h.act(s,'a',{'yes':True});self.assertEqual(s['tracker'],2)
 def test_powers_and_special_rotation(self):
  for size,powers in [(5,[None,None,'peek','execute','execute']),(7,[None,'investigate','special','execute','execute']),(9,['investigate','investigate','special','execute','execute'])]:
   for index,power in enumerate(powers):
    s=h.start(list(map(str,range(size))));s['laws']['Ф']=index;h.enact(s,'Ф');self.assertEqual(s['phase'],power or 'nominate')
  s=h.start(IDS);s.update(phase='special',pres='b');h.act(s,'b',{'target':'f'});h.advance(s);self.assertEqual(s['pres'],'c')
 def test_investigation_not_role_and_execution(self):
  s=h.start(IDS);t=next(i for i in IDS if s['roles'][i]=='Гитлер');p=next(i for i in IDS if i!=t);s.update(phase='investigate',pres=p)
  h.act(s,p,{'target':t});self.assertIn('Фашистская',s['notes'][p][-1]);self.assertNotIn('Гитлер',s['notes'][p][-1]);s.update(phase='execute',pres=p);h.act(s,p,{'target':t});self.assertEqual(s['winner'],'Либералы')
 def test_full_random_games(self):
  rng=random.Random(7)
  for trial in range(100):
   s=h.start(list(map(str,range(rng.randint(5,10)))))
   for step in range(1000):
    if s['winner']:break
    ph=s['phase'];p=s['pres']
    if ph=='nominate':h.act(s,p,{'target':rng.choice(h.eligible(s))})
    elif ph=='vote':h.act(s,next(i for i in h.living(s) if i not in s['votes']),{'yes':rng.random()<.7})
    elif ph in ('president','chancellor'):h.act(s,p if ph=='president' else s['ch'],{'index':rng.randrange(len(s['hand']))})
    elif ph=='peek':h.act(s,p,{})
    else:h.act(s,p,{'target':rng.choice([i for i in h.living(s) if i!=p and (ph!='investigate' or i not in s['investigated'])])})
    self.assertEqual(len(s['deck'])+len(s['discard'])+len(s['hand'])+sum(s['laws'].values()),17)
   self.assertIsNotNone(s['winner'])
class NinjaTests(unittest.TestCase):
 def state(self):return n.start(list('abcde'))
 def effect(self,s,kind,p='a',stage=3):s.update(phase='effect',active={'player':p,'card':next(c for c in n.deck() if c['kind']==kind)},queue=[],pending=None,stage=stage)
 def test_deck_and_draft(self):
  self.assertEqual(len(n.deck()),33);self.assertEqual(len(set(c['id'] for c in n.deck())),33)
  s=self.state();original=copy.deepcopy(s['offers'])
  for p in s['ids']:n.act(s,p,{'card':s['offers'][p][0]['id']})
  self.assertEqual(s['offers']['b'],original['a'][1:])
  for p in s['ids']:n.act(s,p,{'card':s['offers'][p][0]['id']})
  self.assertEqual(s['stage'],1);self.assertEqual(len(s['discard']),5);self.assertTrue(all(len(h)==2 for h in s['hands'].values()))
 def test_hidden_selection_and_order(self):
  s=self.state();s.update(phase='select',stage=1);s['hands']['a']=[n.card('spy',5,1)];s['hands']['b']=[n.card('spy',2,1)]
  n.act(s,'a',{'cards':['spy5']});self.assertEqual(n.view(s,'b')['played']['a'],[])
  for p in 'bcde':n.act(s,p,{'cards':['spy2'] if p=='b' else []})
  self.assertEqual(s['active']['player'],'b');n.act(s,'b',{'target':'a'});self.assertEqual(s['active']['player'],'a');n.act(s,'a',{'target':'b'});self.assertEqual(s['stage'],2)
 def test_shape_privacy_and_lock(self):
  s=self.state();self.effect(s,'shape');before=copy.deepcopy(s['clans']);n.act(s,'a',{'target':'b','target2':'c'});self.assertNotIn('pending',n.view(s,'b'));n.act(s,'a',{'yes':True})
  self.assertEqual(s['clans']['b'],before['c']);self.assertIsNone(n.view(s,'b')['clan']);self.assertIsNone(n.view(s,'c')['clan'])
 def test_reactions_and_judge(self):
  for kind,dead,reward in [('mirror','a',0),('martyr','b',1)]:
   s=self.state();s['hands']['b']=[n.card(kind)];self.effect(s,'blind',stage=4);n.act(s,'a',{'target':'b'});self.assertEqual(s['phase'],'reaction');n.act(s,'b',{'op':kind});self.assertIn(dead,s['dead']);self.assertEqual(len(s['tokens']['b']),reward)
  s=self.state();s['hands']['b']=[n.card('mirror')];self.effect(s,'judge');n.act(s,'a',{'target':'b'});self.assertIn('b',s['dead']);self.assertNotIn('a',s['dead'])
 def test_dead_actor_skipped(self):
  s=self.state();s['dead']=['b'];s['queue']=[{'player':'b','card':n.card('shinobi',1,5)}];s['stage']=5;n.advance(s);self.assertEqual(s['phase'],'morning')
 def test_thief_and_trade(self):
  s=self.state();s['tokens']['b']=[2,4];self.effect(s,'thief');n.act(s,'a',{'target':'b','index':1});self.assertEqual(s['tokens']['a'],[4]);self.assertIn('a',s['revealed'])
  self.effect(s,'trade');n.act(s,'a',{'target':'b','inspect':'token','index':0});n.act(s,'a',{'yes':True,'own':0,'other':0});self.assertEqual(s['tokens']['a'],[2]);self.assertEqual(s['tokens']['b'],[4])
 def test_grave_immediate(self):
  s=self.state();s['discard']=[n.card('spy',1,1),n.card('shinobi',1,5)];self.effect(s,'grave');n.act(s,'a',{});n.act(s,'a',{'card':'spy1','now':True});self.assertEqual(s['active']['card']['kind'],'spy');n.act(s,'a',{'target':'b'});self.assertEqual(s['stage'],4)
 def test_puppet_ronin(self):
  s=self.state();s['clans']['a']={'clan':'Ронин','rank':0};s['hands']['a']=[n.card('puppet')];n.morning(s);self.assertEqual(len(s['tokens']['a']),1);self.assertTrue(all(not s['tokens'][i] for i in 'bcde'))
 def test_tie_only_survivors_and_dead_clan_reward(self):
  s=self.state();s['clans']={'a':{'clan':'Журавль','rank':1},'b':{'clan':'Лотос','rank':1},'c':{'clan':'Журавль','rank':2},'d':{'clan':'Лотос','rank':2},'e':{'clan':'Ронин','rank':0}};s['dead']=['c','d'];n.morning(s);self.assertEqual([len(s['tokens'][i]) for i in 'abcde'],[1,1,0,0,1])
  s['tokens']={i:[] for i in 'abcde'};s['dead']=['b','c'];n.morning(s);self.assertEqual([len(s['tokens'][i]) for i in 'abcde'],[1,0,1,0,1])
 def test_full_random_games(self):
  rng=random.Random(19)
  for trial in range(80):
   s=n.start(list(map(str,range(rng.randint(3,11)))))
   for step in range(3500):
    if s['winner']:break
    ph=s['phase']
    if ph=='draft':p=next(i for i in s['ids'] if i not in s['picks']);n.act(s,p,{'card':rng.choice(s['offers'][p])['id']})
    elif ph=='select':p=next(i for i in s['ids'] if i not in s['dead'] and i not in s['ready']);n.act(s,p,{'cards':[c['id'] for c in s['hands'][p] if c['stage']==s['stage']]})
    elif ph=='reaction':p=s['pending']['target'];n.act(s,p,{'op':next(c['kind'] for c in s['hands'][p] if c['kind'] in ('mirror','martyr'))})
    elif ph=='morning':n.newround(s)
    else:
     p=s['active']['player'];kind=s['active']['card']['kind'];pd=s['pending']
     if pd:
      if pd['type']=='grave':a={'card':rng.choice(pd['cards'])['id'],'now':True}
      elif pd['type']=='trade':a={'yes':False}
      else:a={'yes':True}
     elif kind=='grave':a={}
     else:
      t=rng.choice(n.targets(s,p,kind));a={'target':t,'target2':rng.choice([i for i in s['ids'] if i!=t]),'index':0}
     n.act(s,p,a)
    self.assertEqual(len(s['bag'])+sum(len(t) for t in s['tokens'].values()),35)
   self.assertIsNotNone(s['winner'],(trial,s['phase'],s['round']))
class ServerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();os.environ['DATA_DIR']=cls.tmp.name
  import server;cls.s=server
 def test_auth_persistence_stale_and_host(self):
  v=self.s.process('/api/create',{'game':'ninja','name':'Аня'},'');r=v['room'];token=v['token'];code=r['code']
  with self.assertRaises(self.s.Bad):self.s.process('/api/state',{'code':code},'bad')
  self.assertEqual(self.s.process('/api/state',{'code':code},token)['room']['me'],r['me'])
  for name in ['Боря','Вика']:other=self.s.process('/api/join',{'code':code,'name':name},'')
  with self.assertRaises(self.s.Bad):self.s.process('/api/start',{'code':code,'version':1},token)
  version=self.s.fetch(code)['version']
  with self.assertRaises(self.s.Bad):self.s.process('/api/start',{'code':code,'version':version},other['token'])
  out=self.s.process('/api/start',{'code':code,'version':version},token)
  self.assertEqual(out['room']['state']['phase'],'draft')
  payload=json.dumps(out);self.assertNotIn('offers": {',payload);self.assertNotIn('clans',payload);self.assertNotIn('token"',payload)
  before=self.s.fetch(code)
  with self.assertRaises(AssertionError):self.s.process('/api/action',{'code':code,'version':before['version'],'turn':before.get('turn',0),'card':'wrong'},token)
  self.assertEqual(self.s.fetch(code),before)
 def test_concurrent_draft_same_revision(self):
  first=self.s.process('/api/create',{'game':'ninja','name':'Один'},'');code=first['room']['code'];users=[first]
  for name in ['Два','Три']:users.append(self.s.process('/api/join',{'code':code,'name':name},''))
  r=self.s.fetch(code);self.s.process('/api/start',{'code':code,'version':r['version']},first['token'])
  r=self.s.fetch(code);version=r['version'];turn=r['turn']
  for u in users:
   pid=u['room']['me'];self.s.process('/api/action',{'code':code,'version':version,'turn':turn,'card':r['state']['offers'][pid][0]['id']},u['token'])
  self.assertEqual(self.s.fetch(code)['state']['draftStep'],2)
  with self.assertRaises(self.s.Bad):self.s.process('/api/action',{'code':code,'version':version,'turn':turn,'card':'spy1'},first['token'])
if __name__=='__main__':unittest.main()
