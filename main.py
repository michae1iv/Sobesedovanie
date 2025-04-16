import sys
import requests
import json
import urllib.parse
import re
import uuid


'''
Коротко:
1. Обращаемся по адресу url = f"https://x.com/elonmusk" - так бы сделал реальный пользователь, аутентифицироваться не будем
2. Далее начинается динамическая подгрузка страницы с кучей ссылок, упростим задачу и обратимся только к https://abs.twimg.com/responsive-web/client-web/main.62271a5a.js - 
    отсюда вытаскиваем хэш, по которому будем вытаскивать твиты, например: Vg2Akr5FzUmF0sTplA5k6g
3. Находим строку типа: queryId:"Vg2Akr5FzUmF0sTplA5k6g",operationName:"UserTweets" - ищем подобную строку и через регулярку вытаскиваем queryId
4. Затем надо сделать запрос options по адресу /graphql/Vg2Akr5FzUmF0sTplA5k6g/TweetResultByRestId, и получить оттуда куку __cf_bm
5. Затем нужно получить guest_token обратясь по адресу api.x.com/1.1/guest/activate.json
6. Установить токен в заголовок и Cookie 
7. Обратиться к /graphql/M3Hpkrb8pjWkEuGdLeXMOA/UserTweets и вытащить оттуда твиты
8. Парсинг твитов и сохранение в файл
'''

AMOUNT_OF_POSTS = 10
RESULT_FILENAME = 'tweets.txt'
USERNAME = "elonmusk"  # Twitter user
HEADERS = { # Заголовки, которые подставляет браузер при первом обращении
    "Host": "x.com",
    "referer": "https://yandex.ru/",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": "\"Not A(Brand\";v=\"8\", \"Chromium\";v=\"132\", \"Opera GX\";v=\"117\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "Windows",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Accept-Encoding": "gzip, deflate, br",
    "Priority": "u=1, i",
    "Connection": "keep-alive",
}
PROXIES = {
    "http": "104.16.104.68", #Менять прокси здесь
}


def generate_transaction_id() -> str:  # Функция, которая генерирует случайный X-Client-Transaction-Id, т.к делаем действия, которые похожи на действия пользователя, то каждый раз, новый заголовок
    raw_id = f"{uuid.uuid4()}"
    return raw_id


def ret_text_from_posts(json_resp: json): #Тут получаем на вход json, вытаскиваем по ключам твиты, берем первые 10 твитов и преобразуем в строку
    result = ''
    tweets_text = []
    instructions = json_resp.get("data", {}).get("user", {}).get("result", {}) \
        .get("timeline", {}).get("timeline", {}).get("instructions", [])

    for instruction in instructions:
        entries = []
        if "addEntries" in instruction:
            entries = instruction["addEntries"].get("entries", [])
        elif "entries" in instruction:
            entries = instruction["entries"]

        for entry in entries:
            try:
                tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
                full_text = tweet["legacy"]["full_text"]
                if "https://t.co" not in full_text:
                    tweets_text.append(full_text)
            except (KeyError, TypeError):
                continue
    for l in tweets_text[:AMOUNT_OF_POSTS]:  # Возвращаем 10 твитов
        result += f'{l}\n'
    return result


# Декоратор для проверки статус-кода ответа
def successful_request(func):
    def wrapper(*args, **kwargs) -> (requests.Response, requests.Session):
        resp, sess = func(*args, **kwargs)
        if resp.status_code == 200:
            return sess, resp
        else:
            print(f'Request unsuccessful, status code: {resp.status_code}\n'
                  f'url: {kwargs['req_url']}')
            sys.exit()
    return wrapper


'''
Далее описана логика запросов в виде функций
'''
# Первый запрос на страницу
@successful_request
def simple_get_req(req_session, req_url) -> (requests.Response, requests.Session):
    req_response = req_session.get(req_url)
    return req_response, req_session


# Отправляем запрос на main.js чтобы получить хэш, который необходим для получения твитов пользователя
@successful_request
def parsing_req(req_session, req_url) -> (requests.Response, requests.Session):
    # Обновляем заголовки
    session.headers["Origin"] = "https://x.com"
    session.headers["Host"] = "abs.twimg.com"
    session.headers["Accept"] = "*/*"
    session.headers["Sec-Fetch-Site"] = "cross-site"
    session.headers["Sec-Fetch-Mode"] = "cors"
    session.headers["Sec-Fetch-Dest"] = "script"
    session.headers["Referer"] = "https://x.com/"
    # Делаем get запрос
    req_response = req_session.get(req_url)
    return req_response, req_session


