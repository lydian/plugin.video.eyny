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
        having_info = soup.find('div', id='messagetext')
        if having_info:
            message = having_info.p.contents[0]
            raise ValueError(message)
        return path, soup

    def login(self):
        if self.is_login:
            return True
        login_url = 'http://' + self.base_url + '/member.php'
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
                    tag.attrs.get('href', ''))
        ))]
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

    def list_filters(self):
        _, soup = self._visit_and_parse('/video.php')
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

        pages = soup.find('div', class_="pg")
        if pages is None:
            last_page = 1
        else:
            last_page = int(re.search(
                '(?P<last_page>\d+)', pages.find('a', class_="last").string
            ).group('last_page'))

        def parse_vid(path):
            return

        videos = []
        for element in pages.find_next('table').find_all('td'):
            link = element.find('a').attrs['href']
            vid = re.search('vid=(?P<vid>[^&]+)', link).group('vid')
            image = element.find('img').attrs['src']
            title = element.find('img').attrs['title']
            info = element.find('p', class_='channel-video-title').find_next(
                lambda tag: tag.name == 'p' and len(tag.contents) > 0
            ).font
            quality = int(info.find_all('font')[1].string)
            duration = info.find_all('font')[2].string
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
        return {
            'videos': videos,
            'current_page': page,
            'last_page': last_page,
            'current_url': current_url
        }

if __name__ == '__main__':
    import os
    eyny = EynyForum(*os.environ['EYNY_STRING'].split(':'))
    print eyny.get_video_link(1350930, 1080)
