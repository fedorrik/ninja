#!/usr/bin/env python3
"""Single-process authoritative game server. Python 3.11+, standard library only."""
import os,json,time,secrets,sqlite3,threading,mimetypes,collections
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from games import hitler,ninja
ROOT=Path(__file__).parent
DATA=Path(os.getenv('DATA_DIR',ROOT/'data'));DATA.mkdir(parents=True,exist_ok=True)
DB=sqlite3.connect(DATA/'rooms.sqlite3',check_same_thread=False)
DB.execute('PRAGMA journal_mode=WAL');DB.execute('CREATE TABLE IF NOT EXISTS rooms(code TEXT PRIMARY KEY, body TEXT NOT NULL, updated REAL NOT NULL)');DB.commit()
LOCK=threading.RLock();ENGINES={'hitler':hitler,'ninja':ninja};SEEN={};LIMIT=collections.defaultdict(collections.deque)
TTL=7*86400
class Bad(Exception):pass
def turn_signature(state):
 if not state:return 'lobby'
 return json.dumps({k:state.get(k) for k in ('phase','pres','ch','round','stage','draftStep','active','pending','winner')},sort_keys=True)
def save(r):
 r['updated']=time.time();r['version']=r.get('version',0)+1
 DB.execute('INSERT OR REPLACE INTO rooms VALUES(?,?,?)',(r['code'],json.dumps(r,ensure_ascii=False),r['updated']));DB.commit()
def fetch(code):
 row=DB.execute('SELECT body FROM rooms WHERE code=? AND updated>?',(code,time.time()-TTL)).fetchone()
 if not row:raise Bad('Комната не найдена или срок хранения истёк')
 return json.loads(row[0])
def name(v):
 if not isinstance(v,str) or not 1<=len(v.strip())<=24:raise Bad('Имя должно содержать от 1 до 24 символов')
 return v.strip()
def auth(r,token):
 p=next((p for p in r['players'] if secrets.compare_digest(p['token'],token)),None)
 if not p:raise Bad('Нет доступа к этой комнате. Войдите по коду.')
 SEEN[(r['code'],p['id'])]=time.time();return p
def public(r,p):
 return {'code':r['code'],'game':r['game'],'host':r['host'],'me':p['id'],'version':r['version'],'turn':r.get('turn',0),'players':[{'id':x['id'],'name':x['name'],'online':time.time()-SEEN.get((r['code'],x['id']),0)<20} for x in r['players']],'state':ENGINES[r['game']].view(r['state'],p['id']) if r['state'] else None}
