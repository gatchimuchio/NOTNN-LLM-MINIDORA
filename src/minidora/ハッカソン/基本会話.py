from __future__ import annotations

import re


基本会話モジュール版 = "basic-chat-v0.1"


class 基本会話モジュール:
    def 応答候補(self, text: str) -> str | None:
        normalized = re.sub(r"\s+", "", text or "").strip().casefold()
        if not normalized:
            return "入力が空です。質問または依頼を入力してください。"
        if normalized in {"こんにちは", "こんばんは", "おはよう", "おはようございます", "hello", "hi"}:
            return "こんにちは。ミニドラです。ニュースの取得、直前内容の要約、基本的な質問への応答ができます。"
        if "何ができ" in normalized or "できること" in normalized or "機能" == normalized:
            return "ニュース取得、直前応答の要約、会話文脈の保持、基礎ミニドラへの一般質問、各応答の追跡情報表示に対応しています。"
        if normalized in {"ありがとう", "ありがとうございます", "thx", "thanks", "thankyou"}:
            return "どういたしまして。"
        if normalized in {"あなたは誰", "誰", "自己紹介", "ミニドラとは"}:
            return "ミニドラです。非ニューラルなMINIDORA Coreに、ハッカソン用の会話・ニュース・要約・監査モジュールを接続しています。"
        return None
