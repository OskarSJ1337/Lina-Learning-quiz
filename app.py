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
        self.font_scale = 0
        self.reading_fonts = {}
        self.title('Linas coola quiz')
        self.geometry('960x820')
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
        self.option_add('*Font', self.reading_font(14))
        self.bank = validate(json.loads((BASE / 'questions.json').read_text(encoding='utf-8')))
        self.session = None
        self.importing = False
        self.header = tk.Frame(self, bg=BG)
        self.header.pack(fill='x', padx=32, pady=(24, 10))
        tk.Label(self.header, text='Linas coola quiz', font=self.reading_font(18, 'bold'), bg=BG, fg=INK).pack(side='top', anchor='w', pady=(0, 10))
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
        self.text_controls = tk.Frame(self, bg=BG)
        self.text_controls.pack(fill='x', padx=32, pady=(0, 10))
        tk.Label(self.text_controls, text='Textstorlek', bg=BG, fg=INK,
                 font=self.reading_font(14)).pack(side='left')
        self.smaller_button = tk.Button(self.text_controls, text='A−', command=lambda: self.change_text_size(-2),
            bg=SURFACE, fg=INK, font=self.reading_font(14), padx=12, pady=5, state='disabled')
        self.smaller_button.pack(side='left', padx=(12, 6))
        self.larger_button = tk.Button(self.text_controls, text='A+', command=lambda: self.change_text_size(2),
            bg=SURFACE, fg=INK, font=self.reading_font(14), padx=12, pady=5)
        self.larger_button.pack(side='left')
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

    def reading_font(self, size, weight='normal'):
        size = max(14, size)
        key = (size, weight)
        if key not in self.reading_fonts:
            self.reading_fonts[key] = tkfont.Font(self, family='Verdana', size=size+self.font_scale, weight=weight)
        return self.reading_fonts[key]

    def change_text_size(self, delta):
        self.font_scale = max(0, min(6, self.font_scale + delta))
        for (size, weight), font in self.reading_fonts.items():
            font.configure(size=size+self.font_scale)
        self.smaller_button.configure(state='disabled' if self.font_scale == 0 else 'normal')
        self.larger_button.configure(state='disabled' if self.font_scale == 6 else 'normal')

    @staticmethod
    def readable_paragraphs(text):
        # Break sentences into shorter reading blocks without changing wording.
        return re.sub(r'(?<=[.!?]) +(?=[A-ZÅÄÖ])', '\n\n', text)

    def resize(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        for child in self.body.winfo_children():
            if isinstance(child, (tk.Label, tk.Button)):
                child.configure(wraplength=max(400, min(780, event.width - 48)))

    def clear(self):
        self.after_idle(self.apply_theme)
        for child in self.body.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)

    def label(self, text, size=13, color=INK):
        w = tk.Label(self.body, text=text, bg=BG, fg=color, font=self.reading_font(size),
                     justify='left', anchor='w', wraplength=max(400, min(780, self.canvas.winfo_width()-48)))
        w.pack(fill='x', pady=8)
        return w

    def button(self, text, command, primary=False, color=None):
        normal = color or (ACCENT if primary else SURFACE)
        hover = color or (ACCENT_HOVER if primary else HOVER)
        b = tk.Button(self.body, text=text, command=command, bg=normal,
                      fg='white' if primary else BUTTON_TEXT,
                      activebackground=hover,
                      activeforeground='white' if primary else BUTTON_TEXT,
                      font=self.reading_font(14, 'bold' if primary else 'normal'),
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
        self.navigation.pack(side='bottom', fill='x', padx=32, pady=(0, 16), before=self.canvas)
        self.back_button.pack(side='right', padx=16)
        self.back_button.configure(state='normal')
        if not review:
            self.selected_questions = list(questions)
        self.session = Session(questions)
        self.show_question()

    def show_question(self):
        self.feedback_shown = False
        self.clear()
        s, q = self.session, self.session.current
        self.counter.configure(text=f'Rätt: {s.score}/{len(s.questions)}')
        self.label(f'Fråga {s.index + 1} av {len(s.questions)}', 13, MUTED)
        ttk.Progressbar(self.body, maximum=len(s.questions), value=s.index).pack(fill='x', pady=(0, 18))
        self.label(self.readable_paragraphs(q['question']), 20)
        self.help_open = False
        self.help_button = self.button('Vad betyder frågan?', self.toggle_help)
        self.help_button.configure(font=self.reading_font(11), pady=8)
        self.help_text = tk.Label(self.body, text=self.readable_paragraphs(q.get('help', 'Välj begreppet som passar i luckan i texten.')),
            bg=HOVER, fg=INK, justify='left', anchor='w', padx=14, pady=12,
            wraplength=max(400, min(780, self.canvas.winfo_width()-48)))
        self.options = [self.button(f'{i + 1}.  {option}', lambda i=i: self.choose(i)) for i, option in enumerate(q['options'])]
        self.previous_button.configure(state='normal' if s.index > 0 else 'disabled')
        self.next_button.configure(text='Visa resultat' if s.index == len(s.questions)-1 else 'Nästa fråga →',
                                   state='normal')
        self.update_idletasks()
        self.canvas.yview_moveto(0)

    def toggle_help(self):
        self.help_open = not self.help_open
        if self.help_open:
            self.help_text.pack(fill='x', pady=(0, 10), after=self.help_button)
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
        }
        value = str(color).lower()
        if self.dark_mode:
            return mapping.get(value, color)
        return {v: k for k, v in mapping.items()}.get(value, color)

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
        self.update_idletasks()
        viewport_top = self.canvas.canvasy(0)
        q = self.session.current
        for i, button in enumerate(self.options):
            color = TRUE if i == q['answer'] else FALSE if i == index else BG
            button.configure(state='disabled', bg=color, disabledforeground=BUTTON_TEXT)
        self.counter.configure(text=f'Rätt: {self.session.score}/{len(self.session.questions)}')
        bubble_color = TRUE if result else FALSE
        self.feedback_box = tk.Frame(self.body, bg=bubble_color, padx=18, pady=14)
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
        bubble_label(self.readable_paragraphs(q['explanation']))
        source_names = {
            'Undervisningsunderlag_bilder_och_text.pdf': 'Undervisningsunderlag',
            'Serder_och_Jober_2021_kapitel_1.pdf': 'Serder & Jobér, kap. 1',
            'God_forskningssed_VR_2024.pdf': 'God forskningssed (2024)',
        }
        source = source_names.get(q['source'], q['source'])
        bubble_label(f'{source} · PDF-sida {q["page"]}', 12)
        self.next_button.configure(state='normal')
        self.apply_theme()
        self.update_idletasks()
        # Keep the same pixel offset as feedback increases the scroll region.
        bounds = self.canvas.bbox('all')
        if bounds and bounds[3] > bounds[1]:
            self.canvas.yview_moveto((viewport_top - bounds[1]) / (bounds[3] - bounds[1]))

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
