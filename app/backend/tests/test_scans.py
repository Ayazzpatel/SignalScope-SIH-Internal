import io
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import func, select, update

from signalscope.core.config import get_settings
from signalscope.db import utcnow
from signalscope.main import create_app
from signalscope.models import Scan
from signalscope.services.fingerprint import hamming, perceptual_hash
from signalscope.services.retention import run_retention

AUTH = "/api/v1/auth"
SCANS = "/api/v1/scans"
PASSWORD = "Correct-Horse-42"


# ---------------------------------------------------------------- helpers


def scene(seed: int, size: tuple[int, int] = (320, 240)) -> Image.Image:
    """A structured test image (gradient + shapes): realistic enough for perceptual hashing."""
    img = Image.linear_gradient("L").resize(size).convert("RGB")
    draw = ImageDraw.Draw(img)
    for i in range(4):
        x, y = (seed * 53 + i * 71) % size[0], (seed * 31 + i * 47) % size[1]
        colour = ((seed * 40 + i * 60) % 256, (seed * 90) % 256, (i * 80) % 256)
        draw.ellipse([x - 40, y - 30, x + 40, y + 30], fill=colour)
        draw.rectangle(
            [(x * 3) % size[0], (y * 2) % size[1], (x * 3) % size[0] + 50, (y * 2) % size[1] + 35],
            fill=colour[::-1],
        )
    return img


def jpeg(img: Image.Image, **kwargs) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=kwargs.pop("quality", 92), **kwargs)
    return buffer.getvalue()


def signup(client, email="alice@example.com"):
    client.cookies.clear()
    response = client.post(
        f"{AUTH}/signup", json={"email": email, "password": PASSWORD, "display_name": "User"}
    )
    assert response.status_code == 201, response.text
    return response.json()["user"]


def analyze(client, data: bytes, *, save_image: bool | None = None, name: str = "photo.jpg"):
    form = {} if save_image is None else {"save_image": str(save_image).lower()}
    response = client.post("/api/v1/analyze", files={"file": (name, data, "image/jpeg")}, data=form)
    assert response.status_code == 200, response.text
    return response.json()


def db_call(client, fn):
    async def run():
        async with client.app.state.sessionmaker() as db:
            return await fn(db)

    return client.portal.call(run)


def count_scans(client) -> int:
    async def q(db):
        return await db.scalar(select(func.count()).select_from(Scan))

    return db_call(client, q)


def stored_files(client) -> list:
    return [p for p in client.app.state.storage._root.rglob("*") if p.is_file()]


# ---------------------------------------------------------------- fingerprint


def test_phash_tolerates_recompression_but_separates_different_images():
    original = scene(1)
    recompressed = Image.open(io.BytesIO(jpeg(original.resize((256, 192)), quality=55)))

    assert hamming(perceptual_hash(original), perceptual_hash(recompressed)) <= 8
    assert hamming(perceptual_hash(original), perceptual_hash(scene(7))) > 8


# ---------------------------------------------------------------- what gets stored


def test_guest_scans_leave_no_trace(client):
    body = analyze(client, jpeg(scene(1)))

    assert body["scan"] is None
    assert count_scans(client) == 0
    assert stored_files(client) == []


def test_signed_in_scan_saves_result_but_not_image_by_default(client):
    signup(client)

    body = analyze(client, jpeg(scene(1)), name="C:\\fakepath\\mug.jpg")

    assert body["scan"]["image_saved"] is False
    items = client.get(SCANS).json()["items"]
    assert len(items) == 1 and items[0]["image_url"] is None
    assert items[0]["filename"] == "mug.jpg"  # path parts stripped
    detail = client.get(f"{SCANS}/{body['scan']['id']}").json()
    assert detail["verdict"] == body["verdict"]
    heatmap = client.get(detail["explanation"]["heatmap_png"])
    assert heatmap.status_code == 200 and heatmap.headers["content-type"] == "image/png"
    assert "private" in heatmap.headers["cache-control"]
    assert client.get(f"{SCANS}/{body['scan']['id']}/image").status_code == 404


