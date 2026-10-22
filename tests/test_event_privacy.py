import unittest,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from games import ninja as n,hitler as h
class EventPrivacy(unittest.TestCase):
 def effect(self,kind):
  s=n.start(['alice','bob','carol']);s.update(phase='effect',stage=3,active={'player':'alice','card':next(c for c in n.deck() if c['kind']==kind)},pending=None,queue=[]);return s
 def test_peek_result_never_public(self):
  s=self.effect('spy');other=copy.deepcopy(s);other['clans']['bob']={'clan':'ДРУГОЙ СЕКРЕТ','rank':99}
  n.act(s,'alice',{'target':'bob'});n.act(other,'alice',{'target':'bob'})
  self.assertEqual(s['log'],other['log']);self.assertTrue(any('alice смотрит клан игрока bob' in x for x in s['log']));self.assertNotEqual(s['notes']['alice'],other['notes']['alice'])
 def test_shape_decision_is_secret(self):
  s=self.effect('shape');n.act(s,'alice',{'target':'bob','target2':'carol'});other=copy.deepcopy(s)
  n.act(s,'alice',{'yes':True});n.act(other,'alice',{'yes':False});self.assertEqual(s['log'],other['log'])
 def test_grave_choice_is_secret_until_played(self):
  s=self.effect('grave');s['pending']={'type':'grave','cards':[n.card('spy',1,1),n.card('shinobi',2,5)]};s['discard']=s['pending']['cards'].copy();other=copy.deepcopy(s)
  n.act(s,'alice',{'card':'spy1','now':False});n.act(other,'alice',{'card':'shinobi2','now':False});self.assertEqual(s['log'],other['log'])
 def test_token_value_is_secret(self):
  s=self.effect('thief');s['tokens']['bob']=[2];other=copy.deepcopy(s);other['tokens']['bob']=[4]
  n.act(s,'alice',{'target':'bob','index':0});n.act(other,'alice',{'target':'bob','index':0});self.assertEqual(s['log'],other['log'])
 def test_choices_revealed_simultaneously(self):
  s=self.effect('spy');s.update(phase='select',stage=1,active=None);s['hands']['alice']=[n.card('spy',1,1)]
  original=list(s['log']);n.act(s,'alice',{'cards':['spy1']});self.assertEqual(s['log'],original)
  n.act(s,'bob',{'cards':[]});self.assertEqual(s['log'],original)
  n.act(s,'carol',{'cards':[]});self.assertIn('alice играет: Шпион 1',s['log']);self.assertIn('bob пасует',s['log'])
 def test_votes_and_investigation_privacy(self):
  ids=['alice','bob','carol','dave','eve'];s=h.start(ids);h.act(s,s['pres'],{'target':h.eligible(s)[0]});before=list(s['log'])
  h.act(s,'alice',{'yes':True});self.assertEqual(s['log'],before)
  for p in ids[1:]:h.act(s,p,{'yes':True})
  self.assertTrue(any('alice — за' in x for x in s['log']))
  s.update(phase='investigate',pres='alice');other=copy.deepcopy(s);s['roles']['bob']='Либерал';other['roles']['bob']='Гитлер'
  h.act(s,'alice',{'target':'bob'});h.act(other,'alice',{'target':'bob'});self.assertEqual(s['log'],other['log'])
 def test_invalid_action_not_logged(self):
  s=self.effect('spy');before=list(s['log'])
  with self.assertRaises(AssertionError):n.act(s,'bob',{'target':'carol'})
  self.assertEqual(s['log'],before)
if __name__=='__main__':unittest.main()
