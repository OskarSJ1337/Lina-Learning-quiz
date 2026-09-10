'use strict';
const $ = id => document.getElementById(id);
const sources = [
  ['Aasberg-2001.pdf', 'Åsberg (2001)', 'pink'],
  ['God_forskningssed_VR_2024.pdf', 'God forskningssed', 'green'],
  ['Serder_och_Jober_2021_kapitel_1.pdf', 'Serder & Jobér, kapitel 1', 'blue'],
  ['Undervisningsunderlag_bilder_och_text.pdf', 'Undervisningsunderlag', 'peach']
];
let bank, session, selected;
function element(tag, text, className) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (className) e.className = className;
  return e;
}
function button(text, action, className) {
  const b = element('button', text, className);
  b.onclick = action;
  return b;
}
function clear(focus = true) {
  $('content').replaceChildren();
  if (focus) { $('content').focus(); window.scrollTo(0, 0); }
}
function home() {
  session = null;
  clear();
  $('home').hidden = $('navigation').hidden = true;
  $('score').textContent = `Rätt: 0/${bank.length}`;
  const menu = element('div', undefined, 'menu');
  menu.append(button(`Starta quiz – Alla frågor (${bank.length})`, () => start(bank), 'primary'));
  for (const [source, title, color] of sources) {
    const questions = bank.filter(q => q.source === source);
    if (questions.length) menu.append(button(`Starta quiz – ${title} (${questions.length})`, () => start(questions), color));
  }
  $('content').append(element('h1', 'Vetenskaplig metodkurs Speciallärar- och specialpedagogprogrammet'), element('p', `${bank.length} frågor · Fyra svarsalternativ`, 'muted'), menu, element('p', 'Frågorna är genererade med AI och kan innehålla fel. Kontrollera svaren mot kursmaterialet.', 'muted notice'));
}
function start(questions, review = false) {
  if (!review) selected = questions;
  session = new QuizSession(questions);
  $('home').hidden = $('navigation').hidden = false;
  showQuestion();
}
function navigation() {
  $('score').textContent = `Rätt: ${session.score}/${session.questions.length}`;
  $('previous').disabled = session.index === 0;
  $('next').disabled = session.index >= session.questions.length;
  $('next').textContent = session.index === session.questions.length - 1 ? 'Visa resultat' : 'Nästa fråga →';
  $('progress').replaceChildren(...session.questions.map((q, i) => {
    const status = !(i in session.choices) ? '' : session.choices[i] === q.answer ? 'correct' : 'wrong';
    const b = button(String(i + 1), () => { session.index = i; showQuestion(); }, status);
    b.setAttribute('aria-label', `Fråga ${i + 1}: ${status === 'correct' ? 'rätt' : status === 'wrong' ? 'fel' : 'obesvarad'}`);
    b.setAttribute('aria-current', String(i === session.index));
    return b;
  }));
}
function showQuestion(focus = true) {
  const q = session.current;
  clear(focus);
  navigation();
  const layout = element('div', undefined, 'question-layout');
  const quiz = element('section');
  quiz.append(element('h2', q.question, 'question'));
  const options = element('div', undefined, 'options');
  q.options.forEach((option, i) => {
    const answered = session.index in session.choices;
    const status = !answered ? '' : i === q.answer ? 'correct' : i === session.choices[session.index] ? 'wrong' : '';
    const b = button(`${i + 1}.  ${option}`, () => choose(i), `answer ${status}`);
    b.disabled = answered;
    if (status) b.append(element('span', status === 'correct' ? 'Rätt svar' : 'Fel svar'));
    options.append(b);
  });
  quiz.append(options);
  const aside = element('aside');
  const help = element('p', q.help || 'Välj begreppet som passar i luckan i texten.');
  help.hidden = true;
  help.id = 'question-help';
  const toggle = button('Förenkla frågan', () => {
    help.hidden = !help.hidden;
    toggle.setAttribute('aria-expanded', String(!help.hidden));
  });
  toggle.setAttribute('aria-expanded', 'false');
  toggle.setAttribute('aria-controls', help.id);
  aside.append(toggle, help);
  const feedback = element('div');
  feedback.setAttribute('aria-live', 'polite');
  quiz.append(feedback);
  layout.append(quiz, aside);
  $('content').append(layout);
  if (session.index in session.choices) {
    const correct = session.choices[session.index] === q.answer;
    feedback.className = `feedback ${correct ? 'correct' : 'wrong'}`;
    feedback.append(element('h3', correct ? '● Rätt svar' : '● Fel svar'));
    if (!correct) feedback.append(element('p', `Rätt svar: ${q.options[q.answer]}`));
    feedback.append(element('strong', 'Varför är svaret rätt?'), element('p', q.explanation), element('p', `${sources.find(s => s[0] === q.source)?.[1] || q.source} · PDF-sida ${q.page}`, 'notice'));
  }
}
function choose(i) { if (session?.answer(i)) { showQuestion(false); $('next').focus({preventScroll:true}); } }
function finish() {
  clear();
  navigation();
  const menu = element('div', undefined, 'menu');
  if (session.unanswered.length) menu.append(button(`Svara på obesvarade frågor (${session.unanswered.length})`, () => start(session.unanswered, true)));
  if (session.missed.length) menu.append(button(`Öva på missade frågor (${session.missed.length})`, () => start(session.missed, true), 'primary'));
  menu.append(button('Nytt test', () => start(selected), 'primary'), button('Startsida', home));
  $('content').append(element('h1', 'Resultat'), element('h2', `${session.score} rätt av ${session.questions.length} · ${Math.round(session.score / session.questions.length * 100)}%`), element('p', `Obesvarade: ${session.unanswered.length}`, 'muted'), menu);
}
$('home').onclick = home;
$('previous').onclick = () => { if (session && session.index > 0) { session.index--; showQuestion(); } };
$('next').onclick = () => { if (session && session.current) { session.index++; session.current ? showQuestion() : finish(); } };
function theme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  $('theme').textContent = dark ? 'Dagläge' : 'Nattläge';
}
try { theme(localStorage.getItem('lina-theme') === 'dark'); } catch (_) { theme(false); }
$('theme').onclick = () => {
  theme(document.documentElement.dataset.theme !== 'dark');
  try { localStorage.setItem('lina-theme', document.documentElement.dataset.theme); } catch (_) {}
};
document.addEventListener('keydown', event => {
  if (!event.ctrlKey && !event.metaKey && !event.altKey && /^[1-4]$/.test(event.key)) choose(Number(event.key) - 1);
});
fetch('questions.json').then(response => {
  if (!response.ok) throw new Error('Frågebanken kunde inte hämtas.');
  return response.json();
}).then(data => { bank = data; home(); }).catch(() => {
  clear(false);
  $('content').append(element('h1', 'Kunde inte läsa frågorna'), element('p', 'Kontrollera anslutningen och försök igen.'), button('Försök igen', () => location.reload(), 'primary'));
});
