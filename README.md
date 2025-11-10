# AAVE v3 Health Factor Snapshot API — Base Network

A high-performance, read-only API that returns a complete AAVE v3 Health Factor and risk snapshot for any wallet on the **Base** network (chainId 8453).  
Designed for liquidation bots, dashboards, risk engines, trading systems, and portfolio trackers needing accurate, machine-readable AAVE data.

---

## ✅ Features

- Real-time **Health Factor (HF)**
- **LTV**, liquidation threshold, and liquidation buffer (USD)
- Total collateral, total debt, net equity, leverage ratio
- Full **collateral breakdown** (asset weights, LTV/LT, USD values)
- Full **debt breakdown** (variable/stable, APY, caps, utilization)
- Oracle pricing data with update timestamps
- Stress-tested HF under −1%, −3%, −5% market moves
- E-Mode & Isolation Mode detection
- Cap usage per asset (borrow/supply caps)
- Clean, stable, machine-readable JSON output
- Zero infrastructure required — runs as a dRPC Add-On

---

## ✅ Documentation

### • API Reference  
Full endpoint details, request format, and field descriptions:  
➡️ [`docs/api.md`](docs/api.md)

### • JSON Schema  
Formal schema defining all fields, types, and structure:  
➡️ [`schemas/aave-base-hf-snapshot.schema.json`](schemas/aave-base-hf-snapshot.schema.json)

### • Sample Output  
Real example response from a Base AAVE account:  
➡️ [`examples/sample-response.json`](examples/sample-response.json)

---

## ✅ Use Cases

- Liquidation monitoring  
- Health Factor alerting  
- Automated deleveraging bots  
- Smart debt manager agents  
- Dashboard integrations  
- Quant strategy engines  
- Wallet portfolio analytics  
- Whale-risk watchers  

---

## ✅ Network Support

- **Base Mainnet** — chainId **8453**  
- AAVE Protocol: **v3**

---

## ✅ Versioning

- Current spec/schema: **1.0.0**
- Breaking changes increment the major version and create a new schema file.

---

## ✅ License

Licensed under the MIT License.  
See [`LICENSE`](LICENSE) for details.

---

## ✅ Contact

For questions, integration support, or feature requests, contact:

### 👉 **Telegram: @DeFiDataOps**
