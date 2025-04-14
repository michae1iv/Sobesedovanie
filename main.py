import sys

import requests
import json
import re
import uuid

BEARER_TOKEN = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
USERNAME = "elonmusk"  # Twitter user
# Заголовки, которые подставляет браузер при первом обращении
HEADERS = {
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
    for l in tweets_text[:10]:  # Возвращаем 10 твитов
        result += f'{l}\n'
    return result


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


if __name__ == '__main__':
    session = requests.Session()
    session.headers.update(HEADERS)
    session.proxies.update(PROXIES)
    # URL запроса
    url = f"https://x.com/{USERNAME}"

    # Выполняем запрос к странице пользователя
    response = session.get(url)
    if response.status_code == 200:
        # Далее эмулируем действия браузера и отправляем get запрос
        HEADERS["Origin"] = "https://x.com"
        HEADERS["Host"] = "abs.twimg.com"
        HEADERS["Accept"] = "*/*"
        HEADERS["Sec-Fetch-Site"] = "cross-site"
        HEADERS["Sec-Fetch-Mode"] = "cors"
        HEADERS["Sec-Fetch-Dest"] = "script"
        HEADERS["Referer"] = "https://x.com/"
        session.headers.update(HEADERS)
        url = "https://abs.twimg.com/responsive-web/client-web/main.62271a5a.js"
        response = session.get(url)
        if response.status_code == 200:  # Далее нужно вытащить хэш, который необходим для получения твитов пользователя
            match = re.search(r'queryId:"(\w*)",operationName:"UserTweets"', response.text)
            if match:
                query_id = match.group(1)
                print("queryId:", query_id)
                # Далее браузер отправляет запрос OPTIONS по url /graphql/{query_id}/TweetResultByRestId и получает куку __cf_bm, данная кука действует недолго и после каждого запроса обнуляется
                url = f"https://api.x.com/graphql/{query_id}/UserTweets?variables=%7B%22userId%22%3A%2244196397%22%2C%22count%22%3A20%2C%22includePromotedContent%22%3Atrue%2C%22withQuickPromoteEligibilityTweetFields%22%3Atrue%2C%22withVoice%22%3Atrue%7D&features=%7B%22rweb_video_screen_enabled%22%3Afalse%2C%22profile_label_improvements_pcf_label_in_post_enabled%22%3Atrue%2C%22rweb_tipjar_consumption_enabled%22%3Atrue%2C%22responsive_web_graphql_exclude_directive_enabled%22%3Atrue%2C%22verified_phone_label_enabled%22%3Afalse%2C%22creator_subscriptions_tweet_preview_api_enabled%22%3Atrue%2C%22responsive_web_graphql_timeline_navigation_enabled%22%3Atrue%2C%22responsive_web_graphql_skip_user_profile_image_extensions_enabled%22%3Afalse%2C%22premium_content_api_read_enabled%22%3Afalse%2C%22communities_web_enable_tweet_community_results_fetch%22%3Atrue%2C%22c9s_tweet_anatomy_moderator_badge_enabled%22%3Atrue%2C%22responsive_web_grok_analyze_button_fetch_trends_enabled%22%3Afalse%2C%22responsive_web_grok_analyze_post_followups_enabled%22%3Afalse%2C%22responsive_web_jetfuel_frame%22%3Afalse%2C%22responsive_web_grok_share_attachment_enabled%22%3Atrue%2C%22articles_preview_enabled%22%3Atrue%2C%22responsive_web_edit_tweet_api_enabled%22%3Atrue%2C%22graphql_is_translatable_rweb_tweet_is_translatable_enabled%22%3Atrue%2C%22view_counts_everywhere_api_enabled%22%3Atrue%2C%22longform_notetweets_consumption_enabled%22%3Atrue%2C%22responsive_web_twitter_article_tweet_consumption_enabled%22%3Atrue%2C%22tweet_awards_web_tipping_enabled%22%3Afalse%2C%22responsive_web_grok_show_grok_translated_post%22%3Afalse%2C%22responsive_web_grok_analysis_button_from_backend%22%3Afalse%2C%22creator_subscriptions_quote_tweet_preview_enabled%22%3Afalse%2C%22freedom_of_speech_not_reach_fetch_enabled%22%3Atrue%2C%22standardized_nudges_misinfo%22%3Atrue%2C%22tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled%22%3Atrue%2C%22longform_notetweets_rich_text_read_enabled%22%3Atrue%2C%22longform_notetweets_inline_media_enabled%22%3Atrue%2C%22responsive_web_grok_image_annotation_enabled%22%3Atrue%2C%22responsive_web_enhance_cards_enabled%22%3Afalse%7D&fieldToggles=%7B%22withArticlePlainText%22%3Afalse%7D"
                HEADERS["Host"] = "api.x.com"
                HEADERS["Access-Control-Request-Method"] = "GET"
                HEADERS[
                    "Access-Control-Request-Headers"] = "authorization,content-type,x-client-transaction-id,x-guest-token,x-twitter-active-user,x-twitter-client-language"
                HEADERS["Sec-Fetch-Site"] = "same-site"
                HEADERS["Sec-Fetch-Dest"] = "empty"
                session.headers.update(HEADERS)
                response = session.options(url)
                if response.status_code == 200:  # Далее нужно получить guest token
                    url = "https://api.x.com/1.1/guest/activate.json"
                    HEADERS["Authorization"] = BEARER_TOKEN
                    HEADERS["X-Client-Transaction-Id"] = generate_transaction_id()
                    HEADERS["X-Twitter-Active-User"] = "yes"
                    HEADERS["Content-Type"] = "application/x-www-form-urlencoded"
                    session.headers.update(HEADERS)

                    response = session.post(url)
                    # Устанавливаем guest_token в заголовки запроса и в cookie и генерируем новый X-Client-Transaction-Id
                    HEADERS["X-Guest-Token"] = response.json()["guest_token"]
                    HEADERS["X-Client-Transaction-Id"] = generate_transaction_id()
                    session.cookies.set('gt', response.json()["guest_token"], domain="x.com")
                    session.headers.update(HEADERS)
                    # Отправляем запрос по тому же адресу, что и браузер, без X-Client-Transaction-Id и X-Guest-Token доступ запрещен
                    url = "https://api.x.com/graphql/M3Hpkrb8pjWkEuGdLeXMOA/UserTweets?variables=%7B%22userId%22%3A%2244196397%22%2C%22count%22%3A20%2C%22includePromotedContent%22%3Atrue%2C%22withQuickPromoteEligibilityTweetFields%22%3Atrue%2C%22withVoice%22%3Atrue%7D&features=%7B%22rweb_video_screen_enabled%22%3Afalse%2C%22profile_label_improvements_pcf_label_in_post_enabled%22%3Atrue%2C%22rweb_tipjar_consumption_enabled%22%3Atrue%2C%22responsive_web_graphql_exclude_directive_enabled%22%3Atrue%2C%22verified_phone_label_enabled%22%3Afalse%2C%22creator_subscriptions_tweet_preview_api_enabled%22%3Atrue%2C%22responsive_web_graphql_timeline_navigation_enabled%22%3Atrue%2C%22responsive_web_graphql_skip_user_profile_image_extensions_enabled%22%3Afalse%2C%22premium_content_api_read_enabled%22%3Afalse%2C%22communities_web_enable_tweet_community_results_fetch%22%3Atrue%2C%22c9s_tweet_anatomy_moderator_badge_enabled%22%3Atrue%2C%22responsive_web_grok_analyze_button_fetch_trends_enabled%22%3Afalse%2C%22responsive_web_grok_analyze_post_followups_enabled%22%3Afalse%2C%22responsive_web_jetfuel_frame%22%3Afalse%2C%22responsive_web_grok_share_attachment_enabled%22%3Atrue%2C%22articles_preview_enabled%22%3Atrue%2C%22responsive_web_edit_tweet_api_enabled%22%3Atrue%2C%22graphql_is_translatable_rweb_tweet_is_translatable_enabled%22%3Atrue%2C%22view_counts_everywhere_api_enabled%22%3Atrue%2C%22longform_notetweets_consumption_enabled%22%3Atrue%2C%22responsive_web_twitter_article_tweet_consumption_enabled%22%3Atrue%2C%22tweet_awards_web_tipping_enabled%22%3Afalse%2C%22responsive_web_grok_show_grok_translated_post%22%3Afalse%2C%22responsive_web_grok_analysis_button_from_backend%22%3Afalse%2C%22creator_subscriptions_quote_tweet_preview_enabled%22%3Afalse%2C%22freedom_of_speech_not_reach_fetch_enabled%22%3Atrue%2C%22standardized_nudges_misinfo%22%3Atrue%2C%22tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled%22%3Atrue%2C%22longform_notetweets_rich_text_read_enabled%22%3Atrue%2C%22longform_notetweets_inline_media_enabled%22%3Atrue%2C%22responsive_web_grok_image_annotation_enabled%22%3Atrue%2C%22responsive_web_enhance_cards_enabled%22%3Afalse%7D&fieldToggles=%7B%22withArticlePlainText%22%3Afalse%7D"
                    response = session.get(url)
                    json_data = response.json()
                    with open('tweets.txt', 'w', encoding="utf-8") as file:
                        file.write(ret_text_from_posts(json_data))
                        file.close()
                    print("all good")
                    sys.exit()
    print("all bad")

