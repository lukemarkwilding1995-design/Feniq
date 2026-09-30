const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/app.js', 'utf8');
let unload, calls = 0, warnings = 0;
const context = vm.createContext({
  window:{addEventListener:(name, handler) => {unload = handler;}},
  openModal:() => {warnings++;},
  action:() => {calls++;},
});
vm.runInContext(source.slice(source.indexOf('let inspectionDirty'),
  source.indexOf('const outcomes')), context);
vm.runInContext('guardInspectionExit(action)', context);
assert.equal(calls, 1);
let prevented = false;
unload({preventDefault:() => {prevented = true;}});
assert.equal(prevented, false);
vm.runInContext('inspectionDirty = true; guardInspectionExit(action)', context);
assert.equal(calls, 1, 'Dirty edits must block navigation');
assert.equal(warnings, 1);
const event = {preventDefault:() => {prevented = true;}};
unload(event);
assert.equal(prevented, true);
assert.equal(event.returnValue, '');
vm.runInContext('inspectionDirty = false; pendingInspectionExit()', context);
assert.equal(calls, 2);
prevented = false;
unload({preventDefault:() => {prevented = true;}});
assert.equal(prevented, false, 'Successful save/explicit leave clears unload warning');
console.log('Inspection exit guard regression checks passed.');
