import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
const baseUrl = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const token = __ENV.AUTH_TOKEN;
if (!token) throw new Error('Set AUTH_TOKEN for a dedicated test student');
const headers = { Authorization: `Bearer ${token}` };
const errors = new Rate('journey_errors');
const draftLatency = new Trend('draft_latency', true);
export const options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '1m', target: 10 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    journey_errors: ['rate<0.05'],
    'http_req_duration{name:evaluation}': ['p(95)<500'],
  },
};
export default function () {
  group('Find assignment', () => {
    const me = http.get(`${baseUrl}/api/me`, { headers, tags: { name: 'me' } });
    const classroomId = me.status === 200 ? me.json().classroom_ids?.[0] : null;
    check(me, { 'student has a classroom': () => Boolean(classroomId) });
    if (!classroomId) { errors.add(true); sleep(1); return; }
    sleep(1);
    const list = http.get(`${baseUrl}/api/assignments/?classroom_id=${classroomId}`, {
      headers, tags: { name: 'assignments' },
    });
    const assignmentId = list.status === 200 ? list.json()?.[0]?.id : null;
    check(list, { 'student sees an assignment': () => Boolean(assignmentId) });
    if (!assignmentId) { errors.add(true); sleep(1); return; }
    sleep(1);
    const page = http.get(`${baseUrl}/api/assignments/${assignmentId}/evaluation/group`, {
      headers, tags: { name: 'evaluation' },
    });
    const pairId = page.status === 200 ? page.json()?.pairs?.[0]?.id : null;
    check(page, { 'evaluation has a pair': () => Boolean(pairId) });
    errors.add(!pairId);
    if (!pairId) { sleep(1); return; }
    sleep(1);
    // Enable writes only for a disposable local or staging test account.
    if (__ENV.ENABLE_DRAFT_WRITE === '1') {
      const draft = http.put(`${baseUrl}/api/assignments/${assignmentId}/evaluation/group/draft`,
        JSON.stringify({ changes: [{ pair_id: pairId, choice: 3 }] }),
        { headers: { ...headers, 'Content-Type': 'application/json' }, tags: { name: 'draft' } });
      draftLatency.add(draft.timings.duration);
      check(draft, { 'draft saved': (response) => response.status === 200 });
      errors.add(draft.status !== 200);
      sleep(1);
    }
  });
}