def test_opt_in_image_is_resized_and_stripped_of_metadata(client):
    signup(client)
    exif = Image.Exif()
    exif[271] = "Canon"
    exif[0x8825] = {1: "N", 2: (12.0, 34.0, 56.0)}

    body = analyze(client, jpeg(scene(2, size=(2400, 1600)), exif=exif), save_image=True)

    assert body["scan"]["image_saved"] is True
    response = client.get(f"{SCANS}/{body['scan']['id']}/image")
    stored = Image.open(io.BytesIO(response.content))
    assert stored.format == "WEBP"
    assert max(stored.size) == 1024
    assert not stored.getexif()


def test_default_preference_controls_image_saving(client):
    signup(client)
    client.patch("/api/v1/account/preferences", json={"save_images_default": True})

    assert analyze(client, jpeg(scene(1)))["scan"]["image_saved"] is True
    assert analyze(client, jpeg(scene(2)), save_image=False)["scan"]["image_saved"] is False


def test_other_users_cannot_see_or_delete_a_scan(client):
    signup(client, "alice@example.com")
    scan_id = analyze(client, jpeg(scene(1)), save_image=True)["scan"]["id"]
    signup(client, "bob@example.com")

    for response in (
        client.get(f"{SCANS}/{scan_id}"),
        client.get(f"{SCANS}/{scan_id}/image"),
        client.get(f"{SCANS}/{scan_id}/heatmap"),
        client.delete(f"{SCANS}/{scan_id}"),
    ):
        assert response.status_code == 404
    assert client.get(SCANS).json()["items"] == []
    assert count_scans(client) == 1


def test_history_requires_sign_in(client):
    assert client.get(SCANS).status_code == 401


# ---------------------------------------------------------------- cache & seen-before


def test_identical_image_reuses_cached_result(client):
    detector = client.app.state.detector
    original, calls = detector.predict, []
    detector.predict = lambda image: calls.append(1) or original(image)
    data = jpeg(scene(3))
    signup(client)

    first = analyze(client, data)
    second = analyze(client, data)

    assert len(calls) == 1
    assert first["cached"] is False and second["cached"] is True
    assert second["verdict"] == first["verdict"]
    assert second["explanation"]["heatmap_png"] == first["explanation"]["heatmap_png"]


def test_seen_before_recognises_exact_and_near_duplicates(client):
    signup(client)
    first = analyze(client, jpeg(scene(4)))

    exact = analyze(client, jpeg(scene(4)))["seen_before"]["yours"]
    near = analyze(client, jpeg(scene(4).resize((256, 192)), quality=55))["seen_before"]["yours"]

    assert exact["exact"] is True
    assert near["exact"] is False
    assert first["seen_before"] is None


def test_cross_user_count_only_shown_from_two_other_users(client):
    data = jpeg(scene(5))
    signup(client, "a@example.com")
    analyze(client, data)
    signup(client, "b@example.com")

    only_one_other = analyze(client, data)["seen_before"]

    signup(client, "c@example.com")
    two_others = analyze(client, data)["seen_before"]

    assert only_one_other is None  # a single other user could be identified — hide it
    assert two_others["others_count"] == 2
    assert two_others["yours"] is None
    assert two_others["consistent"] is True


# ---------------------------------------------------------------- listing


