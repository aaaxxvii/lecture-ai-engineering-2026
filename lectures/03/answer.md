# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
    - 質問は「AIE2026の講座で使う「lecNN-start タグ」とは何ですか？」、モデルはどちらも `gemini-3.5-flash-lite`。用語集の定義は「各回の演習開始時点のコードに付けている Git タグ（例：lec03-start）。前の回が終わっていなくても、このタグからブランチを作ればその回の演習を始められる」。
    - 素のLLM（`app.ask`）：
        - 1回目は「Git のタグで、講義の開始地点を示す目印」と、おおむね当たった。ただし講座名を「AIエンジニア育成講座など」とぼかし、使い方を `git checkout lec03-start` と書いた。課題の手順は `git switch -c lec03 lec03-start`（ブランチを作ってから作業する）なので、細部は推測だった。最後は「教材の目次のようなもの」とまとめ、定義からずれた。
        - 別の回に同じ質問をすると「コードの中に書く `# === lec01-start ===` というコメントの目印」と、まったく違う答えになった。
    - エージェント（`app.agent`）：`search_glossary` で用語集を引き、定義どおりに答えた。最後に「関係する回：第1回」と書いた。
    - 素のLLMは、たまたま当たることもあるが、**当たっているかどうかを答えだけでは見分けられない**。エージェントの答えは `--trace` で根拠（ツールの結果）をたどれる。
- `--trace` で見えたツール呼び出し（ツール名と引数）：
    - 「LoRAとQLoRAの違いは？」：`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` を、**1回の応答の中で同時に**呼んだ。docstring の「query には調べたい用語を1つだけ入れる」に従い、用語を分けて検索していた。
    - 「lecNN-start タグ」：`search_glossary({'query': 'lecNN-start タグ'})` を1回。
    - 追加で、性質の違う3つの質問を試した。
        - 「こんにちは」：ツールを呼ばなかった。`INSTRUCTIONS` は「用語や講座に固有のことを答える前に」用語集を確認する、という指示なので、あいさつには使わない。**ツールを使うかどうかはモデルが決めている。**
        - 「第5回では何を学ぶ？そこに出てくる用語を1つ選んで詳しく説明して」：`get_lecture_summary({'lecture': 5})` → `search_glossary({'query': 'MCP'})` の順に呼んだ。第5回の要点を読むまで、どの用語を調べるか決められないため、2つを順番に呼んだ。
        - 「Transformerとは何ですか？」：`search_glossary({'query': 'Transformer'})` が「見つかりませんでした」を返した（用語集に Transformer はない）。モデルは「用語集には登録されていない」と正しく伝えたが、回答の最後に根拠のない「（第1回など）」を付けた。`INSTRUCTIONS` の「推測で断定しない」と「回答の最後に関係する回を示す」がぶつかり、後者を優先して回をでっち上げたと考えられる。
- 1つの質問での LLM 呼び出し回数（`requests`）：
    - 「lecNN-start タグ」「LoRAとQLoRA」：2。LoRA/QLoRA はツールを2回呼んだが、同じ応答の中で同時に頼んだので `requests` は増えず、`tool_calls=2` になった。
    - 「こんにちは」：1。「第5回＋用語」：3。
    - まとめると、`requests` は「ツールの往復の回数 ＋ 1（最後の回答）」で、呼んだツールの個数ではない。
    - 入力トークンは、こんにちは 310 / lecNN-start 783 / LoRA・QLoRA 1196 / 第5回＋用語 2492（`make_quiz` を追加する前）。素のLLMは同じ質問で 23 だった。ツールを使わない「こんにちは」でも 310 あるのは、`INSTRUCTIONS` とツールの説明が毎回送られるため。往復が増えるほど多いのは、LLM を呼ぶたびにそれまでの会話（ツールの結果を含む）を全部送り直すため。
- 追加したツールと、docstring に書いた説明：
    - `make_quiz(lecture: int) -> str`（[app/tools.py](../../app/tools.py)）。`load_glossary()` から `lecture` が一致する用語に絞り、`random.choice` で1つ選んで、`{"question": ..., "answer": ...}` を JSON の文字列で返す。該当する用語がない回（第4回など）には、その旨のメッセージを返す。[app/agent.py](../../app/agent.py) で `agent.tool_plain(tools.make_quiz)` として登録した。
    - docstring：
      「指定した回（1始まりの整数）の用語から1つを選び、確認問題と答えを返す。『第2回の確認問題を出して』のように、学習者が理解度を確かめる問題を求めた時に使う。学習者には question だけを見せ、answer は学習者が答えた後か、求められた時に示すこと。」
    - 登録前は `--list-tools` で「モデルに見えているツール: 2 個」、登録後は3個になった。tools.py に関数を書いただけではモデルに伝わらず、`tool_plain` で登録して初めて、ツールの説明がモデルに送られる。
    - 「第2回の内容から確認問題を1問出して」→ `make_quiz({'lecture': 2})` が呼ばれ、「過学習とはどのような状態のことですか？」のように問題だけを出し、答えは伏せた。
    - 確かめたこと：
        - モデルが `lecture="2"`（文字列）で呼ぶと、Pydantic AI が型ヒントを見て整数の 2 に変換し、そのまま実行された。`"abc"` のように整数にできない値では関数は実行されず、「Input should be a valid integer」というエラーがモデルに差し戻された（偽のモデル `FunctionModel` で確認）。
        - docstring から「answer は学習者が答えた後か、求められた時に示すこと」を消しても、2回とも答えを伏せた（消さない場合も2回とも伏せた）。`INSTRUCTIONS` の「宿題の答えそのものは書かず、考え方のヒントで導く」や、確認問題では答えを伏せるという一般的な常識が効いていると考えられる。試した回数が少ないので、はっきりしたことは言えない。
        - `make_quiz` の追加後、ツールを使わない「lecNN-start タグ」の質問でも、入力トークンが 783 → 1001 に増えた（+218）。`requests=2` なので、1回あたり約109トークン。ツールの説明は、使うかどうかに関係なく毎回送られる。
    - `uv run python -m pytest -q`：11 passed（既存のテスト）。

