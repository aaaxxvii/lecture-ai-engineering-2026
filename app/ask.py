"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする

回答のあとも続けて質問できる（会話履歴を保つ）。空行か Ctrl+D で終了する。

ツールを持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import time

from google import genai
from google.genai import chats, errors, types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def new_chat(client: genai.Client, temperature: float | None = None) -> chats.Chat:
    # temperature を省略した場合はモデルの既定値を使う
    config = types.GenerateContentConfig(temperature=temperature)
    # chat はやり取りを履歴として保持し、送信のたびに履歴ごとモデルに渡す
    return client.chats.create(model=MODEL, config=config)


def ask(chat: chats.Chat, question: str) -> str:
    start = time.perf_counter()
    response = chat.send_message(question)
    elapsed = time.perf_counter() - start
    print(f"[応答時間] {elapsed:.2f} 秒")

    # 入力（プロンプト）と出力（応答）のトークン数を表示する
    # 履歴ごと送るので、続けて質問するほど入力トークン数が増える
    usage = response.usage_metadata
    if usage is not None:
        print(f"[入力トークン] {usage.prompt_token_count}")
        print(f"[出力トークン] {usage.candidates_token_count}")
        # 回答の前にモデルが内部で考えた分（出力トークンとは別に数えられる）
        print(f"[思考トークン] {usage.thoughts_token_count or 0}\n")

    return response.text


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--temperature", type=float, default=None, help="0.0〜2.0（省略時はモデルの既定値）"
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    if args.temperature is not None:
        print(f"[temperature] {args.temperature}")

    # client は main で持ち続ける（破棄されると通信が閉じ、chat から送信できなくなる）
    client = genai.Client(api_key=get_api_key())
    chat = new_chat(client, args.temperature)
    question = args.question
    while question:
        print(f"[質問] {question}\n")
        try:
            print(ask(chat, question) + "\n")
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            raise SystemExit(1)
        try:
            question = input("続けて質問（空行で終了）> ").strip()
        except EOFError:
            break


if __name__ == "__main__":
    main()
