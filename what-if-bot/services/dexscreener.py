"""Fetches live price/liquidity/volume data from the DexScreener public API.

DexScreener indexes pairs across essentially every EVM (and many non-EVM)
chain and DEX, so this works regardless of which chain the token is on or
which exchange (Uniswap, a smaller DEX, etc.) has the deepest pool — you
just need the token's contract address. No API key required.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

import config

API_URL = "https://api.dexscreener.com/latest/dex/tokens/{address}"
PAIR_URL = "https://api.dexscreener.com/latest/dex/pairs/{chain}/{pair}"


@dataclass
class PriceInfo:
    chain: str
    dex: str
    pair_url: str
    base_symbol: str
    quote_symbol: str
    price_usd: float | None
    price_change_24h: float | None
    liquidity_usd: float | None
    fdv: float | None
    market_cap: float | None
    volume_24h: float | None


class DexScreenerError(RuntimeError):
    pass


async def fetch_price() -> PriceInfo:
    if not config.TOKEN_CONTRACT_ADDRESS:
        raise DexScreenerError(
            "TOKEN_CONTRACT_ADDRESS is not set in .env, so I don't know which "
            "token to look up."
        )

    async with httpx.AsyncClient(timeout=10) as client:
        if config.DEXSCREENER_PAIR_ADDRESS:
            # Chain is unknown ahead of time, so try the token endpoint first
            # and filter down to the configured pair address.
            resp = await client.get(API_URL.format(address=config.TOKEN_CONTRACT_ADDRESS))
        else:
            resp = await client.get(API_URL.format(address=config.TOKEN_CONTRACT_ADDRESS))

        if resp.status_code != 200:
            raise DexScreenerError(f"DexScreener returned HTTP {resp.status_code}")

        data = resp.json()

    pairs = data.get("pairs") or []
    if not pairs:
        raise DexScreenerError(
            "No trading pairs found for that contract address on DexScreener yet. "
            "Double check TOKEN_CONTRACT_ADDRESS in .env, or the pair may be too "
            "new/not indexed yet."
        )

    if config.DEXSCREENER_PAIR_ADDRESS:
        pairs = [p for p in pairs if p.get("pairAddress", "").lower() == config.DEXSCREENER_PAIR_ADDRESS.lower()] or pairs

    # Pick the pair with the highest liquidity — that's the most reliable price.
    best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)

    liquidity = best.get("liquidity") or {}
    price_change = best.get("priceChange") or {}
    volume = best.get("volume") or {}

    return PriceInfo(
        chain=best.get("chainId", "unknown"),
        dex=best.get("dexId", "unknown"),
        pair_url=best.get("url", ""),
        base_symbol=(best.get("baseToken") or {}).get("symbol", config.TOKEN_TICKER),
        quote_symbol=(best.get("quoteToken") or {}).get("symbol", ""),
        price_usd=float(best["priceUsd"]) if best.get("priceUsd") else None,
        price_change_24h=price_change.get("h24"),
        liquidity_usd=liquidity.get("usd"),
        fdv=best.get("fdv"),
        market_cap=best.get("marketCap"),
        volume_24h=volume.get("h24"),
    )


def _fmt_usd(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value < 0.01:
        return f"${value:.8f}"
    if value < 1000:
        return f"${value:,.4f}"
    return f"${value:,.0f}"


def format_price_message(info: PriceInfo) -> str:
    change = info.price_change_24h
    if change is None:
        change_str = "n/a"
    else:
        arrow = "🟢" if change >= 0 else "🔴"
        change_str = f"{arrow} {change:+.2f}%"

    lines = [
        f"*{config.TOKEN_NAME} (${info.base_symbol})*",
        "",
        f"Price: `{_fmt_usd(info.price_usd)}`",
        f"24h change: {change_str}",
        f"Liquidity: `{_fmt_usd(info.liquidity_usd)}`",
    ]
    if info.market_cap:
        lines.append(f"Market cap: `{_fmt_usd(info.market_cap)}`")
    elif info.fdv:
        lines.append(f"FDV: `{_fmt_usd(info.fdv)}`")
    if info.volume_24h:
        lines.append(f"24h volume: `{_fmt_usd(info.volume_24h)}`")

    lines.append("")
    lines.append(f"Chain: `{info.chain}` · DEX: `{info.dex}`")
    if info.pair_url:
        lines.append(f"[View chart]({info.pair_url})")

    return "\n".join(lines)
