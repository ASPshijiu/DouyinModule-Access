"""从 Gitee 提案生成签名名单并发布；私钥和令牌仅由运行环境注入。"""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://gitee.com/api/v5/repos/shijiudada/douyinmodule-access/contents/'
LISTS = ('blacklist', 'whitelist', 'administrators')
def validate(d):
    if type(d.get('schema')) is not int or d['schema'] != 1: raise ValueError('不支持的格式')
    if type(d.get('revision')) is not int or not 0 <= d['revision'] < 2**63: raise ValueError('无效版本')
    for name in LISTS:
        a=d.get(name)
        if not isinstance(a,list) or len(a)>20000: raise ValueError('无效名单')
        if any(not isinstance(x,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',x) for x in a): raise ValueError('无效标识')
        if len(a)!=len(set(a)): raise ValueError('重复标识')
    if not d['administrators']: raise ValueError('至少保留一名管理员')
    if set(d['blacklist']) & set(d['whitelist']): raise ValueError('黑白名单冲突')
    if len(json.dumps(d).encode())>1024*1024: raise ValueError('名单过大')

def canonical(d):
    return ('doux-access-v1\n'+str(d['revision'])+'\n'+'\n'.join(sorted(d['blacklist']))+
        '\n--whitelist--\n'+'\n'.join(sorted(d['whitelist']))+'\n--administrators--\n'+
        '\n'.join(sorted(d['administrators']))+'\n').encode()

def check_next(new, old):
    if new['revision']<old['revision']: raise ValueError('提案版本过旧')
    if new['revision']==old['revision'] and canonical(new)!=canonical(old): raise ValueError('相同版本内容冲突')

def api(path, token, method='GET', form=None):
    url=BASE+path
    if method=='GET':url+='?ref=master'
    body=urllib.parse.urlencode(form).encode() if form is not None else None
    req=urllib.request.Request(url,data=body,method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    try:
        # 固定主机且不携带凭据跟随重定向。
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        with urllib.request.build_opener(NoRedirect).open(req,timeout=25) as r:
            raw=r.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:raise ValueError('服务器响应过大')
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raise RuntimeError('Gitee HTTP '+str(e.code)) from None

def document(reply):
    return json.loads(base64.b64decode(reply['content'],validate=False))

def publish():
    token=os.environ['GITEE_TOKEN']
    proposal=document(api('policies/proposal.json',token));validate(proposal)
    current_reply=api('policies/access.json',token);current=document(current_reply)
    # 迁移时旧名单无管理员字段；不允许降低版本或更改相同版本的名单。
    for old in [current,json.loads(Path('policies/access.json').read_text())]:
        if 'administrators' in old:check_next(proposal,old)
        elif proposal['revision']<=old['revision']:raise ValueError('首次签名必须增加版本')
    with tempfile.TemporaryDirectory() as tmp:
        key=Path(tmp)/'key.pem';key.write_text(os.environ['POLICY_SIGNING_KEY']);key.chmod(0o600)
        sig=subprocess.run(['openssl','dgst','-sha256','-sign',str(key)],input=canonical(proposal),capture_output=True,check=True).stdout
    signed={k:proposal[k] for k in ('schema','revision',*LISTS)}
    signed['signature']=base64.b64encode(sig).decode()
    raw=json.dumps(signed,ensure_ascii=False,indent=2)+'\n'
    if signed!=current:
        api('policies/access.json',token,'PUT',dict(branch='master',sha=current_reply['sha'],
            content=base64.b64encode(raw.encode()).decode(),message='发布签名名单第'+str(signed['revision'])+'版'))
        if document(api('policies/access.json',token))!=signed:raise ValueError('Gitee写入后核对不一致')
    Path('policies/access.json').write_text(raw)
    print('已核对签名名单第'+str(signed['revision'])+'版；黑名单'+str(len(signed['blacklist']))+'，白名单'+str(len(signed['whitelist'])))

if __name__=='__main__':
    try:publish()
    except Exception as e:
        # 不输出请求、响应、环境变量或可能含凭据的异常堆栈。
        print('名单发布失败：'+(str(e) if isinstance(e,(ValueError,RuntimeError)) else type(e).__name__))
        raise SystemExit(1)
