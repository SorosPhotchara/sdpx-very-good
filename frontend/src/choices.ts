// Six-point forced choice (PRD D1, FR-EVAL-03, §9.1). There is deliberately no
// "equal" option: a midpoint invites central-tendency bias, so the scale makes
// the evaluator pick a side. Index + 1 is the choice value the API stores, and
// this order must stay in step with POINTS in backend/app/scoring.py.
export const choices = [
  'Left much better', 'Left better', 'Left slightly better',
  'Right slightly better', 'Right better', 'Right much better',
]

// Left/right points each option awards, shown in the raw answers table.
export const choicePoints = ['1/0', '.8/.2', '.6/.4', '.4/.6', '.2/.8', '0/1']
