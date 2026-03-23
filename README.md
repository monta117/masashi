# Autonomous Research OS v3.0

マルチエージェント型特許自動生成パイプライン。

## セットアップ

1. `.env` に以下を設定:
   ```
   GEMINI_API_KEY=your_key
   GITHUB_TOKEN=your_token
   GITHUB_REPO=username/repo
   ```

2. 実行:
   ```bash
   python autonomous_research_os.py
   ```

## パイプライン概要

| フェーズ | 内容 |
|---------|------|
| Phase 1 RAG | arXiv論文取得 + GitHubからfailure_log.md読込 |
| Phase 2 推論 | Agent 1(科学者) → Agent 2(弁理士) → Agent 3(MIエンジニア) |
| Phase 3 評価 | Agent 4(CSO)が100点満点で採点 |
| Phase 4 出力 | スコア80以上 → GitHub Issue自動起票 |
