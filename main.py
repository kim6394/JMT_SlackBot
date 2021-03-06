# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
import requests

from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, jsonify, make_response, render_template

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

slack_token = "xoxb-503818135714-507351131587-qX7wlR86NdZy8vGiERZB7MkJ"
slack_client_id = "503818135714.507284889508"
slack_client_secret = "5629395b663813a6bc8156667fcdb94b"
slack_verification = "XghV8wu7By7jQRBIHzHlmt1b"
sc = SlackClient(slack_token)

def get_answer(text, user_key):
    data_send = {
        'query': text,
        'sessionId': user_key,
        'lang': 'ko',
    }

    data_header = {
        'Authorization': 'Bearer 163eb1c7b8a3498bb5ba69775bf71e43',
        'Content-Type': 'application/json; charset=utf-8'
    }

    dialogflow_url = 'https://api.dialogflow.com/v1/query?v=20150910'
    res = requests.post(dialogflow_url, data=json.dumps(data_send), headers=data_header)

    if res.status_code != requests.codes.ok:
        return '오류가 발생했습니다.'

    data_receive = res.json()
    result = {
        "speech" : data_receive['result']['fulfillment']['speech']
        #"intent" : data_receive['result']['metadata']['intentName']
    }
    print(result)
    return result

# 크롤링 함수 구현하기
def _crawl_naver_keywords(text):
    # 여기에 함수를 구현해봅시다.

    url = "https://www.tripadvisor.co.kr/Restaurants-"

    location = {
        '서울': "g294197-Seoul.html",
        '부산': "g297884-Busan.html",
        '제주': "g297885-Jeju_Jeju_Island.html",
        '대전': "g297887-Daejeon.html",
        '전주': "g1143545-Jeonju_Jeollabuk_do.html"
    }
    name = []
    cuisines = []
    keywords = []
    # 여기에 함수를 구현해봅시다.
    print(len(text))
    if len(text) == 2:
        if text in location.keys():
            keywords = ["[★" + text + " 맛집 TOP 10★]"]
            url += location[text]
            urlList = []
            sourcecode = urllib.request.urlopen(url).read()
            soup = BeautifulSoup(sourcecode, "html.parser")

            for name_text in soup.find_all("a", class_="property_title"):
                name.append(name_text.get_text().strip('\n'))

            for finance_title in soup.find_all("div", class_="cuisines"):
                cuisines.append(
                    finance_title.get_text().replace('₩', '').replace(' ', '').replace('-', '').strip('\n').split('\n'))

            for link in soup.findAll("a"):
                if 'href' in link.attrs:
                    if 'class' in link.attrs:
                        for c in link.attrs['class']:
                            if c == 'property_title':
                                urlLank = "https://www.tripadvisor.co.kr"
                                urlLank += link.attrs['href']
                                urlList.append(urlLank)
            for i in range(10):
                print(len(cuisines[i]))
                if len(cuisines[i]) == 0:
                    keywords.append(str(i + 1) + "위 : " + name[i]  +"\n" + urlList[i])
                elif len(cuisines[i]) == 1:
                    keywords.append(str(i + 1) + "위 : " + name[i] + " (#" + cuisines[i][0]+ ")\n" + urlList[i])
                else :
                    keywords.append(str(i + 1) + "위 : " + name[i] + " (#" + cuisines[i][0] + ", #" + cuisines[i][1] + ")\n"+urlList[i])

        keywords = keywords[:11]

    else:
        keywords.append("모르는 정보가 들어왔어요")
    # 한글 지원을 위해 앞에 unicode u를 붙혀준다.
    return u'\n'.join(keywords)

# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):
    print(slack_event["event"])

    if event_type == "app_mention":
        channel = slack_event["event"]["channel"]
        text = slack_event["event"]["text"]

        get_data = get_answer(text, 'session')['speech']

        keywords = _crawl_naver_keywords(get_data)
        print(keywords)

        sc.api_call(
            "chat.postMessage",
            channel=channel,
            text=keywords
        )

        return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/listening", methods=["GET", "POST"])

def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)