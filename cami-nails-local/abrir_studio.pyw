"""Inicializador Windows: servidor local e painel, sem terminal."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error
import webbrowser
import tkinter as tk
from tkinter import messagebox
ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:5000'
INSTALLATION = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]

def server_state():
    try:
        with urllib.request.urlopen(URL+'/saude', timeout=0.5) as response:
            result=json.load(response)
        return 'ready' if result.get('app')=='cami-nails' and result.get('installation')==INSTALLATION else 'other'
    except urllib.error.HTTPError:
        return 'other'
    except (urllib.error.URLError, TimeoutError, OSError):
        return 'offline'
    except (ValueError, AttributeError):
        return 'other'

class Launcher:
    def __init__(self):
        self.process=None;self.log=None;self.closing=False
        self.window=tk.Tk();self.window.title('Cami Nails · Studio')
        self.window.geometry('410x290');self.window.resizable(False,False)
        self.window.configure(bg='#faf7f4')
        try:self.window.iconbitmap(str(ROOT/'app'/'static'/'cami-nails.ico'))
        except tk.TclError:pass
        tk.Label(self.window,text='Cami Nails',font=('Georgia',28,'italic'),bg='#faf7f4',fg='#a4516a').pack(pady=(24,8))
        self.status=tk.Label(self.window,text='Iniciando o Studio…',bg='#faf7f4',fg='#403438',wraplength=360)
        self.status.pack(pady=8)
        self.open_button=tk.Button(self.window,text='Abrir sistema',command=lambda:webbrowser.open(URL),state='disabled',bg='#a4516a',fg='white',width=27,pady=7)
        self.open_button.pack(pady=7)
        tk.Button(self.window,text='Minimizar',command=self.window.iconify,width=27).pack(pady=3)
        self.stop_button=tk.Button(self.window,text='Encerrar sistema',command=self.stop,width=27)
        self.stop_button.pack(pady=3)
        self.window.protocol('WM_DELETE_WINDOW',self.stop)
        self.window.after(100,self.start)
    def fail(self,text):
        self.status.config(text='Não foi possível iniciar.')
        messagebox.showerror('Cami Nails',text,parent=self.window)
    def start(self):
        state=server_state()
        if state=='ready':
            self.status.config(text='O sistema já está aberto. Esta janela não controla o servidor anterior.')
            self.stop_button.config(text='Fechar esta janela');self.open_button.config(state='normal');webbrowser.open(URL);return
        if state=='other':
            self.fail('A porta 5000 está sendo usada por outra versão ou programa. Feche a janela antiga do sistema e tente novamente.');return
        python=ROOT/'.venv'/'Scripts'/'python.exe'
        if not python.exists():
            self.fail('Execute instalar_atalho.bat nesta pasta uma vez para preparar o sistema.');return
        try:
            (ROOT/'instance').mkdir(exist_ok=True)
            self.log=(ROOT/'instance'/'inicializacao.log').open('ab')
            self.process=subprocess.Popen([str(python),str(ROOT/'run.py')],cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.deadline=time.monotonic()+40;self.window.after(250,self.wait_ready)
        except OSError:
            self.fail('Não foi possível abrir o servidor. Execute instalar_atalho.bat novamente.')
    def wait_ready(self):
        if self.closing:return
        if self.process.poll() is not None:
            self.fail('O servidor encerrou durante a inicialização. Confira instance/inicializacao.log ou envie esse arquivo para diagnóstico.');return
        if server_state()=='ready':
            self.status.config(text='Sistema em funcionamento neste computador. Você pode minimizar esta janela.')
            self.open_button.config(state='normal');webbrowser.open(URL);self.window.after(3000,self.monitor);return
        if time.monotonic()>self.deadline:
            self.fail('A inicialização demorou mais que o esperado. Encerre esta janela e tente novamente.');return
        self.window.after(350,self.wait_ready)
    def monitor(self):
        if self.closing:return
        if self.process.poll() is not None:
            self.open_button.config(state='disabled');self.fail('O servidor parou. Feche esta janela e abra o atalho novamente.');return
        self.window.after(3000,self.monitor)
    def stop(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno('Encerrar o Studio','Termine de salvar os cadastros antes de encerrar. Deseja parar o sistema agora?',parent=self.window):return
            self.closing=True
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=5)
        if self.log:self.log.close()
        self.window.destroy()
    def run(self):self.window.mainloop()
if __name__=='__main__':Launcher().run()
