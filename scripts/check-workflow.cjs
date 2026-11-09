const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const workflow = JSON.parse(fs.readFileSync(path.join(__dirname, '../workflows/client-briefing.json'), 'utf8'));
assert.equal(workflow.active, false);
const nodes = new Map(workflow.nodes.map(node => [node.name, node]));
for (const [from, connections] of Object.entries(workflow.connections)) {
  assert(nodes.has(from));
  for (const output of connections.main.flat()) assert(nodes.has(output.node));
}
const code = nodes.get('Prepare human review packet').parameters.jsCode;
function execute(input) {
  const sandbox = {$input: {first: () => ({json: input})}};
  return JSON.parse(JSON.stringify(vm.runInNewContext(`(function(){${code}\n})()`, sandbox, {timeout: 1000})));
}
const packet = execute({statusCode: 200, body: {request_id: 'demo', status: 'draft_pending_review', report_markdown: 'Mock data', follow_up_draft: 'DRAFT', replayed: false}})[0].json;
assert.equal(packet.response.review_required, true);
assert.equal(packet.response.replayed, false);
const replay = execute({statusCode: 200, body: {...packet.response, replayed: true}})[0].json;
assert.equal(replay.response.replayed, true);
const invalid = execute({statusCode: 422, body: {error: 'invalid_request'}})[0].json;
assert.equal(invalid.statusCode, 422);
assert.equal(invalid.response.error, 'invalid_request');
assert.throws(() => execute({statusCode: 200, body: {}}));
assert(!workflow.nodes.some(node => /sendEmail|gmail|outlook/i.test(node.type)));
console.log('Workflow graph and review JavaScript checks passed (not an n8n runtime test).');
