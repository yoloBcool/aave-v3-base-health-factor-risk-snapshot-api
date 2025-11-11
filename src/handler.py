# /src/handler.py
import os
import json
import time
import argparse
from decimal import Decimal, getcontext
from typing import Any, Dict, List, Tuple
from web3 import Web3
from dotenv import load_dotenv

# =========================
# Precision configuration
# =========================
getcontext().prec = 120  # high precision for intermediate math

def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))

def to_units(raw: int, decimals: int) -> Decimal:
    if decimals <= 0:
        return D(raw)
    return D(raw) / (Decimal(10) ** decimals)

# --- strict formatters for schema contract ---
def _fmt_plain_decimal(x: Decimal) -> str:
    """Return a plain decimal string (no scientific notation), trim '-0' to '0'."""
    s = format(x, "f")
    if s.startswith("-0"):
        try:
            if Decimal(s) == 0:
                return "0"
        except Exception:
            pass
    return s

def as_str(dec: Decimal) -> str:
    """
    String decimals for money/ratios/apys/etc.
    """
    return _fmt_plain_decimal(dec)

def as_str_udecimal(x) -> str:
    """
    Unsigned decimal for non-negative quantities; clamps '-0' to '0'.
    """
    s = _fmt_plain_decimal(D(x))
    return "0" if s in ("-0", "-0.0") else s

def as_str_uint(x) -> str:
    """
    String integer for large on-chain counters/caps/supplies (can exceed JS safe range).
    Floors toward zero and rejects negatives.
    """
    if isinstance(x, int):
        if x < 0:
            raise ValueError("uint cannot be negative")
        return str(x)
    d = D(x)
    if d < 0:
        raise ValueError("uint cannot be negative")
    return str(int(d))

def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default

# =========================
# Minimal ABIs
# =========================
IPool_ABI = [
    {"name": "getReservesList", "inputs": [], "outputs": [{"type": "address[]", "name": ""}],
     "stateMutability": "view", "type": "function"},
    {"name": "getReserveData", "inputs": [{"name": "asset", "type": "address"}], "outputs": [
        {"name": "configuration", "type": "uint256"},
        {"name": "liquidityIndex", "type": "uint128"},
        {"name": "currentLiquidityRate", "type": "uint128"},
        {"name": "variableBorrowIndex", "type": "uint128"},
        {"name": "currentVariableBorrowRate", "type": "uint128"},
        {"name": "currentStableBorrowRate", "type": "uint128"},
        {"name": "lastUpdateTimestamp", "type": "uint40"},
        {"name": "id", "type": "uint16"},
        {"name": "aTokenAddress", "type": "address"},
        {"name": "stableDebtTokenAddress", "type": "address"},
        {"name": "variableDebtTokenAddress", "type": "address"},
        {"name": "interestRateStrategyAddress", "type": "address"},
        {"name": "accruedToTreasury", "type": "uint128"},
        {"name": "unbacked", "type": "uint128"},
        {"name": "isolationModeTotalDebt", "type": "uint128"},
    ], "stateMutability": "view", "type": "function"},
    {"name": "getUserAccountData", "inputs": [{"name": "user", "type": "address"}], "outputs": [
        {"name": "totalCollateralBase", "type": "uint256"},
        {"name": "totalDebtBase", "type": "uint256"},
        {"name": "availableBorrowsBase", "type": "uint256"},
        {"name": "currentLiquidationThreshold", "type": "uint256"},
        {"name": "ltv", "type": "uint256"},
        {"name": "healthFactor", "type": "uint256"}
    ], "stateMutability": "view", "type": "function"},
    {"name": "ADDRESSES_PROVIDER", "inputs": [], "outputs": [{"type": "address", "name": ""}],
     "stateMutability": "view", "type": "function"},
]

