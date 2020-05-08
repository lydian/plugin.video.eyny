# -*- coding: utf-8 -*-
import os
import random

import pytest

from resources.lib.eyny_clientlib import EynyForum


@pytest.mark.skipif(
    os.environ.get('EYNY_STRING', None) is None,
    reason="requires setting EYNY_STRING in environment variable")
class TestEynyForum(object):

    @pytest.fixture(scope='session')
    def forum(self):
        user_name, password = os.environ['EYNY_STRING'].split(':')
        forum = EynyForum(user_name, password)
        return forum

    def _verify_valid_output(self, result, expected_page=1):
        assert len(result['items']) > 0
        assert isinstance(result['last_page'], int)
        assert result['current_page'] == expected_page
        assert all(
            col in item
            for item in result['items']
            for col in ['id', 'image', 'title', 'quality', 'duration']
        )

    def test_login(self, forum):
        assert forum.is_login()

    def test_list_filters(Self, forum):
        result = forum.list_filters()
        assert len(result['categories']) > 0
        categories = [cat['name'] for cat in result['categories']]
        assert u"其他" in categories

    @pytest.mark.parametrize('search_string', (
        'test', u'三國'
    ))
    def test_search_video(self, forum, search_string):
        result = forum.search_video(search_string)
        self._verify_valid_output(result)

    # 生活 飲食
    @pytest.fixture(params=['UCVoegm3b0-', 'UClwzxVEep8'])
    def cid(self, request):
        return request.param

    # @pytest.fixture(params=['channel', 'index'])
    # def mod(self, request):
    #    return request.param

    @pytest.fixture(params=[1, 2])
    def page(self, request):
        return request.param

    def test_list_videos(self, forum, cid, page):
        result = forum.list_videos(cid=cid, page=page)
        self._verify_valid_output(result, page)

    @pytest.fixture
    def vid(self, cid, forum):
        videos = filter(
            lambda video: video.get('quality') >= 360,
            forum.list_videos(cid, None)['items']
        )
        return random.choice(videos)['id']

    def test_get_video_link(self, forum, vid):
        result = forum.get_video_link(vid, 360)
        assert result['video'].startswith('http')

    @pytest.fixture(params=[
        {'type':'user','query':'yahoo','page':1,'pl':False},
        {'type':'user','query':'yahoo','page':2,'pl':False},
        {'type':'user','query':'yahoo','page':1,'pl':True},
        {'type':'channel','query':'UC_zEqrZt9z','page':1,'pl':False},
        {'type':'user','query':'NotExisted','page':1,'pl':False}])
    def user_channel(self, request):
        return request.param

    def test_search_user_channel(self, forum, user_channel):
        result = forum.search_user_channel(
            search_type=user_channel['type'],
            search_txt=user_channel['query'],
            page=user_channel['page'],
            playlist=user_channel['pl'])
        if user_channel['query'] == 'NotExisted':
            assert not result
            return
        assert len(result['items']) > 0
        if user_channel['pl']:
            assert result['items'][0]['type'] == 'playlist'
            assert result['items'][0]['id']
            assert not result['items'][0]['quality']
            assert not result['items'][0]['duration']
        else:
            assert result['items'][0]['type'] == 'video'
            assert result['has_playlist']

    @pytest.fixture(params=['PLqUwhbz8PM', 'PLgTiVmIsDF'])
    def pid(self, request):
        return request.param

    def test_list_videos_in_playlist(self, forum, pid):
        result = forum.list_videos_in_playlist(pid)
        assert len(result['items']) > 0
        assert result['items'][0]['type'] == 'video'
        assert result['items'][0]['id']
        assert result['items'][0]['image'].startswith('http')
        assert result['items'][0]['title']
        assert result['items'][0]['quality'] > 100
        assert result['items'][0]['duration'] > 0
