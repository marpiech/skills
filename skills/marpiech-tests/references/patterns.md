# Generic test shapes

Use only when the repository has no neighbouring test to copy — the repo's own patterns
always win. Python/pytest and TypeScript shown; the shapes carry over to other stacks.

## Unit test, mocked boundary (async service)

```python
from unittest.mock import AsyncMock
import pytest


def _make_order(**overrides):
    """Factory: readable defaults, override only what the test is about."""
    data = {"id": "ord-1", "status": "open", "items": []}
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_close_order_with_no_items_is_rejected():
    repo = AsyncMock()
    repo.get.return_value = _make_order(items=[])
    service = OrderService(repo=repo)          # inject the boundary; never mock OrderService itself

    with pytest.raises(EmptyOrderError):
        await service.close("ord-1")

    repo.save.assert_not_called()               # the call IS the behaviour here: nothing persisted
```

Rules: set dummy configuration (env vars) in `conftest.py` **before** importing app
modules that read it at import time; `AsyncMock` for awaitables, `MagicMock` for plain
attributes; factories over inline dicts.

## Unit/integration test against a real database

```python
pytestmark = pytest.mark.asyncio


async def test_search_matches_tag_inside_json_column(db_session):
    await create_product(db_session, name="Mug", tags=["kitchen", "gift"])
    await create_product(db_session, name="Pen", tags=["office"])

    found = await ProductRepository(db_session).search(tag="gift")

    assert [p.name for p in found] == ["Mug"]
```

Use when correctness depends on the database (JSON/array operators, constraints,
transactions, migrations). The `db_session` fixture should roll back or truncate per test.

## API end-to-end test

```python
import os
import httpx
import pytest


def _env(name):                       # read lazily, at test time — not at import time
    return os.environ.get(name)


@pytest.fixture
def token():
    t = _env("E2E_USER_TOKEN")
    if not t:
        pytest.skip("E2E_USER_TOKEN not set — inject it with the secrets tool")
    return t


@pytest.mark.mutating
async def test_create_order_returns_201_and_location(api: httpx.AsyncClient, token):
    r = await api.post("/api/v1/orders", json={"ref": "E2E-demo"},
                       headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    assert r.headers["location"].endswith(r.json()["id"])
```

A skip keeps local runs usable without credentials — and is why a run summary must
report skips: in CI, a missing secret turns the whole suite into green skips.
Generate unique identifiers per run (`uuid4().hex[:8]`) so reruns do not collide, and
clean up what a mutating test creates.

## CLI end-to-end test

```python
import subprocess


def test_export_without_output_flag_fails_with_usage_error():
    r = subprocess.run(["acme", "export"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "--output" in r.stderr
```

## UI end-to-end test (Playwright)

```ts
import { test, expect } from '@playwright/test';

test('a manager can archive an order', async ({ page }) => {
  await page.goto('/orders/E2E-demo');
  await page.getByRole('button', { name: 'Archive' }).click();
  await expect(page.getByText('Order archived')).toBeVisible();   // auto-waits; no sleeps
});
```

Select by role and accessible name (what the user sees), not by CSS classes; one happy
path plus the most important failure per flow.

## Performance threshold

```python
import time


def test_price_list_for_1000_items_under_200ms(catalogue_1000):
    t0 = time.perf_counter()
    price_list(catalogue_1000)
    assert time.perf_counter() - t0 < 0.2     # generous: catches 10x regressions, not noise
```

Mark it `slow` if it needs real infrastructure; never assert tight margins on shared CI.

## Test smells to avoid

- Assertions only on mocks (`assert_called_once`) when an outcome could be checked.
- Re-implementing the code under test inside the test to compute the expected value.
- `sleep()` to wait for something — wait for the condition instead.
- Tests that depend on run order or on data left by another test.
- Snapshot tests of large outputs nobody reads; snapshot only small, stable shapes.
- Catch-all `try/except: pass` or `expect(...).toBeTruthy()` on complex objects.
- A test that cannot fail (no assertion, or asserting a constant).
