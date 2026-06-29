"""Fase 6: gerador de dashboard.html estatico.

Le spans (`.testforge/spans.jsonl`) e o catalog de intents SQLite,
emite um unico arquivo HTML auto-contido com graficos Chart.js (CDN):

- Distribuicao por nivel de resolucao: L0_cache vs L1_candidate vs FAILED
- Top intents por frequencia
- Histograma de latencia de resolucao (ms)
- Tamanho do catalog de intents + razao de stale

Zero infraestrutura: abra o HTML em qualquer navegador. Sem servidor, sem CSS
framework — apenas estilos inline. Chart.js carregado do jsDelivr CDN.
"""
from __future__ import annotations

import html
import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Optional


def _read_spans(spans_path: str) -> list[dict]:
    if not os.path.exists(spans_path):
        return []
    out: list[dict] = []
    with open(spans_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _catalog_stats(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {"available": False}
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM intent_resolutions")
        total = cur.fetchone()[0]
        cur = conn.execute(
            "SELECT COUNT(*) FROM intent_resolutions WHERE status = 'active'")
        active = cur.fetchone()[0]
        cur = conn.execute(
            "SELECT COUNT(*) FROM intent_resolutions WHERE status = 'stale'")
        stale = cur.fetchone()[0]
        cur = conn.execute(
            "SELECT AVG(confidence) FROM intent_resolutions WHERE status = 'active'")
        avg_conf = cur.fetchone()[0] or 0.0
        return {
            "available": True,
            "total": total, "active": active, "stale": stale,
            "avg_confidence": round(avg_conf, 3),
        }
    finally:
        conn.close()


def _compute_resolve_metrics(spans: list[dict]) -> dict:
    levels = Counter()
    strategies = Counter()
    intents = Counter()
    latencies: list[float] = []
    for s in spans:
        if s.get("name") != "resolve":
            continue
        attrs = s.get("attributes") or {}
        levels[attrs.get("level", "UNKNOWN")] += 1
        strategies[attrs.get("strategy", "n/a")] += 1
        if attrs.get("intent_text"):
            intents[attrs["intent_text"]] += 1
        d = s.get("duration_ms")
        if isinstance(d, (int, float)):
            latencies.append(float(d))
    return {
        "level_counts": dict(levels),
        "strategy_counts": dict(strategies),
        "top_intents": intents.most_common(15),
        "latencies": latencies,
        "total_resolves": sum(levels.values()),
    }


def _hist_buckets(latencies: list[float], bucket_edges: list[float]) -> list[int]:
    """Retorna contagens por bucket (e[i], e[i+1]]; ultimo bucket e >= e[-1]."""
    counts = [0] * (len(bucket_edges) - 1)
    for v in latencies:
        for i in range(len(bucket_edges) - 1):
            if v < bucket_edges[i + 1]:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return counts


def generate_html(
    spans_path: str = ".testforge/spans.jsonl",
    db_path: str = ".testforge/intent_catalog.sqlite",
) -> str:
    """Retorna o HTML do dashboard como string. Funcao pura — sem IO."""
    spans = _read_spans(spans_path)
    metrics = _compute_resolve_metrics(spans)
    catalog = _catalog_stats(db_path)

    latency_edges = [0, 5, 20, 100, 500, 2000, 10000]
    latency_buckets = _hist_buckets(metrics["latencies"], latency_edges)
    latency_labels = [f"<{latency_edges[i+1]}ms" for i in range(len(latency_edges) - 2)]
    latency_labels.append(f">={latency_edges[-1]}ms")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "catalog": catalog,
        "latency_labels": latency_labels,
        "latency_buckets": latency_buckets,
    }
    payload_json = html.escape(json.dumps(payload, default=str), quote=False)
    levels_json = json.dumps(metrics["level_counts"])
    strategies_json = json.dumps(metrics["strategy_counts"])
    top_intents_json = json.dumps(metrics["top_intents"])
    latency_buckets_json = json.dumps(latency_buckets)
    latency_labels_json = json.dumps(latency_labels)

    catalog_block = (
        f'<p>Total: <b>{catalog["total"]}</b> | Active: <b>{catalog["active"]}</b> | '
        f'Stale: <b>{catalog["stale"]}</b> | '
        f'Avg confidence: <b>{catalog["avg_confidence"]}</b></p>'
        if catalog.get("available")
        else '<p>SQLite intent catalog not found.</p>'
    )

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>TestForge Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
 h1 {{ margin: 0 0 4px; font-size: 22px; }}
 .meta {{ color: #94a3b8; font-size: 12px; margin-bottom: 24px; }}
 .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }}
 .card {{ background: #1e293b; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
 h2 {{ font-size: 14px; margin: 0 0 12px; color: #cbd5e1; }}
 ul {{ list-style: none; padding: 0; margin: 0; font-size: 13px; }}
 li {{ padding: 4px 0; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; }}
 li:last-child {{ border-bottom: 0; }}
 .num {{ color: #93c5fd; font-variant-numeric: tabular-nums; }}
 details {{ margin-top: 24px; color: #94a3b8; }}
 pre {{ background: #0f172a; padding: 12px; border-radius: 6px; overflow: auto; font-size: 11px; }}
</style>
</head>
<body>
<h1>TestForge Dashboard</h1>
<div class="meta">Generated {payload["generated_at"]} • {metrics["total_resolves"]} resolves observed</div>
<div class="grid">
 <div class="card"><h2>Resolve level distribution</h2><canvas id="levels"></canvas></div>
 <div class="card"><h2>Strategy distribution</h2><canvas id="strategies"></canvas></div>
 <div class="card"><h2>Latency histogram (ms)</h2><canvas id="latency"></canvas></div>
 <div class="card">
   <h2>Top intents</h2>
   <ul id="intents-list"></ul>
 </div>
 <div class="card"><h2>Intent catalog (SQLite L0)</h2>{catalog_block}</div>
</div>
<details><summary>Raw payload</summary><pre id="raw">{payload_json}</pre></details>
<script>
const levels = {levels_json};
const strategies = {strategies_json};
const intents = {top_intents_json};
const latencyBuckets = {latency_buckets_json};
const latencyLabels = {latency_labels_json};

function bar(canvasId, labels, data, color) {{
  new Chart(document.getElementById(canvasId), {{
    type: 'bar',
    data: {{ labels: labels, datasets: [{{ data: data, backgroundColor: color }}] }},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ x: {{ ticks: {{ color: '#94a3b8' }} }},
                 y: {{ ticks: {{ color: '#94a3b8' }} }} }}
    }}
  }});
}}

bar('levels', Object.keys(levels), Object.values(levels), '#3b82f6');
bar('strategies', Object.keys(strategies), Object.values(strategies), '#10b981');
bar('latency', latencyLabels, latencyBuckets, '#f59e0b');

const ul = document.getElementById('intents-list');
intents.forEach(([intent, count]) => {{
  const li = document.createElement('li');
  li.innerHTML = '<span>' + intent + '</span><span class="num">' + count + '</span>';
  ul.appendChild(li);
}});
</script>
</body>
</html>
"""


def write_dashboard(
    output_path: str = "reports/dashboard.html",
    spans_path: str = ".testforge/spans.jsonl",
    db_path: str = ".testforge/intent_catalog.sqlite",
) -> str:
    """Gera e salva o dashboard HTML no caminho especificado."""
    html_content = generate_html(spans_path=spans_path, db_path=db_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path