def newplayer(n):return {'id':secrets.token_hex(4),'name':name(n),'token':secrets.token_urlsafe(32)}
def process(path,a,token):
 code=str(a.get('code','')).upper().strip()
 if path=='/api/create':
  if a.get('game') not in ENGINES:raise Bad('Выберите игру')
  if DB.execute('SELECT count(*) FROM rooms').fetchone()[0]>=5000:raise Bad('Сервер заполнен')
  while True:
   code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
   if not DB.execute('SELECT 1 FROM rooms WHERE code=?',(code,)).fetchone():break
  p=newplayer(a.get('name'));r={'code':code,'game':a['game'],'host':p['id'],'players':[p],'state':None};save(r);SEEN[(code,p['id'])]=time.time();return {'token':p['token'],'room':public(r,p)}
 r=fetch(code)
 if path=='/api/join':
  if r['state']:raise Bad('Игра уже идёт. Вернуться можно из того же браузера.')
  if len(r['players'])>=(10 if r['game']=='hitler' else 11):raise Bad('Комната заполнена')
  p=newplayer(a.get('name'))
  if any(x['name'].casefold()==p['name'].casefold() for x in r['players']):raise Bad('Это имя уже занято')
  r['players'].append(p);save(r);SEEN[(code,p['id'])]=time.time();return {'token':p['token'],'room':public(r,p)}
 p=auth(r,token);pid=p['id']
 if path=='/api/state':return {'room':public(r,p)}
 if path=='/api/action':
  if a.get('turn')!=r.get('turn',0):raise Bad('Стол изменился. Повторите действие.')
 elif a.get('version')!=r['version']:raise Bad('Стол изменился. Повторите действие.')
 before_turn=turn_signature(r['state'])
 if path=='/api/start':
  if pid!=r['host'] or r['state']:raise Bad('Начать может хозяин комнаты в лобби')
  r['state']=ENGINES[r['game']].start([x['id'] for x in r['players']])
 elif path=='/api/action':
  if not r['state']:raise Bad('Игра ещё не началась')
  ENGINES[r['game']].act(r['state'],pid,a)
 elif path=='/api/next':
  if pid!=r['host'] or not r['state'] or r['game']!='ninja' or r['state']['phase']!='morning':raise Bad('Недоступно')
  ninja.newround(r['state'])
 elif path=='/api/reset':
  if pid!=r['host']:raise Bad('Только хозяин может вернуть комнату в лобби')
  r['state']=None
 elif path=='/api/host':
  target=a.get('target')
  if pid!=r['host'] or not any(x['id']==target for x in r['players']):raise Bad('Недоступно')
  r['host']=target
 elif path=='/api/claim':
  if time.time()-SEEN.get((code,r['host']),0)<120:raise Bad('Хозяин недавно был онлайн. Подождите две минуты.')
  r['host']=pid
 elif path=='/api/leave':
  if r['state']:raise Bad('Покинуть место можно в лобби. Во время игры можно закрыть вкладку и вернуться.')
  r['players']=[x for x in r['players'] if x['id']!=pid]
  if not r['players']:DB.execute('DELETE FROM rooms WHERE code=?',(code,));DB.commit();return {'left':True}
  if r['host']==pid:r['host']=r['players'][0]['id']
  save(r);return {'left':True}
 elif path=='/api/kick':
  if pid!=r['host'] or r['state'] or a.get('target')==pid:raise Bad('Удаление доступно хозяину в лобби')
  r['players']=[x for x in r['players'] if x['id']!=a.get('target')]
 else:raise Bad('Неизвестный запрос')
 if turn_signature(r['state'])!=before_turn:r['turn']=r.get('turn',0)+1
 save(r);return {'room':public(r,p)}
class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def setup(self):
  super().setup();self.connection.settimeout(15)
 def log_message(self,*args):pass
 def reply(self,status,body,ctype='application/json; charset=utf-8'):
  if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=self.path.split('?')[0]
  if path=='/health':self.reply(200,{'ok':True});return
  files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/rules':'rules.html','/images/ninja.png':'images/ninja.png','/images/hitler.png':'images/hitler.png'}
  if path not in files:self.reply(404,{'error':'Не найдено'});return
  file=ROOT/'static'/files[path];self.reply(200,file.read_bytes(),(mimetypes.guess_type(file)[0] or 'text/plain')+'; charset=utf-8')
 def do_POST(self):
  try:
   # Browsers cannot issue authenticated cross-origin requests: no CORS; JSON only; origin checked.
   origin=self.headers.get('Origin')
   if origin and origin.split('://',1)[-1]!=self.headers.get('Host'):raise Bad('Недопустимый источник запроса')
   if self.headers.get_content_type()!='application/json':raise Bad('Ожидается JSON')
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=16384:raise Bad('Недопустимый размер запроса')
   a=json.loads(self.rfile.read(size));assert isinstance(a,dict),'Ожидается объект'
   with LOCK:
    now=time.time();ip=self.client_address[0];bucket=LIMIT[ip]
    while bucket and bucket[0]<now-60:bucket.popleft()
    if len(bucket)>=1800:raise Bad('Слишком много запросов. Подождите минуту.')
    bucket.append(now)
    if self.path in ('/api/create','/api/join'):
     b=LIMIT[ip+'join']
     while b and b[0]<now-60:b.popleft()
     if len(b)>=60:raise Bad('Слишком много входов. Подождите минуту.')
     b.append(now)
    DB.execute('DELETE FROM rooms WHERE updated<?',(now-TTL,));DB.commit()
    result=process(self.path,a,self.headers.get('Authorization','').removeprefix('Bearer '))
   self.reply(200,result)
  except (Bad,AssertionError,ValueError,TypeError,KeyError) as e:self.reply(400,{'error':str(e) or 'Недопустимое действие'})
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception:
   import traceback;traceback.print_exc();self.reply(500,{'error':'Ошибка сервера. Состояние хода не сохранено.'})
if __name__=='__main__':
 server=ThreadingHTTPServer((os.getenv('HOST','127.0.0.1'),int(os.getenv('PORT','8080'))),Handler);server.daemon_threads=True
 print('Game Night listening',server.server_address,flush=True);server.serve_forever()
