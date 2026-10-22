import secrets
R=secrets.SystemRandom()
def shuffled(x):
 x=list(x);R.shuffle(x);return x
def start(ids):
 n=len(ids); assert 5<=n<=10,'Нужно 5–10 игроков'
 roles=shuffled(['Гитлер']+['Фашист']*((n-5)//2+1)+['Либерал']*(n-1-((n-5)//2+1)))
 return dict(kind='hitler',phase='nominate',ids=ids,roles=dict(zip(ids,roles)),dead=[],pres=R.choice(ids),ch=None,last=[],votes={},laws={'Л':0,'Ф':0},deck=shuffled(['Л']*6+['Ф']*11),discard=[],hand=[],tracker=0,investigated=[],resume=None,log=[],notes={i:[] for i in ids},winner=None)
def living(s):return [i for i in s['ids'] if i not in s['dead']]
def nextid(s,i):
 ids=s['ids'];return next(ids[(ids.index(i)+k)%len(ids)] for k in range(1,len(ids)+1) if ids[(ids.index(i)+k)%len(ids)] not in s['dead'])
def eligible(s):return [i for i in living(s) if i!=s['pres'] and i not in (s['last'][-1:] if len(living(s))<=5 else s['last'])]
def refill(s):
 if len(s['deck'])<3:s['deck']=shuffled(s['deck']+s['discard']);s['discard']=[]
def advance(s):
 s['pres']=nextid(s,s['resume'] or s['pres']);s['resume']=None;s['phase']='nominate';s['ch']=None;s['votes']={};s['hand']=[];s['veto_refused']=False
def enact(s,law,chaos=False):
 s['laws'][law]+=1;s['tracker']=0;s['log'].append('Принят '+('либеральный' if law=='Л' else 'фашистский')+' закон'+(' (хаос)' if chaos else ''))
 refill(s)
 if s['laws']['Л']>=5:s['winner']='Либералы'
 if s['laws']['Ф']>=6:s['winner']='Фашисты'
 if s['winner']:s['phase']='finished';return
 power=None
 if law=='Ф' and not chaos:
  f=s['laws']['Ф'];n=len(s['ids'])
  if f in (4,5):power='execute'
  elif f==3:power='peek' if n<=6 else 'special'
  elif (n>=9 and f in (1,2)) or (n in (7,8) and f==2):power='investigate'
 if power:
  s['phase']=power
  if power=='peek':s['notes'][s['pres']].append('Верх колоды: '+' · '.join(s['deck'][:3]))
 else:advance(s)
def failed(s):
 s['tracker']+=1
 if s['tracker']==3:
  s['last']=[];enact(s,s['deck'].pop(0),True)
 else:advance(s)
def _act(s,p,a):
 phase=s['phase'];t=a.get('target');op=a.get('op')
 assert not s['winner'],'Партия завершена'
 if phase=='nominate':
  assert p==s['pres'] and t in eligible(s),'Недоступный кандидат'
  s['ch']=t;s['phase']='vote';s['votes']={}
 elif phase=='vote':
  assert p in living(s) and p not in s['votes'] and type(a.get('yes')) is bool,'Голос уже принят или недоступен'
  s['votes'][p]=a['yes']
  if len(s['votes'])==len(living(s)):
   s['result']=dict(s['votes'])
   if sum(s['votes'].values())>len(living(s))/2:
    s['last']=[s['pres'],s['ch']]
    if s['laws']['Ф']>=3 and s['roles'][s['ch']]=='Гитлер':s['winner']='Фашисты';s['phase']='finished'
    else:refill(s);s['hand']=s['deck'][:3];del s['deck'][:3];s['phase']='president'
   else:failed(s)
 elif phase in ('president','chancellor'):
  assert p==(s['pres'] if phase=='president' else s['ch']),'Сейчас ход другого игрока'
  if op=='veto':
   assert phase=='chancellor' and s['laws']['Ф']>=5 and not s.get('veto_refused'),'Вето недоступно'
   s['phase']='veto';return
  k=a.get('index');assert type(k) is int and 0<=k<len(s['hand']),'Выберите карту'
  if phase=='president':s['discard'].append(s['hand'].pop(k));s['phase']='chancellor'
  else:
   law=s['hand'].pop(k);s['discard']+=s['hand'];s['hand']=[];enact(s,law)
 elif phase=='veto':
  assert p==s['pres'] and type(a.get('yes')) is bool,'Решает президент'
  if a['yes']:s['discard']+=s['hand'];s['hand']=[];failed(s)
  else:s['veto_refused']=True;s['phase']='chancellor'
 else:
  assert p==s['pres'],'Решает президент'
  if phase=='peek':advance(s);return
  assert t in living(s) and t!=p,'Выберите другого живого игрока'
  if phase=='investigate':
   assert t not in s['investigated'],'Этот игрок уже проверен'
   s['investigated'].append(t);s['notes'][p].append('Партия '+t+': '+('Либеральная' if s['roles'][t]=='Либерал' else 'Фашистская'));advance(s)
  elif phase=='special':s['resume']=p;s['pres']=t;s['ch']=None;s['phase']='nominate';s['votes']={}
  elif phase=='execute':
   s['dead'].append(t);s['log'].append('Казнён '+t)
   if s['roles'][t]=='Гитлер':s['winner']='Либералы';s['phase']='finished'
   else:advance(s)
  else:raise AssertionError('Неизвестное действие')
def act(s,p,a):
 """Public chronology; hidden votes and discarded policies never enter the log."""
 phase=s['phase'];t=a.get('target');offset=len(s['log']);events=[]
 if phase=='nominate':events=[p+' выдвигает '+str(t)+' в канцлеры']
 elif phase=='president':events=[p+' сбрасывает один закон и передаёт два канцлеру '+str(s['ch'])]
 elif phase=='chancellor':events=[p+(' предлагает вето' if a.get('op')=='veto' else ' принимает закон')]
 elif phase=='veto':events=[p+(' соглашается с вето' if a.get('yes') else ' отклоняет вето')]
 elif phase=='investigate':events=[p+' проверяет партийную принадлежность игрока '+str(t)]
 elif phase=='special':events=[p+' назначает '+str(t)+' на внеочередные выборы']
 elif phase=='execute':events=[p+' приказывает казнить '+str(t)]
 elif phase=='peek':events=[p+' завершает просмотр трёх верхних законов']
 _act(s,p,a)
 if phase=='vote' and s['phase']!='vote':
  result=s['result'];approved=sum(result.values())>len(result)/2
  events=['Голосование: '+', '.join(i+' — '+('за' if result[i] else 'против') for i in s['ids'] if i in result),'Правительство '+('избрано' if approved else 'отклонено')]
 s['log'][offset:offset]=events
 if s['phase']=='peek' and phase!='peek':s['log'].append(s['pres']+' смотрит три верхних закона')
 if s['phase']=='nominate' and phase!='nominate':s['log'].append('Кандидат в президенты: '+s['pres'])
 if s['winner']:s['log'].append('Победа: '+s['winner'])

def view(s,p):
 out={k:s[k] for k in ('kind','phase','ids','dead','pres','ch','laws','tracker','winner','log','investigated')}
 out.update(role=s['roles'][p],notes=s['notes'][p],voted=list(s['votes']),result=s.get('result',{}),eligible=eligible(s),deckCount=len(s['deck']),discardCount=len(s['discard']))
 out['allies']={i:r for i,r in s['roles'].items() if i!=p and r!='Либерал'} if s['roles'][p]=='Фашист' or (s['roles'][p]=='Гитлер' and len(s['ids'])<=6) else {}
 out['hand']=s['hand'] if (s['phase']=='president' and p==s['pres']) or (s['phase']=='chancellor' and p==s['ch']) else []
 out['vetoAvailable']=s['laws']['Ф']>=5 and not s.get('veto_refused')
 if s['winner']:out['roles']=s['roles']
 return out
