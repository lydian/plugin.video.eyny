# -*- coding: utf-8 -*-
import codecs
import json
import logging
import os
import sys
import urlparse
import urllib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib.eyny_clientlib import EynyForum


class EynyGui(object):

    def __init__(self, base_url, addon_handle):
        addon = xbmcaddon.Addon()
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.eyny = EynyForum(
            addon.getSetting('username'), addon.getSetting('password'))
        self.is_login = self.eyny.login()
        self.search_history_file = os.path.join(
            xbmc.translatePath(addon.getAddonInfo('profile')),
            'search_history.json')

    def handle(self, args):
        mode = args.get('mode', None)
        if mode is None:
            self.main()
        if mode == 'list':
            self.list_video(
                cid=args.get('cid', None),
                page=int(args.get('page', 1)),
                orderby=args.get('orderby')
            )
        if mode == 'video':
            self.play_video(args['vid'])

        if mode == 'search':
            self.search_video(
                new_search=args.get('new_search', False),
                search_string=args.get('search_string'),
                page=int(args.get('page', 1)))

    def _build_url(self, mode, **kwargs):
        query = kwargs
        query['mode'] = mode
        return self.base_url + '?' + urllib.urlencode(query)

    def build_request_url(self, url, referer):
        USER_AGENT = (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) '
                'AppleWebKit/601.7.8 (KHTML, like Gecko) '
                'Version/9.1.3 Safari/601.7.8')
        added_header = url + '|' + urllib.urlencode({
            'User-Agent': USER_AGENT,
            'Referer': referer})
        return added_header

    def main(self):
        filters = self.eyny.list_filters()
        xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('search'),
                listitem=xbmcgui.ListItem('Search'),
                isFolder=True)

        for category in filters['categories']:
            li = xbmcgui.ListItem(category['name'])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('list', cid=category['cid']),
                listitem=li,
                isFolder=True)
        for orderby in filters['mod']:
            li = xbmcgui.ListItem(orderby['name'])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('list', orderby=orderby['orderby']),
                listitem=li,
                isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    def _add_page_item(self, page, last_page, url_mode, **url_kwargs):
        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle,
            url=self._build_url(url_mode, page=page, **url_kwargs),
            listitem=xbmcgui.ListItem(
                '~~ Go to Page {}/{} ~~'.format(page, last_page)),
            isFolder=True)

    def _add_video_items(self, videos, current_url):
        for video in videos:
            li = xbmcgui.ListItem(label=video['title'])
            li.setProperty('IsPlayable', 'true')
            image_url = self.build_request_url(
                video['image'], current_url)
            li.setArt({
                'fanart': image_url,
                'icon': image_url,
                'thumb': image_url
            })
            li.addStreamInfo('video', {
                'width': video['quality'],
                'aspect': 1.78,
                'duration': video['duration']
            })
            li.setInfo('video', {'size': video['quality']})
            li.setProperty('VideoResolution', str(video['quality']))
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('video', vid=video['vid']),
                listitem=li,
                isFolder=False)

    def list_video(self, cid=None, page=1, orderby='channel'):
        try:
            result = self.eyny.list_videos(cid=cid, page=page, mod=orderby)
        except ValueError as e:
            xbmcgui.Dialog().ok(
                heading='Error',
                line1=unicode(e).encode('utf-8'))
            return

        self._add_video_items(result['videos'], result['current_url'])
        if page < int(result['last_page']):
            self._add_page_item(
                page+1,
                result['last_page'],
                'list', orderby=orderby, cid=cid)
        xbmcplugin.endOfDirectory(self.addon_handle)

    def update_search_history(self, search_string):
        search_list = self.get_search_history()
        search_string = search_string.decode('utf-8')
        if search_string in search_list:
            search_list.remove(search_string)
        search_list = [search_string] + search_list
        with codecs.open(
            self.search_history_file, 'w', encoding='utf-8'
        ) as fp:
            json.dump(search_list[:20], fp)

    def get_search_history(self):
        if os.path.exists(self.search_history_file):
            with codecs.open(
                self.search_history_file, 'r', encoding='utf-8-sig'
            ) as fp:
                search_list = json.load(fp)
        else:
            search_list = []
        return search_list

    def search_video(self, new_search=False, search_string=None, page=1):
        if new_search:
            search_string = xbmcgui.Dialog().input(
                'Search term',
                type=xbmcgui.INPUT_ALPHANUM).strip()

        if search_string is None:
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('search', new_search=True),
                listitem=xbmcgui.ListItem("New Search"),
                isFolder=True)

            for search_string in self.get_search_history():
                xbmcplugin.addDirectoryItem(
                    handle=self.addon_handle,
                    url=self._build_url(
                        'search',
                        search_string=search_string.encode('utf-8')),
                    listitem=xbmcgui.ListItem(search_string),
                    isFolder=True)
            return xbmcplugin.endOfDirectory(self.addon_handle)

        result = self.eyny.search_video(search_string, page=page)
        if len(result['videos']) > 0:
            self.update_search_history(search_string)

        self._add_video_items(result['videos'], result['current_url'])
        if page < int(result['last_page']):
            self._add_page_item(
                page + 1,
                result['last_page'],
                'search',
                search_string=search_string
            )
        xbmcplugin.endOfDirectory(self.addon_handle)

    def play_video(self, vid, size=None):
        try:
            play_info = self.eyny.get_video_link(vid, size)
        except ValueError as e:
            xbmcgui.Dialog().notification(
                heading='Error',
                message=unicode(e))
            return

        if size is None and len(play_info['sizes']) > 1:
            ret = int(xbmcgui.Dialog().select(
                'Please choose quality',
                map(str, play_info['sizes'])))
            logging.warning('SELECTED: {}'.format(ret))
            if ret < 0 or ret >= len(play_info['sizes']):
                return
            return self.play_video(vid, play_info['sizes'][ret])

        play_item = xbmcgui.ListItem(
            path=self.build_request_url(
                play_info['video'],
                play_info['current_url']))
        play_item.setProperty("IsPlayable", "true")
        play_item.setInfo(
            type="Video",
            infoLabels={"Title": play_info['title']})
        xbmcplugin.setResolvedUrl(self.addon_handle, True, listitem=play_item)


if __name__ == '__main__':
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = dict(urlparse.parse_qsl(sys.argv[2][1:]))
    gui = EynyGui(base_url, addon_handle)
    gui.handle(args)
