# -*- coding: utf-8 -*-
import sys
import urlparse
import urllib

import html5lib
import urlresolver
import xbmcaddon
import xbmcgui
import xbmcplugin

from eyny_clientlib import EynyForum


class EynyGui(object):

    def __init__(self, base_url, addon_handle):
        addon = xbmcaddon.Addon()
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.eyny = EynyForum(
            addon.getSetting('username'), addon.getSetting('password'))
        self.is_login = self.eyny.login()

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
        for category in filters['categories']:
            li = xbmcgui.ListItem(category['name'])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('list', cid=category['cid']),
                listitem=li,
                isFolder=True)
        for orderby in filters['orderbys']:
            li = xbmcgui.ListItem(orderby['name'])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('list', orderby=orderby['orderby']),
                listitem=li,
                isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    def list_video(self, cid=None, page=1, orderby=None):
        try:
            result = self.eyny.list_videos(cid=cid, page=page, orderby=orderby)
        except ValueError as e:
            xbmcgui.Dialog().ok(
                heading='Error',
                line1=unicode(e).encode('utf-8'))
            return

        if page > 1:
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url(
                    'list', orderby=orderby, cid=cid, page=page - 1),
                listitem=xbmcgui.ListItem('~~ Previous Page ~~'),
                isFolder=True)

        for video in result['videos']:
            li = xbmcgui.ListItem(label=video['title'])
            li.setProperty('IsPlayable', 'true')
            image_url = self.build_request_url(
                video['image'], result['current_url'])
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
            li.setProperty('VideoResolution', str(video['quality']))
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url('video', vid=video['vid']),
                listitem=li,
                isFolder=False)
        if page < result['last_page']:
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=self._build_url(
                    'list', orderby=orderby, cid=cid, page=page + 1),
                listitem=xbmcgui.ListItem('~~ Next Page ~~'),
                isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

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
            self.play_video(vid, ret)

        play_item = xbmcgui.ListItem(
            path=self.build_request_url(
                play_info['video'],
                play_info['current_url']))
        play_item.setProperty( "IsPlayable", "true" )
        play_item.setInfo(
            type="Video",
            infoLabels={ "Title": play_info['title']})
        xbmcplugin.setResolvedUrl(self.addon_handle, True, listitem=play_item)


if __name__ == '__main__':
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = dict(urlparse.parse_qsl(sys.argv[2][1:]))
    gui = EynyGui(base_url, addon_handle)
    gui.handle(args)
