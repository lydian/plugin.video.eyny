# -*- coding: utf-8 -*-
import random
import re
import urlparse

import requests
from bs4 import BeautifulSoup


class EynyForum(object):

    def __init__(self, user_name, password):
        self.user_name = user_name
        self.password = password
        self.base_url = random.choice(['video.eyny.com'])
        self.session = requests.Session()
        self.is_login = False

    def _visit_and_parse(self, path, method='get', **kwargs):
        if not path.startswith('http'):
            if not path.startswith('/'):
                path = '/' + path
            path = 'http://' + self.base_url + path
        user_agent = (
            "Mozilla/5.0 (Windows NT 5.1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/27.0.1453.116 Safari/537.36")

        header = {
            "User-Agent": user_agent,
            "Host": self.base_url
        }

        html = self.session.__getattribute__(method)(
            path, headers=header, **kwargs
        ).text
        soup = BeautifulSoup(html, 'html5lib')
        having_info = soup.find('div', id='messagetext')
        if having_info:
            message = having_info.p.contents[0]
            raise ValueError(message)
        return path, soup

    def login(self):
        if self.is_login:
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
            id=re.compile('^main_messaqge_')
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
        if re.search(u'.*succeedhandle_login.*', str(soup)):
            self.is_login = True
        else:
            self.is_login = False
        return self.is_login

    def get_video_link(self, vid, size):
        if not self.is_login:
            if not self.login():
                raise ValueError('Failed to login')

        current_url, soup = self._visit_and_parse(
                '/video.php',
                params={'mod': 'video', 'vid': vid, 'size': size})
        title = soup.find('title').string.replace(u'-  伊莉影片區', '').strip()

        sizes = [
            int(elem.string)
            for elem in soup.find_all(lambda tag: (
                tag.name == 'a'
                and re.search(
                    'mod=video&vid=%s&size=\d+' % vid,
                    tag.attrs.get('href', '')))
            )
        ]
        sizes.reverse()

        js = str(soup.find(lambda tag: (
            tag.name == 'script'
            and re.search('jwplayer', str(tag)) is not None
        )))
        match = re.search(
            r"width: (?P<width>\d+),\s+"
            r"height: (?P<height>\d+),\s+"
            r"image: '(?P<image_url>.*)',\s+"
            r"file: '(?P<video_url>.*)'",
            js)
        image_url = match.group('image_url')
        video_url = match.group('video_url')
        return {
            'title': title,
            'image': image_url,
            'video': video_url,
            'current_url': current_url,
            'sizes': sizes
        }

    def parse_filters(self, soup):
        first_table = soup.find('table', class_='block').find('tr')
        second_table = first_table.find_next_sibling('tr')

        main_category = first_table.find('table')
        categories = [{
            'name': element.string,
            'cid': dict(urlparse.parse_qsl(
                urlparse.urlsplit(element.attrs['href']).query
            ))['cid']
        } for element in main_category.find_all('a')]

        if len(first_table.find_all('table')) > 1:
            sub_categories = [{
                'name': elem.string,
                'cid': dict(urlparse.parse_qsl(
                    urlparse.urlsplit(elem.attrs['href']).query
                ))['cid']
            }for elem in first_table.find_all('table')[1].find_all('a')]
        else:
            sub_categories = []

        orderbys = [{
            'name': element.string,
            'orderby': re.search(
                'mod=([^&]+)', element.attrs['href']).group(1)
            } for element in second_table.find_all('a')]
        return {
            'categories': categories,
            'sub_categories': sub_categories,
            'mod': orderbys
        }

    def list_filters(self):
        _, soup = self._visit_and_parse('/')
        return self.parse_filters(soup)

    def _get_video_list(self, videos_rows):
        videos = []
        for videos_row in videos_rows:
            for element in videos_row.find_all('td'):
                link = element.find('a').attrs['href']
                match = re.search('vid=(?P<vid>[^&]+)', link)
                if match is None:
                    continue
                vid = re.search('vid=(?P<vid>[^&]+)', link).group('vid')
                image = element.find('img').attrs['src']
                title = element.find('img').attrs['title']
                quality = int(element.find_all('p')[2].find(
                    lambda e: e.name == 'font' and re.match('^\d+$', e.string)
                ).string)

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
                '(?P<last_page>\d+)', last_page.string).group('last_page')
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
        path = '/index.php'
        params = {
            'mod': 'search',
            'cid': cid,
            'srchtxt': search_txt,
            'date': day or '',
            'orderby': orderby or '',
            'page': page
        }
        current_url, soup = self._visit_and_parse(path, params=params)
        video_table = soup.find_all('table', class_='block')[2]
        pages_row = video_table.find('tr')

        videos_rows = list(pages_row.find_next_siblings('tr'))[:-2]
        return {
            'videos': self._get_video_list(videos_rows),
            'current_page': page,
            'last_page': self._parse_last_page(pages_row),
            'current_url': current_url
        }

    def list_videos(self, cid=None, page=1, mod='channel'):
        path = '/index.php'
        params = {'page': page}
        if cid is not None:
            params['cid'] = cid
        if mod is not None:
            params['mod'] = mod

        current_url, soup = self._visit_and_parse(path, params=params)

        validate_form = soup.find(lambda tag: (
            tag.name == 'form'
            and tag.find('input', attrs={'value': re.compile('.*Yes.*')})
        ))
        if validate_form:
            data = dict(
                (input_.attrs['name'], input_.attrs['value'])
                for input_ in validate_form.find_all('input'))
            current_url, soup = self._visit_and_parse(
                path, params=params, method='post', data=data)

        video_table = soup.find_all('table', class_='block')[2]
        pages_row = video_table.find('tr')
        videos_rows = list(pages_row.find_next_siblings('tr'))[:-2]

        videos = self._get_video_list(videos_rows)

        return {
            'category': self.parse_filters(soup),
            'videos': videos,
            'current_page': page,
            'last_page': self._parse_last_page(pages_row),
            'current_url': current_url
        }
