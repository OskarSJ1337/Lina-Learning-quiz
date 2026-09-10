const assert = require('node:assert/strict');
const fs = require('node:fs');
const QuizSession = require('./quiz.js');
const bank = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../questions.json'), 'utf8'));
assert.equal(bank.length, 98);
assert.equal(new Set(bank.map(q => q.source)).size, 4);
for (let run = 0; run < 20; run++) {
  const s = new QuizSession(bank);
  for (const q of s.questions) {
    const original = bank.find(item => item.question === q.question);
    assert.equal(q.options[q.answer], original.options[original.answer]);
    assert.equal(new Set(q.options).size, 4);
    assert.equal(s.answer(q.answer), true);
    assert.equal(s.answer((q.answer + 1) % 4), false);
    s.index++;
  }
  assert.equal(s.score, 98);
  assert.equal(s.unanswered.length, 0);
  assert.equal(s.answer(0), false);
}
const s = new QuizSession(bank.slice(0, 3));
assert.equal(s.answer(-1), false);
s.answer((s.current.answer + 1) % 4);
s.index = 2;
s.answer(s.current.answer);
assert.equal(s.score, 1);
assert.equal(s.missed.length, 1);
assert.equal(s.unanswered.length, 1);
s.index = 0;
assert.equal(s.answer(s.current.answer), false);
const retry = new QuizSession(s.missed);
retry.answer(retry.current.answer);
assert.equal(retry.score, 1);
assert.equal(new QuizSession(bank).score, 0);
assert.throws(() => new QuizSession([]));
console.log('Quiz tests passed: question bank, shuffled answers, scores, skip, revisit, retry, visitor isolation.');
