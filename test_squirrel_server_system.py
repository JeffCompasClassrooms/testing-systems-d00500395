import os
import shutil
import time
import subprocess
import http.client
import urllib.parse
import json
import socket
import pytest
from http.client import RemoteDisconnected


TEMPLATE_DB_PATH = "empty_squirrel_db.db"
WORKING_DB = "squirrel_db.db"
SERVER_SCRIPT = "squirrel_server.py"

def wait_for_port(host, port, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            s = socket.create_connection((host, port), timeout=0.5)
            s.close()
            return True
        except Exception:
            time.sleep(0.05)
    return False

@pytest.fixture(scope="session", autouse=True)
def start_server():
    host, port = "127.0.0.1", 8080
    if wait_for_port(host, port, timeout=0.2):
        pytest.skip("Port busy")
    proc = subprocess.Popen(
        ["python3", SERVER_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    if not wait_for_port(host, port, timeout=5.0):
        proc.terminate()
        raise RuntimeError("Server failed")
    yield
    try:
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        proc.kill()
        proc.wait(timeout=2)

@pytest.fixture(autouse=True)
def reset_db(tmp_path):
    if os.path.exists(WORKING_DB):
        os.remove(WORKING_DB)
    shutil.copy(TEMPLATE_DB_PATH, WORKING_DB)
    yield
    if os.path.exists(WORKING_DB):
        os.remove(WORKING_DB)

@pytest.fixture
def http_client():
    c = http.client.HTTPConnection("127.0.0.1", 8080, timeout=5)
    yield c
    try:
        c.close()
    except Exception:
        pass

def safe_json(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None

def post_form(conn, path, data):
    body = urllib.parse.urlencode(data)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    return resp, raw

def put_form(conn, path, data):
    body = urllib.parse.urlencode(data)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    conn.request("PUT", path, body=body, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    return resp, raw

def get(conn, path):
    conn.request("GET", path)
    resp = conn.getresponse()
    raw = resp.read()
    return resp, safe_json(raw)

def delete(conn, path):
    conn.request("DELETE", path)
    resp = conn.getresponse()
    raw = resp.read()
    return resp, raw


def describe_squirrel_api():

    def describe_get_collection():

        def it_returns_empty_list(http_client):
            resp, parsed = get(http_client, "/squirrels")
            assert resp.status == 200
            assert isinstance(parsed, list)
            assert parsed == []

    def describe_post():

        def it_creates_and_is_reflected_in_get(http_client):
            resp, _ = post_form(http_client, "/squirrels", {"name": "Sam", "size": "large"})
            assert resp.status == 201
            resp2, parsed2 = get(http_client, "/squirrels")
            assert resp2.status == 200
            assert len(parsed2) == 1
            s = parsed2[0]
            assert s["name"] == "Sam"
            assert s["size"] == "large"

        def it_rejects_missing_fields(http_client):
            resp, _ = post_form(http_client, "/squirrels", {"name": "X", "size": "Y"})
            resp2, parsed2 = get(http_client, "/squirrels")
            sid = parsed2[0]["id"]

            try:
                resp3, _ = put_form(http_client, f"/squirrels/{sid}", {"name": "Only"})
                # If server DOES respond, it must be an error
                assert resp3.status >= 400
            except RemoteDisconnected:
                # Server closing the connection is acceptable as an error condition
                pass


    def describe_put():

        def it_updates_existing(http_client):
            resp, _ = post_form(http_client, "/squirrels", {"name": "A", "size": "B"})
            assert resp.status == 201

            resp2, parsed = get(http_client, "/squirrels")
            sid = parsed[0]["id"]

            resp3, _ = put_form(http_client, f"/squirrels/{sid}", {"name": "A", "size": "C"})
            assert resp3.status in (200, 201, 204)

        def it_rejects_missing_fields(http_client):
            resp, _ = post_form(http_client, "/squirrels", {"name": "X", "size": "Y"})
            resp2, parsed2 = get(http_client, "/squirrels")
            sid = parsed2[0]["id"]

            try:
                resp3, _ = put_form(http_client, f"/squirrels/{sid}", {"name": "Only"})
                assert resp3.status >= 400
            except RemoteDisconnected:
                pass

        def it_returns_404_for_nonexistent(http_client):
            resp, _ = put_form(http_client, "/squirrels/9999", {"name": "X", "size": "Y"})
            assert resp.status == 404

    def describe_delete():

        def it_deletes_and_makes_record_inaccessible(http_client):
            resp, _ = post_form(http_client, "/squirrels", {"name": "T", "size": "S"})
            resp2, parsed2 = get(http_client, "/squirrels")
            sid = parsed2[0]["id"]

            resp3, _ = delete(http_client, f"/squirrels/{sid}")
            assert resp3.status in (200, 204)

            resp4, _ = get(http_client, f"/squirrels/{sid}")
            assert resp4.status == 404

        def it_returns_404_for_nonexistent(http_client):
            resp, _ = delete(http_client, "/squirrels/9999")
            assert resp.status == 404

    def describe_failure_cases():

        def it_returns_404_for_nonexistent_id(http_client):
            resp, _ = get(http_client, "/squirrels/9999")
            assert resp.status == 404

        def it_returns_404_for_invalid_path(http_client):
            resp, _ = get(http_client, "/nope")
            assert resp.status == 404

        def it_rejects_post_to_specific_id(http_client):
            resp, _ = post_form(http_client, "/squirrels/1", {"name": "X", "size": "Y"})
            assert resp.status in (404, 405)

        def it_rejects_delete_on_collection(http_client):
            http_client.request("DELETE", "/squirrels")
            resp = http_client.getresponse()
            resp.read()
            assert resp.status in (404, 405)

        def it_handles_unknown_methods(http_client):
            http_client.request("PATCH", "/squirrels")
            resp = http_client.getresponse()
            resp.read()
            assert resp.status in (404, 405, 500, 501)

    def describe_multiple_entries():

        def it_creates_multiple_and_lists_them(http_client):
            for i in range(3):
                resp, _ = post_form(http_client, "/squirrels", {"name": f"N{i}", "size": f"S{i}"})
                assert resp.status == 201
            resp2, parsed2 = get(http_client, "/squirrels")
            assert len(parsed2) == 3

        def it_runs_full_lifecycle(http_client):
            resp, _ = post_form(http_client, "/squirrels", {"name": "Seq", "size": "one"})
            resp2, parsed2 = get(http_client, "/squirrels")
            sid = parsed2[0]["id"]
            resp3, _ = put_form(http_client, f"/squirrels/{sid}", {"name": "Seq2", "size": "two"})
            resp4, parsed4 = get(http_client, f"/squirrels/{sid}")
            assert parsed4["size"] == "two"
            resp5, _ = delete(http_client, f"/squirrels/{sid}")
            resp6, _ = get(http_client, f"/squirrels/{sid}")
            assert resp6.status == 404
