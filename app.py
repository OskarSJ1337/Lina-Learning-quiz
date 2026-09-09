"""Lina – lokalt självtest med PDF-baserad frågebank."""
import json
import random
import re
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, ttk

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
BG, INK, ACCENT = '#F4F6FB', '#182235', '#51409B'
SURFACE, HOVER, ACCENT_HOVER = '#FFFFFF', '#EDE7FF', '#403080'
TRUE, FALSE, BUTTON_TEXT = '#D0F2DE', '#FFDDD8', INK
MUTED = '#37445A'


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

    def answer(self, choice, replace=False):
        if self.answered and not replace:
            return None
        if choice not in range(4):
            raise ValueError('Ogiltigt svarsalternativ.')
        self.choices[self.index] = choice
        correct = choice == self.current['answer']
        self.score = sum(value == self.questions[i]['answer'] for i, value in self.choices.items())
        self.missed = [self.questions[i] for i, value in self.choices.items() if value != self.questions[i]['answer']]
        return correct

    def advance(self):
        if self.index >= len(self.questions):
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
        self.dark_mode = False
        self.reading_fonts = {}
        self.title('Linas självstudie quiz')
        self.geometry('1200x850')
        self.minsize(860, 640)
        self.configure(bg=BG)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TProgressbar', background=ACCENT, troughcolor=BG,
                        bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure('TScrollbar', background=HOVER, troughcolor=BG,
                        bordercolor=BG, arrowcolor=BUTTON_TEXT,
                        lightcolor=ACCENT, darkcolor=ACCENT)
        style.map('TScrollbar', background=[('active', ACCENT)])
        self.option_add('*Font', self.reading_font(13))
        self.bank = validate(json.loads((BASE / 'questions.json').read_text(encoding='utf-8')))
        self.session = None
        self.importing = False
        self.header = tk.Frame(self, bg=BG)
        self.header.pack(fill='x', padx=32, pady=(24, 10))
        tk.Label(self.header, text='Linas självstudie quiz', font=self.reading_font(18, 'bold'), bg=BG, fg=INK).pack(side='left')
        self.counter = tk.Label(self.header, text='Rätt: 0', bg=HOVER, fg=INK, padx=14, pady=8, font=self.reading_font(14, 'bold'))
        self.counter.pack(side='right')
        self.back_button = tk.Button(self.header, text='Till startsidan', command=self.home,
                                     bg=HOVER, fg=INK, activebackground=ACCENT,
                                     activeforeground='white', relief='flat', bd=0,
                                     padx=12, pady=8, cursor='hand2')
        self.back_button.pack(side='right', padx=16)
        self.theme_button = tk.Button(self.header, text='Nattläge', command=self.toggle_theme,
            bg=HOVER, fg=INK, relief='flat', padx=10, pady=8, cursor='hand2', font=self.reading_font(11))
        self.theme_button.pack(side='right', padx=4)
        self.navigation = tk.Frame(self, bg=BG)
        self.navigation.pack(side='bottom', fill='x', padx=32, pady=(0, 16))
        self.previous_button = tk.Button(self.navigation, text='← Föregående fråga',
            command=self.previous_question, bg=HOVER, fg=INK, relief='flat', padx=16, pady=12)
        self.navigation.columnconfigure(0, weight=0)
        self.navigation.columnconfigure(1, weight=1)
        self.navigation.columnconfigure(2, weight=0)
        self.previous_button.grid(row=0, column=0, sticky='w')
        self.next_button = tk.Button(self.navigation, text='Nästa fråga →',
            command=self.next_question, bg=ACCENT, fg='white', relief='flat', padx=16, pady=12)
        self.next_button.grid(row=0, column=2, sticky='e')
        self.progress_state = None
        self.question_progress = tk.Canvas(self.navigation, width=1, height=26, bg=BG,
            highlightthickness=0, cursor='hand2')
        self.question_progress.grid(row=0, column=1, sticky='ew', padx=16)
        self.question_progress.bind('<Configure>', lambda event: self.update_progress_color())
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.scroll_view)
        self.canvas.pack(fill='both', expand=True, padx=32, pady=(0, 24))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor='nw')
        self.body.bind('<Configure>', self.sync_scroll)
        self.canvas.bind('<Configure>', self.resize)
        self.bind('<MouseWheel>', self.mousewheel)
        for n in range(4):
            self.bind(str(n + 1), lambda e, i=n: self.choose(i))
        self.home()

    def reading_font(self, size, weight='normal'):
        key = (size, weight)
        if key not in self.reading_fonts:
            self.reading_fonts[key] = tkfont.Font(self, family='Helvetica' if sys.platform == 'darwin' else 'Segoe UI', size=size, weight=weight)
        return self.reading_fonts[key]

    @staticmethod
    def readable_paragraphs(text):
        # Break sentences into shorter reading blocks without changing wording.
        return re.sub(r'(?<=[.!?]) +(?=[A-ZÅÄÖ])', '\n\n', text)

    def sync_scroll(self, event=None, offset=None):
        viewport = max(1, self.canvas.winfo_height())
        content = max(1, self.body.winfo_reqheight())
        extent = max(viewport, content)
        top = self.canvas.canvasy(0) if offset is None else offset
        top = max(0, min(top, content - viewport))
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), extent))
        self.canvas.yview_moveto(top / extent)
        if content > viewport:
            if not self.scrollbar.winfo_manager():
                self.scrollbar.pack(side='right', fill='y', before=self.canvas)
        else:
            self.scrollbar.pack_forget()

    def scroll_view(self, *args):
        if self.body.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview(*args)
        self.sync_scroll()

    def mousewheel(self, event):
        if self.body.winfo_reqheight() > self.canvas.winfo_height():
            steps = -int(event.delta if sys.platform == 'darwin' else event.delta / 120)
            if not steps and event.delta:
                steps = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(steps, 'units')
        self.sync_scroll()
        return 'break'

    @staticmethod
    def set_wrap(widget, width):
        if int(widget.cget('wraplength')) != width:
            widget.configure(wraplength=width)

    def resize(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        for child in self.body.winfo_children():
            if isinstance(child, (tk.Label, tk.Button)):
                child.configure(wraplength=max(400, min(780, event.width - 48)))
        self.sync_scroll()

    def clear(self):
        self.after_idle(self.apply_theme)
        for child in self.body.winfo_children():
            child.destroy()
        self.sync_scroll(offset=0)

    def label(self, text, size=13, color=INK):
        w = tk.Label(self.body, text=text, bg=BG, fg=color, font=self.reading_font(size),
                     justify='left', anchor='w', wraplength=max(400, min(780, self.canvas.winfo_width()-48)))
        w.pack(fill='x', pady=8)
        return w

    def button(self, text, command, primary=False, color=None, parent=None):
        normal = color or (ACCENT if primary else SURFACE)
        hover = {'#D0F2DE': '#ADE3C4', '#D8EAFF': '#AECFF7', '#FFE4C7': '#F6CCA0', '#F5D9E8': '#EAB8D2'}.get(color, ACCENT_HOVER if primary else HOVER)
        b = tk.Button(parent or self.body, text=text, command=command, bg=normal,
                      fg='white' if primary else BUTTON_TEXT,
                      activebackground=hover,
                      activeforeground='white' if primary else BUTTON_TEXT,
                      font=self.reading_font(13, 'bold'),
                      highlightcolor=INK, highlightbackground=MUTED, highlightthickness=1, relief='flat', bd=0, padx=20, pady=18,
                      cursor='hand2', anchor='w', justify='left', wraplength=max(400, min(780, self.canvas.winfo_width()-48)))
        b.pack(fill='x', pady=5)
        b.bind('<Enter>', lambda event: b.configure(bg=self.theme_color(hover)) if str(b['state']) == 'normal' else None)
        b.bind('<Leave>', lambda event: b.configure(bg=self.theme_color(normal)) if str(b['state']) == 'normal' else None)
        return b

    def home(self):
        self.navigation.pack_forget()
        self.back_button.pack_forget()
        self.previous_button.configure(state='disabled')
        self.next_button.configure(state='disabled')
        self.back_button.configure(state='disabled')
        self.session = None
        self.clear()
        self.counter.configure(text=f'Rätt: 0/{len(self.bank)}')
        self.label('Vetenskaplig metodkurs Speciallärar- och specialpedagogprogrammet', 26)
        self.label(f'{len(self.bank)} frågor · Fyra svarsalternativ', 14, MUTED)
        self.button(f'Starta quiz – Alla frågor ({len(self.bank)})', lambda: self.start(self.bank), True)
        sources = [
            ('Aasberg-2001.pdf', 'Åsberg (2001)', '#F5D9E8'),
            ('God_forskningssed_VR_2024.pdf', 'God forskningssed', '#D0F2DE'),
            ('Serder_och_Jober_2021_kapitel_1.pdf', 'Serder & Jobér, kapitel 1', '#D8EAFF'),
            ('Undervisningsunderlag_bilder_och_text.pdf', 'Undervisningsunderlag', '#FFE4C7'),
        ]
        for source, title, color in sources:
            questions = [q for q in self.bank if q['source'] == source]
            if questions:
                self.button(f'Starta quiz – {title} ({len(questions)})',
                            lambda questions=questions: self.start(questions), color=color)

        self.label('Frågorna är genererade med AI och kan innehålla fel. Kontrollera svaren mot kursmaterialet.', 11, MUTED)

    def start(self, questions, review=False):
        self.navigation.pack(side='bottom', fill='x', padx=32, pady=(0, 16), before=self.canvas)
        self.back_button.pack(side='right', padx=16)
        self.back_button.configure(state='normal')
        if not review:
            self.selected_questions = list(questions)
        self.session = Session(questions)
        self.show_question()

    def show_question(self):
        self.progress_state = None
        self.feedback_shown = False
        self.clear()
        s, q = self.session, self.session.current
        self.counter.configure(text=f'Rätt: {s.score}/{len(s.questions)}')
        self.question_row = tk.Frame(self.body, bg=BG)
        self.question_row.pack(fill='x', pady=(8, 16))
        self.question_row.columnconfigure(0, weight=1)
        self.quiz_content = tk.Frame(self.question_row, bg=BG)
        self.quiz_content.grid(row=0, column=0, sticky='new', padx=(0, 22))
        self.question_label = tk.Label(self.quiz_content,
            text=q['question'], font=self.reading_font(20, 'bold'),
            bg='#E4EAF8', fg=INK, width=1, anchor='nw', justify='left', wraplength=700, padx=18, pady=16)
        self.question_label.pack(fill='x', pady=(0, 12))
        self.help_panel = tk.Frame(self.question_row, bg='#E5D6F5', padx=12, pady=12)
        self.help_panel.grid(row=0, column=1, sticky='ne')
        self.help_open = False
        self.help_button = tk.Button(self.help_panel, text='Förenkla frågan',
            command=self.toggle_help, bg='#75429D', fg='white',
            activebackground='#5E3183', activeforeground='white',
            font=self.reading_font(12, 'bold'), relief='flat', bd=0,
            padx=16, pady=12, width=21, cursor='hand2', justify='left', anchor='w')
        self.help_button.pack(fill='x')
        self.help_button.bind('<Enter>', lambda event: self.help_button.configure(bg=self.theme_color('#5E3183')))
        self.help_button.bind('<Leave>', lambda event: self.help_button.configure(bg=self.theme_color('#75429D')))
        self.help_text = tk.Label(self.help_panel,
            text=self.readable_paragraphs(q.get('help', 'Välj begreppet som passar i luckan i texten.')),
            bg='#F3EBFC', fg=INK, justify='left', anchor='nw', padx=12, pady=12,
            font=self.reading_font(13), wraplength=220)
        self.quiz_content.bind('<Configure>', lambda event: self.set_wrap(self.question_label, max(280, event.width-36)))
        self.options = []
        self.answer_labels = []
        for i, option in enumerate(q['options']):
            row = tk.Frame(self.quiz_content, bg=SURFACE)
            row.pack(fill='x', pady=5)
            button = self.button(f'{i + 1}.  {option}', lambda i=i: self.choose(i), parent=row)
            button.configure(width=1)
            button.pack_forget()
            status = tk.Label(row, text='', width=11, anchor='e', padx=12,
                              bg=SURFACE, fg=INK, font=self.reading_font(12, 'bold'))
            status.pack(side='right', fill='y')
            button.pack(side='left', fill='both', expand=True)
            button.bind('<Configure>', lambda event, b=button: self.set_wrap(b, max(260, event.width-44)))
            for part in (row, button, status):
                part.bind('<Enter>', lambda event, b=button, r=row, label=status:
                          self.highlight_answer(b, r, label, True))
                part.bind('<Leave>', lambda event, b=button, r=row, label=status:
                          self.highlight_answer(b, r, label, False))
            status.configure(cursor='hand2')
            status.bind('<Button-1>', lambda event, i=i: self.choose(i))
            self.options.append(button)
            self.answer_labels.append(status)
        self.previous_button.configure(state='normal' if s.index > 0 else 'disabled')
        self.next_button.configure(text='Visa resultat' if s.index == len(s.questions)-1 else 'Nästa fråga →',
                                   state='normal')
        self.update_idletasks()
        self.sync_scroll(offset=0)

    def highlight_answer(self, button, row, status, hovered):
        if str(button['state']) != 'normal':
            return
        color = self.theme_color(HOVER if hovered else SURFACE)
        for part in (row, button, status):
            part.configure(bg=color)

    def toggle_help(self):
        self.help_open = not self.help_open
        if self.help_open:
            self.help_text.pack(fill='x', pady=(10, 0), after=self.help_button)
        else:
            self.help_text.pack_forget()
        self.apply_theme()

    def theme_color(self, color):
        mapping = {
            BG.lower(): '#171923', INK.lower(): '#f0f1f7', MUTED.lower(): '#bbc3d5',
            SURFACE.lower(): '#262b3b', HOVER.lower(): '#35304c',
            ACCENT.lower(): '#6955b4', ACCENT_HOVER.lower(): '#58459e',
            TRUE.lower(): '#254c3b', FALSE.lower(): '#633b3e',
            '#d8eaff': '#293e5b', '#ffe4c7': '#51422f',
            '#ade3c4': '#376d52', '#aecff7': '#3d5d86', '#f6cca0': '#7a5835',
            '#176333': '#8cf0ad', '#9d202b': '#ffacb5',
            '#e5d6f5': '#49345f', '#f3ebfc': '#33253f',
            '#75429d': '#8650b0', '#5e3183': '#703f98',
            '#e4eaf8': '#28354e',
            '#f5d9e8': '#512c45', '#eab8d2': '#75405f',
        }
        value = str(color).lower()
        if self.dark_mode:
            return mapping.get(value, color)
        return {v: k for k, v in mapping.items()}.get(value, color)

    def go_to_question(self, index):
        if self.session and 0 <= index < len(self.session.questions):
            self.session.index = index
            self.show_question()

    def update_progress_color(self):
        bar = self.question_progress
        bar.delete('all')
        if not self.session:
            return
        s = self.session
        width = max(1, bar.winfo_width())
        columns = max(1, min(len(s.questions), width // 30))
        rows = (len(s.questions) + columns - 1) // columns
        height = rows * 26
        if int(bar.cget('height')) != height:
            bar.configure(height=height)
        cell_width = width / columns
        for i, question in enumerate(s.questions):
            choice = s.choices.get(i)
            color = ACCENT if choice is None else '#176333' if choice == question['answer'] else '#9d202b'
            x, y = (i % columns) * cell_width, (i // columns) * 26
            tag = f'question_{i}'
            bar.create_rectangle(x + 2, y + 2, x + cell_width - 2, y + 24,
                fill=self.theme_color(color),
                outline=self.theme_color(INK) if i == s.index else self.theme_color(BG),
                width=2 if i == s.index else 1, tags=tag)
            text_color = INK if self.dark_mode and choice is not None else 'white'
            bar.create_text(x + cell_width / 2, y + 13, text=str(i + 1),
                fill=text_color, font=self.reading_font(9, 'bold'), tags=tag)
            bar.tag_bind(tag, '<Button-1>', lambda event, index=i: self.go_to_question(index))

    def apply_theme(self):
        def paint(widget):
            changes = {}
            for key in ('background', 'foreground', 'activebackground', 'activeforeground',
                        'disabledforeground', 'highlightbackground', 'highlightcolor'):
                if key in widget.keys():
                    value = str(widget.cget(key))
                    # White button lettering stays white; white surfaces darken.
                    if 'foreground' in key and value.lower() in ('white', '#ffffff'):
                        continue
                    changes[key] = self.theme_color(value)
            if changes:
                widget.configure(**changes)
            for child in widget.winfo_children():
                paint(child)
        paint(self)
        style = ttk.Style(self)
        background, accent = self.theme_color(BG), self.theme_color(ACCENT)
        style.configure('TProgressbar', background=accent, troughcolor=background,
                        bordercolor=background, lightcolor=accent, darkcolor=accent)
        style.configure('TScrollbar', background=self.theme_color(HOVER), troughcolor=background,
                        bordercolor=background, arrowcolor=self.theme_color(INK),
                        lightcolor=accent, darkcolor=accent)
        style.map('TScrollbar', background=[('active', accent)])

        self.update_progress_color()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_button.configure(text='Dagläge' if self.dark_mode else 'Nattläge')
        self.apply_theme()

    def choose(self, index):
        if not self.session or self.session.index >= len(self.session.questions):
            return
        if self.feedback_shown:
            return
        result = self.session.answer(index, replace=True)
        if result is None:
            return
        self.show_feedback(index)

    def show_feedback(self, index):
        self.after_idle(self.apply_theme)
        self.feedback_shown = True
        result = index == self.session.current['answer']
        self.progress_state = result
        self.update_progress_color()
        self.update_idletasks()
        viewport_top = self.canvas.canvasy(0)
        q = self.session.current
        for i, button in enumerate(self.options):
            color = TRUE if i == q['answer'] else FALSE if i == index else BG
            button.configure(state='disabled', bg=color, disabledforeground=BUTTON_TEXT)
            button.master.configure(bg=color)
            status = self.answer_labels[i]
            status.configure(bg=color,
                text='Rätt svar' if i == q['answer'] else 'Fel svar' if i == index else '',
                fg='#176333' if i == q['answer'] else '#9d202b' if i == index else INK)
        self.counter.configure(text=f'Rätt: {self.session.score}/{len(self.session.questions)}')
        bubble_color = TRUE if result else FALSE
        self.feedback_box = tk.Frame(self.quiz_content, bg=bubble_color, padx=18, pady=14)
        self.feedback_box.pack(fill='x', pady=(14, 6))
        def bubble_label(text, size=13, bold=False):
            label = tk.Label(self.feedback_box, text=text, bg=bubble_color, fg=INK,
                             font=self.reading_font(size, 'bold' if bold else 'normal'),
                             justify='left', anchor='w', wraplength=max(350, self.canvas.winfo_width()-48))
            label.pack(fill='x', pady=5)
            return label
        self.feedback_box.bind('<Configure>', lambda event: [
            child.configure(wraplength=max(300, min(780, event.width-36)))
            for child in self.feedback_box.winfo_children()])
        bubble_label('●  Rätt svar' if result else '●  Fel svar', 17, True)
        if not result:
            bubble_label('Rätt svar: ' + q['options'][q['answer']], bold=True)
        bubble_label('Varför är svaret rätt?', 13, True)
        bubble_label(self.readable_paragraphs(q['explanation']))
        source_names = {
            'Aasberg-2001.pdf': 'Åsberg (2001)',
            'Undervisningsunderlag_bilder_och_text.pdf': 'Undervisningsunderlag',
            'Serder_och_Jober_2021_kapitel_1.pdf': 'Serder & Jobér, kap. 1',
            'God_forskningssed_VR_2024.pdf': 'God forskningssed (2024)',
        }
        source = source_names.get(q['source'], q['source'])
        bubble_label(f'{source} · PDF-sida {q["page"]}', 12)
        self.next_button.configure(state='normal')
        self.apply_theme()
        self.update_idletasks()
        # Preserve reading position while feedback expands the content.
        self.sync_scroll(offset=viewport_top)

    def previous_question(self):
        if self.session and self.session.previous():
            self.show_question()

    def next_question(self):
        if not self.session or self.session.index >= len(self.session.questions):
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
        unanswered = [q for i, q in enumerate(s.questions) if i not in s.choices]
        if unanswered:
            self.label(f'Obesvarade: {len(unanswered)}', 13, MUTED)
            self.button('Svara på obesvarade frågor', lambda: self.start(unanswered, review=True))
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
