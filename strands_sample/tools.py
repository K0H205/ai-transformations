"""
Strands Agent サンプル用カスタムツール定義

@tool デコレータを使ってエージェントが呼び出せる関数を定義します。
関数の docstring がツールの説明としてモデルに渡されます。
"""

import datetime
import math
import json
from strands import tool


@tool
def get_current_datetime() -> str:
    """現在の日時を返す。時刻や日付に関する質問に答えるときに使用する。"""
    now = datetime.datetime.now()
    return now.strftime("%Y年%m月%d日 %H:%M:%S (%A)")


@tool
def calculate(expression: str) -> str:
    """
    数式を計算して結果を返す。
    四則演算、べき乗、平方根、三角関数などの数学的な計算に使用する。

    Args:
        expression: 計算する数式の文字列 (例: "2 + 3 * 4", "sqrt(16)", "sin(pi/2)")
    """
    # 安全のため限られた関数のみ許可
    safe_globals = {
        "__builtins__": {},
        "sqrt": math.sqrt,
        "pow": math.pow,
        "abs": abs,
        "round": round,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "pi": math.pi,
        "e": math.e,
    }
    try:
        result = eval(expression, safe_globals)  # noqa: S307
        return f"{expression} = {result}"
    except Exception as exc:
        return f"計算エラー: {exc}"


@tool
def get_weather(city: str) -> str:
    """
    指定した都市の現在の天気情報を返す（デモ用モックデータ）。

    Args:
        city: 天気を調べる都市名 (例: "東京", "大阪", "札幌")
    """
    mock_weather: dict[str, dict] = {
        "東京": {"temp": 22, "condition": "晴れ", "humidity": 55},
        "大阪": {"temp": 24, "condition": "くもり", "humidity": 62},
        "札幌": {"temp": 12, "condition": "雨", "humidity": 80},
        "福岡": {"temp": 25, "condition": "晴れ", "humidity": 58},
        "名古屋": {"temp": 23, "condition": "晴れ時々くもり", "humidity": 60},
    }
    data = mock_weather.get(city)
    if data is None:
        return f"{city} の天気データは見つかりませんでした。"
    return json.dumps(
        {"都市": city, "気温": f"{data['temp']}°C", "天気": data["condition"], "湿度": f"{data['humidity']}%"},
        ensure_ascii=False,
    )


@tool
def summarize_text(text: str, max_sentences: int = 3) -> str:
    """
    テキストを指定した文数に要約する（デモ用：先頭N文を返す簡易実装）。

    Args:
        text: 要約するテキスト
        max_sentences: 返す文の最大数 (デフォルト: 3)
    """
    sentences = [s.strip() for s in text.replace("。", "。\n").splitlines() if s.strip()]
    selected = sentences[:max_sentences]
    return "。".join(selected) + ("。" if selected else "")