# Запрос options для получения cookie __Cf_bm
@successful_request
def get_cf_bm(req_session, req_url, auth_token) -> (requests.Response, requests.Session):
    # Обновляем заголовки
    session.headers["Host"] = "api.x.com"
    session.headers["Access-Control-Request-Method"] = "GET"
    session.headers[
        "Access-Control-Request-Headers"] = "authorization,content-type,x-client-transaction-id,x-guest-token,x-twitter-active-user,x-twitter-client-language"
    session.headers["Sec-Fetch-Site"] = "same-site"
    session.headers["Sec-Fetch-Dest"] = "empty"
    session.headers["Authorization"] = auth_token
    # Делаем get запрос
    req_response = req_session.options(req_url)
    return req_response, req_session

# Активируем гостя для получения guest token
@successful_request
def activate_guest(req_session, req_url) -> (requests.Response, requests.Session):
    # Обновляем заголовки
    session.headers["X-Client-Transaction-Id"] = generate_transaction_id()
    session.headers["X-Twitter-Active-User"] = "yes"
    session.headers["Content-Type"] = "application/x-www-form-urlencoded"
    # Делаем get запрос
    req_response = req_session.post(req_url)
    return req_response, req_session

@successful_request
def get_tweets(req_session, req_url, gt_resp) -> (requests.Response, requests.Session):
    # Устанавливаем guest_token в заголовки запроса и в cookie и генерируем новый X-Client-Transaction-Id
    session.headers["X-Guest-Token"] = gt_resp.json()["guest_token"]
    session.headers["X-Client-Transaction-Id"] = generate_transaction_id()
    session.cookies.set('gt', gt_resp.json()["guest_token"], domain="x.com")
    # Делаем get запрос
    req_response = req_session.get(req_url)
    return req_response, req_session


# Формируем url для получения твитов
def forming_url(qid) -> str:
    variables = {
        "userId": "44196397",
        "count": 20,
        "includePromotedContent": True,
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True
    }
    features = {
        "rweb_video_screen_enabled": False,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": False,
        "responsive_web_jetfuel_frame": False,
        "responsive_web_grok_share_attachment_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_grok_image_annotation_enabled": True,
        "responsive_web_enhance_cards_enabled": False
    }
    field_toggles = {
        "withArticlePlainText": False
    }
    url_str = (
        f"https://api.x.com/graphql/{qid}/UserTweets"
        f"?variables={urllib.parse.quote(json.dumps(variables))}"
        f"&features={urllib.parse.quote(json.dumps(features))}"
        f"&fieldToggles={urllib.parse.quote(json.dumps(field_toggles))}"
    )
    return url_str


# Функция, которая через регулярки парсит query_id для запосов и Authorisation токен
def reg_search(qid_resp, auth_resp) -> (str, str):
    query_id = ''
    auth_tok = ''
    # Парсим query_id
    qid_match = re.search(r'queryId:"(\w*)",operationName:"UserTweets"', qid_resp.text)
    if qid_match:
        query_id = qid_match.group(1)
    else:
        print("Error in parsing query_id")
        sys.exit()
    # Парсим Authorisation token
    auth_match = re.search(r'Z=e=>e\?"(.*?)":"(.*?)"', auth_resp.text)
    if auth_match:
        auth_tok = auth_match.group(2)
    else:
        print("Error in parsing auth_match")
        sys.exit()
    return query_id, auth_tok


if __name__ == '__main__':
    # Инициализируем Сессию
    session = requests.Session()
    session.headers.update(HEADERS)
    session.proxies.update(PROXIES)

    session, _ = simple_get_req(req_session=session, req_url=f"https://x.com/{USERNAME}") # Выполняем запрос к странице пользователя Elon Musk
    session, qid_response = parsing_req(req_session=session, req_url="https://abs.twimg.com/responsive-web/client-web/main.62271a5a.js") # Запрос к main.62271a5a.js для получения query id
    session, auth_response = simple_get_req(req_session=session, req_url="https://abs.twimg.com/responsive-web/client-web/main.fc80254a.js") # Запрос к main.fc80254a.js для получения Authorisation token
    query_id, auth = reg_search(qid_resp=qid_response, auth_resp=auth_response) # Парсим Authorisation и query_id

    url = forming_url(query_id) # Формируем длинную url, параметры задаются словарем
    session, _ = get_cf_bm(req_url=url, req_session=session, auth_token=auth) # получаем куку __cf_bm
    session, gt_response = activate_guest(req_session=session, req_url="https://api.x.com/1.1/guest/activate.json") # Активируем гостя для получения guest token

    session, response = get_tweets(req_session=session, req_url=url, gt_resp=gt_response)
    json_data = response.json()
    with open(RESULT_FILENAME, 'w', encoding="utf-8") as file:
        file.write(ret_text_from_posts(json_data))
        file.close()
    print(f"Твиты Илона Маска успешно сохранены в файл {RESULT_FILENAME}")
    sys.exit()

