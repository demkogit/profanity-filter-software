# -*- coding: utf-8 -*-
import time
import threading
import tkinter as tk
from tkinter import filedialog
from vosk import Model, KaldiRecognizer, SetLogLevel
#import sys
import os
import wave
import json
from pydub import AudioSegment

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("320x240")
        self.resizable(0,0)

        self.ban_word_list = []
        self.file_path = ''
        self.entry_text = tk.StringVar()
        
        self.read_ban_words_file()
        
        name_label = tk.Label(self, text="Имя файла:")
        name_label.grid(row=0, column=0, sticky=tk.W, pady=10, padx=10)
        
        name_entry = tk.Entry(self, textvariable=self.entry_text,
                              state='readonly')
        name_entry.grid(row=0, column=1,sticky=tk.W, padx=10)

        open_button = tk.Button(self, text='Выбрать аудио файл',
                                command = self.open_file)
        open_button.grid(row=1, column=1,sticky=tk.W, padx=10, pady=5)


        mode_label = tk.Label(self, text="Режим фильтрации:")
        mode_label.grid(row=2, column=0, sticky=tk.W, padx=10)

        #self.mode_button = tk.Button(self, text='Вырезать',
        #                        command = self.toggle_mode)
        #self.mode_button.grid(row=2, column=1, sticky=tk.W, padx=10)

        self.is_cut = tk.BooleanVar()
        self.is_cut.set(0)
        r1 = tk.Radiobutton(self, text='Запикать слова',
                         variable=self.is_cut, value=0)
        r1.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        r2 = tk.Radiobutton(self, text='Вырезать слова',
                         variable=self.is_cut, value=1)
        r2.grid(row=3, column=1, sticky=tk.W, padx=5)
        
        
        ban_words_label = tk.Label(self, text="Список слов:")
        ban_words_label.grid(row=4, column=0, sticky=tk.W, padx=10, pady=10)

        ban_words_button = tk.Button(self, text='Редактировать список слов',
                                command = self.open_ban_word_list)
        ban_words_button.grid(row=4, column=1, sticky=tk.W, padx=10)

        self.convert_button = tk.Button(self, text='Отфильтровать аудио файл\nи сохранить',
                         command=self.start_action, state='disabled')
        self.convert_button.grid(row=6, column=1, padx=10, pady=20)
        


    def start_action(self):
        if len(self.file_path) == 0:
            return
    
        self.disable()
        
        thread = threading.Thread(target=self.run_action)
        thread.start()
        
        self.check_thread(thread)

    def check_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.check_thread(thread))
        else:
            self.enable()

    def disable(self):
        for child in self.winfo_children():
            child.configure(state='disable')

    def enable(self):
        for child in self.winfo_children():
            if(str(child) != '.!entry'):
                child.configure(state='normal')

    def open_file(self):
        audio_file_extensions = ['*.wav', '*.mp3']
        ftypes = [    
            ('audio files', audio_file_extensions), 
        ]

        old_file_path = self.file_path
        self.file_path = filedialog.askopenfilename(filetypes=ftypes)
        
        if len(self.file_path) != 0:
            file_name = self.file_path.split('/')[-1:]
            self.entry_text.set(file_name)
            print(file_name)
            self.convert_button.config(state=tk.NORMAL)
        else:
            self.file_path = old_file_path
            if len(self.entry_text.get()) == 0:
                self.convert_button.config(state=tk.DISABLED)

        from pydub.utils import mediainfo
        print(mediainfo(self.file_path))

    def convert(self):
        import subprocess
        subprocess.call(['sox', self.file_path, '-e', 'signed-integer',
                         '-r', '16k', 'converted_file.wav', 'remix', '1,2'])
    def read_ban_words_file(self):
        if os.path.exists('ban_words.txt'):
            f = open('ban_words.txt', 'r')
            ban_words_string = f.readlines()[0]

        ban_words_string = ban_words_string.replace('\n', '')
        ban_words_string = ban_words_string.replace('\n', ' ')
        self.ban_word_list = ban_words_string.split(',')
        self.ban_word_list = list(filter(None, self.ban_word_list))
        
    def run_action(self):
        #f_path = self.file_path
        output_file = 'output_file.wav'
        self.convert()
        f_path = 'converted_file.wav'
        if(self.file_path.endswith('.mp3')):
            output_file = 'output_file.mp3'
        
        
        wf = wave.open(f_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print ("Audio file must be WAV format mono PCM.")
            exit (1)
        print('wft')
        model = Model("model_s")
        rec = KaldiRecognizer(model, wf.getframerate())
        
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)


        res = rec.FinalResult()
        print(res)

        data = json.loads(res)

        audio = 0
        if(self.file_path.endswith('.wav')):
            audio = AudioSegment.from_wav(self.file_path)
        elif self.file_path.endswith('.mp3'):
            audio = AudioSegment.from_mp3(self.file_path)      
        newAudio = 0

        if self.is_cut.get():
            for r in data['result']:
                if not r['word'] in self.ban_word_list:
                    t1 = r['start']*1000
                    t2 = r['end']*1000
                    newAudio += audio[t1:t2]
        else:
            for r in data['result']:
                if not r['word'] in self.ban_word_list:
                    t1 = r['start']*1000
                    t2 = r['end']*1000
                    newAudio += audio[t1:t2]
                else:
                    t1 = r['start']*1000
                    t2 = r['end']*1000
                    newAudio += self.generate_sine(t2-t1, 480)
                    
        from pydub.utils import mediainfo
        info = mediainfo(self.file_path)
        newAudio.export(output_file, format=output_file[-3:],
                        parameters=['-ar',
                                    info['sample_rate'], '-ac', info['channels'], '-ab', '16', '-f', 'mulaw'])


    def generate_sine(self, duration, freq=440):
        from pydub.generators import Sine
        return Sine(freq=freq).to_audio_segment(duration=duration)
        
    def open_ban_word_list(self):
        ban_words_string =  ''
        self.read_ban_words_file()
        for word in self.ban_word_list:
            ban_words_string += word+','

        # THE CLUE
        self.wm_attributes("-disabled", True)

        # Creating the toplevel dialog
        self.top = tk.Toplevel(self)
        self.top.minsize(300, 100)

        # Tell the window manager, this is the child widget.
        # Interesting, if you want to let the child window 
        # flash if user clicks onto parent
        self.top.transient(self)

        self.top.protocol("WM_DELETE_WINDOW", self.close_ban_word_list)

        #self.top_label = tk.Label(self.top,
        #                          text=' want to enable my parent window again?')
        #self.top_label.pack(side='top')
        
        self.top_text = tk.Text(self.top, height=2, width=30)
        self.top_text.pack(pady=10)

        self.top_text.insert(tk.END, ban_words_string)
        
        self.top_button = tk.Button(self.top, text='Сохранить', command=self.close_ban_word_list)
        self.top_button.pack(side='left', fill='x', expand=True)

    def close_ban_word_list(self):
        ban_words_string = self.top_text.get("1.0","end-1c")
        ban_words_string = ban_words_string.replace('\n', '')
        ban_words_string = ban_words_string.replace('\n', ' ')
        f = open('ban_words.txt', 'w')
        f.write(ban_words_string)
        f.close()
        self.ban_word_list = ban_words_string.split(',')
        self.ban_word_list = list(filter(None, self.ban_word_list))
        # IMPORTANT!
        self.wm_attributes("-disabled", False) # IMPORTANT!
        
        self.top.destroy()

        # Possibly not needed, used to focus parent window again
        self.deiconify() 


if __name__ == "__main__":
    app = App()
    app.mainloop()
