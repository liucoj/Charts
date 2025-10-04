"""
title: ChartJS
author: myria
author_url: https://github.com/liucoj
description: Chart.js chat with automatic colors, toggle theme and download PNG.
version: 1.0.0
license: MIT
"""

from typing import List, Optional, Literal, Dict, Any
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import json, html


class Tools:
    """
    Ritorna un HTMLResponse 'inline' che OpenWebUI incorpora in chat (iframe).
    Passa i dati direttamente come parametri: labels e datasets.
    Esemple datasets:
      [
        {"label":"Serie A","data":[12,18,15,22]},
        {"label":"Serie B","data":[9,11,13,16]}
      ]
    """

    def __init__(self):
        self.valves = self.Valves()
        self.description = (
            "Grafici Chart.js con colori auto, download PNG e toggle Light/Dark."
        )

    class Valves(BaseModel):
        canvas_height: int = Field(440, description="Altezza canvas in px")
        canvas_width: str = Field("100%", description="Larghezza CSS del canvas")
        dark_bg: str = Field("#0b0f19", description="Sfondo tema scuro")
        dark_fg: str = Field("#e6edf3", description="Testo tema scuro")
        dark_grid: str = Field(
            "rgba(255,255,255,0.15)", description="Griglia tema scuro"
        )
        light_bg: str = Field("#ffffff", description="Sfondo tema chiaro")
        light_fg: str = Field("#0b0f19", description="Testo tema chiaro")
        light_grid: str = Field("rgba(0,0,0,0.15)", description="Griglia tema chiaro")

    async def chartjs(
        self,
        labels: List[str],
        datasets: List[Dict[str, Any]],
        chart_type: Literal[
            "line", "bar", "pie", "doughnut", "radar", "polarArea"
        ] = "line",
        title: Optional[str] = "Chart",
        show_legend: bool = True,
        stacked: bool = False,
        y_begin_at_zero: bool = True,
        options_json: Optional[str] = None,
    ) -> HTMLResponse:
        """
        Genera un grafico Chart.js incorporato in chat.
        :param labels: Etichette (asse X o categorie)
        :param datasets: Serie dati [{label, data, (optional) borderColor, backgroundColor, fill, borderWidth}]
        :param chart_type: Tipo grafico Chart.js
        :param title: Titolo
        :param show_legend: Mostra legenda
        :param stacked: Impilato (line/bar)
        :param y_begin_at_zero: Forza zero su Y (line/bar)
        :param options_json: Opzioni Chart.js add-on (JSON string) – merge shallow
        """
        if not isinstance(labels, list) or not labels:
            return self._inline(
                "Nessuna label fornita. Passa labels=['Gen','Feb',...].", title
            )
        if not isinstance(datasets, list) or not datasets:
            return self._inline(
                "Nessun dataset fornito. Passa datasets=[{label:'A',data:[...]},...].",
                title,
            )

        # Pulizia minima: assicura chiavi standard
        cleaned = []
        for d in datasets:
            if not isinstance(d, dict):
                continue
            cleaned.append(
                {
                    "label": d.get("label", "Serie"),
                    "data": d.get("data", []),
                    "fill": bool(d.get("fill", False)),
                    "borderWidth": int(d.get("borderWidth", 2)),
                    **({"borderColor": d["borderColor"]} if "borderColor" in d else {}),
                    **(
                        {"backgroundColor": d["backgroundColor"]}
                        if "backgroundColor" in d
                        else {}
                    ),
                }
            )
        if not cleaned:
            return self._inline("Datasets non validi.", title)

        base_options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": show_legend},
                "title": {"display": bool(title), "text": title},
                "tooltip": {"enabled": True},
            },
            "scales": {},
        }
        if chart_type in ("line", "bar"):
            base_options["scales"] = {
                "x": {"stacked": stacked},
                "y": {"stacked": stacked, "beginAtZero": y_begin_at_zero},
            }

        if options_json:
            try:
                override = json.loads(options_json)
                # merge shallow
                for k, v in override.items():
                    base_options[k] = v
            except Exception:
                pass

        config = {
            "type": chart_type,
            "data": {"labels": labels, "datasets": cleaned},
            "options": base_options,
        }

        # HTML con Chart.js, colori automatici, download PNG, toggle tema
        html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title or "Chart")}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: {self.valves.dark_bg}; --fg: {self.valves.dark_fg}; --grid: {self.valves.dark_grid};
    }}
    .light {{
      --bg: {self.valves.light_bg}; --fg: {self.valves.light_fg}; --grid: {self.valves.light_grid};
    }}
    body {{
      margin: 0; padding: 0; background: var(--bg); color: var(--fg);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    }}
    .wrap {{ padding: 8px 12px 14px; }}
    .toolbar {{ display:flex; gap:8px; align-items:center; margin-bottom:8px; }}
    .btn {{
      border:1px solid rgba(127,127,127,.4); background: transparent; color: var(--fg);
      padding:6px 10px; border-radius:8px; cursor:pointer;
    }}
    .frame {{
      position:relative; width: {self.valves.canvas_width}; height: {self.valves.canvas_height}px;
      background: transparent; border-radius:12px;
    }}
    canvas {{ width:100% !important; height:100% !important; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="toolbar">
      <strong style="flex:1">{html.escape(title or "Chart")}</strong>
      <button id="themeBtn" class="btn" title="Toggle theme">Toggle Theme</button>
      <button id="dlBtn" class="btn" title="Scarica PNG">Download PNG</button>
    </div>
    <div class="frame"><canvas id="owuiChart"></canvas></div>
  </div>

  <script>
    // Colori automatici (HSL) se mancanti
    function autoColor(i, total) {{
      const hue = (i * (360/Math.max(total,1))) % 360;
      return {{
        borderColor: `hsl(${{hue}} 70% 45%)`,
        backgroundColor: `hsl(${{(hue+6)%360}} 70% 55% / 0.25)`
      }};
    }}

    const cfg = {json.dumps(config, ensure_ascii=False)};
    const ctx = document.getElementById('owuiChart');

    (cfg.data.datasets || []).forEach((d, i) => {{
      const c = autoColor(i, cfg.data.datasets.length);
      if (!d.borderColor) d.borderColor = c.borderColor;
      if (!d.backgroundColor) d.backgroundColor = c.backgroundColor;
      if (cfg.type === 'line' && (d.tension === undefined)) d.tension = 0.25;
    }});

    function applyThemeToOptions(opts) {{
      const gridColor = getComputedStyle(document.body).getPropertyValue('--grid').trim();
      const color = getComputedStyle(document.body).getPropertyValue('--fg').trim();
      if (opts.scales) {{
        for (const k of Object.keys(opts.scales)) {{
          const s = opts.scales[k];
          s.ticks = Object.assign({{}}, s.ticks || {{}}, {{ color }});
          s.grid  = Object.assign({{}}, s.grid  || {{}}, {{ color: gridColor }});
        }}
      }}
      opts.plugins = Object.assign({{}}, opts.plugins || {{}});
      opts.plugins.legend = Object.assign({{}}, opts.plugins.legend || {{}}, {{ labels: {{ color }} }});
      opts.plugins.title  = Object.assign({{}}, opts.plugins.title  || {{}}, {{ color }});
    }}

    applyThemeToOptions(cfg.options);
    let chart = new Chart(ctx, cfg);

    // Download PNG
    document.getElementById('dlBtn').addEventListener('click', () => {{
      const url = chart.toBase64Image('image/png', 1.0);
      const a = document.createElement('a');
      a.href = url;
      a.download = (cfg.options?.plugins?.title?.text || 'chart') + '.png';
      a.click();
    }});

    // Toggle Theme
    let light = false;
    document.getElementById('themeBtn').addEventListener('click', () => {{
      light = !light;
      document.body.classList.toggle('light', light);
      applyThemeToOptions(cfg.options);
      chart.destroy();
      chart = new Chart(ctx, cfg);
    }});
  </script>
</body>
</html>"""

        return HTMLResponse(content=html_doc, headers={"Content-Disposition": "inline"})

    # Helpers
    def _inline(self, msg: str, title: Optional[str]) -> HTMLResponse:
        html_doc = (
            f"<!doctype html><html><head><meta charset='utf-8'/>"
            f"<title>{html.escape(title or 'Chart')}</title></head>"
            f"<body style='font-family: sans-serif; padding:12px'>{msg}</body></html>"
        )
        return HTMLResponse(content=html_doc, headers={"Content-Disposition": "inline"})
