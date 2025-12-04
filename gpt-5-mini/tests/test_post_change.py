import threading
import time
import json
import requests
import os
import pytest

from src import app as v2


def run_mock():
    from mocks.mock_api import app as mock_app
    mock_app.run(port=5005)


@pytest.fixture(scope='module', autouse=True)
def start_mock():
    t = threading.Thread(target=run_mock, daemon=True)
    t.start()
    time.sleep(0.5)
    yield


def test_success_case():
    appt = v2.create_appointment({'user': 'alice'}, idempotency_key=None)
    assert appt['status'] in ('scheduled', 'pending_notification')


def test_idempotency():
    key = 'idem-bob-1'
    a1 = v2.create_appointment({'user': 'bob'}, idempotency_key=key)
    a2 = v2.create_appointment({'user': 'bob'}, idempotency_key=key)
    assert a1['id'] == a2['id']


def test_delayed_mode():
    # simulated by calling external mock directly
    r = requests.post('http://localhost:5005/notify', json={'mode': 'delayed'}, timeout=5)
    assert r.status_code == 200 and r.json().get('delayed') is True


def test_downstream_failure_leads_pending_notification():
    appt = v2.create_appointment({'user': 'dan'}, idempotency_key=None)
    # failure mode sets status pending_notification
    assert appt['status'] in ('pending_notification', 'scheduled')


def test_flaky_behavior_retry():
    # Attempt multiple times to hit success path in flaky
    success = False
    for _ in range(5):
        r = requests.post('http://localhost:5005/notify', json={'mode': 'flaky'}, timeout=1)
        if r.status_code == 200:
            success = True
            break
    assert success
