import random
import unittest
from app import Session, validate
import json
from pathlib import Path

class QuizTests(unittest.TestCase):
 def setUp(self):
  self.bank=json.loads(Path('questions.json').read_text(encoding='utf-8'))
 def test_shuffled_answers_and_score(self):
  for seed in range(15):
   s=Session(self.bank, random.Random(seed))
   for n in range(len(self.bank)):
    q=s.current
    original=next(x for x in self.bank if x['question']==q['question'])
    self.assertEqual(q['options'][q['answer']],original['options'][original['answer']])
    self.assertFalse(s.advance())
    self.assertTrue(s.answer(q['answer']))
    self.assertIsNone(s.answer(q['answer']))
    self.assertEqual(s.score,n+1)
    self.assertEqual(s.advance(),n+1<len(self.bank))
 def test_wrong_answer_and_retry(self):
  s=Session(self.bank)
  self.assertFalse(s.answer((s.current['answer']+1)%4))
  self.assertEqual(s.score,0)
  retry=Session(s.missed)
  self.assertTrue(retry.answer(retry.current['answer']))
  self.assertEqual(retry.score,1)
 def test_bank(self):
  validate(self.bank)
  self.assertEqual(len({q['source'] for q in self.bank}),3)
  self.assertEqual(len({q['question'] for q in self.bank}),len(self.bank))

if __name__=='__main__': unittest.main()
