# -*- coding: utf-8 -*-
import random
import re
import urllib
import urlparse

import requests
from bs4 import BeautifulSoup

class EynyForum(object):

    def __init__(self, user_name, password):
        self.user_name = user_name
        self.password = password
        self.base_url = random.choice(['www72.eyny.com', 'www22.eyny.com'])
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
        return soup

    def login(self):
        if self.is_login:
            return True
        login_url = 'http://' + self.base_url + '/member.php'
        soup = self._visit_and_parse(
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
            attrs={'type':"hidden", 'name':"formhash"}
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
        soup = self._visit_and_parse(
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

    def get_video_link(self, vid):
        if not self.is_login:
            if self.login():
                raise ValueError('Failed to login')

        soup = self._visit_and_parse(
                '/video.php', params={'mod': 'video', 'vid': vid})
        title = soup.find('title').string.replace(u'-  伊莉影片區', '').strip()

        def find_js(tag):
            return (
                tag.name == 'script'
                and re.search('jwplayer', str(tag)) is not None
            )
        js = str(soup.find(find_js))
        if js is None:
            print soup
        match = re.search(
                r"width: (?P<width>\d+),\s+height: (?P<height>\d+),\s+image: '(?P<image_url>.*)',\s+file: '(?P<video_url>.*)'",
            js)
        image_url = match.group('image_url')
        video_url = match.group('video_url')
        return {
            'title': title,
            'image': image_url,
            'video': video_url,
        }

    def list_filters(self):
        soup = self._visit_and_parse('/video.php')
        def find_target(tag):
            return (
                tag.name == 'a'
                and tag.attrs.get('href', None) == 'video.php'
                and tag.string == u'伊莉影片區'
            )
        first_table = (soup
            .find(find_target)
            .find_parent('table')
            .find_next_sibling('table')
        )
        second_table = first_table.find_next_sibling('table')
        categories = [{
            'name': element.string,
            'cid': dict(urlparse.parse_qsl(
                urlparse.urlsplit(element.attrs['href']).query
            ))['cid']
        } for element in first_table.find_all('a')]

        orderbys = [{
            'name': element.string,
            'orderby': re.search(
                'orderby=([^&]+)', element.attrs['href']).group(1)
            } for element in second_table.find_all('a')]
        return {'categories': categories, 'orderbys': orderbys}

    def list_videos(self, cid=None, page=1, orderby=None):
        path = '/video.php'
        params = {'mod': 'channel', 'page': page}
        if cid is not None:
            params['cid'] = cid
        if orderby is not None:
            params['orderby'] = orderby

        soup = self._visit_and_parse(path, params=params)
        pages = soup.find('div', class_="pg")
        if pages is None:
            last_page = 1
        else:
            last_page = int(re.search(
                '(?P<last_page>\d+)', pages.find('a', class_="last").string
            ).group('last_page'))

        def parse_vid(path):
            return re.search('vid=(?P<vid>[^&]+)', path).group('vid')
        videos = [
            {
                'vid': parse_vid(element.find('a').attrs['href']),
                'image': element.find('img').attrs['src'],
                'title': element.find('img').attrs['title']
            } for element in pages.find_next('table').find_all('td')
        ]
        return {'videos': videos, 'current_page': page, 'last_page': last_page}
