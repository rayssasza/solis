import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

logger = logging.getLogger(__name__)

COLOR_BAR = "#F59E0B"
COLOR_BAR_HIGHLIGHT = "#EF4444"
COLOR_AVG_LINE = "#3B82F6"
COLOR_BG = "#0F172A"
COLOR_TEXT = "#F8FAFC"
COLOR_GRID = "#334155"

def generate_30day_chart(
    data: list[dict[str, Any]],
    output_dir: Optional[str] = None,
    prefix: str = "usina"
) -> str:
    if not data:
        raise ValueError("Dados insuficientes para gerar o gráfico.")

    dates = [d["date"] for d in data]
    values = [d["energy_kwh"] for d in data]
    avg_energy = sum(values) / len(values) if values else 0

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bar_colors = [
        COLOR_BAR_HIGHLIGHT if v < avg_energy * 0.5 else COLOR_BAR
        for v in values
    ]
    bars = ax.bar(
        range(len(dates)),
        values,
        color=bar_colors,
        width=0.65,
        zorder=3,
        alpha=0.9,
    )

    ax.axhline(
        avg_energy,
        color=COLOR_AVG_LINE,
        linewidth=1.8,
        linestyle="--",
        zorder=4,
        label=f"Média: {avg_energy:.1f} kWh",
    )

    if len(values) <= 31:
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    f"{val:.0f}",
                    ha="center",
                    va="bottom",
                    color=COLOR_TEXT,
                    fontsize=7.5,
                    fontweight="bold",
                )

    short_labels = [
        datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m")
        for d in dates
    ]
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(
        short_labels,
        rotation=45,
        ha="right",
        fontsize=8.5,
        color=COLOR_TEXT,
    )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=9)
    ax.set_ylabel("Geração (kWh)", color=COLOR_TEXT, fontsize=10, labelpad=10)

    ax.yaxis.grid(True, color=COLOR_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[:].set_visible(False)

    title_date = datetime.now().strftime("%d/%m/%Y")
    ax.set_title(
        f"Geração de Energia - Mês Anterior | Relatório gerado dia {title_date}",
        color=COLOR_TEXT,
        fontsize=13,
        fontweight="bold",
        pad=16,
    )
    legend = ax.legend(
        loc="upper right",
        framealpha=0.3,
        labelcolor=COLOR_TEXT,
        fontsize=9,
    )
    legend.get_frame().set_facecolor(COLOR_BG)

    total_kwh = sum(values)
    fig.text(
        0.5, 0.01,
        f"Total no período: {total_kwh:.1f} kWh  |  Gerado pelo Sistema de Monitoramento da Elétrica",
        ha="center",
        fontsize=8,
        color="#CCD1D9",
    )

    plt.tight_layout(rect=[0, 0.03, 1, 1])

    if output_dir is None:
        output_dir = tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)

    filename = f"solis_30dias_{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return filepath

def generate_7day_chart(
    data: list[dict[str, Any]],
    output_dir: Optional[str] = None,
    prefix: str = "usina"
) -> str:
    if not data:
        raise ValueError("Dados insuficientes para gráfico de 7 dias.")

    dates = [d["date"] for d in data]
    values = [d["energy_kwh"] for d in data]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    x = range(len(dates))
    ax.fill_between(x, values, alpha=0.25, color=COLOR_BAR)
    ax.plot(x, values, color=COLOR_BAR, linewidth=2.5, marker="o", markersize=7, zorder=3)

    for xi, val in zip(x, values):
        ax.text(xi, val + 0.8, f"{val:.1f}", ha="center", color=COLOR_TEXT, fontsize=9)

    short_labels = [
        datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in dates
    ]
    ax.set_xticks(list(x))
    ax.set_xticklabels(short_labels, color=COLOR_TEXT, fontsize=9)
    ax.tick_params(axis="y", colors=COLOR_TEXT)
    ax.set_ylabel("kWh", color=COLOR_TEXT, fontsize=9)
    ax.yaxis.grid(True, color=COLOR_GRID, linewidth=0.6)
    ax.spines[:].set_visible(False)
    ax.set_title("Geração - Últimos 7 Dias", color=COLOR_TEXT, fontsize=11, pad=12)

    plt.tight_layout()

    if output_dir is None:
        output_dir = tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)

    filename = f"solis_7dias_{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return filepath
