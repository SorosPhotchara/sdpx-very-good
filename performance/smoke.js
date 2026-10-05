import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 3,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

const baseUrl = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export default function () {
  const response = http.get(`${baseUrl}/api/health`);
  check(response, {
    'health status 200': (result) => result.status === 200,
    'health response under 500ms': (result) => result.status === 200 && result.timings.duration < 500,
  });
  sleep(1);
}
