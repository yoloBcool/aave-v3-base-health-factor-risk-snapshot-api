# API Reference — AAVE v3 Health Factor Snapshot API (Base Network)

Real-time, read-only AAVE v3 account Health Factor and risk snapshot for any wallet on Base Mainnet (chainId 8453).
This API powers dashboards, liquidation bots, risk engines, and trading-automation systems.

## 1. Overview

This endpoint returns a complete, machine-readable AAVE v3 account state including HF, collateral, debt, prices, thresholds, stress tests, caps, and metadata.

## 2. Endpoint

POST /handler

## 3. Request Schema

{ "type": "object", "properties": { "address": { "type": "string" } }, "required": ["address"] }

## 4. Sample Response

See examples/sample-response.json for full sample.

## 5. Usage Examples

### curl
curl -X POST -H "Content-Type: application/json" -d '{"address":"0x..."}' https://drpc.org/addons/<your-addon-id>

### Python
import requests, json
resp = requests.post("https://drpc.org/addons/<your-addon-id>", json={"address":"0x..."})
print(resp.json())

### JavaScript
const resp = await fetch("https://drpc.org/addons/<your-addon-id>", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({address:"0x..."}) });

## 6. Errors

invalid_address, rpc_unavailable, no_reserves.

## 7. Versioning

Current version: 1.0.0

## 8. License

AGPL-3.0-only

## 9. Contact

Telegram: @DeFiDataOps
