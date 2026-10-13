"""备用管理入口；隐藏输入UID和令牌，上传Gitee提案，服务器签名后发布。"""
import argparse
import base64
import getpass
import hashlib
import json
import re
import publisher

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('list',choices=['black','white','admin'])
    parser.add_argument('action',choices=['add','remove'])
    args=parser.parse_args()
    uid=getpass.getpass('输入抖音UID（隐藏输入）: ')
    if not re.fullmatch(r'[1-9][0-9]{0,29}',uid):parser.error('UID格式不正确')
    token=getpass.getpass('输入Gitee仓库授权令牌（隐藏输入）: ')
    remote=publisher.api('policies/proposal.json',token);data=publisher.document(remote);publisher.validate(data)
    key='sha256:'+hashlib.sha256(uid.encode()).hexdigest()
    name='administrators' if args.list=='admin' else args.list+'list'
    old=json.dumps(data,sort_keys=True)
    values=set(data[name])
    if args.action=='add':
        values.add(key)
        if args.list in ('black','white'):
            other='whitelist' if args.list=='black' else 'blacklist'
            data[other]=sorted(set(data[other])-{key})
    else:values.discard(key)
    data[name]=sorted(values)
    if json.dumps(data,sort_keys=True)==old:
        print('名单未变化');return
    data['revision']+=1;publisher.validate(data)
    publisher.api('policies/proposal.json',token,'PUT',dict(branch='master',sha=remote['sha'],content=base64.b64encode(json.dumps(data).encode()).decode(),message='更新名单提案第'+str(data['revision'])+'版'))
    print('提案已上传，等待自动签名发布。')
if __name__=='__main__':main()
