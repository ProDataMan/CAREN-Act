// Merges an accepted bill comment (GitHub issue) into website/bill.json.
// Runs from .github/workflows/bill-comments.yml via actions/github-script.
const fs = require('fs');
const { execFileSync } = require('child_process');

module.exports = async ({ github, context, core }) => {
  const issue = context.payload.issue;
  const sender = context.payload.sender.login;
  const say = body => github.rest.issues.createComment({ ...context.repo, issue_number: issue.number, body });

  // Only people with write access may accept (labels can only be added by triagers+, this double-checks).
  const { data: perm } = await github.rest.repos.getCollaboratorPermissionLevel({ ...context.repo, username: sender });
  if (!['admin', 'maintain', 'write'].includes(perm.permission)) {
    await github.rest.issues.removeLabel({ ...context.repo, issue_number: issue.number, name: 'accepted' }).catch(() => {});
    core.setFailed(`${sender} lacks write permission`);
    return;
  }

  const m = (issue.body || '').match(/```json\n(\{.*\})\n```/);
  if (!m) { await say('⚠️ Could not find the comment data block, so nothing was merged.'); return; }
  let data;
  try { data = JSON.parse(m[1]); } catch (e) { await say('⚠️ The comment data block is not valid JSON, so nothing was merged.'); return; }

  const path = 'website/bill.json';
  const bill = JSON.parse(fs.readFileSync(path, 'utf8'));
  let para = null;
  for (const s of bill.sections) for (const p of s.paragraphs) if (p.id === String(data.para)) para = p;
  if (!para) { await say(`⚠️ Paragraph ${data.para} no longer exists, so nothing was merged.`); return; }

  para.accepted = para.accepted || [];
  if (para.accepted.includes(issue.number)) { core.info('Already applied'); return; }

  const proposed = typeof data.proposed === 'string' ? data.proposed.trim() : '';
  if (proposed.length > 10000) { await say('⚠️ Proposed text is too long to merge automatically.'); return; }

  let note = '';
  para.accepted.push(issue.number);
  if (proposed && proposed !== para.text) {
    if (data.rev !== para.rev) {
      note = `\n\nNote: this suggestion was written against revision ${data.rev} of the paragraph, but it was at revision ${para.rev}. The accepted text replaced the newer wording. Please review the result.`;
    }
    para.history = para.history || [];
    para.history.push({ rev: para.rev, text: para.text, replaced_by_issue: issue.number, replaced_at: new Date().toISOString() });
    para.rev += 1;
    para.text = proposed;
    bill.rev = (bill.rev || 0) + 1;
  }
  bill.updated = new Date().toISOString().slice(0, 10);
  fs.writeFileSync(path, JSON.stringify(bill, null, 2) + '\n');

  const git = (...a) => execFileSync('git', a, { stdio: 'inherit' });
  git('config', 'user.name', 'github-actions[bot]');
  git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com');
  git('add', path);
  git('commit', '-m', `Accept bill comment #${issue.number} from @${issue.user.login} (paragraph ${para.id})`);
  git('pull', '--rebase', '--quiet');
  git('push');

  await say(proposed
    ? `⭐ Accepted by @${sender} and merged into the draft bill (paragraph ${para.id}, now revision ${para.rev}). Thank you @${issue.user.login}!${note}`
    : `⭐ Accepted by @${sender}. Thank you @${issue.user.login}!`);
  await github.rest.issues.update({ ...context.repo, issue_number: issue.number, state: 'closed', state_reason: 'completed' });
};
