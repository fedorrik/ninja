import secrets
R=secrets.SystemRandom()
NAMES={'spy':'Шпион','mystic':'Мистик','shape':'Оборотень','grave':'Могильщик','rebel':'Мятежник','trade':'Торговец духами','thief':'Вор','judge':'Судья','blind':'Слепой убийца','shinobi':'Синоби','mirror':'Зеркальный монах','martyr':'Мученик','puppet':'Кукловод'}
DESC={'spy':'Посмотрите клан другого игрока.','mystic':'Посмотрите клан и случайную скрытую карту ниндзя другого игрока.','shape':'Посмотрите кланы двух игроков. Затем можете тайно поменять их местами. Оба больше не могут смотреть свой клан.','grave':'Посмотрите две случайные карты сброса и возьмите одну. Можно сыграть её сразу или в её этап.','rebel':'Посмотрите клан другого игрока. Затем можете раскрыть его всем.','trade':'Посмотрите клан или один жетон другого игрока. Затем можете обменять любой его жетон на свой.','thief':'Раскройте свой клан и заберите один закрытый жетон чести другого игрока.','judge':'Раскройте свой клан и убейте любого игрока. Реакции не действуют.','blind':'Убейте любого игрока.','shinobi':'Посмотрите клан любого игрока. Затем можете убить его.','mirror':'В ответ на слепого убийцу или синоби: вместо вас погибает нападающий.','martyr':'В ответ на слепого убийцу или синоби: погибните и получите жетон чести.','puppet':'Если выжили: утром ваш клан побеждает. Ронин с этой картой получает награду один.'}
def shuffle(x):x=list(x);R.shuffle(x);return x
def card(kind,rank=0,stage=0):return dict(id=kind+str(rank),kind=kind,rank=rank,stage=stage,name=NAMES[kind],text=DESC[kind])
def deck():
 return [card(k,r,st) for k,st in [('spy',1),('mystic',2),('blind',4),('shinobi',5)] for r in range(1,7)]+[card(k,r,3) for r,k in enumerate(['shape','grave','rebel','trade','thief','judge'],1)]+[card(k) for k in ('mirror','martyr','puppet')]
def start(ids):
 assert 3<=len(ids)<=11,'Нужно 3–11 игроков'
 s=dict(kind='ninja',ids=ids,tokens={i:[] for i in ids},bag=shuffle([2]*14+[3]*14+[4]*7),round=0,winner=None,log=[])
 newround(s);return s
