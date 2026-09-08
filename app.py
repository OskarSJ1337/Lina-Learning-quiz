"""Lina – lokalt självtest med PDF-baserad frågebank."""
import json
import random
import re
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
BG, INK, MUTED, ACCENT = '#f4f6fb', '#202b40', '#617089', '#4f46bb'


def validate(questions):
    if not questions:
        raise ValueError('Inga frågor kunde skapas ur materialet.')
    for q in questions:
        if len(q['options']) != 4 or len(set(q['options'])) != 4 or q['answer'] not in range(4):
            raise ValueError('En fråga saknar fyra unika alternativ eller ett giltigt facit.')
    return questions


class Session:
    def __init__(self, questions, rng=None):
        rng = rng or random.Random()
        self.questions = []
        for original in validate(questions):
            q = dict(original)
            order = list(range(4))
            rng.shuffle(order)
            q['options'] = [original['options'][i] for i in order]
            q['answer'] = order.index(original['answer'])
            self.questions.append(q)
        rng.shuffle(self.questions)
        self.index = self.score = 0
        self.answered = False
        self.missed = []

    @property
    def current(self):
        return self.questions[self.index]

    def answer(self, choice):
        if self.answered:
            return None
        if choice not in range(4):
            raise ValueError('Ogiltigt svarsalternativ.')
        self.answered = True
        correct = choice == self.current['answer']
        self.score += int(correct)
        if not correct:
            self.missed.append(self.current)
        return correct

    def advance(self):
        if not self.answered:
            return False
        self.index += 1
        self.answered = False
        return self.index < len(self.questions)


# Begrepp i samma grupp ger jämförbara alternativ. En mening måste innehålla
# exakt ett av gruppens begrepp för att bli en entydig luckfråga.
GROUPS = [
    ['ontologi', 'epistemologi', 'metodologi', 'teori'],
    ['intervju', 'enkät', 'observation', 'dokumentanalys'],
    ['validitet', 'reliabilitet', 'generaliserbarhet', 'trovärdighet'],
    ['fabricering', 'förfalskning', 'plagiering', 'självplagiat'],
    ['tillförlitlighet', 'ärlighet', 'respekt', 'ansvar'],
    ['forskningsproblem', 'syfte', 'frågeställningar', 'analys'],
]


