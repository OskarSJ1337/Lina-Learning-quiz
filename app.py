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
BG, INK, ACCENT = '#F4F6FB', '#202B40', '#6554C0'
SURFACE, HOVER, ACCENT_HOVER = '#FFFFFF', '#EDE7FF', '#5141A6'
TRUE, FALSE, BUTTON_TEXT = '#D0F2DE', '#FFDDD8', INK
MUTED = '#48566B'


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
        self.choices = {}
        self.missed = []

    @property
    def answered(self):
        return self.index in self.choices

    @property
    def current(self):
        return self.questions[self.index]

    def answer(self, choice):
        if self.answered:
            return None
        if choice not in range(4):
            raise ValueError('Ogiltigt svarsalternativ.')
        self.choices[self.index] = choice
        correct = choice == self.current['answer']
        self.score += int(correct)
        if not correct:
            self.missed.append(self.current)
        return correct

    def advance(self):
        if not self.answered:
            return False
        self.index += 1
        return self.index < len(self.questions)

    def previous(self):
        if self.index == 0:
            return False
        self.index -= 1
        return True


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
        self.title('Linas coola quiz')
        self.geometry('960x820')
        self.minsize(720, 640)
        self.configure(bg=BG)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TProgressbar', background=ACCENT, troughcolor=BG,
                        bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure('TScrollbar', background=HOVER, troughcolor=BG,
                        bordercolor=BG, arrowcolor=BUTTON_TEXT,
                        lightcolor=ACCENT, darkcolor=ACCENT)
        style.map('TScrollbar', background=[('active', ACCENT)])
        self.option_add('*Font', ('Segoe UI', 13))
        self.bank = validate(json.loads((BASE / 'questions.json').read_text(encoding='utf-8')))
        self.session = None
        self.importing = False
        self.header = tk.Frame(self, bg=BG)
        self.header.pack(fill='x', padx=32, pady=(24, 10))
        tk.Label(self.header, text='Linas coola quiz', font=('Segoe UI', 18, 'bold'), bg=BG, fg=INK).pack(side='left')
        self.counter = tk.Label(self.header, text='Rätt: 0', bg=HOVER, fg=ACCENT, padx=14, pady=8, font=('Segoe UI', 14, 'bold'))
        self.counter.pack(side='right')
        self.back_button = tk.Button(self.header, text='Till startsidan', command=self.home,
                                     bg=HOVER, fg=INK, activebackground=ACCENT,
                                     activeforeground='white', relief='flat', bd=0,
                                     padx=12, pady=8, cursor='hand2')
        self.back_button.pack(side='right', padx=16)
        self.navigation = tk.Frame(self, bg=BG)
        self.navigation.pack(side='bottom', fill='x', padx=32, pady=(0, 16))
        self.previous_button = tk.Button(self.navigation, text='← Föregående fråga',
            command=self.previous_question, bg=HOVER, fg=INK, relief='flat', padx=16, pady=12)
        self.previous_button.pack(side='left')
        self.next_button = tk.Button(self.navigation, text='Nästa fråga →',
            command=self.next_question, bg=ACCENT, fg='white', relief='flat', padx=16, pady=12)
        self.next_button.pack(side='right')
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

    def label(self, text, size=13, color=INK):
        w = tk.Label(self.body, text=text, bg=BG, fg=color, font=('Segoe UI', size),
                     justify='left', anchor='w', wraplength=max(400, self.canvas.winfo_width()-48))
        w.pack(fill='x', pady=8)
        return w

    def button(self, text, command, primary=False, color=None):
        normal = color or (ACCENT if primary else SURFACE)
        hover = color or (ACCENT_HOVER if primary else HOVER)
        b = tk.Button(self.body, text=text, command=command, bg=normal,
                      fg='white' if primary else BUTTON_TEXT,
                      activebackground=hover,
                      activeforeground='white' if primary else BUTTON_TEXT,
                      font=('Segoe UI', 13, 'bold' if primary else 'normal'),
                      highlightcolor=INK, relief='flat', bd=0, padx=18, pady=14,
                      cursor='hand2', anchor='w', justify='left', wraplength=max(400, self.canvas.winfo_width()-48))
        b.pack(fill='x', pady=5)
        b.bind('<Enter>', lambda event: b.configure(bg=hover) if str(b['state']) == 'normal' else None)
        b.bind('<Leave>', lambda event: b.configure(bg=normal) if str(b['state']) == 'normal' else None)
        return b

    def home(self):
        self.previous_button.configure(state='disabled')
        self.next_button.configure(state='disabled')
        self.back_button.configure(state='disabled')
        self.session = None
        self.clear()
        self.counter.configure(text='Rätt: 0')
        self.label('Vetenskaplig metod', 26)
        self.label(f'{len(self.bank)} frågor · Fyra svarsalternativ', 14, MUTED)
        self.button(f'Starta quiz – Alla frågor ({len(self.bank)})', lambda: self.start(self.bank), True)
        sources = [
            ('God_forskningssed_VR_2024.pdf', 'God forskningssed', '#D0F2DE'),
            ('Serder_och_Jober_2021_kapitel_1.pdf', 'Serder & Jobér, kapitel 1', '#D8EAFF'),
            ('Undervisningsunderlag_bilder_och_text.pdf', 'Undervisningsunderlag', '#FFE4C7'),
        ]
        for source, title, color in sources:
            questions = [q for q in self.bank if q['source'] == source]
            if questions:
                self.button(f'Starta quiz – {title} ({len(questions)})',
                            lambda questions=questions: self.start(questions), color=color)

    def start(self, questions, review=False):
        self.back_button.configure(state='normal')
        if not review:
            self.selected_questions = list(questions)
        self.session = Session(questions)
        self.show_question()

    def show_question(self):
        self.clear()
        s, q = self.session, self.session.current
        self.counter.configure(text=f'Rätt: {s.score}')
        self.label(f'Fråga {s.index + 1} av {len(s.questions)}', 13, MUTED)
        ttk.Progressbar(self.body, maximum=len(s.questions), value=s.index).pack(fill='x', pady=(0, 18))
        self.label(q['question'], 20)
        self.options = [self.button(f'{i + 1}.  {option}', lambda i=i: self.choose(i)) for i, option in enumerate(q['options'])]
        self.previous_button.configure(state='normal' if s.index > 0 else 'disabled')
        self.next_button.configure(text='Visa resultat' if s.index == len(s.questions)-1 else 'Nästa fråga →',
                                   state='normal' if s.answered else 'disabled')
        if s.answered:
            self.show_feedback(s.choices[s.index])
        self.update_idletasks()
        self.canvas.yview_moveto(0)

    def choose(self, index):
        if not self.session or self.session.index >= len(self.session.questions):
            return
        result = self.session.answer(index)
        if result is None:
            return
        self.show_feedback(index)

    def show_feedback(self, index):
        result = index == self.session.current['answer']
        self.update_idletasks()
        viewport_top = self.canvas.canvasy(0)
        q = self.session.current
        for i, button in enumerate(self.options):
            color = TRUE if i == q['answer'] else FALSE if i == index else BG
            button.configure(state='disabled', bg=color, disabledforeground=BUTTON_TEXT)
        self.counter.configure(text=f'Rätt: {self.session.score}')
        feedback = self.label('●  Rätt svar' if result else '●  Fel svar', 17, BUTTON_TEXT)
        feedback.configure(bg=TRUE if result else FALSE, padx=12, pady=8)
        if not result:
            self.label('Rätt svar: ' + q['options'][q['answer']], 13)
        self.label(q['explanation'])
        source_names = {
            'Undervisningsunderlag_bilder_och_text.pdf': 'Undervisningsunderlag',
            'Serder_och_Jober_2021_kapitel_1.pdf': 'Serder & Jobér, kap. 1',
            'God_forskningssed_VR_2024.pdf': 'God forskningssed (2024)',
        }
        source = source_names.get(q['source'], q['source'])
        self.label(f'{source} · PDF-sida {q["page"]}', 12, MUTED)
        self.next_button.configure(state='normal')
        self.update_idletasks()
        # Keep the same pixel offset as feedback increases the scroll region.
        bounds = self.canvas.bbox('all')
        if bounds and bounds[3] > bounds[1]:
            self.canvas.yview_moveto((viewport_top - bounds[1]) / (bounds[3] - bounds[1]))

    def previous_question(self):
        if self.session and self.session.previous():
            self.show_question()

    def next_question(self):
        if not self.session or not self.session.answered:
            return
        if self.session.advance():
            self.show_question()
        else:
            self.finish()

    def finish(self):
        self.previous_button.configure(state='normal')
        self.next_button.configure(state='disabled')
        self.clear()
        s = self.session
        self.label('Resultat', 25)
        self.label(f'{s.score} rätt av {len(s.questions)}  ·  {s.score / len(s.questions):.0%}', 22, INK)
        if s.missed:
            missed = s.missed[:]
            self.button(f'Öva på missade frågor ({len(missed)})', lambda: self.start(missed, review=True), True)
        self.button('Nytt test', lambda: self.start(self.selected_questions), True)
        self.button('Startsida', self.home)

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
        self.button('Startsida', self.home)


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