## 宿題

- 取り組んだレベル：発展（a）
- やったこと：
    - Google ADK（`google-adk==2.13.0`）を依存グループ `adk` に追加した（`uv add --group adk "google-adk==2.13.0"`）。固定済みの `google-genai==2.31.0` のまま入った。
    - 同じエージェントを ADK で作り直した（[adk_agents/aie_agent/agent.py](../../adk_agents/aie_agent/agent.py)）。フレームワーク以外の条件をそろえるため、`INSTRUCTIONS`・ツール関数・モデル名は Pydantic AI 版から書き写さずに import した。

      ```python
      root_agent = LlmAgent(
          name="aie_agent",
          model=MODEL,
          instruction=INSTRUCTIONS,
          tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
      )
      ```

    - `PYTHONPATH=. uv run --group adk adk web adk_agents` で起動し、ブラウザから質問した。
    - 演習と同じ3つの質問を両方のエージェントに投げ、ツール呼び出し・`requests`・トークン数を比べた。
- 結果：
    - 書き方の比較

      | | Pydantic AI | ADK |
      |---|---|---|
      | エージェントを作る | `Agent(instructions=...)` | `LlmAgent(name=..., model=..., instruction=..., tools=[...])` |
      | モデルを決めるタイミング | 実行するとき（`run_sync(..., model=...)`） | 作るとき |
      | ツールの登録 | `agent.tool_plain(関数)` を1つずつ | `tools=[関数, ...]` でまとめて |
      | ツールの説明の出どころ | docstring と型ヒント | 同じ |
      | 名前 | なし | `name` が必須（複数エージェントを組み合わせる前提のため） |
      | 実行・トレース表示 | `main` と `print_trace` を自分たちで書いている | `adk web` に最初から含まれる |
      | ファイルの置き方 | 自由 | `エージェント名/__init__.py` と `agent.py` の `root_agent` という決まりがある |

    - 同じ質問への結果（モデルはどちらも `gemini-3.5-flash-lite`）

      | 質問 | ツール呼び出し（両方同じ） | requests | 入力トークン（Pydantic AI / ADK） | 出力トークン（Pydantic AI / ADK） |
      |---|---|---|---|---|
      | lecNN-start タグとは | `search_glossary('lecNN-start タグ')` | 2 / 2 | 1001 / 1127（+126） | 111 / 123 |
      | LoRA と QLoRA の違い | `search_glossary('LoRA')`, `search_glossary('QLoRA')` を同時に | 2 / 2 | 1414 / 1538（+124） | 185 / 210 |
      | 第2回の確認問題 | `make_quiz(lecture=2)` | 2 / 2 | 940 / 1101（+161） | 64 / 64 |

        - 3問とも、呼んだツール・引数・`requests` は同じだった。
        - ADK は入力トークンが毎回 124〜161（9〜17%）多かった。モデルに送られるシステムプロンプトを取り出すと、ADK は `INSTRUCTIONS` の末尾に `You are an agent. Your internal name is "aie_agent".` という一文を自動で足していた。さらに、ツールの戻り値を `{'result': '...'}` という形に包んでモデルに返していた。どちらも LLM を呼ぶたびに送られる。
    - `adk web` での見え方
        - `--trace` で見ていたツール名・引数・結果は、画面のイベント一覧に、ユーザーの質問 → ツール呼び出し → ツールの結果 → 回答の順で並ぶ。イベントをクリックすると、トークン数などの詳細が見られる。
        - LLM の呼び出しとツールの実行が、それぞれ時間付きのトレースとして記録される。エージェントと3つのツールの関係を示す図も自動で作られる。
        - 会話は `adk_agents/aie_agent/.adk/session.db` に保存され、再起動しても残る。
    - つまずいた点：`adk web` はリポジトリ直下を import の検索先に入れないので、`PYTHONPATH=.` を付けないと `from app import ...` が `No module named 'app'` で失敗する。API キーは、ADK がリポジトリ直下の `.env` を自動で読んだ（Pydantic AI 版では `uv run --env-file .env` で渡した）。
- 気づき・疑問：
    - 同じ指示・同じツール関数・同じモデルなら、どちらのフレームワークでも、モデルの動き（どのツールを、どの引数で、何回呼ぶか）は変わらなかった。エージェントの振る舞いを決めているのは、フレームワークよりも、指示とツールの説明文だと分かった。
    - 違いが出たのは「フレームワークがモデルに黙って足すもの」だった。ADK のシステムプロンプトに足される一文や、戻り値の包み方は、自分のコードのどこにも書いていない。トークン数を比べなければ気づかなかった。
    - 書く量は ADK のほうが少なかった（`LlmAgent` を1つ作るだけ）。実行やトレース表示を `adk web` が引き受けてくれるため。その代わり、ファイルの置き方や `root_agent` という名前などの決まりに従う必要がある。Pydantic AI は、自分で書く部分が多い分、どう実行するかを自由に決められる（テストで偽のモデルに差し替える、など）。
    - 疑問：ADK が自動で足す一文は消せるのか。消した場合、モデルの動きは変わるのか。
