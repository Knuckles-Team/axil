# Arbora City embed contract

Provider: arbora-city CITY-PACKAGE-R001.5
Provider: arbora-city CITY-PACKAGE-R003.3
Provider: arbora-city CITY-SOURCE-R001.3
Provider: arbora-city CITY-SOURCE-R002
Provider: arbora-city CITY-SOURCE-R008
Consumer: axil AXIL-CLIENT-R022.1
Consumer: axil AXIL-CLIENT-R022.2
Consumer: axil AXIL-CLIENT-R022.3
Consumer: axil AXIL-CLIENT-R022.4

## Wire shape

- The page `dist/embed/index.html` reads `window.arboraCityHost = { transport, kitBaseUrl, capabilities }` at load. It waits 2000 ms for the `arbora-city:host` event, then shows the labelled demo city.
- `transport.invoke(op, params)` returns a promise of the Arbora result object, or rejects with `{ code: "UNAVAILABLE" | "REFUSED" | "TIMEOUT", detail? }`.
- `dist/source/operations.json` lists every operation the page may call. The host allows exactly that list.
- A write returns `{ plan_ref, summary, expires_at }` first. The page raises `arbora-city:confirm`; the host resends with `plan_ref` and `execute: true`.
- `arbora-city-kit --out <dir>` writes the kit and verifies each file against `assets.lock.json`. It exits 0 on success, 2 on a network failure, 3 on a digest mismatch and 4 on a bad argument.

## Refusal codes

- `REFUSED`: the op is not listed, or Arbora refused it. The detail holds the Arbora code.
- `UNAVAILABLE`: the gateway is not reachable or not signed in.
- `TIMEOUT`: no answer within 5 s.

## Authoritative types

`CitySource`, `ArboraTransport` and `TransportError` in the `arbora-city` package (`src/source/`).

## Test vectors

`tests/fixtures/arbora/*.json` in the `arbora-city` package; `tests/test_city_bridge.py` in this repository.
