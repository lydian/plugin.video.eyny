# -*- coding: utf-8 -*-
import os
import random

import pytest

from resources.lib.eyny_clientlib import EynyForum


class TestEynyForum(object):

    @pytest.fixture
    def forum(self):
        return EynyForum('user', 'test_password')

    def _verify_valid_output(self, result, expected_page=1):
        assert len(result['videos']) > 0
        assert isinstance(result['last_page'], int)
        assert result['current_page'] == expected_page
        assert all(
            col in video
            for video in result['videos']
            for col in ['vid', 'image', 'title', 'quality', 'duration']
        )

    @pytest.mark.skipif(
        os.environ.get('EYNY_STRING', None) is None,
        reason="requires setting EYNY_STRING in environment variable")
    def test_login(self):
        user_name, password = os.environ['EYNY_STRING'].split(':')
        forum = EynyForum(user_name, password)
        assert not forum.is_login
        assert forum.login()
        assert forum.is_login

    def test_list_filters(Self, forum):
        result = forum.list_filters()
        assert len(result['categories']) > 0
        assert u'電影' in [cat['name'] for cat in result['categories']]
        assert len(result['mod']) > 0

    @pytest.mark.parametrize('search_string', (
        'test', u'三國'
    ))
    def test_search_video(self, forum, search_string):
        result = forum.search_video(search_string)
        self._verify_valid_output(result)

    @pytest.fixture(params=[20, 55, 3])
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
    def vid(self, forum, cid, mod, page):
        videos = forum.list_videos(cid, mod, page)
        return random.choice(videos['videos'])['vid']

    @pytest.mark.skipif(
        os.environ.get('EYNY_STRING', None) is None,
        reason="requires setting EYNY_STRING in environment variable")
    def test_get_video_link(self, forum, vid):
        user_name, password = os.environ['EYNY_STRING'].split(':')
        forum = EynyForum(user_name, password)
        result = forum.get_video_link(vid, None)
        assert result['video'].startswith('http')
