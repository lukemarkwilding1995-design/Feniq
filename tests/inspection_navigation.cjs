// Run with: node tests/inspection_navigation.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');
const capture = source.slice(source.indexOf('function captureDraftForm()'),
  source.indexOf('async function saveInspectionDraft()'));
function run(form, initial) {
  const context = vm.createContext({
    ...initial,
    document: {querySelector: () => form},
    FormData: class {constructor(value) {return Object.entries(value.values);}},
  });
  vm.runInContext(capture + '\ncaptureDraftForm();', context);
  return context;
}
let result = run({id:'resultForm', values:{work_done:'Repair notes',
  engineer_notes:'Retain me', approved_by_engineer:'on'}},
  {draft:{approved_by_engineer:true}, diagnosis:{title:'Previous finding'}});
assert.equal(result.draft.engineer_notes, 'Retain me');
assert.equal(result.draft.work_done, 'Repair notes');
assert.equal(result.draft.approved_by_engineer, false);
result = run({id:'detailsForm', values:{module:'new'}},
  {draft:{module:'old', diagnostic_answers:{clearance:5}, approved_by_engineer:true},
    diagnosis:{title:'Old finding'}});
assert.equal(Object.keys(result.draft.diagnostic_answers).length, 0);
assert.equal(result.diagnosis, null);
assert.equal(result.draft.approved_by_engineer, false);
result = run({id:'detailsForm', values:{module:'same'}},
  {draft:{module:'same', diagnostic_answers:{clearance:0}}, diagnosis:null});
assert.equal(result.draft.diagnostic_answers.clearance, 0);
result = run({id:'checksForm', values:{clearance:'0', exhausted:'false', blank:''}},
  {draft:{module:'same'}, catalogue:[{id:'same', checks:[
    {key:'clearance',type:'number'}, {key:'exhausted',type:'bool'},
    {key:'blank',type:'number'}]}]});
assert.equal(result.draft.diagnostic_answers.clearance, 0);
assert.equal(result.draft.diagnostic_answers.exhausted, false);
assert.equal('blank' in result.draft.diagnostic_answers, false);
console.log('Inspection navigation regression checks passed (4 scenarios).');
