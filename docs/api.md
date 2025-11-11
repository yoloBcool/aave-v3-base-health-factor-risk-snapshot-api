# AAVE v3 Health Factor Snapshot API — Base Network
**Version:** 1.0.0  

This document defines the dRPC Add‑On interface that returns a complete, read‑only AAVE v3 risk snapshot for a wallet on **Base Mainnet (chainId 8453)**.

---

## 1. Overview

The endpoint produces a deterministic JSON snapshot of an account’s AAVE v3 state:

- Health Factor (HF)
- LTV, liquidation threshold, liquidation buffer (USD)
- Totals: collateral, debt, net equity, leverage
- Complete collateral breakdown
- Complete debt breakdown (variable/stable, APYs, utilization, caps)
- Oracle prices with update timestamps
- eMode / Isolation Mode, caps usage
- Metadata/provenance fields (`meta.vendor`, `meta.version`, `meta.signature`, etc.)

### Output typing rules
- **Prices, USD values, ratios, APYs, LTVs, liquidation thresholds, leverage, utilization:** string decimals (e.g., `"123.456"`, never scientific notation)
- **Token amounts, caps, supplies, on‑chain counters:** string integers/decimals (may exceed JS safe range)
- **Timestamps, counts, booleans, enums:** native (`integer`, `boolean`, `string`)
- **Addresses & symbols:** `string`

---

## 2. Endpoint

**Path:** `POST /handler`  
This path is executed by dRPC to call your `src/handler.py`.

### 2.1 Request (OpenAPI YAML)

```yaml
openapi: 3.0.3
info:
  title: AAVE v3 Health Factor Snapshot API — Base
  version: "1.0.0"
paths:
  /handler:
    post:
      summary: Return a Health Factor & risk snapshot for a Base wallet
      operationId: getAaveHfSnapshot
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SnapshotRequest'
      responses:
        '200':
          description: Snapshot produced
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SnapshotResponse'
        '400':
          description: Invalid input (e.g., bad address)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '503':
          description: Upstream RPC unavailable
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
components:
  schemas:
    SnapshotRequest:
      type: object
      required: [address]
      properties:
        address:
          type: string
          description: Wallet address on Base
          pattern: "^0x[a-fA-F0-9]{40}$"
```

---

## 3. Response Schema (OpenAPI YAML)

