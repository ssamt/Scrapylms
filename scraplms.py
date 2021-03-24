import tkinter as tk
from tkinter.filedialog import askdirectory
from tkinter import messagebox

import os
from urllib import parse
import threading
import requests
from bs4 import BeautifulSoup

main_url = "http://lms.ksa.hs.kr"
login_url = main_url + "/Source/Include/login_ok.php"
board_url = main_url + "/nboard.php"


def setEntry(entry, text):
    entry.delete(0, tk.END)
    entry.insert(0, text)


def createWindow():
    def chooseFolder():
        setEntry(folderEntry, askdirectory())

    def downloadAction():
        url = urlEntry.get()
        folder = folderEntry.get()
        index_f = indexFrom.get()
        index_t = indexTo.get()
        id = idEntry.get()
        pw = pwEntry.get()
        includePoster = posterVar.get()
        download = Download(url=url, folder=folder, index_f=index_f, index_t=index_t, id=id, pw=pw,
                            includePoster=includePoster)
        download.start()

    def message(text):
        downloadLabel.config(text=text)

    def boardPostNum(html):
        soup = BeautifulSoup(html, 'html.parser')
        info = soup.find(class_='NB_tPageArea').text
        start = info.index(':')+1
        end = info.index('건')
        return int(info[start:end])

    class Download(threading.Thread):
        def __init__(self, url, folder, index_f, index_t, id, pw, includePoster):
            super().__init__()
            self.session = None
            self.url = url
            self.folder = folder
            self.index_f = index_f
            self.index_t = index_t
            self.id = id
            self.pw = pw
            self.includePoster = includePoster

        def downloadPost(self, post_url, poster):
            post_html = self.session.get(post_url).text
            post_soup = BeautifulSoup(post_html, 'html.parser')
            info_table = post_soup.find(id='NB_FormTable')
            info_rows = info_table.find_all('tr')
            for info_row in info_rows:
                label = info_row.find_all(class_='nbLabelField pad')
                if len(label) > 0:
                    if '첨부파일' in label[0].text:
                        links = info_row.find_all('a')
                        for link in links:
                            file_name = link.text
                            file_name = file_name[:file_name.rfind('(')].strip()
                            if self.includePoster:
                                file_name = f'({poster}){file_name}'
                            file_url = main_url + link['href']
                            data = self.session.get(file_url, allow_redirects=True).content
                            store_file = open(f'{self.folder}/{file_name}', 'wb')
                            store_file.write(data)

        def run(self):
            if 'http' not in self.url:
                self.url = 'https://' + self.url
            try:
                params = dict(parse.parse_qsl(parse.urlsplit(self.url).query))
            except ValueError:
                downloadLabel.config(text='URL이 올바르지 않음')
                return None
            if 'scBCate' in params.keys():
                self.scBCate = params['scBCate']
            else:
                downloadLabel.config(text='URL이 올바르지 않음')
                return None
            if not os.path.isdir(self.folder):
                downloadLabel.config(text='폴더를 찾을 수 없음')
                return None
            if self.index_f == '':
                self.index_f = '0'
            if self.index_t == '':
                self.index_t = '0'
            try:
                self.index_f = int(self.index_f)
                self.index_t = int(self.index_t)
            except ValueError:
                downloadLabel.config(text='번호가 올바르지 않음')
                return None
            message('로그인 중...')
            try:
                requests.get(main_url)
            except requests.exceptions.RequestException:
                message('LMS에 접속할 수 없음')
                return None
            self.session = requests.session()
            if 'location.replace' not in self.session.post(login_url, data={'user_id': self.id, 'user_pwd': self.pw}).text:
                message('로그인 실패')
                return None
            first_page = self.session.get(board_url, params={'db': 'vod', 'scBCate': self.scBCate}).text
            post_num = boardPostNum(first_page)
            posts_in_page = 20
            if self.index_f <= 0:
                self.index_f = 1
            elif self.index_f > post_num:
                self.index_f = post_num
            if self.index_t < 0:
                self.index_t = 1
            elif self.index_t == 0 or self.index_t > post_num:
                self.index_t = post_num
            download_num = 0
            start_page = (post_num-self.index_t)//posts_in_page+1
            end_page = (post_num-self.index_f)//posts_in_page+1
            post_index = post_num-(start_page-1)*posts_in_page
            for page in range(start_page, end_page+1):
                page_html = self.session.get(board_url, params={'page': page, 'db': 'vod', 'scBCate': self.scBCate}).text
                page_soup = BeautifulSoup(page_html, 'html.parser')
                table = page_soup.find(id='NB_ListTable')
                tbody = table.find('tbody')
                post_rows = tbody.find_all('tr')
                for post_row in post_rows:
                    poster = post_row.find(class_='Board').text
                    if self.index_f <= post_index <= self.index_t:
                        message(f'다운로드 중... {self.index_t-post_index+1}/{self.index_t-self.index_f+1}')
                        post_link_td = post_row.find(class_='tdPad4L6px')
                        if len(post_link_td.find_all('a')) > 0:
                            post_url = main_url + post_link_td.find('a')['href']
                            self.downloadPost(post_url, poster)
                            download_num += 1
                    post_index -= 1
            download_failed = self.index_t-self.index_f+1-download_num
            if download_failed == 0:
                message('')
            else:
                message(f'{download_failed}개 다운로드 실패')
            messagebox.showinfo('Scraplms', '다운로드 완료')
            return None

    window = tk.Tk()
    window.title('scraplms')
    window.geometry('600x300')

    padw, pade, padn, pads = 10, 10, 7, 3

    urlFrame = tk.Frame()
    urlLabel = tk.Label(urlFrame, text='URL: ')
    urlLabel.pack(side='left')
    urlEntry = tk.Entry(urlFrame, width=50)
    urlEntry.pack(side='left')
    urlFrame.pack(anchor='w', padx=(padw, pade), pady=(padn, pads))

    folderFrame = tk.Frame()
    folderLabel = tk.Label(folderFrame, text='폴더: ')
    folderLabel.pack(side='left')
    folderEntry = tk.Entry(folderFrame, width=50)
    folderEntry.pack(side='left')
    folderButton = tk.Button(folderFrame, text='...', command=chooseFolder, width=3)
    folderButton.pack(side='left', padx=(10, 0))
    folderFrame.pack(anchor='w', padx=(padw, pade), pady=(padn, pads))

    indexFrame = tk.Frame()
    indexLabel1 = tk.Label(indexFrame, text='번호: ')
    indexLabel1.pack(side='left')
    indexFrom = tk.Entry(indexFrame, width=7)
    indexFrom.pack(side='left')
    indexLabel2 = tk.Label(indexFrame, text=' ~ ')
    indexLabel2.pack(side='left')
    indexTo = tk.Entry(indexFrame, width=7)
    indexTo.pack(side='left')
    indexFrame.pack(anchor='w', padx=(padw, pade), pady=(padn, pads))

    idPwFrame = tk.Frame()
    idPwLabel1 = tk.Label(idPwFrame, text='아이디: ')
    idPwLabel1.pack(side='left')
    idEntry = tk.Entry(idPwFrame)
    idEntry.pack(side='left')
    idPwLabel2 = tk.Label(idPwFrame, text=' 비밀번호: ')
    idPwLabel2.pack(side='left')
    pwEntry = tk.Entry(idPwFrame, show='*')
    pwEntry.pack(side='left')
    idPwFrame.pack(anchor='w', padx=(padw, pade), pady=(padn, pads))

    posterFrame = tk.Frame()
    posterLabel = tk.Label(posterFrame, text='작성자를 파일명에 포함: ')
    posterLabel.pack(side='left')
    posterVar = tk.BooleanVar()
    posterCheck = tk.Checkbutton(posterFrame, variable=posterVar)
    posterCheck.pack(side='left')
    posterFrame.pack(anchor='w', padx=(padw, pade), pady=(padn, pads))

    downloadFrame = tk.Frame()
    downloadButton = tk.Button(downloadFrame, text='다운로드', command=downloadAction)
    downloadButton.pack(side='left')
    downloadLabel = tk.Label(downloadFrame, text='')
    downloadLabel.pack(side='left', padx=(5, 0))
    downloadFrame.pack(anchor='w', padx=(padw, pade), pady=(padn, pads))

    return window


window = createWindow()
window.mainloop()
