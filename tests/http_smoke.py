"""Isolated real HTTP integration test, including a server restart. No production data."""
import subprocess,sys,tempfile,os,time,json,urllib.request,urllib.error,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory() as data:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  env={**os.environ,'HOST':'127.0.0.1','PORT':str(port),'DATA_DIR':data};base=f'http://127.0.0.1:{port}'
  def launch():
   command=[sys.executable,str(ROOT/'start_lan.py'),'--port',str(port)] if '--lan' in sys.argv else [sys.executable,str(ROOT/'server.py')]
   proc=subprocess.Popen(command,env=env,stdout=subprocess.DEVNULL)
   for _ in range(100):
    try:
     with urllib.request.urlopen(base+'/health',timeout=1) as r:assert json.load(r)['ok'];return proc
    except OSError:time.sleep(.05)
   proc.terminate();raise RuntimeError('Server did not start')
  def request(path,a,token='',expected=200):
   req=urllib.request.Request(base+'/api/'+path,json.dumps(a).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
   try:
    with urllib.request.urlopen(req,timeout=3) as r:status=r.status;body=json.load(r)
   except urllib.error.HTTPError as e:status=e.code;body=json.load(e)
   assert status==expected,(status,body);return body
  proc=launch()
  try:
   for path in ('/','/app.js','/style.css','/rules','/images/ninja.png','/images/hitler.png'):
    with urllib.request.urlopen(base+path) as r:assert r.status==200 and len(r.read())>100
   v=request('create',{'name':'Первый','game':'hitler'});code=v['room']['code'];token=v['token'];users=[v]
   for k in range(4):users.append(request('join',{'code':code,'name':'Игрок '+str(k)}))
   v=request('state',{'code':code},token)
   v=request('start',{'code':code,'version':v['room']['version']},token)
   request('state',{'code':code},'invalid',400)
   me={u['room']['me']:u['token'] for u in users}
   st=v['room']['state'];pres=st['pres'];target=st['eligible'][0]
   v=request('action',{'code':code,'version':v['room']['version'],'turn':v['room']['turn'],'target':target},me[pres])
   for i,tok in me.items():v=request('action',{'code':code,'version':v['room']['version'],'turn':v['room']['turn'],'yes':True},tok)
   selfview=request('state',{'code':code},me[pres])['room'];assert len(selfview['state']['hand'])==3
   for i,tok in me.items():
    other=request('state',{'code':code},tok)['room']['state'];assert 'deck' not in other and 'roles' not in other
    if i!=pres:assert other['hand']==[]
   version=selfview['version'];turn=selfview['turn'];v=request('action',{'code':code,'version':version,'turn':turn,'index':0},me[pres]);request('action',{'code':code,'version':version,'turn':turn,'index':0},me[pres],400)
   before=request('state',{'code':code},me[target])['room'];assert len(before['state']['hand'])==2
   proc.terminate();proc.wait(timeout=5);proc=launch()
   after=request('state',{'code':code},me[target])['room'];assert before['version']==after['version'] and before['state']==after['state']
   request('action',{'code':code,'version':after['version'],'turn':after['turn'],'index':0},me[target])
   print('HTTP OK: assets, 5 clients, auth, votes, hidden cards, stale action rejection, restart recovery.')
  finally:proc.terminate();proc.wait(timeout=5)
if __name__=='__main__':main()