IAddressesProvider_ABI = [
    {"name": "getPriceOracle", "inputs": [], "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"name": "getPoolConfigurator", "inputs": [], "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

IPriceOracle_ABI = [
    {"name": "getAssetPrice", "inputs": [{"name": "asset", "type": "address"}],
     "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"name": "getSourceOfAsset", "inputs": [{"name": "asset", "type": "address"}],
     "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"name": "BASE_CURRENCY_UNIT", "inputs": [], "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

IChainlinkAggregator_ABI = [
    {"name": "latestRoundData", "inputs": [], "outputs": [
        {"name": "roundId", "type": "uint80"},
        {"name": "answer", "type": "int256"},
        {"name": "startedAt", "type": "uint256"},
        {"name": "updatedAt", "type": "uint256"},
        {"name": "answeredInRound", "type": "uint80"}],
     "stateMutability": "view", "type": "function"}
]

IPoolConfigurator_ABI = [
    {"name": "getReserveCaps", "inputs": [{"name": "asset", "type": "address"}], "outputs": [
        {"name": "borrowCap", "type": "uint256"},
        {"name": "supplyCap", "type": "uint256"}],
     "stateMutability": "view", "type": "function"}
]

ERC20_ABI = [
    {"name": "symbol", "inputs": [], "outputs": [{"type": "string"}],
     "stateMutability": "view", "type": "function"},
    {"name": "decimals", "inputs": [], "outputs": [{"type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"name": "balanceOf", "inputs": [{"name": "owner", "type": "address"}],
     "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"name": "totalSupply", "inputs": [], "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

MULTICALL3_ABI = [
    {"inputs": [{"internalType": "bool", "name": "requireSuccess", "type": "bool"},
                {"components": [{"internalType": "address", "name": "target", "type": "address"},
                                {"internalType": "bytes", "name": "callData", "type": "bytes"}],
                 "internalType": "struct Multicall3.Call[]", "name": "calls", "type": "tuple[]"}],
     "name": "tryAggregate",
     "outputs": [{"components": [{"internalType": "bool", "name": "success", "type": "bool"},
                                 {"internalType": "bytes", "name": "returnData", "type": "bytes"}],
                  "internalType": "struct Multicall3.Result[]", "name": "returnData", "type": "tuple[]"}],
     "stateMutability": "payable", "type": "function"},
]

# =========================
# Constants (Base / Aave v3)
# =========================
POOL_ADDRESS = Web3.to_checksum_address("0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")
MULTICALL3_ADDRESS = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")

# =========================
# Helpers
# =========================
def _encode(fn) -> bytes:
    return Web3.to_bytes(hexstr=fn._encode_transaction_data())

def run_multicall(w3, multicall, calls: List[Tuple[str, bytes]]) -> List[Tuple[bool, bytes]]:
    call_structs = [{"target": target, "callData": data} for target, data in calls]
    results = multicall.functions.tryAggregate(False, call_structs).call()
    return [(res[0], res[1]) for res in results]

def conf_bits(x: int, start: int, length: int) -> int:
    mask = (1 << length) - 1
    return (x >> start) & mask

def decode_config(conf_uint: int) -> Dict[str, Any]:
    ltv_bps = conf_bits(conf_uint, 0, 16)
    liq_thr_bps = conf_bits(conf_uint, 16, 16)
    liq_bonus_bps = conf_bits(conf_uint, 32, 16)
    decimals_bits = conf_bits(conf_uint, 48, 8)
    emode_cat = conf_bits(conf_uint, 184, 8)
    return {
        "ltv_bps": ltv_bps,
        "liq_thr_bps": liq_thr_bps,
        "liq_bonus_bps": liq_bonus_bps,
        "decimals_bits": decimals_bits,
        "emode_category": int(emode_cat) if emode_cat > 0 else None,
        "usage_as_collateral_enabled": bool(ltv_bps > 0),
    }

# =========================
# Core engine (pure function)
# =========================
def build_snapshot(rpc_url: str, user_address: str) -> Dict[str, Any]:
    t0 = time.perf_counter()

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to Base RPC at {rpc_url}")

    # --- Contracts ---
    pool = w3.eth.contract(address=POOL_ADDRESS, abi=IPool_ABI)
    multicall = w3.eth.contract(address=MULTICALL3_ADDRESS, abi=MULTICALL3_ABI)

    provider_addr = pool.functions.ADDRESSES_PROVIDER().call()
    provider = w3.eth.contract(address=provider_addr, abi=IAddressesProvider_ABI)

    oracle_addr = provider.functions.getPriceOracle().call()
    oracle = w3.eth.contract(address=oracle_addr, abi=IPriceOracle_ABI)

    configurator_addr = provider.functions.getPoolConfigurator().call()
    configurator = w3.eth.contract(address=configurator_addr, abi=IPoolConfigurator_ABI)

    base_unit = safe(lambda: oracle.functions.BASE_CURRENCY_UNIT().call(), 10**8) or 10**8
    base_unit_d = D(base_unit)

    reserves: List[str] = [Web3.to_checksum_address(a) for a in pool.functions.getReservesList().call()]

    # --- symbol/decimals caches ---
    symbols: Dict[str, str] = {}
    decimals: Dict[str, int] = {}

    # -------- Batch 1 --------
    batch1_calls = []
    for asset in reserves:
        batch1_calls.append((pool.address, _encode(pool.functions.getReserveData(asset))))
        batch1_calls.append((oracle.address, _encode(oracle.functions.getAssetPrice(asset))))
        batch1_calls.append((configurator.address, _encode(configurator.functions.getReserveCaps(asset))))
        batch1_calls.append((oracle.address, _encode(oracle.functions.getSourceOfAsset(asset))))
        erc = w3.eth.contract(address=Web3.to_checksum_address(asset), abi=ERC20_ABI)
        batch1_calls.append((asset, _encode(erc.functions.symbol())))
        batch1_calls.append((asset, _encode(erc.functions.decimals())))

    results_b1 = run_multicall(w3, multicall, batch1_calls)

    asset_data: Dict[str, Any] = {}
    batch2_calls: List[Tuple[str, bytes]] = []
    call_idx = 0
    for asset in reserves:
        res_rd, res_px, res_cap, res_src, res_sym, res_dec = results_b1[call_idx: call_idx + 6]

        if not res_rd[0]:
            call_idx += 6
            continue

        output_types = ['uint256', 'uint128', 'uint128', 'uint128', 'uint128', 'uint128', 'uint40', 'uint16',
                        'address', 'address', 'address', 'address', 'uint128', 'uint128', 'uint128']
        rd = w3.codec.decode(output_types, res_rd[1])
        conf_uint, var_rate, st_rate = int(rd[0]), D(rd[4]), D(rd[5])

        aToken = Web3.to_checksum_address(rd[8])
        sDebt = Web3.to_checksum_address(rd[9])
        vDebt = Web3.to_checksum_address(rd[10])

        px_raw = w3.codec.decode(['uint256'], res_px[1])[0] if res_px[0] else 0
        borrow_cap, supply_cap = w3.codec.decode(['uint256', 'uint256'], res_cap[1]) if res_cap[0] else (0, 0)
        raw_price_feed = w3.codec.decode(['address'], res_src[1])[0] if res_src[0] else "0x0000000000000000000000000000000000000000"
        price_feed_addr = Web3.to_checksum_address(raw_price_feed)

        try:
            symbols[asset] = w3.codec.decode(['string'], res_sym[1])[0]
        except Exception:
            symbols[asset] = "UNKNOWN"
        try:
            decimals[asset] = w3.codec.decode(['uint8'], res_dec[1])[0]
        except Exception:
            decimals[asset] = 18

        asset_data[asset] = {
            "config": decode_config(conf_uint),
            "var_rate": var_rate / (D(10) ** 27),
            "st_rate": st_rate / (D(10) ** 27),
            "px": D(px_raw) / base_unit_d,
            "borrow_cap": int(borrow_cap or 0),
            "supply_cap": int(supply_cap or 0),
            "aToken": aToken,
            "sDebt": sDebt,
            "vDebt": vDebt,
            "price_feed": price_feed_addr,
        }

        if int(aToken, 16) != 0:
            aErc = w3.eth.contract(address=aToken, abi=ERC20_ABI)
            batch2_calls.append((aToken, _encode(aErc.functions.balanceOf(user_address))))
            batch2_calls.append((aToken, _encode(aErc.functions.totalSupply())))
        else:
            batch2_calls.extend([(multicall.address, b''), (multicall.address, b'')])

        if int(sDebt, 16) != 0:
            sErc = w3.eth.contract(address=sDebt, abi=ERC20_ABI)
            batch2_calls.append((sDebt, _encode(sErc.functions.balanceOf(user_address))))
            batch2_calls.append((sDebt, _encode(sErc.functions.totalSupply())))
        else:
            batch2_calls.extend([(multicall.address, b''), (multicall.address, b'')])

        if int(vDebt, 16) != 0:
            vErc = w3.eth.contract(address=vDebt, abi=ERC20_ABI)
            batch2_calls.append((vDebt, _encode(vErc.functions.balanceOf(user_address))))
            batch2_calls.append((vDebt, _encode(vErc.functions.totalSupply())))
        else:
            batch2_calls.extend([(multicall.address, b''), (multicall.address, b'')])

        if int(price_feed_addr, 16) != 0:
            agg = w3.eth.contract(address=price_feed_addr, abi=IChainlinkAggregator_ABI)
            batch2_calls.append((price_feed_addr, _encode(agg.functions.latestRoundData())))
        else:
            batch2_calls.append((multicall.address, b''))

        call_idx += 6

    # -------- Batch 2 --------
    results_b2 = run_multicall(w3, multicall, batch2_calls)

    collateral: List[Dict[str, Any]] = []
    debt: List[Dict[str, Any]] = []
    oracle_assets: List[Dict[str, Any]] = []
    config_caps: List[Dict[str, Any]] = []

    total_collateral_usd_sum = D(0)
    total_debt_usd_sum = D(0)

    call_idx_b2 = 0
    for asset in reserves:
        if asset not in asset_data:
            call_idx_b2 += 7
            continue

        ad = asset_data[asset]
        cfg = ad["config"]
        decs = int(cfg["decimals_bits"]) if cfg["decimals_bits"] > 0 else int(decimals.get(asset, 18))

        res_a_bal, res_a_supply = results_b2[call_idx_b2: call_idx_b2 + 2]
        res_s_bal, res_s_supply = results_b2[call_idx_b2 + 2: call_idx_b2 + 4]
        res_v_bal, res_v_supply = results_b2[call_idx_b2 + 4: call_idx_b2 + 6]
        res_feed = results_b2[call_idx_b2 + 6]

        a_bal_raw = Web3.to_int(res_a_bal[1]) if res_a_bal[0] and res_a_bal[1] else 0
        a_sup_raw = Web3.to_int(res_a_supply[1]) if res_a_supply[0] and res_a_supply[1] else 0
        s_bal_raw = Web3.to_int(res_s_bal[1]) if res_s_bal[0] and res_s_bal[1] else 0
        s_sup_raw = Web3.to_int(res_s_supply[1]) if res_s_supply[0] and res_s_supply[1] else 0
        v_bal_raw = Web3.to_int(res_v_bal[1]) if res_v_bal[0] and res_v_bal[1] else 0
        v_sup_raw = Web3.to_int(res_v_supply[1]) if res_v_supply[0] and res_v_supply[1] else 0

        last_update = 0
        if res_feed[0] and res_feed[1]:
            try:
                rd_feed = w3.codec.decode(['uint80', 'int256', 'uint256', 'uint256', 'uint80'], res_feed[1])
                last_update = int(rd_feed[3])
            except Exception:
                last_update = 0

        a_bal = to_units(a_bal_raw, decs)
        s_bal = to_units(s_bal_raw, decs)
        v_bal = to_units(v_bal_raw, decs)
        a_total = to_units(a_sup_raw, decs)
        s_total = to_units(s_sup_raw, decs)
        v_total = to_units(v_sup_raw, decs)

        debt_total = s_total + v_total
        utilization = D(0)
        if a_total > 0:
            utilization = debt_total / a_total

        borrow_cap_used_pct = D(0)
        if ad["borrow_cap"] > 0:
            denom_tokens = to_units(ad["borrow_cap"], decs)
            if denom_tokens > 0:
                borrow_cap_used_pct = (debt_total / denom_tokens) * D(100)

        supply_cap_used_pct = D(0)
        if ad["supply_cap"] > 0:
            denom_tokens_s = to_units(ad["supply_cap"], decs)
            if denom_tokens_s > 0:
                supply_cap_used_pct = (a_total / denom_tokens_s) * D(100)

        confidence = D("0.99")
        if (symbols.get(asset, "") or "").upper() == "USDC":
            confidence = D("0.999")

        collateral_row = {
            "token": {"symbol": symbols.get(asset, "UNKNOWN"), "address": asset, "decimals": decs},
            "amount": as_str(a_bal),  # string decimal
            "amount_usd": as_str(a_bal * ad["px"]),  # string decimal
            "price_usd": as_str(ad["px"]),  # string decimal
            "usage_as_collateral_enabled": bool(cfg["usage_as_collateral_enabled"]),
            "reserve_ltv": as_str(D(cfg["ltv_bps"]) / D(10000)),  # string decimal
            "reserve_liquidation_threshold": as_str(D(cfg["liq_thr_bps"]) / D(10000)),  # string decimal
            "reserve_liquidation_bonus": as_str(D(cfg["liq_bonus_bps"]) / D(10000)),  # string decimal
            "emode_category": (str(cfg["emode_category"]) if cfg["emode_category"] is not None else None)
        }
        collateral.append(collateral_row)

        user_total_debt_tokens = s_bal + v_bal
        debt_row = {
            "token": {"symbol": symbols.get(asset, "UNKNOWN"), "address": asset, "decimals": decs},
            "variable_debt": as_str(v_bal),  # string decimal
            "stable_debt": as_str(s_bal),    # string decimal
            "total_debt_usd": as_str(user_total_debt_tokens * ad["px"]),  # string decimal
            "variable_borrow_apy": as_str(ad["var_rate"]),  # string decimal
            "stable_borrow_apy": as_str(ad["st_rate"]),     # string decimal
            "reserve_utilization": as_str(utilization),      # string decimal
            "borrow_cap": as_str_uint(ad["borrow_cap"]),     # big counter -> string integer
            "borrow_cap_used_percent": as_str(borrow_cap_used_pct)  # string decimal
        }
        debt.append(debt_row)

        oracle_row = {
            "token": {"symbol": symbols.get(asset, "UNKNOWN"), "address": asset, "decimals": decs},
            "price_usd": as_str(ad["px"]),  # string decimal
            "last_update": int(last_update),  # integer timestamp
            "confidence_score": as_str(confidence)  # string decimal
        }
        oracle_assets.append(oracle_row)

        caps_row = {
            "token": {"symbol": symbols.get(asset, "UNKNOWN"), "address": asset, "decimals": decs},
            "supply_cap": as_str_uint(ad["supply_cap"]),                 # big counter -> string integer
            "supply_cap_used_percent": as_str(supply_cap_used_pct),      # string decimal
            "borrow_cap": as_str_uint(ad["borrow_cap"]),                 # big counter -> string integer
            "borrow_cap_used_percent": as_str(borrow_cap_used_pct)       # string decimal
        }
        config_caps.append(caps_row)

        total_collateral_usd_sum += a_bal * ad["px"]
        total_debt_usd_sum += user_total_debt_tokens * ad["px"]

        call_idx_b2 += 7

    # --- User account data ---
    u = pool.functions.getUserAccountData(Web3.to_checksum_address(user_address)).call()
    total_collateral_base = D(u[0])
    total_debt_base = D(u[1])
    available_borrows = D(u[2])
    liq_threshold_bps = D(u[3])
    ltv_bps_user = D(u[4])
    health_factor_ray = D(u[5])

    hf = health_factor_ray / (D(10) ** 18) if health_factor_ray > 0 else D(0)
    ltv_user = ltv_bps_user / D(10000)
    liq_thr_user = liq_threshold_bps / D(10000)

    total_collateral_usd_api = total_collateral_base / base_unit_d
    total_debt_usd_api = total_debt_base / base_unit_d
    available_borrows_usd = available_borrows / base_unit_d

    liq_buffer_usd = (total_collateral_usd_api * liq_thr_user) - total_debt_usd_api
    if liq_buffer_usd < 0:
        liq_buffer_usd = D(0)

    total_collateral_usd = total_collateral_usd_sum if total_collateral_usd_sum > 0 else total_collateral_usd_api
    total_debt_usd = total_debt_usd_sum if total_debt_usd_sum > 0 else total_debt_usd_api
    net_equity_usd = D(total_collateral_usd - total_debt_usd)

    current_leverage_ratio = D(0)
    if net_equity_usd > 0:
        current_leverage_ratio = total_collateral_usd / net_equity_usd

    max_leverage_at_current_hf = D(0)
    if total_collateral_usd > 0 and liq_thr_user > 0 and total_debt_usd > 0:
        debt_ratio = total_debt_usd / total_collateral_usd
        denom = (liq_thr_user - debt_ratio)
        if denom > 0:
            max_leverage_at_current_hf = liq_thr_user / denom
    elif ltv_user > 0:
        max_leverage_at_current_hf = ltv_user / (D(1) - ltv_user)

    risk_class = "low"
    if hf < D("1.05"):
        risk_class = "high"
    elif hf < D("1.25"):
        risk_class = "moderate"
    is_safe = bool(hf > D("1.05"))

    hf_minus_1pct = hf * D("0.99")
    hf_minus_3pct = hf * D("0.97")
    hf_minus_5pct = hf * D("0.95")

    # --- Base currency info (WETH) ---
    weth_addr = None
    for a in reserves:
        if (symbols.get(a, "") or "").upper() in ("WETH", "WETH.E", "WETH9"):
            weth_addr = a
            break
    if weth_addr is None and reserves:
        weth_addr = reserves[0]

    eth_price = D(0)
    base_last_update = 0
    if weth_addr in asset_data:
        ad_weth = asset_data[weth_addr]
        eth_price = ad_weth["px"]
        if ad_weth["price_feed"] != "0x0000000000000000000000000000000000000000":
            try:
                agg = w3.eth.contract(address=ad_weth["price_feed"], abi=IChainlinkAggregator_ABI)
                rd = agg.functions.latestRoundData().call()
                base_last_update = int(rd[3])
            except Exception:
                base_last_update = 0

    oracles = {
        "base_currency": {"symbol": "ETH", "price_usd": as_str(eth_price), "last_update": int(base_last_update)},
        "assets": oracle_assets
    }

    config = {
        "emode": {"active": False, "category": None, "settings": None},
        "isolation_mode": {"active": False, "debt_ceiling_remaining_usd": "0"},
        "caps": config_caps
    }

    latency_ms = int((time.perf_counter() - t0) * 1000)

    snapshot = {
        "network": "base",
        "chain_id": 8453,  # integer
        "address": Web3.to_checksum_address(user_address),  # string
        "timestamp": int(time.time()),  # integer
        "user": {
            "health_factor": as_str(hf),
            "ltv": as_str(ltv_user),
            "liquidation_threshold": as_str(liq_thr_user),
            "liquidation_buffer_usd": as_str(liq_buffer_usd),
            "available_borrows_usd": as_str(available_borrows_usd),
            "risk_class": risk_class,
            "is_safe": is_safe,
            "stress_tests": {
                "hf_minus_1pct": as_str(hf_minus_1pct),
                "hf_minus_3pct": as_str(hf_minus_3pct),
                "hf_minus_5pct": as_str(hf_minus_5pct)
            }
        },
        "totals": {
            "total_collateral_usd": as_str(total_collateral_usd),
            "total_debt_usd": as_str(total_debt_usd),
            "net_equity_usd": as_str(net_equity_usd),
            "current_leverage_ratio": as_str(current_leverage_ratio),
            "max_leverage_at_current_hf": as_str(max_leverage_at_current_hf)
        },
        "collateral": collateral,
        "debt": debt,
        "oracles": oracles,
        "config": config,
        "meta": {
            "data_provider": "aave-v3",
            "oracle_source": "aave-oracle",
            "latency_ms": latency_ms,  # integer
            "version": "2.1.2"
        }
    }
    return snapshot

# =========================
# dRPC entrypoint (serverless-style)
# =========================
def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    dRPC calls this function with JSON like:
      { "address": "0xYourWallet", "rpc_url": "<optional-for-local-testing>" }

    In production on dRPC, omit rpc_url so their internal provider is used.
    """
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=True)

    addr = event.get("address") or os.environ.get("MY_ADDRESS")
    if not addr:
        raise ValueError("Missing 'address'. Provide wallet address in request or MY_ADDRESS in .env.")
    user_address = Web3.to_checksum_address(addr)

    rpc_url = event.get("rpc_url") or os.environ.get("RPC_URL")
    if not rpc_url:
        rpc_url = "https://base.drpc.org"

    return build_snapshot(rpc_url=rpc_url, user_address=user_address)

# =========================
# Local CLI helper (optional)
# =========================
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AAVE v3 Health Factor Snapshot (Base 8453) — JSON output by default with --json-only"
    )
    parser.add_argument("address", nargs="?", help="Wallet address (checksum or hex).")
    parser.add_argument("--rpc", dest="rpc_url", default=None, help="Override Base RPC URL for local testing.")
    parser.add_argument("--json-only", action="store_true",
                        help="Print ONLY the JSON snapshot to stdout (no prompts, no banners).")
    return parser.parse_args()

if __name__ == "__main__":
    # Local testing:
    #   python src/handler.py --json-only 0xYourAddress
    #   python src/handler.py --json-only --rpc https://base.drpc.org 0xYourAddress
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=True)
    args = _parse_args()

    # address resolution
    addr = args.address or os.environ.get("MY_ADDRESS")
    if not addr:
        if args.json_only:
            raise SystemExit("Missing address. Provide as CLI arg or MY_ADDRESS in .env.")
        addr = input("Please enter your wallet address: ").strip()
        if not addr:
            raise SystemExit("Error: No address provided. Exiting.")

    try:
        checksum_addr = Web3.to_checksum_address(addr)
    except Exception as e:
        raise SystemExit(f"Error: Invalid address '{addr}'. {e}")

    # rpc resolution
    default_rpc = "https://base.drpc.org"
    rpc = args.rpc_url or os.environ.get("RPC_URL")
    if not rpc and not args.json_only:
        rpc_input = input(f"Please enter your Base RPC URL (press Enter to use default: {default_rpc}): ").strip()
        rpc = rpc_input if rpc_input else default_rpc
    if not rpc:
        rpc = default_rpc

    snapshot = build_snapshot(rpc, checksum_addr)

    if args.json_only:
        # IMPORTANT: emit ONLY JSON (for test_local.py parsing)
        print(json.dumps(snapshot, ensure_ascii=False))
    else:
        print(f"Fetching snapshot for {checksum_addr} via {rpc}...")
        print("\n--- Snapshot Complete ---")
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
