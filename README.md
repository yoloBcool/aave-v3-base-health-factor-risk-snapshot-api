# AAVE v3 Health Factor Snapshot API — Base Network

A high-performance, read-only API that returns a complete AAVE v3 Health Factor and risk snapshot for any wallet on the Base network (chainId 8453).  
Designed for liquidation bots, dashboards, risk engines, quant strategies, and portfolio trackers needing accurate, machine-readable AAVE risk data.

---

## ✅ Features

- Real-time Health Factor (HF)  
- LTV, liquidation threshold, liquidation buffer (USD)  
- Total collateral, total debt, net equity, leverage ratio  
- Full collateral breakdown (per-asset amounts, USD values, weights, LTV/LT)  
- Full debt breakdown (variable/stable, APY, caps, utilization)  
- Oracle pricing with last-update timestamps  
- Stress-tested HF under −1%, −3%, −5% market moves  
- E-Mode & Isolation Mode detection  
- Supply-cap and borrow-cap usage per asset  
- Clean, stable, machine-readable JSON output  
- Zero infrastructure required — runs entirely as a dRPC Add-On

---

## ✅ Documentation

### API Reference  
Full endpoint details, parameters, and field descriptions:  
➡️ `docs/api.md`

### JSON Schema  
Formal schema defining all fields, types, and structure:  
➡️ `schemas/aave-base-hf-snapshot.schema.json`

### Sample Output  
Real output from the handler, ready for schema validation:  
➡️ `examples/sample-response.json`

---

## ✅ Use Cases

- Liquidation monitoring  
- Health Factor alerting  
- Automated deleveraging bots  
- Smart-debt-manager agents  
- Dashboard or portfolio integrations  
- Quant trading engines  
- Wallet-risk analytics  
- Whale liquidation-risk watchers  

---

## ✅ Output Type Policy (Marketplace-Safe)

- **Prices, USD values, APYs, LTVs, LT, ratios →** string decimals (`"123.456"`)  
- **Token amounts, caps, counters →** string integers/decimals  
- **Timestamps →** integers  
- **Booleans →** true/false  
- **Addresses/symbols →** strings  

---

## ✅ Supported Network

- Base Mainnet — chainId **8453**  
- AAVE Protocol — **v3**

---

## ✅ Quick Start (Local Development)

```
# Run local test to generate snapshot
python test_local.py

# Validate the output matches the schema
python validate_schema.py .\examples\sample-response.json
```

---

## ✅ Versioning

Current spec/schema: **1.0.0**  
Non-breaking changes increment the minor version.  
Breaking changes create a new schema file and major version.

---

## ✅ License

Licensed under the MIT License.  
See `LICENSE` for details.

---

## ✅ Contact

For questions or integration support:  
👉 Telegram: **@DeFiDataOps**