```yaml
openapi: 3.0.3
info:
  title: AAVE v3 Health Factor Snapshot API — Base
  version: "1.0.0"
components:
  schemas:
    SnapshotResponse:
      type: object
      required:
        - network
        - chain_id
        - address
        - timestamp
        - user
        - totals
        - collateral
        - debt
        - oracles
        - config
        - meta
      properties:
        network:
          type: string
          enum: ["base"]
        chain_id:
          type: integer
          example: 8453
        address:
          type: string
          pattern: "^0x[a-fA-F0-9]{40}$"
        timestamp:
          type: integer
          description: Unix epoch seconds
        user:
          type: object
          required: [health_factor, ltv, liquidation_threshold, liquidation_buffer_usd, available_borrows_usd, risk_class, is_safe, stress_tests]
          properties:
            health_factor: { type: string, description: "HF as string decimal" }
            ltv: { type: string, description: "Account LTV as string decimal" }
            liquidation_threshold: { type: string, description: "Account LT as string decimal" }
            liquidation_buffer_usd: { type: string, description: "USD distance from liquidation" }
            available_borrows_usd: { type: string, description: "Borrowable USD at current HF" }
            risk_class:
              type: string
              enum: [low, moderate, elevated, critical]
            is_safe:
              type: boolean
            stress_tests:
              type: object
              required: [hf_minus_1pct, hf_minus_3pct, hf_minus_5pct]
              properties:
                hf_minus_1pct: { type: string }
                hf_minus_3pct: { type: string }
                hf_minus_5pct: { type: string }
        totals:
            type: object
            required:
              - total_collateral_usd
              - total_debt_usd
              - net_equity_usd
              - current_leverage_ratio
              - max_leverage_at_current_hf
            properties:
              total_collateral_usd: { type: string }
              total_debt_usd: { type: string }
              net_equity_usd: { type: string }
              current_leverage_ratio: { type: string }
              max_leverage_at_current_hf: { type: string }
        tokenRef:
          type: object
          required: [symbol, address, decimals]
          properties:
            symbol: { type: string }
            address: { type: string }
            decimals: { type: integer }
        collateral:
          type: array
          items:
            type: object
            required: [token, amount, amount_usd, price_usd, usage_as_collateral_enabled, reserve_ltv, reserve_liquidation_threshold, reserve_liquidation_bonus, emode_category]
            properties:
              token: { $ref: '#/components/schemas/tokenRef' }
              amount: { type: string }
              amount_usd: { type: string }
              price_usd: { type: string }
              usage_as_collateral_enabled: { type: boolean }
              reserve_ltv: { type: string }
              reserve_liquidation_threshold: { type: string }
              reserve_liquidation_bonus: { type: string }
              emode_category:
                type: [ "integer", "null" ]
        debt:
          type: array
          items:
            type: object
            required: [token, variable_debt, stable_debt, total_debt_usd, variable_borrow_apy, stable_borrow_apy, reserve_utilization, borrow_cap, borrow_cap_used_percent]
            properties:
              token: { $ref: '#/components/schemas/tokenRef' }
              variable_debt: { type: string }
              stable_debt: { type: string }
              total_debt_usd: { type: string }
              variable_borrow_apy: { type: string }
              stable_borrow_apy: { type: string }
              reserve_utilization: { type: string }
              borrow_cap: { type: string }
              borrow_cap_used_percent: { type: string }
        oracles:
          type: object
          required: [base_currency, assets]
          properties:
            base_currency:
              type: object
              required: [symbol, price_usd, last_update]
              properties:
                symbol: { type: string }
                price_usd: { type: string }
                last_update: { type: integer }
            assets:
              type: array
              items:
                type: object
                required: [token, price_usd, last_update, confidence_score]
                properties:
                  token: { $ref: '#/components/schemas/tokenRef' }
                  price_usd: { type: string }
                  last_update: { type: integer }
                  confidence_score: { type: string }
        config:
          type: object
          required: [emode, isolation_mode, caps]
          properties:
            emode:
              type: object
              required: [active, category, settings]
              properties:
                active: { type: boolean }
                category: { type: [ "integer", "null" ] }
                settings: { type: [ "object", "null" ] }
            isolation_mode:
              type: object
              required: [active, debt_ceiling_remaining_usd]
              properties:
                active: { type: boolean }
                debt_ceiling_remaining_usd: { type: string }
            caps:
              type: array
              items:
                type: object
                required: [token, supply_cap, supply_cap_used_percent, borrow_cap, borrow_cap_used_percent]
                properties:
                  token: { $ref: '#/components/schemas/tokenRef' }
                  supply_cap: { type: string }
                  supply_cap_used_percent: { type: string }
                  borrow_cap: { type: string }
                  borrow_cap_used_percent: { type: string }
        meta:
          type: object
          required: [data_provider, oracle_source, latency_ms, version]
          properties:
            data_provider: { type: string }
            oracle_source: { type: string }
            latency_ms: { type: integer }
            version: { type: string }
            vendor: { type: string }
            brand: { type: string }
            repo: { type: string }
            signature: { type: string }
            brand_colors:
              type: array
              items: { type: string }
    ErrorResponse:
      type: object
      required: [error]
      properties:
        error:
          type: string
          enum: [invalid_address, rpc_unavailable, no_reserves, internal_error]
        detail:
          type: string
```

---

## 4. Examples

### 4.1 cURL

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -d '{"address":"0x1111111111111111111111111111111111111111"}' \
  https://drpc.org/addons/<your-addon-id>
```

### 4.2 Python

```python
import requests, json
url = "https://drpc.org/addons/<your-addon-id>"
payload = {"address":"0x1111111111111111111111111111111111111111"}
r = requests.post(url, json=payload, timeout=20)
print(json.dumps(r.json(), indent=2))
```

### 4.3 JavaScript (Node)

```javascript
import fetch from "node-fetch";
const url = "https://drpc.org/addons/<your-addon-id>";
const body = { address: "0x1111111111111111111111111111111111111111" };
const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
console.log(await r.json());
```

---

## 5. Error Codes

| code              | http | meaning                                   |
|-------------------|------|-------------------------------------------|
| invalid_address   | 400  | Address malformed or missing              |
| rpc_unavailable   | 503  | Upstream RPC provider unavailable/timeout |
| no_reserves       | 200  | Wallet has no AAVE positions              |
| internal_error    | 500  | Unhandled exception                       |

---

## 6. Versioning

- Spec version: **1.0.0**
- Non‑breaking additions → minor version bump
- Breaking changes → major bump and a new schema file under `/schemas/`

---

## 7. Compliance & Determinism

- Read‑only; no private keys, no side effects  
- Deterministic numeric formatting (no scientific notation)  
- Addresses/symbols as strings  
- AGPL‑3.0‑only license with attribution requirements

---

## 8. Contact

- Telegram: **@DeFiDataOps**  
- Issues: GitHub Issues on the repository  
