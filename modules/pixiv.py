import threading
import random
import os
import time
import modules.utils as u
import modules.globals as g

from pixivapi import Client
from pixivapi import RankingMode
from pixivapi import BadApiResponse
from pathlib import Path
from os import listdir
from os.path import isfile, join


class ThreadPixiv(threading.Thread):

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.client = Client()
        self.allranking = []
        self.artpath = Path('data/pixiv/')
        self.tasks = []

    def run(self):
        self.pixiv_init()
        while True:
            time.sleep(0.1)
            if self.tasks:
                task = self.tasks.pop(0)
                task['func'](*task['args'], **task['kwargs'])

    def download_art(self, obj, size, filename):
        obj.download(directory=self.artpath,
                     size=size, filename=filename)

    def random_setup(self):  # download and set random pixiv art
        try:
            ranking = random.choice(self.allranking)
            fetchmode = random.random()  # ranked or ranked related art 20/80
            if fetchmode > 0.2:
                related_offset = 0
                allrelated = []
                for _ in range(4):
                    related = self.client.fetch_illustration_related(ranking.id,
                                                                     offset=related_offset).get('illustrations')
                    allrelated = u.sort_pixiv_arts(related, allrelated)
                    related_offset += 30
                illustration = random.choice(list(allrelated))
            else:
                illustration = ranking
            print(f'art id: {illustration.id}')
            artid = illustration.id
            g.lastlink = f'https://www.pixiv.net/en/artworks/{artid}'
            g.last_rand_img = f'{artid}.png'
            art = Path(f'data/pixiv/{artid}.png')
            if not art.is_file():
                self.download_art(illustration, g.pixiv_size, artid)
                if not art.is_file():
                    os.rename(f'data/pixiv/{artid}.jpg', f'data/pixiv/{artid}.png')
            u.call_draw('data/pixiv/', f'{artid}.png')
        except BadApiResponse as pixiv_exception:  # reconnect
            if 'Status code: 400' in str(pixiv_exception):
                self.pixiv_init()
            self.random_pixiv_art()
        except Exception as e:
            if 'RemoteDisconnected' in str(e):
                self.random_pixiv_art()

    def save_setup(self, namesave, owner, artid, folder='data/custom/', setpic=False, save=False, save_msg=False):
        """
        save pixiv art by art id
        :param save_msg: whether send <image saved> message
        :param save: whether save image
        :param setpic: whether set image
        :param namesave: filename
        :param owner: twitch username
        :param artid: pixiv art id
        :param folder: save folder
        """
        try:
            print(f'art id: {artid}')
            namesave = u.while_is_file(folder, namesave, '.png')
            namesave = u.while_is_file(folder, namesave, '_p0.png')
            savedart = self.client.fetch_illustration(int(artid))
            self.download_art(savedart, g.pixiv_size, namesave)
            if os.path.isdir('data/pixiv/' + namesave):
                mypath2 = 'data/pixiv/' + namesave
                onlyfiles = [f for f in listdir(mypath2) if isfile(join(mypath2, f))]
                for i in onlyfiles:
                    os.rename(f'data/pixiv/{namesave}/{i}', f'{folder}{namesave}{i[8:-4]}.png')
                    if save:
                        g.db.add_link(f'https://www.pixiv.net/en/artworks/{artid}', f'{namesave}{i[8:-4]}.png')
                        g.db.add_owner(f'{namesave}{i[8:-4]}.png', owner)
                    if setpic:
                        u.call_draw(folder, f'{namesave}{i[8:-4]}.png')
                        time.sleep(1.5)
                os.rmdir(f'data/pixiv/{namesave}')
                if save_msg:
                    u.send_message(f'{owner}, {namesave}.png saved')
                return
            art = Path(f'data/pixiv/{namesave}.png')
            filepath = f'data/pixiv/{namesave}.png'
            if not art.is_file():
                filepath = f'data/pixiv/{namesave}.jpg'
            os.rename(filepath, f'{folder}{namesave}.png')
            if save:
                g.db.add_link(f'https://www.pixiv.net/en/artworks/{artid}', f'{namesave}.png')
                g.db.add_owner(f'{namesave}.png', owner)
            if setpic:
                u.call_draw(folder, f'{namesave}.png')
            if save_msg:
                u.send_message(f'{owner}, {namesave}.png saved')
        except BadApiResponse as pixiv_exception:  # reconnect
            print(f'badapiresponse - {pixiv_exception}')
            if 'Status code: 404' in str(pixiv_exception):
                u.send_message(f'{owner}, {artid} not found')
                return
            if 'Status code: 400' in str(pixiv_exception):
                self.pixiv_init()
            self.save_pixiv_art(namesave, owner, artid, setpic, save, save_msg)
        except Exception as e:
            if 'RemoteDisconnected' in str(e):
                self.save_pixiv_art(namesave, owner, artid, setpic, save, save_msg)

    def random_pixiv_art(self):
        self.tasks.append({'func': self.random_setup, 'args': (), 'kwargs': {}})

    def save_pixiv_art(self, *args, **kwargs):
        self.tasks.append({'func': self.save_setup, 'args': args, 'kwargs': kwargs})

    def pixiv_init(self):
        try:
            self.allranking *= 0
            self.client.authenticate(g.px_token)
            print('pixiv auth √')
            rank_offset = 30
            ranking1 = self.client.fetch_illustrations_ranking(
                mode=RankingMode.DAY).get('illustrations')  # check 500 arts, filter by tags and ratio
            self.allranking = u.sort_pixiv_arts(ranking1, self.allranking)
            for i in range(16):
                print(f'\rpixiv load={int(i / 16 * 100) + 7}%', end='')
                ranking = self.client.fetch_illustrations_ranking(mode=RankingMode.DAY,
                                                                  offset=rank_offset).get('illustrations')
                self.allranking = u.sort_pixiv_arts(ranking, self.allranking)
                rank_offset += 30
            print()
        except BadApiResponse:
            time.sleep(30)
            self.run()


Pixiv = ThreadPixiv("ThreadPixiv")
