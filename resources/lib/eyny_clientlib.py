# -*- coding: utf-8 -*-
import logging
import os
import random
import re

import requests
from bs4 import BeautifulSoup


class EynyForum(object):

    def __init__(self, user_name, password):
        self.user_name = user_name
        self.password = password
        self.base_url = random.choice(['video.eyny.com'])
        self.session = requests.Session()
        self.login()

    def __del__(self):
        self.logout()

    def _visit_and_parse(
        self, path, method='get', get_info=False, **kwargs
    ):
        if not path.startswith('http'):
            if path.startswith('/'):
                path = path[1:]
            path = 'http://' + os.path.join(self.base_url, path)
        user_agent = (
            "Mozilla/5.0 (Windows NT 5.1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/27.0.1453.116 Safari/537.36")

        header = {
            "User-Agent": user_agent,
            'Accept-Encoding': 'gzip, deflate',
            "Accept-Language":
                'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
            "Host": self.base_url
        }
        request = self.session.__getattribute__(method)(
            path, headers=header, **kwargs
        )
        html = request.text
        soup = BeautifulSoup(html, 'html5lib')
        having_info = soup.find('div', id='messagetext')
        message = having_info.p.contents[0] if having_info else None
        if not get_info and message:
            raise ValueError(message)
        if get_info:
            return request.url, message
        return request.url, soup

    def _login(self):
        if self.is_login():
            return True
        _, soup = self._visit_and_parse(
            '/member.php',
            params={
                'referer': 'http://' + self.base_url + '/index.php',
                'mod': 'logging',
                'action': 'login'
            })
        login_hash = soup.find(
            "div",
            id=re.compile(r'^main_messaqge_')
        )['id'].replace('main_messaqge_', '')
        form_hash = soup.find(
            'input',
            attrs={'type': "hidden", 'name': "formhash"}
        )['value']
        cookietime = soup.find(
            "input",
            attrs={'type': 'checkbox', 'name': 'cookietime'}
        )['value']

        post_data = {
            'formhash': form_hash,
            'referer': 'http://' + self.base_url + '/index.php',
            'loginfield': 'username',
            'username': self.user_name,
            'password': self.password,
            'questionid': 0,
            'answer': '',
            'loginsubmit': 'true',
            'cookietime': cookietime
        }
        _, soup = self._visit_and_parse(
            '/member.php',
            method='post',
            data=post_data,
            params={
                'mod': 'logging',
                'action': 'login',
                'loginsubmit': 'yes',
                'handlekey': 'login',
                'loginhash': login_hash,
                'inajax': 1
            }
        )
        return re.search(u'.*succeedhandle_login.*', str(soup)) is not None

    def login(self):
        is_login = False
        try:
            is_login = self._login()
        except ValueError as e:
            if (
                e.message.strip() ==
                u'由於你的帳號從多處登入，已經被強制登出。'
            ):
                is_login = self._login()
            if not is_login:
                raise e

    def is_login(self):
        _, soup = self._visit_and_parse('/')
        logout_button = soup.find(lambda elem: (
            elem.name == 'a'
            and re.search('action=logout', elem.attrs.get('href', ''))
        ))
        return logout_button is not None

    def logout(self):
        _, soup = self._visit_and_parse('/')
        logout_button = soup.find(lambda elem: (
            elem.name == 'a'
            and re.search('action=logout', elem.attrs.get('href', ''))
        ))
        _, message = self._visit_and_parse(
            logout_button.attrs['href'], get_info=True)
        logging.warning(message)

    def get_video_link(self, vid, size):
        current_url, soup = self._visit_and_parse(
                'watch?v={}&size={}'.format(vid, size))
        title = soup.find('title').string.replace(u'-  伊莉影片區', '').strip()

        sizes = []
        for elem in soup.find_all(lambda tag: (
            tag.name == 'a'
            and re.search(
                r'watch\?v=.*\&size=\d+',
                tag.attrs.get('href', '')))
        ):
            sizes.append(int(elem.string))
        sizes.reverse()

        video_item = soup.find('video')
        video_url = video_item.find('source').attrs['src']
        image_url = video_item.attrs['poster']
        logging.warning('VIDEO: {}'.format(video_url))
        return {
            'title': title,
            'image': image_url,
            'video': video_url,
            'current_url': current_url,
            'sizes': sizes
        }

    def parse_filters(self, soup):
        tables = soup.find('table', class_='block').find_all('tr')
        first_table = tables[0]

        def channel_parser(url):
            return re.search(r'channel/(?P<cid>[^&]+)', url).group('cid')

        main_category = first_table.find('table')
        categories = [{
            'name': element.string,
            'cid': channel_parser(element.attrs['href'])
        } for element in main_category.find_all('a')]

        if len(tables) > 3:
            sub_categories = [
                {
                    'name': elem.string,
                    'cid': channel_parser(elem.attrs['href'])
                }
                for elem in tables[2].find_all('a')
            ]
        else:
            sub_categories = []

        return {
            'categories': categories,
            'sub_categories': sub_categories,
        }

    def list_filters(self):
        _, soup = self._visit_and_parse('/')
        return self.parse_filters(soup)

    def _get_video_list(self, videos_rows):
        videos = []
        for videos_row in videos_rows:
            for element in videos_row.find_all('td'):
                if element.find('a') is None:
                    continue
                link = element.find('a').attrs['href']
                match = re.search(r'watch\?v=(?P<vid>[^&]+)', link)
                if match is None:
                    continue
                vid = match.group('vid')
                image = element.find('img').attrs['src']
                title = element.find_all('p')[0].find('a').string
                try:
                    quality = int(element.find_all('p')[2].find(
                        lambda e: (
                            e.name == 'font' and re.match(r'^\d+$', e.string)
                        )
                    ).string)
                except Exception:
                    quality = 180

                duration = element.find('a').div.div.string

                def duration_to_seconds(duration_str):
                    t = duration_str.split(':')
                    t.reverse()
                    duration = 0
                    for idx, val in enumerate(t):
                        duration += int(val) * 60 ** idx
                    return duration
                duration_in_seconds = duration_to_seconds(duration)

                videos.append({
                    'vid': vid,
                    'image': image,
                    'title': title,
                    'quality': quality,
                    'duration': duration_in_seconds
                })
        return videos

    def _parse_last_page(self, pages_row):
        pages = pages_row.find('div', class_="pg")
        if pages is None:
            return 1

        last_page = pages.find('a', class_='last')
        if last_page is not None:
            last_page = re.search(
                r'(?P<last_page>\d+)', last_page.string).group('last_page')
            if last_page is not None:
                return int(last_page)
        last_page = [
            page.string.strip('.')
            for page in reversed(list(
                pages_row.find('div', class_='pg').children))
            if page.string != u'下一頁']
        if len(last_page) > 0:
            return int(last_page[0])
        return 1

    def search_video(self, search_txt, day=None, orderby=None, cid=0, page=1):
        search_txt = re.sub(' +', '-', search_txt)
        path = '/tag/' + search_txt
        params = {
            'page': page
        }
        current_url, soup = self._visit_and_parse(path, params=params)
        logging.warning(current_url)
        video_table = soup.find_all('table', class_='block')[3]
        pages_row = video_table.find('tr')
        videos_rows = list(pages_row.find_next_siblings('tr'))[:-2]
        return {
            'videos': self._get_video_list(videos_rows),
            'current_page': page,
            'last_page': self._parse_last_page(pages_row),
            'current_url': current_url
        }

    def list_videos(self, cid=None, page=1):
        path = '/channel/' + cid + '/videos&page=' + str(page)

        current_url, soup = self._visit_and_parse(path)
        validate_form = soup.find(lambda tag: (
            tag.name == 'form'
            and tag.find('input', attrs={'value': re.compile('.*Yes.*')})
        ))
        if validate_form:
            data = dict(
                (input_.attrs['name'], input_.attrs['value'])
                for input_ in validate_form.find_all('input'))
            current_url, soup = self._visit_and_parse(
                path, method='post', data=data)
        video_table = soup.find(lambda tag: (
            tag.name == 'a'
            and re.search(r'watch\?v=', tag.attrs.get('href', '')))
        ).find_parent('table')
        pages_row = video_table.find('tr')
        videos_rows = list(pages_row.find_next_siblings('tr'))[:-1]

        videos = self._get_video_list(videos_rows)

        return {
            'category': self.parse_filters(soup),
            'videos': videos,
            'current_page': page,
            'last_page': self._parse_last_page(pages_row),
            'current_url': current_url
        }
