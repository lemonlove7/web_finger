#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import os
import requests
import urllib3
urllib3.disable_warnings()
import mmh3
import base64
import argparse
import threading
import queue

def read_config():
    if lr_flag==0:
        config_file = os.path.join("web_finger.json")
        with open(config_file, 'r') as f:
            mark_list = json.load(f)
        return mark_list
    if lr_flag==1:
        mark_list = json.loads(sqljson.text)
        return mark_list


class Fofacms:

    def __init__(self, html, title,header,icon_hash):
        self.html = html.lower()
        self.title = title.lower()
        self.header=header.lower()
        self.icon_hash=icon_hash.lower()

    def get_result(self, a):
        builts = ["(body)\s*=\s*\"", "(title)\s*=\s*\"","(header)\s*=\s*\"","(icon_hash)\s*=\s*\""]
        if a is True:
            return True
        if a is False:
            return False
        for regx in builts:
            match = re.search(regx, a, re.I | re.S | re.M)
            if match:
                name = match.group(1)
                length = len(match.group(0))
                content = a[length: -1]
                if name == "body":
                    if content.lower() in self.html:
                        return True
                    else:
                        return False
                elif name == "title":
                    if content.lower() in self.title:
                        return True
                    else:
                        return False
                elif name =="header":
                    if content.lower() in self.header:
                        return True
                    else:
                        return False
                elif name =="icon_hash":
                    if content.lower() in self.icon_hash:
                        return True
                    else:
                        return False
        raise Exception("不能识别的a:" + str(a))

    def calc_express(self, expr):
        expr = self.in2post(expr)

        stack = []
        special_sign = ["||", "&&"]
        if len(expr) > 1:
            for exp in expr:
                if exp not in special_sign:
                    stack.append(exp)
                else:
                    a = self.get_result(stack.pop())
                    b = self.get_result(stack.pop())
                    c = None
                    if exp == "||":
                        c = a or b
                    elif exp == "&&":
                        c = a and b
                    stack.append(c)
            if stack:
                return stack.pop()
        else:
            return self.get_result(expr[0])

    def in2post(self, expr):

        stack = []
        post = []
        special_sign = ["&&", "||", "(", ")"]
        builts = ["body\s*=\s*\"", "title\s*=\s*\"","header\s*=\s*\"","icon_hash\s*=\s*\""]

        exprs = []
        tmp = ""
        in_quote = 0
        for z in expr:
            is_continue = False
            tmp += z
            if in_quote == 0:
                for regx in builts:
                    if re.search(regx, tmp, re.I):
                        in_quote = 1
                        is_continue = True
                        break
            elif in_quote == 1:
                if z == "\"":
                    in_quote = 2
            if is_continue:
                continue
            for i in special_sign:
                if tmp.endswith(i):

                    if i == ")" and in_quote == 2:
                        zuo = 0
                        you = 0
                        for q in exprs:
                            if q == "(":
                                zuo += 1
                            elif q == ")":
                                you += 1
                        if zuo - you < 1:
                            continue
                    length = len(i)
                    _ = tmp[0:-length]
                    if in_quote == 2 or in_quote == 0:
                        if in_quote == 2 and not _.strip().endswith("\""):
                            continue
                        if _.strip() != "":
                            exprs.append(_.strip())
                        exprs.append(i)
                        tmp = ""
                        in_quote = 0
                        break
        if tmp != "":
            exprs.append(tmp)
        if not exprs:
            return [expr]
        for z in exprs:
            if z not in special_sign:
                post.append(z)
            else:
                if z != ')' and (not stack or z == '(' or stack[-1] == '('):
                    stack.append(z)  # 运算符入栈

                elif z == ')':  # 右括号出栈
                    while True:
                        x = stack.pop()
                        if x != '(':
                            post.append(x)
                        else:
                            break

                else:  # 比较运算符优先级，看是否入栈出栈
                    while True:
                        if stack and stack[-1] != '(':
                            post.append(stack.pop())
                        else:
                            stack.append(z)
                            break
        while stack:  # 还未出栈的运算符，需要加到表达式末尾
            post.append(stack.pop())
        return post


def fingerprint(body,header,url):
    mark_list = read_config()
    # title
    m = re.search('<title>(.*?)<\/title>', body, re.I | re.M | re.S)

    title = ""
    if m:
        title = m.group(1).strip()
    icon_hash=''
    p0=re.findall(r'href="(.*?)\.ico',body)
    if len(p0)==0:
        p0=['favicon']
        reg = '^(?:[^\/]*\/){2}([^\/]*)\/.*$'
        e = url[0:url.rfind('//')]
        r = re.findall(reg, url)
        url=e+"//"+"".join(r)
    hash_url =url+ '/' + p0[0] + '.ico'
    p1=requests.get(url=hash_url,headers=headers,verify=False).content
    p2 = base64.encodebytes(p1)
    p3 = mmh3.hash(p2)
    icon_hash=str(p3)
    fofa = Fofacms(body, title,header,icon_hash)
    whatweb = ""
    for item in mark_list:
        express = item["rule"]
        name = item["name"]
        try:
            if fofa.calc_express(express):
                whatweb = f'[{name.lower()}]'
                break
        except Exception:
            print("config error express:{} name:{}".format(express, name))
    return whatweb




def main():
    while not q.empty():
        url=q.get()
        hs=url.endswith("/")
        if len(url.split('/'))-1 ==2:
            url=url+'/'
        try:
            res = requests.get(url,headers=headers,verify=False)
            restatus=f'[{res.status_code}]'
            resp=res.text
            resh=res.headers
            Server=dict(resh).get('Server','')
            if Server!='':
                Server=f'[{Server}]'
            try:
                m = re.search('<title>(.*?)<\/title>', resp, re.I | re.M | re.S)
                titles = m.group(1).strip()
                titles = f'[{titles}]'
            except:
                titles=''

            print(f'[+] \033[34m[{url}]\033[0m \033[31m{fingerprint(body=resp,header=str(resh),url=url)}\033[0m \033[33m{titles}\033[0m \033[35m{Server}\033[0m \033[32m{restatus}\033[0m')
        except:
            print(f'[-] \033[34m[{url}]\033[0m \033[36m异常\033[0m')



if __name__ == '__main__':
    q = queue.Queue()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    }

    # 菜单
    parser = argparse.ArgumentParser(description='web_finger help')
    parser.add_argument("-l", "--LocalRemote", help="l or r", default='')
    parser.add_argument("-u", "--url", help="url", default='')
    parser.add_argument("-f", "--file", help="file url", default='')
    parser.add_argument("-t","--thread",help="thread",default='')
    args = parser.parse_args()
    lr = args.LocalRemote
    lr_flag = 0
    if lr == 'r':
        sqljson_url = 'http://113.125.57.126:56745/sql.json'
        sqljson = requests.get(url=sqljson_url)
        lr_flag = 1
    uri = args.url
    if uri !='':
        q.put(uri)
        main()
    file = args.file
    th=args.thread
    if th=='':
        th=1
    if uri == '' and file == '':
        exit()
    if file != "":
        with open(file) as ff:
            pp=ff.readlines()
        for ii in pp:
            if 'http' not in ii:
                ii='http://'+ii
            ii=ii.replace('\n','')
            q.put(ii)
        thread_list = []
        for i in range(int(th)):
            t = threading.Thread(target=main)
            thread_list.append(t)
        for t in thread_list:
            t.setDaemon(True)
            t.start()
        for t in thread_list:
            t.join()
