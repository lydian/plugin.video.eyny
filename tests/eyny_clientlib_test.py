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
        assert len(result['videos']) > 0
        assert isinstance(result['last_page'], int)
        assert result['current_page'] == expected_page
        assert all(
            col in video
            for video in result['videos']
            for col in ['vid', 'image', 'title', 'quality', 'duration']
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

    @pytest.fixture(params=[6, 3])
    def cid(self, request):
        return request.param

    @pytest.fixture(params=['channel', 'index'])
    def mod(self, request):
        return request.param

    @pytest.fixture(params=[1, 2])
    def page(self, request):
        return request.param

    def test_list_videos(self, forum, cid, mod, page):
        result = forum.list_videos(cid=cid, page=page, mod=mod)
        self._verify_valid_output(result, page)

    @pytest.fixture
    def vid(self, forum):
        cid = 69
        videos = filter(
            lambda video: video.get('quality') >= 360,
            forum.list_videos(cid, 'index', None)['videos']
        )
        return random.choice(videos)['vid']

    def test_get_video_link(self, forum, vid):
        result = forum.get_video_link(vid, 360)
        assert result['video'].startswith('http')
