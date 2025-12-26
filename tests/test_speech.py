def test_speak_test_creates_wav(client_and_headers):
  client, headers, tmp_path = client_and_headers

  r = client.get("/speak/test", headers=headers)
  assert r.status_code == 200
  data = r.json()
  assert data.get("ok") is True

  wavs = list(tmp_path.glob("*.wav"))
  assert len(wavs) >= 1
  assert wavs[0].stat().st_size > 0


def test_speak_last_returns_latest_entry(client_and_headers):
  client, headers, tmp_path = client_and_headers

  # Create at least one file
  client.get("/speak/test", headers=headers)

  r = client.get("/speak/last", headers=headers)
  assert r.status_code == 200
  data = r.json()
  assert data["name"].endswith(".wav")
  assert data["size"] > 0


def test_speak_play_serves_audio_bytes(client_and_headers):
  client, headers, tmp_path = client_and_headers

  # Create one file
  t = client.get("/speak/test", headers=headers)
  assert t.status_code == 200
  file_path = t.json()["file"]
  speech_id = file_path.split("/")[-1].replace(".wav", "")

  r = client.get(f"/speak/play/{speech_id}", headers=headers)
  assert r.status_code == 200
  assert r.headers["content-type"].startswith("audio/x-wav")
  assert len(r.content) > 0