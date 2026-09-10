'use strict';
// Independent session state: every browser visitor has their own quiz.
class QuizSession {
  constructor(bank, random = Math.random) {
    if (!bank.length) throw new Error('Frågebanken är tom.');
    const shuffle = items => {
      for (let i = items.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [items[i], items[j]] = [items[j], items[i]];
      }
      return items;
    };
    this.questions = shuffle(bank.map(q => {
      const order = shuffle([0, 1, 2, 3]);
      return {...q, options: order.map(i => q.options[i]), answer: order.indexOf(q.answer)};
    }));
    this.choices = {};
    this.index = 0;
  }
  get current() { return this.questions[this.index]; }
  get score() { return this.questions.filter((q, i) => this.choices[i] === q.answer).length; }
  get missed() { return this.questions.filter((q, i) => i in this.choices && this.choices[i] !== q.answer); }
  get unanswered() { return this.questions.filter((q, i) => !(i in this.choices)); }
  answer(choice) {
    if (!this.current || !Number.isInteger(choice) || choice < 0 || choice > 3 || this.index in this.choices) return false;
    this.choices[this.index] = choice;
    return true;
  }
}
if (typeof module !== 'undefined') module.exports = QuizSession;
