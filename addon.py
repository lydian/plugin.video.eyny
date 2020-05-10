# -*- coding: utf-8 -*-
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import map
from builtins import object

import codecs
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import urllib.parse
import urllib.error

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib.eyny_clientlib import EynyForum


class EynyGui(object):

    def __init__(self, base_url, addon_handle):
        addon = xbmcaddon.Addon()
        self.addon_path = addon.getAddonInfo('path')
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.eyny = EynyForum(
            addon.getSetting('username'), addon.getSetting('password'))
        self.search_history_file = os.path.join(
            xbmc.translatePath(addon.getAddonInfo('profile')),
            'search_history.json')

    def handle(self, args):
        mode = args.get('mode', None)
        if mode is None:
            self.main()
        if mode == 'category':
            self.list_categories()
        if mode == 'list':
            self.list_video(
                cid=args.get('cid', None),
                page=int(args.get('page', 1)),
            )
        if mode == 'video':
            self.play_video(args['vid'])
        if mode == 'search':
            self.search(
                new_search=args.get('new_search', False),
                search_string=args.get('search_string'),
                page=int(args.get('page', 1)),
                search_by=args.get('search_by')
            )
        if mode == 'playlist':
            self.list_playlist(
                search_by=args.get('search_by'),
                search_string=args.get('search_string'),
                page=int(args.get('page', 1))
            )
        if mode == 'show_playlist':
            self.show_playlist(
                pid=args.get('pid')
            )

    def _build_url(self, mode, **kwargs):
        query = kwargs
        query['mode'] = mode
        return self.base_url + '?' + urllib.parse.urlencode(query)

    def build_request_url(self, url, referer):
        USER_AGENT = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) '
            'AppleWebKit/601.7.8 (KHTML, like Gecko) '
            'Version/9.1.3 Safari/601.7.8')
        added_header = url + '|' + urllib.parse.urlencode({
            'User-Agent': USER_AGENT,
            'Range': '',
            'Referer': referer})
        return added_header

    def _add_folder(self, item_label, mode, icon=None, **url_kwargs):
        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle,
            url=self._build_url(mode, **url_kwargs),
            listitem=xbmcgui.ListItem(item_label, iconImage=icon),
            isFolder=True)

    def main(self):
        search_icon = self._get_icon('search.png')
        self._add_folder('Search', 'search', icon=search_icon)
        self._add_folder('Browse by categories', 'category')
        xbmcplugin.endOfDirectory(self.addon_handle)

    def _add_category_item(self, categories):
        for category in categories:
            self._add_folder(category['name'], 'list', cid=category['cid'])

    def _add_page_item(self, page, last_page, url_mode, **url_kwargs):
        next_icon = self._get_icon('next.png')
        self._add_folder('Next Page ({}/{})'.format(page, last_page),
                         url_mode, icon=next_icon, page=page, **url_kwargs)

    def _add_video_items(self, videos, current_url):
        for video in videos:
            title = video['title']
            if 'quality' in video:
                title = '({}p) '.format(video['quality']) + title
            li = xbmcgui.ListItem(label=title)
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
                url=self._build_url('video', vid=video['id']),
                listitem=li,
                isFolder=False)

    def _add_playlist_items(self, playlists, current_url):
        for playlist in playlists:
            title = playlist['title']
            li = xbmcgui.ListItem(label=title)
            image_url = self.build_request_url(
                playlist['image'], current_url)
            li.setArt({
                'fanart': image_url,
                'icon': image_url,
                'thumb': image_url
            })
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('show_playlist', pid=playlist['id']),
                listitem=li,
                isFolder=True)

    def _get_icon(self, filename):
        return os.path.join(
            self.addon_path,
            'resources',
            'icon',
            filename)

    def list_categories(self):
        filters = self.eyny.list_filters()
        self._add_category_item(filters['categories'])
        xbmcplugin.endOfDirectory(self.addon_handle)

    def list_video(self, cid=None, page=1):
        try:
            result = self.eyny.list_videos(cid=cid, page=page)
        except ValueError as e:
            xbmcgui.Dialog().ok(
                heading='Error',
                line1=str(e).encode('utf-8'))
            return

        sub_cids = [sub['cid'] for sub in result['category']['sub_categories']]
        if cid not in sub_cids:
            self._add_category_item(result['category']['sub_categories'])
        self._add_video_items(result['items'], result['current_url'])
        if page < int(result['last_page']):
            self._add_page_item(
                page + 1,
                result['last_page'],
                'list',
                cid=cid
            )
        xbmcplugin.endOfDirectory(self.addon_handle)

    def update_search_history(self, search_entry):
        search_list = self.get_search_history()
        if type(search_entry) is str:
            search_entry = search_entry.decode('utf-8')
        if search_entry in search_list:
            search_list.remove(search_entry)
        elif search_entry['query'] in search_list:
            search_list.remove(search_entry['query'])
        search_list = [search_entry] + search_list
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

    def search(
        self, new_search=False, search_string=None, page=1, search_by=None
    ):
        if new_search:
            search_by_list = ['keyword', 'user', 'channel']
            search_by = xbmcgui.Dialog().select(
                'Search by',
                list=search_by_list,
                preselect=0)
            if search_by < 0:
                return
            search_by = search_by_list[search_by]
            search_string = xbmcgui.Dialog().input(
                'Search term',
                type=xbmcgui.INPUT_ALPHANUM).strip()
            if not search_string:
                return

        if search_string is None:
            icon = self._get_icon('search.png')
            self._add_folder(
                'New Search', 'search', icon=icon, new_search=True
            )

            for search_entry in self.get_search_history():
                if type(search_entry) is dict:
                    search_string = search_entry['query']
                    display_string = search_entry['display']
                    search_by = search_entry['by']
                else:
                    search_string = search_entry
                    display_string = search_entry.encode('utf-8')
                    search_by = 'keyword'
                self._add_folder(
                    display_string, 'search',
                    search_string=search_string, search_by=search_by
                )
            return xbmcplugin.endOfDirectory(self.addon_handle)

        if search_by == 'user' or search_by == 'channel':
            result = self.eyny.search_user_channel(
                search_by,
                search_string,
                page=page)
            if not result or not result.get("username", None):
                xbmcgui.Dialog().notification(
                    'No such ' + search_by,
                    search_string,
                    icon=xbmcgui.NOTIFICATION_ERROR)
                return
            if page == 1:
                xbmcgui.Dialog().notification(
                    result['username'],
                    '/' + search_by + '/' + search_string)
                self.update_search_history({
                    'by': search_by,
                    'query': search_string,
                    'display': result['username']})
                if 'has_playlist' in result and result['has_playlist']:
                    self._add_folder(
                        '專輯',
                        'playlist',
                        search_by=search_by,
                        search_string=search_string)
        else:  # 'keyword'
            result = self.eyny.search_video(search_string, page=page)
            if not result or len(result['items']) == 0:
                xbmcgui.Dialog().notification(
                    'No results',
                    search_string,
                    icon=xbmcgui.NOTIFICATION_ERROR)
                return
            self.update_search_history({
                'by': 'keyword',
                'query': search_string,
                'display': search_string})

        self._add_video_items(result['items'], result['current_url'])
        if page < int(result['last_page']):
            self._add_page_item(
                page + 1,
                result['last_page'],
                'search',
                search_by=search_by,
                search_string=search_string
            )
        xbmcplugin.endOfDirectory(self.addon_handle)

    def list_playlist(self, search_by, search_string, page=1):
        result = self.eyny.search_user_channel(
            search_by,
            search_string,
            page=page,
            playlist=True)
        self._add_playlist_items(result['items'], result['current_url'])
        if page < int(result['last_page']):
            self._add_page_item(
                page + 1,
                result['last_page'],
                'playlist',
                search_by=search_by,
                search_string=search_string
            )
        xbmcplugin.endOfDirectory(self.addon_handle)

    def show_playlist(self, pid):
        result = self.eyny.list_videos_in_playlist(pid=pid)
        if not result or 'items' not in result or not result['items']:
            return
        self._add_video_items(result['items'], result['current_url'])
        xbmcplugin.endOfDirectory(self.addon_handle)

    def play_video(self, vid, size=None):
        play_info = self.eyny.get_video_link(vid, size)

        if size is None and len(play_info['sizes']) > 1:
            ret = int(xbmcgui.Dialog().select(
                'Please choose quality',
                list(map(str, play_info['sizes']))))
            logging.warning(
                'SELECTED: {} - {}'.format(ret, play_info['sizes'][ret]))
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
    args = dict(urllib.parse.parse_qsl(sys.argv[2][1:].decode("utf-8")))
    gui = EynyGui(base_url, addon_handle)
    gui.handle(args)