def test_list_pagination_sorting_and_filters(client):
    signup(client)
    ids = [analyze(client, jpeg(scene(i)), name=f"shot-{i}.jpg")["scan"]["id"] for i in range(10, 15)]

    seen, cursor = [], None
    while True:
        page = client.get(SCANS, params={"limit": 2, **({"cursor": cursor} if cursor else {})}).json()
        seen += [item["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break

    assert seen == ids[::-1]  # newest first, no duplicates across pages
    oldest = [i["id"] for i in client.get(SCANS, params={"sort": "oldest"}).json()["items"]]
    assert oldest == ids
    assert [i["filename"] for i in client.get(SCANS, params={"q": "SHOT-12"}).json()["items"]] == [
        "shot-12.jpg"
    ]
    band = client.get(SCANS).json()["items"][0]["band"]
    assert all(i["band"] == band for i in client.get(SCANS, params={"band": band}).json()["items"])


def test_invalid_cursor(client):
    signup(client)

    response = client.get(SCANS, params={"cursor": "not-a-cursor"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cursor"


def test_stats(client):
    signup(client)
    for i in range(3):
        analyze(client, jpeg(scene(20 + i)))

    stats = client.get(f"{SCANS}/stats").json()

    assert stats["total"] == 3 == sum(stats["by_band"].values())
    assert set(stats["by_band"]) == {"likely_real", "uncertain", "likely_ai"}
    assert stats["this_week"] == 3


# ---------------------------------------------------------------- deletion


def test_delete_one_removes_its_files(client):
    signup(client)
    scan_id = analyze(client, jpeg(scene(1)), save_image=True)["scan"]["id"]
    assert len(stored_files(client)) == 2  # heat-map + image

    assert client.delete(f"{SCANS}/{scan_id}").status_code == 200

    assert client.get(f"{SCANS}/{scan_id}").status_code == 404
    assert stored_files(client) == []


def test_bulk_delete_and_delete_all(client):
    signup(client)
    ids = [analyze(client, jpeg(scene(30 + i)))["scan"]["id"] for i in range(4)]

    assert client.post(f"{SCANS}/bulk-delete", json={"ids": ids[:2]}).json() == {"deleted": 2}
    assert client.delete(SCANS).json() == {"deleted": 2}
    assert count_scans(client) == 0
    assert stored_files(client) == []


# ---------------------------------------------------------------- account & privacy


def test_preferences_update_and_validation(client):
    signup(client)

    assert client.get(f"{AUTH}/me").json()["retention_days"] == 90
    assert client.patch("/api/v1/account/preferences", json={"retention_days": 13}).status_code == 422
    assert (
        client.patch("/api/v1/account/preferences", json={"retention_days": None}).json()["retention_days"]
        is None
    )
    updated = client.patch("/api/v1/account/preferences", json={"save_images_default": True}).json()
    assert updated["save_images_default"] is True
    assert updated["retention_days"] is None  # untouched when omitted


def test_export_contains_everything_but_secrets(client):
    signup(client)
    analyze(client, jpeg(scene(1)))

    response = client.get("/api/v1/account/export")

    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert data["account"]["email"] == "alice@example.com"
    assert len(data["scans"]) == 1 and data["scans"][0]["result"]["verdict"]
    assert data["sessions"]
    assert "password" not in response.text and "token" not in response.text


def test_delete_account_removes_everything(client):
    signup(client)
    analyze(client, jpeg(scene(1)), save_image=True)

    wrong = client.post("/api/v1/account/delete", json={"password": "nope-nope-nope"})
    ok = client.post("/api/v1/account/delete", json={"password": PASSWORD})

    assert wrong.status_code == 400 and wrong.json()["error"]["field"] == "password"
    assert ok.status_code == 200
    assert count_scans(client) == 0
    assert stored_files(client) == []
    client.cookies.clear()
    login = client.post(f"{AUTH}/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert login.status_code == 401


def test_retention_deletes_only_expired_scans(client):
    signup(client, "short@example.com")
    client.patch("/api/v1/account/preferences", json={"retention_days": 7})
    analyze(client, jpeg(scene(40)), save_image=True)
    signup(client, "forever@example.com")
    client.patch("/api/v1/account/preferences", json={"retention_days": None})
    analyze(client, jpeg(scene(41)))

    async def age_everything(db):
        await db.execute(update(Scan).values(created_at=utcnow() - timedelta(days=10)))
        await db.commit()

    db_call(client, age_everything)
    report = client.portal.call(run_retention, client.app.state.sessionmaker, client.app.state.storage)

    assert report.scans_deleted == 1
    assert count_scans(client) == 1  # the "keep forever" user's scan survives
    assert len(stored_files(client)) == 1  # only the survivor's heat-map remains


@pytest.fixture
def expired_client(monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("ACCESS_TOKEN_TTL_S", "-10")
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def test_expired_session_on_analyze_asks_client_to_refresh(expired_client):
    signup(expired_client)

    response = expired_client.post("/api/v1/analyze", files={"file": ("a.jpg", jpeg(scene(1)), "image/jpeg")})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"
