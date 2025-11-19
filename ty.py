import os

import requests
from bs4 import BeautifulSoup
from lxml import etree
import json

from time import sleep
import re

tsession=requests.session()

def get_various(uid: str):
  
    head = json.loads(os.getenv("H1"))

    d = {"uid": uid}
    api_url = "http://211.83.159.5/tyexam/api/l/v6/token?"

    res = tsession.post(api_url, headers=head, data=d).text
    cgAuth = json.loads(res)["data"]

    head = json.loads(os.getenv("H2"))

    page_url = " http://211.83.159.5/tyexam/app/"

    res = tsession.get(page_url, headers=head).headers

    Cookie = json.loads(str(res).replace("'", '"'))["Set-Cookie"].split(";")[0]

    header = json.loads(os.getenv("HP"))

    header["Cookie"]=Cookie
    header["cgAuthorization"]=cgAuth

    tsession.headers.update(header)
    return Cookie, cgAuth

def write_new_paper():
    cover_url = "http://211.83.159.5/tyexam//app/redir.php?newPage=1&catalog_id=6&cmd=testing"
    event_raw = tsession.get(cover_url).text
    event_pattern = r"tikubh=[0-9]+"
    event_list = [i.replace("tikubh=", "")
                  for i in re.findall(event_pattern, event_raw)]
    # print(event_list)
    event_list.remove("524156")
    test_result=[]
    for final_tikubh in event_list:
        name=re.findall(r"tikubh=" + final_tikubh + r"\"\>(.+)\</a\>", event_raw)[-1]
        req_url = "http://211.83.159.5/tyexam//app/redir.php?newPage=1&catalog_id=6&cmd=testing&tikubh="+final_tikubh

        res = tsession.get(req_url).text
        soup = BeautifulSoup(res, "lxml")
        soup.prettify()
        try:
            search_res = soup.find_all(attrs={"name": "huihuabh"})[0]
        except IndexError:
            print(soup)
            raise Exception
        s_pattern = r"[0-9]{6}"
        huihuabh = re.findall(s_pattern, str(search_res))[0]
        test_result.append((name,huihuabh))
    return test_result

def getUrl(url: str) -> None:
    try:
        res = tsession.get(
            url).text
        return res
    except requests.exceptions.ConnectTimeout:
        print("*回应时间过长，10s后继续")
        clk = 10
        while True:
            sleep(1)
            clk -= 1
            print("\r\r", clk, end="")
            if not clk:
                print("\n")
                break


def htmlAnalys(htmlFile: str) -> dict:
    element = etree.HTML(htmlFile)
    res=element.xpath('//div[@class="shiti"]')
    ans = {"判断题":{},"单选题":{},"多选题":{}}
    for i in res:
        question=i.xpath("strong/text()")[0]
        answers=i.xpath("ul/li/text()")
        types=i.xpath("span/text()")[0].replace("[","").replace("]","")
        if answers: # 选择题
            for j in range(len(answers)):
                answers[j]=answers[j].lstrip()
            right=i.xpath("text()")
            clean_r = re.findall(r'\t\t\t\t\t\t  ([A-Z]+)\n\t\t\t\t\t', str(right[-1]))[0]
        else:   # 判断题
            right = i.xpath("text()")
            clean_r = re.findall(r'\t\t\t\t\t\t  (.{2})\t\t\t\t\t', str(right[-1]))[0]

        ans[types][question]={"content":answers, "answer": clean_r}
    return ans


def main() -> None:
    secret_id = os.getenv("ID")
    get_various(secret_id)

    repeat = 3
    for _ in range(repeat):
        new_papers=write_new_paper()
        for new_paper in new_papers:
            tkname,tkid=new_paper
            baseUrl_1 = "http://211.83.159.5/tyexam//app/redir.php?"
            baseUrl_2 = "&direction=1&tijiao=0&postflag=1&huihuabh=" + \
                tkid+"&cmd=dati&catalog_id=6&mode=test"
            ckUrl = "http://211.83.159.5/tyexam//app/redir.php?catalog_id=6&cmd=dajuan_chakan&huihuabh="+tkid+"&mode=test"
            urlDict = {}
            ansDict = {}
            for i in range(0, 10):
                ansDict[i] = []
                tempDict = {}
                for j in range(0, 5):
                    tempDict["ti_"+str(j+1+i*5)] = 0
                for k in tempDict:
                    ansDict[i].append(k+"="+str(tempDict[k]))
                urlDict["page="+str(i)] = "&".join(ansDict[i])
    
            for i in urlDict:
                resUrl = baseUrl_1+urlDict[i]+"&"+i+baseUrl_2
                getUrl(resUrl)
    
            ans = getUrl(ckUrl)
    
            if "考生信息获取失败" in ans:
                return
            if "<body>" not in ans:
                print("Authorization失效，程序退出")
                exit(0)
            else:
                print(tkid, "已成功获取!")
            res=htmlAnalys(ans)
            librec = {}
            with open(f"题库/{tkname}.json", "r", encoding="utf-8-sig") as fp:
                librec = json.loads(fp.read())
            for i in librec.keys():
                for j in res[i].keys():
                    if j in librec[i] and res[i][j] not in librec[i][j]:
                        librec[i][j].append(res[i][j])
                    if j not in librec[i]:
                        librec[i][j]=[res[i][j]]
            with open(f"题库/{tkname}.json", "w+", encoding="utf-8-sig") as fp:
                fp.write(json.dumps(librec, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