def newround(s):
 s['round']+=1;s['log'].append('Раунд '+str(s['round'])+' · закат');n=len(s['ids']);clans=shuffle([{'clan':c,'rank':r} for c in ('Журавль','Лотос') for r in range(1,n//2+1)]+([{'clan':'Ронин','rank':0}] if n%2 else []));d=shuffle(deck())
 s.update(phase='draft',draftStep=1,clans=dict(zip(s['ids'],clans)),hands={i:[] for i in s['ids']},offers={i:d[k*3:k*3+3] for k,i in enumerate(s['ids'])},picks={},discard=[],dead=[],locked=[],revealed={},notes={i:[] for i in s['ids']},played={i:[] for i in s['ids']},stage=0,ready={},queue=[],active=None,pending=None)
def note(s,p,x):s['notes'][p].append(x)
def peek(s,p,t):
 c=s['clans'][t];note(s,p,t+': '+c['clan']+(' · ранг '+str(c['rank']) if c['rank'] else ''))
def reveal(s,t):
 s['revealed'][t]=dict(s['clans'][t]);s['log'].append(t+' раскрывает карту клана')
def award(s,p):
 if s['bag']:s['tokens'][p].append(s['bag'].pop());s['log'].append(p+' получает жетон чести')
def morning(s):
 s['phase']='morning';s['active']=None
 for i in s['ids']:
  if i not in s['dead']:reveal(s,i)
 puppet=next((i for i in s['ids'] if i not in s['dead'] and any(c['kind']=='puppet' for c in s['hands'][i])),None)
 win=None;tie=False
 if puppet:
  win=s['clans'][puppet]['clan'];s['played'][puppet]+=[c for c in s['hands'][puppet] if c['kind']=='puppet'];s['hands'][puppet]=[c for c in s['hands'][puppet] if c['kind']!='puppet'];s['log'].append(puppet+' раскрывает Кукловода')
 else:
  ranks={c:sorted(s['clans'][i]['rank'] for i in s['ids'] if i not in s['dead'] and s['clans'][i]['clan']==c) for c in ('Журавль','Лотос')}
  a,b=ranks.values();width=max(len(a),len(b));aa=a+[99]*(width-len(a));bb=b+[99]*(width-len(b))
  if aa==bb:tie=True
  else:win='Журавль' if aa<bb else 'Лотос'
 for i in s['ids']:
  clan=s['clans'][i]['clan'];alive=i not in s['dead']
  if (puppet and win=='Ронин' and i==puppet) or (win!='Ронин' and ((clan==win) or (tie and alive) or (clan=='Ронин' and alive))):award(s,i)
 s['log'].append('Утро: '+('полная ничья' if tie else 'превосходство — '+str(win)))
 scores={i:sum(s['tokens'][i]) for i in s['ids']};top=max(scores.values())
 if top>=10:s['winner']=[i for i,v in scores.items() if v==top];s['phase']='finished'
def advance(s):
 s['pending']=None;s['active']=None
 while s['queue']:
  item=s['queue'].pop(0)
  if item['player'] in s['dead']:continue
  s['active']=item;s['phase']='effect';return
 s['stage']+=1;s['ready']={}
 if s['stage']>5 or len(s['dead'])==len(s['ids']):morning(s)
 else:s['phase']='select';s['log'].append('Этап: '+['','Шпионы','Мистики','Трикстеры','Слепые убийцы','Синоби'][s['stage']])
def kill(s,p,t,react=True):
 if t in s['dead']:advance(s);return
 if react and any(c['kind'] in ('mirror','martyr') for c in s['hands'][t]):s['pending']={'type':'reaction','attacker':p,'target':t};s['phase']='reaction'
 else:s['dead'].append(t);s['log'].append(t+' погибает');advance(s)
def targets(s,p,kind):
 return [i for i in s['ids'] if i!=p or kind in ('shape','blind','shinobi','judge')]
def _act(s,p,a):
 phase=s['phase'];op=a.get('op');t=a.get('target')
 assert not s['winner'],'Партия завершена'
 if phase=='draft':
  assert p not in s['picks'],'Вы уже выбрали карту'
  k=a.get('card');c=next((c for c in s['offers'][p] if c['id']==k),None);assert c,'Выберите карту'
  s['picks'][p]=k
  if len(s['picks'])==len(s['ids']):
   remaining={}
   for i in s['ids']:
    s['hands'][i]+=[c for c in s['offers'][i] if c['id']==s['picks'][i]];remaining[i]=[c for c in s['offers'][i] if c['id']!=s['picks'][i]]
   if s['draftStep']==1:s['offers']={s['ids'][(k+1)%len(s['ids'])]:remaining[i] for k,i in enumerate(s['ids'])};s['draftStep']=2;s['picks']={}
   else:s['discard']=[c for cs in remaining.values() for c in cs];s['offers']={};advance(s)
 elif phase=='select':
  assert p not in s['dead'] and p not in s['ready'],'Вы уже готовы или выбыли'
  chosen=a.get('cards',[]);assert isinstance(chosen,list) and len(chosen)==len(set(chosen)),'Некорректные карты'
  allowed=[c['id'] for c in s['hands'][p] if c['stage']==s['stage']];assert all(c in allowed for c in chosen),'Эти карты сейчас не играют'
  s['ready'][p]=chosen
  if all(i in s['ready'] for i in s['ids'] if i not in s['dead']):
   for i,keys in s['ready'].items():
    cards=[c for c in s['hands'][i] if c['id'] in keys];s['hands'][i]=[c for c in s['hands'][i] if c['id'] not in keys];s['played'][i]+=cards;s['queue']+=[{'player':i,'card':c} for c in cards]
   s['queue'].sort(key=lambda x:x['card']['rank']);advance(s)
 elif phase=='reaction':
  pend=s['pending'];assert p==pend['target'],'Реагирует атакованный игрок'
  if op=='accept':s['dead'].append(p);s['log'].append(p+' погибает');advance(s);return
  c=next((c for c in s['hands'][p] if c['kind']==op and op in ('mirror','martyr')),None);assert c,'Нет такой реакции'
  s['hands'][p].remove(c);s['played'][p].append(c)
  victim=pend['attacker'] if op=='mirror' else p
  if victim not in s['dead']:s['dead'].append(victim)
  if op=='martyr':award(s,p)
  s['log'].append(victim+' погибает ('+c['name']+')');advance(s)
 elif phase=='effect':
  cur=s['active'];assert cur and p==cur['player'] and p not in s['dead'],'Сейчас ход другого игрока'
  kind=cur['card']['kind'];pend=s['pending']
  if pend:
   if pend['type']=='shape':
    assert type(a.get('yes')) is bool,'Подтвердите решение'
    x,y=pend['targets']
    if a['yes']:s['clans'][x],s['clans'][y]=s['clans'][y],s['clans'][x]
    for i in (x,y):
     if i not in s['locked']:s['locked'].append(i)
     if i in s['revealed']:reveal(s,i)
    advance(s)
   elif pend['type']=='shinobi':
    assert type(a.get('yes')) is bool,'Подтвердите решение'
    if a['yes']:kill(s,p,pend['target'])
    else:advance(s)
   elif pend['type']=='rebel':
    if a.get('yes'):reveal(s,pend['target'])
    advance(s)
   elif pend['type']=='trade':
    if a.get('yes'):
     x=a.get('own');y=a.get('other');t=pend['target'];assert type(x) is int and type(y) is int and 0<=x<len(s['tokens'][p]) and 0<=y<len(s['tokens'][t]),'Выберите два жетона'
     s['tokens'][p][x],s['tokens'][t][y]=s['tokens'][t][y],s['tokens'][p][x]
    advance(s)
   elif pend['type']=='grave':
    c=next((c for c in pend['cards'] if c['id']==a.get('card')),None);assert c,'Выберите карту'
    s['discard'].remove(c);s['hands'][p].append(c)
    if a.get('now') and c['stage']>0:
     s['hands'][p].remove(c);s['played'][p].append(c);s['queue'].insert(0,{'player':p,'card':c})
    advance(s)
   return
  if kind=='grave':
   cards=R.sample(s['discard'],min(2,len(s['discard'])))
   if cards:s['pending']={'type':'grave','cards':cards}
   else:advance(s)
   return
  assert t in targets(s,p,kind),'Недопустимая цель'
  if kind=='shape':
   t2=a.get('target2');assert t2 in s['ids'] and t2!=t,'Выберите двух разных игроков';peek(s,p,t);peek(s,p,t2);s['pending']={'type':'shape','targets':[t,t2]}
  elif kind in ('spy','mystic','rebel','shinobi'):
   peek(s,p,t)
   if kind=='mystic' and s['hands'][t]:note(s,p,'Карта '+t+': '+R.choice(s['hands'][t])['name'])
   if kind in ('rebel','shinobi'):s['pending']={'type':kind,'target':t}
   else:advance(s)
  elif kind=='trade':
   if a.get('inspect')=='token':
    k=a.get('index');assert type(k) is int and 0<=k<len(s['tokens'][t]),'Укажите жетон';note(s,p,'Жетон '+t+' №'+str(k+1)+': '+str(s['tokens'][t][k]))
   else:peek(s,p,t)
   s['pending']={'type':'trade','target':t}
  elif kind=='thief':
   reveal(s,p)
   if s['tokens'][t]:
    k=a.get('index');assert type(k) is int and 0<=k<len(s['tokens'][t]),'Выберите жетон';s['tokens'][p].append(s['tokens'][t].pop(k))
   advance(s)
  elif kind=='judge':reveal(s,p);kill(s,p,t,False)
  elif kind=='blind':kill(s,p,t)
  else:raise AssertionError('Неизвестная карта')
 elif phase=='morning':raise AssertionError('Следующий раунд начинает хозяин комнаты')
 else:raise AssertionError('Действие недоступно')
def act(s,p,a):
 """Log only observable actions after validation; never copy private notes or choices."""
 phase=s['phase'];before_stage=s['stage'];before_ready=dict(s['ready']);pending=s.get('pending');active=s.get('active');t=a.get('target');events=[];offset=len(s['log'])
 if phase=='draft':events=[p+' выбирает карту ниндзя']
 elif phase=='effect' and active:
  kind=active['card']['kind'];label=active['card']['name']
  if pending:
   target=pending.get('target')
   if kind=='shape':events=[p+' завершает действие Оборотня'] # identical for swap and no swap
   elif kind=='shinobi':events=[p+(' атакует ' if a.get('yes') else ' не атакует ')+str(target)+' · Синоби']
   elif kind=='rebel':events=[p+(' раскрывает клан игрока ' if a.get('yes') else ' оставляет скрытым клан игрока ')+str(target)+' · Мятежник']
   elif kind=='trade':events=[p+(' обменивается жетоном чести с ' if a.get('yes') else ' отказывается от обмена с ')+str(target)]
   elif kind=='grave':
    events=[p+' берёт одну карту из сброса']
    chosen=next((c for c in pending.get('cards',[]) if c['id']==a.get('card')),None)
    if chosen and a.get('now') and chosen['stage']>0:events.append(p+' сразу играет карту «'+chosen['name']+' '+str(chosen['rank'])+'»')
  elif kind=='grave':events=[p+' смотрит карты в сбросе · Могильщик']
  elif kind=='shape':events=[p+' смотрит кланы игроков '+str(t)+' и '+str(a.get('target2'))+' · Оборотень']
  elif kind=='mystic':events=[p+' смотрит клан и скрытую карту ниндзя игрока '+str(t)+' · Мистик']
  elif kind in ('spy','rebel','shinobi'):events=[p+' смотрит клан игрока '+str(t)+' · '+label]
  elif kind=='trade':events=[p+' смотрит '+('жетон чести' if a.get('inspect')=='token' else 'клан')+' игрока '+str(t)+' · Торговец духами']
  elif kind=='thief':events=[p+(' забирает жетон чести у ' if s['tokens'].get(t) else ' применяет Вора к игроку без жетонов: ')+str(t)+' · Вор']
  elif kind in ('blind','judge'):events=[p+' атакует '+str(t)+' · '+label]
 elif phase=='reaction':
  events=[p+' принимает удар'] if a.get('op')=='accept' else [p+' применяет реакцию «'+NAMES.get(a.get('op'),'')+'» против '+str(pending.get('attacker'))]
 _act(s,p,a)
 if phase=='select' and (s['phase']!='select' or s['stage']!=before_stage):
  before_ready[p]=a.get('cards',[])
  public_cards={c['id']:c for c in deck()}
  for actor in s['ids']:
   if actor not in before_ready:continue
   keys=before_ready[actor]
   events.append(actor+(' играет: '+', '.join(public_cards[k]['name']+' '+str(public_cards[k]['rank']) for k in keys) if keys else ' пасует'))
 s['log'][offset:offset]=events
 if s['winner']:s['log'].append('Победа: '+', '.join(s['winner']))

def view(s,p):
 out={k:s[k] for k in ('kind','phase','ids','dead','round','stage','revealed','played','winner','log')}
 out.update(hand=s['hands'][p],tokens=s['tokens'][p],tokenCounts={i:len(s['tokens'][i]) for i in s['ids']},clan=None if p in s['locked'] else s['clans'][p],notes=s['notes'][p],ready=list(s['ready']),picked=list(s['picks']),draftStep=s['draftStep'],offers=s['offers'].get(p,[]),active=s['active'])
 if s['active'] and s['active']['player']==p:out['pending']=s['pending'];out['targets']=targets(s,p,s['active']['card']['kind'])
 if s['phase']=='reaction':
  out['reactionTarget']=s['pending']['target']
  if p==s['pending']['target']:out['pending']=s['pending']
 if s['winner']:out['scores']={i:sum(s['tokens'][i]) for i in s['ids']}
 return out