def extract_questions(paths):
    from pypdf import PdfReader
    questions, seen, reports = [], set(), []
    for path in paths:
        reader = PdfReader(path)
        count = 0
        for page_no, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            text = re.sub(r'-\s*\n\s*', '', text).replace('\u00ad', '')
            text = re.sub(r'\s+', ' ', text)
            for sentence in re.split(r'(?<=[.!?])\s+', text):
                if not 80 <= len(sentence) <= 360 or sentence.endswith('?'):
                    continue
                for group in GROUPS:
                    matches = [term for term in group if re.search(r'\b' + term + r'\b', sentence, re.I)]
                    if len(matches) != 1:
                        continue
                    term = matches[0]
                    prompt = re.sub(r'\b' + term + r'\b', '____', sentence, flags=re.I)
                    if prompt.casefold() in seen:
                        continue
                    seen.add(prompt.casefold())
                    questions.append(dict(question='Vilket begrepp saknas i texten?\n\n' + prompt,
                        options=group[:], answer=group.index(term), explanation=sentence,
                        source=Path(path).name, page=page_no, category='Begrepp ur PDF'))
                    count += 1
                    break
        reports.append(f'{Path(path).name}: {count} frågor')
    return questions, reports


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Lina – självtest')
        self.geometry('960x820')
        self.minsize(720, 640)
        self.configure(bg=BG)
        self.option_add('*Font', ('Segoe UI', 11))
        self.bank = validate(json.loads((BASE / 'questions.json').read_text(encoding='utf-8')))
        self.session = None
        self.importing = False
        self.header = tk.Frame(self, bg=BG)
        self.header.pack(fill='x', padx=32, pady=(24, 10))
        tk.Label(self.header, text='Lina / självtest', font=('Segoe UI', 18, 'bold'), bg=BG, fg=INK).pack(side='left')
        self.counter = tk.Label(self.header, text='Rätt: 0', bg=BG, fg=ACCENT, font=('Segoe UI', 14, 'bold'))
        self.counter.pack(side='right')
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        scroll.pack(side='right', fill='y')
        self.canvas.pack(fill='both', expand=True, padx=32, pady=(0, 24))
        self.canvas.configure(yscrollcommand=scroll.set)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self.resize)
        self.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-int(e.delta / 120), 'units'))
        for n in range(4):
            self.bind(str(n + 1), lambda e, i=n: self.choose(i))
        self.home()

    def resize(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        for child in self.body.winfo_children():
            if isinstance(child, (tk.Label, tk.Button)):
                child.configure(wraplength=max(400, event.width - 48))

    def clear(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)

    def label(self, text, size=12, color=INK):
        w = tk.Label(self.body, text=text, bg=BG, fg=color, font=('Segoe UI', size),
                     justify='left', anchor='w', wraplength=max(400, self.canvas.winfo_width()-48))
        w.pack(fill='x', pady=8)
        return w

    def button(self, text, command, primary=False):
        b = tk.Button(self.body, text=text, command=command, bg=ACCENT if primary else 'white',
                      fg='white' if primary else INK, relief='flat', bd=0, padx=18, pady=14,
                      cursor='hand2', anchor='w', justify='left', wraplength=780)
        b.pack(fill='x', pady=5)
        return b

    def home(self):
        self.session = None
        self.clear()
        self.counter.configure(text='Rätt: 0')
        self.label('Lite övning. Mer förståelse.', 26)
        self.label('Vetenskaplig metod · teori · forskningsetik', 13, MUTED)
        self.label(f'{len(self.bank)} övningsfrågor från dina tre PDF-filer. Välj ett av fyra alternativ. Efter svaret får du en förklaring och en sidhänvisning.')
        self.label('Ett självtest för övning – inte ett officiellt examinationsfacit.', 11, MUTED)
        self.button('Starta självtestet  →', lambda: self.start(self.bank), True)
        self.button('Läs PDF-filer och skapa fler begreppsfrågor', self.import_pdf)
        self.label('PDF-läget skapar automatiska luckfrågor ur texten. De färdiga övningsfrågorna tränar också förståelse och tillämpning. Allt fungerar lokalt.', 11, MUTED)
        self.label('Tips: du kan även välja svar med tangenterna 1–4.', 11, MUTED)

    def start(self, questions):
        self.session = Session(questions)
        self.show_question()

    def show_question(self):
        self.clear()
        s, q = self.session, self.session.current
        self.counter.configure(text=f'Rätt: {s.score}')
        self.label(f'FRÅGA {s.index + 1} AV {len(s.questions)}  ·  {q["category"]}', 11, MUTED)
        ttk.Progressbar(self.body, maximum=len(s.questions), value=s.index).pack(fill='x', pady=(0, 18))
        self.label(q['question'], 19)
        self.label('Välj det alternativ du tycker stämmer bäst.', 11, MUTED)
        self.options = [self.button(f'{i + 1}.  {option}', lambda i=i: self.choose(i)) for i, option in enumerate(q['options'])]

    def choose(self, index):
        if not self.session or self.session.index >= len(self.session.questions):
            return
        result = self.session.answer(index)
        if result is None:
            return
        q = self.session.current
        for i, button in enumerate(self.options):
            color = '#d9f2e2' if i == q['answer'] else '#fce0e2' if i == index else '#e9edf3'
            button.configure(state='disabled', bg=color, disabledforeground=INK)
        self.counter.configure(text=f'Rätt: {self.session.score}')
        self.label('●  Rätt svar!' if result else '●  Fel svar', 17, '#16713c' if result else '#b32b3a')
        if not result:
            self.label('Rätt svar: ' + q['options'][q['answer']], 13)
        self.label(q['explanation'])
        self.label(f'Källa: {q["source"]} · PDF-sida {q["page"]}', 10, MUTED)
        self.next_button = self.button('Visa resultat  →' if self.session.index == len(self.session.questions)-1 else 'Nästa  →', self.next_question, True)
        self.next_button.focus_set()
        self.update_idletasks()
        self.canvas.yview_moveto(1)

    def next_question(self):
        if self.session.advance():
            self.show_question()
        else:
            self.finish()

    def finish(self):
        self.clear()
        s = self.session
        self.label('Bra jobbat – testet är klart!', 25)
        self.label(f'{s.score} rätt av {len(s.questions)}  ·  {s.score / len(s.questions):.0%}', 22, ACCENT)
        if s.missed:
            missed = s.missed[:]
            self.button(f'Öva igen på de {len(missed)} frågor du missade', lambda: self.start(missed), True)
        self.button('Starta ett nytt blandat test', lambda: self.start(self.bank), True)
        self.button('Till startsidan', self.home)

    def import_pdf(self):
        paths = filedialog.askopenfilenames(title='Välj dina PDF-filer', filetypes=[('PDF-filer', '*.pdf')])
        if not paths:
            return
        self.clear()
        self.label('Läser PDF-filer och skapar frågor …', 22)
        progress = ttk.Progressbar(self.body, mode='indeterminate')
        progress.pack(fill='x', pady=20)
        progress.start()
        self.import_result = None
        def work():
            try:
                self.import_result = (True, extract_questions(paths))
            except Exception as error:
                self.import_result = (False, str(error))
        threading.Thread(target=work, daemon=True).start()
        self.after(100, self.check_import)

    def check_import(self):
        if self.import_result is None:
            self.after(100, self.check_import)
            return
        success, result = self.import_result
        self.clear()
        if not success:
            messagebox.showerror('Kunde inte läsa PDF', str(result))
            self.home()
            return
        questions, reports = result
        self.label('PDF-filerna är genomgångna', 22)
        self.label('\n'.join(reports))
        if questions:
            self.label('Frågorna bygger på originaltext med ett begrepp borttaget. Kontrollera formuleringarna mot källan vid behov.', 12, MUTED)
            self.button(f'Starta {len(questions)} begreppsfrågor', lambda: self.start(questions), True)
        else:
            self.label('Inga lämpliga textstycken hittades. Skannade PDF-filer utan textlager behöver OCR innan de kan användas.')
        self.button('Till startsidan', self.home)


def self_test(report, pdf_paths):
    """Exercise the bundled app from an arbitrary working directory."""
    app = App()
    app.withdraw()
    try:
        app.start(app.bank[:2])
        app.update()
        app.choose(app.session.current['answer'])
        if app.session.score != 1:
            raise RuntimeError('Incorrect score')
        app.next_question()
        app.choose((app.session.current['answer'] + 1) % 4)
        if app.session.score != 1:
            raise RuntimeError('Wrong answer changed score')
        app.next_question()
        app.home()
        questions, reports = extract_questions(pdf_paths) if pdf_paths else ([], [])
        if pdf_paths:
            validate(questions)
        Path(report).write_text(json.dumps({'ok': True, 'bank': len(app.bank),
            'imported': len(questions), 'pdfs': reports}, ensure_ascii=False), encoding='utf-8')
    finally:
        app.destroy()


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--self-test':
        self_test(sys.argv[2], sys.argv[3:])
    else:
        App().mainloop()
